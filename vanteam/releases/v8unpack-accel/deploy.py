"""
Раскатка поставки в tools\\ проектов 1С.

  python deploy.py <версия> <каталог tools> [<каталог tools> ...]   скопировать и сверить
  python deploy.py <версия> --check <каталог tools> ...              только сверить

Копирует все файлы tools/ поставки в каталог проекта. Перед копированием каждый существующий файл
сверяется с предыдущими поставками: файл, который не совпадает ни с одной из них (правили на месте),
не перезаписывается — каталог пропускается целиком. После копирования sha256 сверяются с MANIFEST.json.
Журнал — DEPLOY_<версия>.json рядом со скриптом. Код возврата 0 — все каталоги в порядке.
"""
import datetime
import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def sha256(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def tools_manifest(version):
    with open(os.path.join(HERE, f'v{version}', 'MANIFEST.json'), encoding='utf-8') as f:
        files = json.load(f)['files']
    return {k.split('/', 1)[1]: h for k, h in files.items() if k.startswith('tools/')}


def main(argv):
    version, rest = argv[0], argv[1:]
    check_only = '--check' in rest
    targets = [t for t in rest if t != '--check']
    with open(os.path.join(HERE, 'RELEASES.json'), encoding='utf-8') as f:
        known = [r['version'] for r in json.load(f)['releases']]
    target_files = tools_manifest(version)
    released = {}  # имя файла -> множество sha256 всех поставок
    for v in known:
        for name, h in tools_manifest(v).items():
            released.setdefault(name, set()).add(h)
    log = dict(version=version, date=datetime.datetime.now().isoformat(timespec='seconds'), targets=[])
    ok_all = True
    for target in targets:
        entry = dict(dir=target)
        if not check_only:
            foreign = [n for n in target_files if os.path.exists(os.path.join(target, n))
                       and sha256(os.path.join(target, n)) not in released.get(n, set())]
            if foreign:
                entry.update(status='пропущен', reason='файлы правили на месте', files=foreign)
                log['targets'].append(entry)
                ok_all = False
                print(f'ПРОПУЩЕН {target}: не совпадают ни с одной поставкой {foreign}')
                continue
            before = {n: sha256(os.path.join(target, n)) for n in target_files if os.path.exists(os.path.join(target, n))}
            entry['before'] = sorted({next((v for v in known if tools_manifest(v).get(n) == h), '?') for n, h in before.items()})
            for name in target_files:
                shutil.copyfile(os.path.join(HERE, f'v{version}', 'tools', name), os.path.join(target, name))
        bad = [n for n, h in target_files.items()
               if not os.path.exists(os.path.join(target, n)) or sha256(os.path.join(target, n)) != h]
        entry.update(status='OK' if not bad else 'РАСХОЖДЕНИЕ', mismatched=bad)
        ok_all &= not bad
        log['targets'].append(entry)
        print(f'{"OK " if not bad else "ОШИБКА"} {target}' + (f' {bad}' if bad else ''))
    if not check_only:
        with open(os.path.join(HERE, f'DEPLOY_{version}.json'), 'w', encoding='utf-8') as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    print(f'итог: {sum(t["status"] == "OK" for t in log["targets"])} из {len(targets)} в порядке')
    return 0 if ok_all else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
