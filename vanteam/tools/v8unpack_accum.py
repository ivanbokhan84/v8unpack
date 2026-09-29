"""
Остальные квадратичные накопления строк в v8unpack 1.2.6-1.2.13.

Источник: изменённые копии методов JsonContainerDecoder (decode_b64_line,
_decode_line_read_text_file, _decode_line_begin_read_multi_string_value,
_decode_line_end_read_multi_string_value) и OrganizerCode.unpack
(saby-integration/v8unpack, MIT, Copyright (c) 2015 infactum).

Тот же приём, что в v8unpack_fastparse: строка отвязывается от атрибута или словаря, у неё
остаётся одна ссылка, и CPython дописывает её на месте, а не копирует целиком на каждое добавление.

  1. decode_b64_line — base64 внутри скобочного файла (картинки форм), строки по 64 символа;
  2. _decode_line_read_text_file — текстовый файл: self.data += line;
  3. многострочные значения — self.current_value += line;
  4. OrganizerCode.unpack — модуль BSL собирался построчно в self.code_areas[k]['data'] += line
     (строка в словаре, копия на каждую строку модуля: модуль 3,2 МБ — 30 с). Теперь куски
     копятся в списках и склеиваются один раз, ключи и порядок областей те же.

Логика автоматов и порядок операций не меняются; меняется только способ накопления.
"""
import os

from v8unpack.ext_exception import ExtException
from v8unpack.json_container_decoder import JsonContainerDecoder, Mode
from v8unpack.organizer_code import OrganizerCode


def decode_b64_line(self, line, start_pos):
    end_pos = line.find('}')
    if end_pos >= 0:
        cur = self.current_value
        self.current_value = None
        cur += line[start_pos:end_pos]
        self.current_value = cur
        if start_pos == 1:  # b64 не разбит на строки
            self.current_value = "#" + self.current_value
        self._end_current_object()
        self.decode_object(line[end_pos + 1:])
        return True
    cur = self.current_value
    self.current_value = None
    cur += line[start_pos:-1]
    self.current_value = cur
    return False


def _decode_line_read_text_file(self, line):
    cur = self.data
    self.data = None
    cur += line
    self.data = cur


def _decode_line_begin_read_multi_string_value(self, line):
    if line.count('""') * 2 != line.count('"'):
        self.mode = Mode.BEGIN_READ_STRING_VALUE
        self.decode_object(line)
    else:
        cur = self.current_value
        self.current_value = None
        cur += line
        self.current_value = cur
        return False


def _decode_line_end_read_multi_string_value(self, line):
    if line[0] in ['{', '}']:
        self._end_value()
        self._decode_line_read_param(line)
    else:
        self.mode = Mode.BEGIN_READ_MULTI_STRING_VALUE
        cur = self.current_value
        self.current_value = None
        cur += ",\n"
        self.current_value = cur
        self._decode_line_begin_read_multi_string_value(line)


def split_code_areas(cls, file, file_name):
    """Разбор модуля на области include: тело OrganizerCode.unpack для открытого текстового потока."""
    code_areas = {'root': dict(data='')}
    chunks = {'root': []}
    _path = ['']
    _include_path = ['root']
    line = file.readline()
    while line:
        try:
            _line = line.strip()
            dynamic_directive_index = line.rfind(' //DynamicDirective')
            if dynamic_directive_index >= 0:
                if line.find('&') >= 0:
                    line = line[dynamic_directive_index + 1:]
            if _line and _line[0] == '#':
                if _line.startswith('#Область'):
                    area_type = cls.is_area(_line)
                    if area_type:
                        area_name_parts = _line[17:].strip().split(' //')
                        key = area_name_parts[0]
                        chunks[_include_path[-1]].append(line)
                        code_areas[key] = dict(data='', area_type=area_type)
                        chunks[key] = []
                        _include_path.append(key)
                        _path.append(key)
                    else:
                        chunks[_include_path[-1]].append(line)
                        _path.append('')
                elif _line.startswith('#КонецОбласти'):
                    if _path[-1]:  # кончилась include область
                        _include_path.pop()
                    _path.pop()
                    chunks[_include_path[-1]].append(line)
                else:
                    chunks[_include_path[-1]].append(line)
            else:
                chunks[_include_path[-1]].append(line)
            line = file.readline()
        except Exception as err:
            raise ExtException(parent=err, detail=f'in file {file_name} line {line}')
    for key, area in code_areas.items():
        area['data'] = ''.join(chunks[key])
    return code_areas


def organizer_code_unpack(cls, params):
    src_dir, path, file_name, dest_dir, index, descent = params
    with open(os.path.join(src_dir, path, file_name), 'r', encoding='utf-8-sig') as file:
        return split_code_areas(cls, file, file_name)


def apply():
    if not getattr(JsonContainerDecoder, "_fast_accum", False):
        JsonContainerDecoder.decode_b64_line = decode_b64_line
        JsonContainerDecoder._decode_line_read_text_file = _decode_line_read_text_file
        JsonContainerDecoder._decode_line_begin_read_multi_string_value = _decode_line_begin_read_multi_string_value
        JsonContainerDecoder._decode_line_end_read_multi_string_value = _decode_line_end_read_multi_string_value
        JsonContainerDecoder._fast_accum = True
    if not getattr(OrganizerCode, "_fast_accum", False):
        OrganizerCode.unpack = classmethod(organizer_code_unpack)
        OrganizerCode._fast_accum = True
