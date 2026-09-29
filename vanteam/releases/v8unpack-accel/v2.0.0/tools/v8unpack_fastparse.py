"""
Ускорение разборщика скобочного формата v8unpack 1.2.6-1.2.13 (JsonContainerDecoder).

Источник: fast_decode_object — изменённая копия JsonContainerDecoder.decode_object,
fast_add_to_current_value — переписанный _add_to_current_value
(saby-integration/v8unpack, MIT, Copyright (c) 2015 infactum).

Проблема 1: строковые значения (текст модуля формы, длинные описания) накапливаются посимвольно
через `self.current_value += value`. Левый операнд живёт в атрибуте объекта, поэтому CPython
не может дописать строку на месте и копирует её целиком на каждый символ: время квадратично
от длины строки. На крупных формах УНФ (ЗаказПокупателя, регламентированные отчёты) один объект
разбирался 100-200 секунд.

Проблема 2: значения вне кавычек (числа, UUID, даты) идут по одному символу: на каждый символ —
сравнения режима и вызов _add_to_current_value (в профиле УНФ 11 млн вызовов, ~47% собственного CPU).

Патч сохраняет логику автомата разбора и меняет только способ накопления:
  1. _add_to_current_value дописывает через локальную переменную, отвязав строку от атрибута,
     и CPython расширяет её на месте;
  2. в режиме чтения строки (BEGIN_READ_STRING_VALUE) текст до ближайшей кавычки берётся
     одним куском через str.find вместо цикла по символам;
  3. в режиме READ_PARAM подряд идущие обычные символы берутся одним куском до ближайшего из
     ',', '}', '"', '\\n' — ровно тех символов, которые автомат обрабатывает особо.

previous_char по-прежнему сравнивается только с '}', а кусок никогда не равен '}':
в режиме строки он заканчивается кавычкой, в READ_PARAM не содержит '}'. Поведение _end_value
не меняется.

Эквивалентность проверяется tools/v8unpack_fastparse_check.py на реальных файлах decode_stage_1.
"""
import re

from v8unpack.json_container_decoder import JsonContainerDecoder, Mode

_SPECIAL = re.compile(r'[,}"\n]')
# Члены Enum берутся один раз: доступ Mode.X через класс в 3.11 идёт через дескриптор
_READ_PARAM = Mode.READ_PARAM
_BEGIN_STR = Mode.BEGIN_READ_STRING_VALUE
_END_STR = Mode.END_READ_STRING_VALUE
_BEGIN_MULTI = Mode.BEGIN_READ_MULTI_STRING_VALUE


def fast_add_to_current_value(self, value):
    current = self.current_value
    if current is None:
        self.current_value = value
    elif isinstance(current, str):
        self.current_value = None  # у строки остаётся одна ссылка, и += расширяет её на месте
        current += value
        self.current_value = current
    else:
        self.current_value += value
    self.previous_char = value


def fast_decode_object(self, line):
    i = 0
    length = len(line)
    search = _SPECIAL.search
    while i < length:
        mode = self.mode
        if mode is _BEGIN_STR:
            quote = line.find('"', i)
            if quote < 0:
                self._add_to_current_value(line[i:])
                return
            self._add_to_current_value(line[i:quote + 1])
            self.mode = _END_STR
            i = quote + 1
            continue
        char = line[i]
        if mode is _READ_PARAM:
            if char == ',':
                self._end_value()
            elif char == '}':
                self._end_current_object()
            elif char == '"':
                if line.endswith(',"\n') and i == length - 2:
                    self.mode = _BEGIN_MULTI
                    self._add_to_current_value(line[i:])
                    return
                self.mode = _BEGIN_STR
                self._add_to_current_value(char)
            elif char == '\n':
                return
            else:
                m = search(line, i + 1)
                j = m.start() if m else length
                self._add_to_current_value(line[i:j])
                i = j
                continue
        elif mode is _END_STR:
            if char == '"':
                self.mode = _BEGIN_STR
                self._add_to_current_value(char)
            elif char == ',':
                self._end_value()
            elif char == '}':
                self._end_current_object()
            else:
                self._add_to_current_value(char)
        else:
            raise NotImplementedError(f'mode {self.mode}')
        i += 1


def apply():
    if getattr(JsonContainerDecoder, "_fast_parse", False):
        return
    JsonContainerDecoder._add_to_current_value = fast_add_to_current_value
    JsonContainerDecoder.decode_object = fast_decode_object
    JsonContainerDecoder._fast_parse = True
