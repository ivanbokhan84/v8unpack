"""
Проверка эквивалентности ускоренного разборщика (v8unpack_fastparse) исходному JsonContainerDecoder.

Каждый файл разбирается двумя классами, результаты (данные или тип и текст исключения) сравниваются.
Для файлов из списка «тяжёлых» печатается время обоих разборов.

Запуск: python v8unpack_fastparse_check.py <каталог decode_stage_1\\1> <случайных файлов> [тяжёлый файл ...]
"""
import os
import random
import sys
import time

from v8unpack.json_container_decoder import JsonContainerDecoder
import v8unpack_fastparse as fast


class FastDecoder(JsonContainerDecoder):
    _add_to_current_value = fast.fast_add_to_current_value
    decode_object = fast.fast_decode_object


def parse(cls, path):
    folder, name = os.path.split(path)
    for code_page in ("utf-8-sig", "windows-1251"):
        try:
            with open(path, "r", encoding=code_page) as file:
                return "ok", cls(src_dir=folder, file_name=name).decode_file(file)
        except UnicodeDecodeError:
            continue
        except Exception as err:  # сравниваем и падения: тип и текст должны совпасть
            return "err", f"{type(err).__name__}: {err}"
    return "err", "code page"


def compare(path, timed=False):
    started = time.time()
    original = parse(JsonContainerDecoder, path)
    middle = time.time()
    patched = parse(FastDecoder, path)
    finished = time.time()
    if timed:
        print(f"{os.path.basename(path)} {os.path.getsize(path) >> 10} КБ: "
              f"исходный {middle - started:.1f} с, ускоренный {finished - middle:.2f} с, "
              f"совпадает={original == patched}", flush=True)
    return original == patched, original[0]


if __name__ == "__main__":
    folder, count = sys.argv[1], int(sys.argv[2])
    heavy = sys.argv[3:]
    names = [entry.name for entry in os.scandir(folder) if entry.is_file()]
    random.seed(1)
    sample = random.sample(names, min(count, len(names)))
    mismatches, kinds = [], {"ok": 0, "err": 0}
    for name in sample:
        same, kind = compare(os.path.join(folder, name))
        kinds[kind] += 1
        if not same:
            mismatches.append(name)
    print(f"случайных файлов {len(sample)}: разобрано {kinds['ok']}, с исключением {kinds['err']}, "
          f"расхождений {len(mismatches)} {mismatches[:10]}", flush=True)
    for path in heavy:
        compare(path, timed=True)
