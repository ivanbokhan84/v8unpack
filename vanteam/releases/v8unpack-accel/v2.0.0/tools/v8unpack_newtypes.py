"""
Поддержка видов метаданных, которых нет в v8unpack (1.2.6 и 1.2.13).

v8unpack сопоставляет вид объекта по GUID класса через перечисление MetaDataTypes, а обработчик
ищет по имени как класс v8unpack.MetaDataObject.<Имя>.<Имя>. Неизвестный GUID он пропускает
с сообщением «неизвестный тип вложенных метаданных», и объекты этого вида не распаковываются.

Здесь вид добавляется в перечисление на лету (без пересоздания Enum, чтобы уже импортированные
модули видели тот же класс), а обработчик регистрируется как модуль пакета.

Виды:
  102f6202-43fa-40b0-8898-acd3876daacb: «Цвет палитры» (PaletteColor, ЦветаПалитры), с платформы 8.5.1.
  В выгрузке Конфигуратора: PaletteColors/<Имя>.xml, в EDT: src/PaletteColors/<Имя>/<Имя>.mdo.
  В УНФ 3.0.14.159 таких объектов 130. GUID в .cf отличается от кода класса EDT, как у Бота и WebSocketКлиента.
  Файл объекта: {1,{0,{3,{1,0,<uuid>},"Имя",{синоним},"комментарий",...},{4,<вид>,{<значение>},<...>}},0}.
  Заголовок с именем лежит в header_data[0][1][1], значение цвета сохраняется в JSON как есть.
"""
import sys
import types

import v8unpack.MetaDataObject as metadata_package
from v8unpack.MetaDataObject.core.Simple import Simple
from v8unpack.metadata_types import MetaDataTypes

NEW_TYPES = {
    "PaletteColor": "102f6202-43fa-40b0-8898-acd3876daacb",
}


class PaletteColor(Simple):
    @classmethod
    def get_decode_header(cls, header_data):
        return header_data[0][1][1]


HANDLERS = {"PaletteColor": PaletteColor}


def _add_enum_member(enum_cls, name, value):
    if name in enum_cls._member_map_:
        return
    member = object.__new__(enum_cls)
    member._name_ = name
    member._value_ = value
    member.__objclass__ = enum_cls
    enum_cls._member_map_[name] = member
    enum_cls._value2member_map_[value] = member
    enum_cls._member_names_.append(name)


def _register_handler(name, handler):
    module_name = f"{metadata_package.__name__}.{name}"
    if module_name in sys.modules:
        return
    module = types.ModuleType(module_name)
    setattr(module, name, handler)
    handler.__module__ = module_name
    sys.modules[module_name] = module
    setattr(metadata_package, name, module)


def apply():
    for name, guid in NEW_TYPES.items():
        _add_enum_member(MetaDataTypes, name, guid)
        _register_handler(name, HANDLERS[name])
