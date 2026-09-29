"""
CPU разбора тяжёлых файлов decode_stage_1 цепочкой заданной версии инструментов (brace_file_read, лучший из N).

python heavy_forms.py <каталог tools версии> <повторов> <файл> [файл ...]
"""
import json
import os
import sys
import time

TOOLS, REPEAT = sys.argv[1], int(sys.argv[2])
sys.path.insert(0, os.path.abspath(TOOLS))
import v8unpack_serial  # noqa: E402,F401
from v8unpack import helper  # noqa: E402

out = dict(version=getattr(v8unpack_serial, '__version__', '1.0.0'), files={})
for path in sys.argv[3:]:
    best = None
    for _ in range(REPEAT):
        t0 = time.process_time()
        helper.brace_file_read(os.path.dirname(path), os.path.basename(path))
        dt = time.process_time() - t0
        best = dt if best is None else min(best, dt)
    out['files'][os.path.basename(path)] = dict(kb=os.path.getsize(path) >> 10, cpu=round(best, 3))
print(json.dumps(out, ensure_ascii=False))
