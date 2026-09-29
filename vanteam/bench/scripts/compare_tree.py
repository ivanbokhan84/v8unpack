"""
Побайтное сравнение дерева результата с эталонным каталогом (эталон только читается).

python compare_tree.py <result.json от run_variant.py> <эталонный каталог> <report.json> [каталог результата]

Сравниваются относительные пути и sha256 всех файлов и список каталогов. Код возврата 0 — деревья
побайтно равны, 1 — есть расхождения (первые 50 — в отчёте).

Исключение — zip-архивы: v8unpack сам пересобирает dummy.zip (второй контейнер .cf) через
shutil.make_archive при каждой распаковке, и в записях архива стоит время распаковки. Архив с другим
sha256 считается равным, если у всех записей совпадают имена, CRC, размеры и байты содержимого;
такие архивы перечислены отдельно (zip_same_content).
"""
import hashlib
import json
import os
import sys
import zipfile


def zip_same_content(a, b):
    try:
        with zipfile.ZipFile(a) as za, zipfile.ZipFile(b) as zb:
            ia = [(i.filename, i.CRC, i.file_size) for i in za.infolist()]
            ib = [(i.filename, i.CRC, i.file_size) for i in zb.infolist()]
            return ia == ib and all(za.read(n) == zb.read(n) for n, _, _ in ia)
    except zipfile.BadZipFile:
        return False

RESULT, REF, REPORT = sys.argv[1:4]
with open(RESULT, encoding='utf-8') as f:
    res = json.load(f)
files, dirs = {}, []
for dp, dn, fn in os.walk(REF):
    rel = os.path.relpath(dp, REF)
    dirs.append(rel)
    for name in fn:
        h = hashlib.sha256()
        with open(os.path.join(dp, name), 'rb') as fh:
            for block in iter(lambda: fh.read(1 << 20), b''):
                h.update(block)
        files[os.path.join(rel, name)] = h.hexdigest()
got = res['manifest']
only_ref = sorted(set(files) - set(got))
only_new = sorted(set(got) - set(files))
differ = sorted(k for k in set(files) & set(got) if files[k] != got[k])
result_root = sys.argv[4] if len(sys.argv) > 4 else res['out_dir']  # каталог результата для сверки zip
zip_same = [k for k in differ if k.lower().endswith('.zip')
            and zip_same_content(os.path.join(REF, k), os.path.join(result_root, k))]
differ = [k for k in differ if k not in zip_same]
dirs_diff = sorted(set(dirs) ^ set(res['dir_list']))
tree_sha = hashlib.sha256(json.dumps([sorted(files.items()), sorted(dirs)]).encode()).hexdigest()
report = dict(reference=REF, reference_files=len(files), reference_dirs=len(dirs), reference_tree_sha=tree_sha,
              result_files=len(got), result_dirs=len(res['dir_list']), result_tree_sha=res['tree_sha'],
              only_in_reference=only_ref[:50], only_in_result=only_new[:50], different=differ[:50],
              dirs_mismatch=dirs_diff[:50], zip_same_content=zip_same,
              counts=dict(only_in_reference=len(only_ref), only_in_result=len(only_new), different=len(differ),
                          dirs_mismatch=len(dirs_diff), zip_same_content=len(zip_same)),
              identical=not (only_ref or only_new or differ or dirs_diff))
with open(REPORT, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(json.dumps({k: v for k, v in report.items() if k in ('reference_files', 'result_files', 'reference_dirs',
                                                           'result_dirs', 'counts', 'identical')},
                 ensure_ascii=False))
sys.exit(0 if report['identical'] else 1)
