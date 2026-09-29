"""
Ускорение разборщика скобочного формата v8unpack 1.2.6 (JsonContainerDecoder).

Проблема: строковые значения (текст модуля формы, длинные описания) накапливаются посимвольно
через `self.current_value += value`. Левый операнд живёт в атрибуте объекта, поэтому CPython
не может дописать строку на месте и копирует её целиком на каждый символ: время квадратично
от длины строки. На крупных формах УНФ (ЗаказПокупателя, регламентированные отчёты) один объект
разбирался 100-200 секунд.

Патч сохраняет логику автомата разбора и меняет только способ накопления:
  1. _add_to_current_value дописывает через локальную переменную, отвязав строку от атрибута,
     и CPython расширяет её на месте;
  2. в режиме чтения строки (BEGIN_READ_STRING_VALUE) текст до ближайшей кавычки берётся
     одним куском через str.find вместо цикла по символам.

previous_char по-прежнему сравнивается только с '}', а кусок никогда не равен '}':
в режиме строки он заканчивается кавычкой, поэтому поведение _end_value не меняется.

Эквивалентность проверяется tools/v8unpack_fastparse_check.py на реальных файлах decode_stage_1.
"""
from v8unpack.json_container_decoder import JsonContainerDecoder, Mode


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
    while i < length:
        mode = self.mode
        if mode == Mode.BEGIN_READ_STRING_VALUE:
            quote = line.find('"', i)
            if quote < 0:
                self._add_to_current_value(line[i:])
                return
            self._add_to_current_value(line[i:quote + 1])
            self.mode = Mode.END_READ_STRING_VALUE
            i = quote + 1
            continue
        char = line[i]
        if mode == Mode.READ_PARAM:
            if char == ',':
                self._end_value()
            elif char == '}':
                self._end_current_object()
            elif char == '"':
                if line.endswith(',"\n') and i == length - 2:
                    self.mode = Mode.BEGIN_READ_MULTI_STRING_VALUE
                    self._add_to_current_value(line[i:])
                    return
                self.mode = Mode.BEGIN_READ_STRING_VALUE
                self._add_to_current_value(char)
            elif char == '\n':
                return
            else:
                self._add_to_current_value(char)
        elif mode == Mode.END_READ_STRING_VALUE:
            if char == '"':
                self.mode = Mode.BEGIN_READ_STRING_VALUE
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
