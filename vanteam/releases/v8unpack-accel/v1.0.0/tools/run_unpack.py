# -*- coding: utf-8 -*-
"""
Детач-лаунчер распаковки контейнера 1С (.cf / .cfe / .epf) для крупных файлов.

Отвечает только за окружение: TEMP на отдельном диске, каталоги, зашитые пути,
замер времени. Все патчи (серийный пул, ретраи WinError 32/5, толерантность
decode_file, ускоренный разбор длинных строк, неизвестные виды метаданных,
пониженный приоритет) подключаются импортом tools/v8unpack_serial.py.

Почему лаунчер, а не прямой вызов v8unpack:
  - TEMP переносится ДО импорта v8unpack, иначе тысячи временных каталогов лягут на C:;
  - пути зашиваются в файл, а не передаются в командной строке (обход проблем с кириллицей);
  - процесс переживает остановку bash-задачи, если запущен отделённо.

Запуск:
    python tools/run_unpack.py <src.cf|cfe|epf> <out_dir> [temp_dir]

Отделённый запуск (переживает закрытие сессии, не наследует дескрипторы):
    powershell Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
      CommandLine='cmd /c "python <проект>\\tools\\run_unpack.py <src> <out> <temp> > <out.log> 2> <err.log>"'}

Если прогон оборвался на третьем проходе («Разбираем вложенные объекты»), первые два
повторять не нужно: python tools/v8unpack_resume.py "<TEMP>\\tmpXXXX" "<out_dir>" "<журнал>"
"""
import os
import sys
import time

# Пути задаются аргументами; для постоянной задачи их можно зашить прямо здесь
# (так обходятся проблемы с кириллицей в командной строке).
SRC = OUT = TMP = None

if len(sys.argv) > 1:
    SRC = sys.argv[1]
if len(sys.argv) > 2:
    OUT = sys.argv[2]
if len(sys.argv) > 3:
    TMP = sys.argv[3]

if not SRC or not OUT:
    sys.exit("Использование: python tools/run_unpack.py <src.cf|cfe|epf> <out_dir> [temp_dir]\n"
             "temp_dir по умолчанию — <out_dir>/../_v8unpack_tmp, выносите его на диск с запасом места.")

if not TMP:
    TMP = os.path.join(os.path.dirname(os.path.abspath(OUT)), "_v8unpack_tmp")

# TEMP переносится ДО импорта v8unpack: распаковка создаёт тысячи временных каталогов,
# на системном диске это упирается и в место, и в антивирус.
os.environ["TMP"] = os.environ["TEMP"] = os.environ["TMPDIR"] = TMP
os.makedirs(TMP, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

import tempfile  # noqa: E402  (после подмены переменных окружения)
tempfile.tempdir = TMP

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v8unpack_serial  # noqa: E402  импорт применяет все патчи
from v8unpack.v8unpack import extract  # noqa: E402


if __name__ == "__main__":
    v8unpack_serial._limit_load()
    started = time.time()
    print(f"SRC={SRC}\nOUT={OUT}\nTEMP={TMP}\nDESCENT=нет", flush=True)
    print("START", flush=True)
    # Без descent: это номер версии для инкрементальной сборки, а не глубина.
    # Любое значение включает OrganizerFileCE с побайтным сравнением O(N^2).
    extract(SRC, OUT)
    print("EXTRACT_DONE_OK, минут: %.1f" % ((time.time() - started) / 60), flush=True)
