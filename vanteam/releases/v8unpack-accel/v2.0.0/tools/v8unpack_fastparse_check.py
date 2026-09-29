"""
Проверка эквивалентности ускоренного разбора исходному JsonContainerDecoder v8unpack.

Эталон — исходные методы JsonContainerDecoder, взятые до подключения ускорений, плюс толерантный
decode_file (текстовый поток, как в v8unpack_serial). Проверяемый — JsonContainerDecoder после
импорта v8unpack_serial: все ускорения разбора из V8UNPACK_DISABLE не исключённые
(fastparse, accum, fastbrace). Каждый файл разбирается обоими, результаты (данные или тип и текст
исключения) сравниваются. Для файлов из списка «тяжёлых» печатается время обоих разборов.

Запуск: python v8unpack_fastparse_check.py <каталог decode_stage_1> <случайных файлов> [тяжёлый файл ...]
Каталог обходится рекурсивно. Код возврата 0 — расхождений нет, 1 — есть.
"""
import os
import random
import sys
import time

from v8unpack.json_container_decoder import JsonContainerDecoder, Mode

# Исходные методы — до импорта v8unpack_serial, который подменяет их на классе
_PATCHED = ("decode_file", "decode_object", "_add_to_current_value", "decode_b64_line",
            "_decode_line_read_text_file", "_decode_line_begin_read_multi_string_value",
            "_decode_line_end_read_multi_string_value")
_ORIGINAL = {name: JsonContainerDecoder.__dict__[name] for name in _PATCHED}


def _tolerant_decode_file(self, file):
    try:
        return _ORIGINAL["decode_file"](self, file)
    except Exception:
        if getattr(self, "mode", None) == Mode.READ_TEXT_FILE:
            return self.data if self.data else ""
        raise


ReferenceDecoder = type("ReferenceDecoder", (JsonContainerDecoder,),
                        dict(_ORIGINAL, decode_file=_tolerant_decode_file))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v8unpack_serial  # noqa: E402  подключает ускорения на JsonContainerDecoder


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
    started = time.process_time()
    original = parse(ReferenceDecoder, path)
    middle = time.process_time()
    patched = parse(JsonContainerDecoder, path)
    finished = time.process_time()
    if timed:
        print(f"{os.path.basename(path)} {os.path.getsize(path) >> 10} КБ: "
              f"исходный {middle - started:.1f} с, ускоренный {finished - middle:.2f} с CPU, "
              f"совпадает={original == patched}", flush=True)
    return original == patched, original[0], middle - started, finished - middle


if __name__ == "__main__":
    folder, count = sys.argv[1], int(sys.argv[2])
    heavy = sys.argv[3:]
    paths = [os.path.join(dp, f) for dp, _dn, fn in os.walk(folder) for f in fn]
    random.seed(1)
    sample = random.sample(paths, min(count, len(paths)))
    mismatches, kinds = [], {"ok": 0, "err": 0}
    t_ref = t_new = 0.0
    for path in sample:
        same, kind, a, b = compare(path)
        kinds[kind] += 1
        t_ref += a
        t_new += b
        if not same:
            mismatches.append(os.path.relpath(path, folder))
    print(f"{v8unpack_serial.banner()}", flush=True)
    print(f"случайных файлов {len(sample)}: разобрано {kinds['ok']}, с исключением {kinds['err']}, "
          f"расхождений {len(mismatches)} {mismatches[:10]}; CPU исходный {t_ref:.1f} с, ускоренный {t_new:.1f} с",
          flush=True)
    for path in heavy:
        same, *_ = compare(path, timed=True)
        if not same:
            mismatches.append(path)
    sys.exit(1 if mismatches else 0)
