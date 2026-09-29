"""
Один прогон распаковки заданной версией инструментов: CPU и wall по этапам, пик памяти, манифест результата.

python run_variant.py <каталог tools версии> <src.cf|cfe|epf> <out_dir> <temp_dir> <result.json>

TEMP переносится в <temp_dir> до импорта v8unpack. Ускорения v2 выключаются как обычно:
переменной V8UNPACK_DISABLE. Манифест — sha256 каждого файла и список каталогов результата;
tree_sha — sha256 от отсортированного манифеста: одинаковый tree_sha = побайтно одинаковое дерево.
"""
import hashlib
import json
import os
import sys
import tempfile
import time

TOOLS, SRC, OUT, TMP, RESULT = sys.argv[1:6]
os.makedirs(TMP, exist_ok=True)
os.environ["TMP"] = os.environ["TEMP"] = os.environ["TMPDIR"] = TMP
tempfile.tempdir = TMP
sys.path.insert(0, os.path.abspath(TOOLS))

import psutil  # noqa: E402
import v8unpack_serial  # noqa: E402  все патчи версии
from v8unpack import v8unpack as V  # noqa: E402
from v8unpack.organizer_file import OrganizerFile  # noqa: E402

proc = psutil.Process()
stages = {}


def timed(name, fn):
    def wrapper(*args, **kwargs):
        c0 = proc.cpu_times()
        w0 = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            c1 = proc.cpu_times()
            stages[name] = dict(user=round(c1.user - c0.user, 2), kernel=round(c1.system - c0.system, 2),
                                wall=round(time.perf_counter() - w0, 2))
    return wrapper


V.container_extract = timed('1_container', V.container_extract)
V.decompress_and_extract = timed('2_decompress', V.decompress_and_extract)
V.decode = timed('3_decode', V.decode)
OrganizerFile.unpack = classmethod(timed('4_organizer', OrganizerFile.unpack.__func__))


def manifest(root):
    files, dirs = {}, []
    for dp, dn, fn in os.walk(root):
        rel = os.path.relpath(dp, root)
        dirs.append(rel)
        for f in fn:
            h = hashlib.sha256()
            with open(os.path.join(dp, f), 'rb') as fh:
                for block in iter(lambda: fh.read(1 << 20), b''):
                    h.update(block)
            files[os.path.join(rel, f)] = h.hexdigest()
    return files, sorted(dirs)


if __name__ == "__main__":
    v8unpack_serial._limit_load()
    version = getattr(v8unpack_serial, '__version__', '1.0.0')
    enabled = getattr(v8unpack_serial, 'ENABLED', ['fastparse'])
    c0 = proc.cpu_times()
    w0 = time.perf_counter()
    V.extract(SRC, OUT)
    c1 = proc.cpu_times()
    wall = time.perf_counter() - w0
    peak = getattr(proc.memory_info(), 'peak_wset', 0)
    files, dirs = manifest(OUT)
    tree_sha = hashlib.sha256(json.dumps([sorted(files.items()), dirs]).encode()).hexdigest()
    res = dict(version=version, enabled=enabled, src=os.path.basename(SRC), out_dir=os.path.abspath(OUT),
               wall=round(wall, 1),
               user=round(c1.user - c0.user, 2), kernel=round(c1.system - c0.system, 2),
               cpu=round(c1.user - c0.user + c1.system - c0.system, 2), peak_mb=round(peak / 2**20),
               files=len(files), dirs=len(dirs),
               bytes=sum(os.path.getsize(os.path.join(OUT, f)) for f in files),
               tree_sha=tree_sha, stages=stages)
    with open(RESULT, 'w', encoding='utf-8') as f:
        json.dump(dict(res, manifest=files, dir_list=dirs), f, ensure_ascii=False)
    print(json.dumps(res, ensure_ascii=False), flush=True)
