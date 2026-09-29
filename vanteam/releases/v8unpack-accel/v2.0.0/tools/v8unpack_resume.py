"""
Продолжение распаковки v8unpack 1.2.6 с третьего прохода («Разбираем вложенные объекты»).

Первые два прохода (извлечение контейнера и распаковка файлов в decode_stage_1) на крупной .cf
занимают около 25 минут. Если прогон оборвался на третьем проходе, decode_stage_1 во временном
каталоге уже готов, и повторять эти проходы не нужно.

Все патчи серийной обёртки (последовательный пул, ретраи WinError, толерантность decode_file,
пониженный приоритет) подключаются импортом v8unpack_serial.

Дополнительно в журнал пишется каждый объект, разбор которого занял больше SLOW_SEC секунд,
и каждый REPORT_EVERY-й объект с памятью процесса, чтобы найти, на чём распаковка тормозит.
Раз в REPORT_EVERY объектов вызывается gc.collect(): в серийном режиме всё живёт в одном процессе.

Запуск: python v8unpack_resume.py <временный каталог с decode_stage_1> <out_dir> <журнал>
"""
import gc
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v8unpack_serial  # noqa: E402  патчи применяются при импорте

import psutil  # noqa: E402
from v8unpack import helper  # noqa: E402
from v8unpack.decoder import Decoder, decode  # noqa: E402
from v8unpack.organizer_file import OrganizerFile  # noqa: E402

SLOW_SEC = 2
REPORT_EVERY = 100

_process = psutil.Process()
_counter = 0
_log = None
_orig_decode_include = Decoder.decode_include.__func__


def _decode_include_logged(cls, params):
    global _counter
    include_type, (obj_uuid, _src_dir, _dest_dir, new_dest_path, *_rest) = params
    started = time.time()
    result = _orig_decode_include(cls, params)
    elapsed = time.time() - started
    _counter += 1
    if _counter % REPORT_EVERY == 0:
        gc.collect()
    if elapsed > SLOW_SEC or _counter % REPORT_EVERY == 0:
        rss_mb = _process.memory_info().rss >> 20
        _log.write(f"{_counter}\t{elapsed:.1f}s\t{rss_mb}MB\t{include_type}\t{new_dest_path}\t{obj_uuid}\n")
        _log.flush()
    return result


Decoder.decode_include = classmethod(_decode_include_logged)


if __name__ == "__main__":
    temp_dir, out_dir, log_path = sys.argv[1:4]
    v8unpack_serial._limit_load()
    stage1 = os.path.join(temp_dir, "decode_stage_1")
    stage3 = os.path.join(temp_dir, "decode_stage_3")
    if not os.path.isdir(stage1):
        sys.exit(f"Нет {stage1}: сначала нужен полный прогон v8unpack_serial.py")
    print(f"{v8unpack_serial.banner()}\nSTAGE1={stage1}\nDST={out_dir}\nLOG={log_path}", flush=True)
    with open(log_path, "w", encoding="utf-8") as _log:
        pool = helper.get_pool()
        decode(stage1, stage3, pool=pool, options={})
        OrganizerFile.unpack(stage3, out_dir, pool=pool, index=None)
    print("EXTRACT_DONE_OK", flush=True)
