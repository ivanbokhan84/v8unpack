"""
Проверка поставок v8unpack-accel.

  python verify_release.py                 sha256 всех файлов каждой версии по её MANIFEST.json
  python verify_release.py --replay        + патчи версии поверх базовой (git apply) дают её tools побайтно
  python verify_release.py --working       + tools/ проекта побайтно равен последней версии
  python verify_release.py --build <вер>   собрать patches/, series.json и MANIFEST.json версии (для выпуска)

Состав версий — RELEASES.json. Патчи — unified diff (git diff --no-index --no-prefix), пути от корня
поставки (tools/...), применяются по порядку series.json. Код возврата 0 — всё сходится, 1 — нет.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.normpath(os.path.join(HERE, '..', '..'))
RELEASES = os.path.join(HERE, 'RELEASES.json')
# Порядок и назначение патчей версии: имя патча -> файлы tools
SERIES = {
    '2.0.0': [
        ('001-fastparse-readparam.patch', ['v8unpack_fastparse.py']),
        ('002-accum.patch', ['v8unpack_accum.py']),
        ('003-fastbrace.patch', ['v8unpack_fastbrace.py']),
        ('004-jsonwrite.patch', ['v8unpack_jsonwrite.py']),
        ('005-io.patch', ['v8unpack_io.py']),
        ('006-organizer-inplace.patch', ['v8unpack_organizer.py']),
        ('007-serial-wiring.patch', ['v8unpack_serial.py']),
        ('008-check-tool.patch', ['v8unpack_fastparse_check.py']),
        ('009-launchers.patch', ['run_unpack.py', 'v8unpack_resume.py']),
    ],
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def release_files(version_dir):
    """Все файлы поставки, кроме самого MANIFEST.json."""
    out = []
    for dp, dn, fn in os.walk(version_dir):
        dn[:] = [d for d in dn if d != '__pycache__']
        for f in fn:
            rel = os.path.relpath(os.path.join(dp, f), version_dir).replace('\\', '/')
            if rel != 'MANIFEST.json':
                out.append(rel)
    return sorted(out)


def load_releases():
    with open(RELEASES, encoding='utf-8') as f:
        return json.load(f)


def verify_manifest(version):
    vdir = os.path.join(HERE, f'v{version}')
    with open(os.path.join(vdir, 'MANIFEST.json'), encoding='utf-8') as f:
        manifest = json.load(f)['files']
    errors = []
    actual = release_files(vdir)
    for rel in sorted(set(manifest) | set(actual)):
        if rel not in manifest:
            errors.append(f'лишний файл {rel}')
        elif rel not in actual:
            errors.append(f'нет файла {rel}')
        elif sha256(os.path.join(vdir, rel)) != manifest[rel]:
            errors.append(f'sha256 не совпадает: {rel}')
    print(f'v{version}: манифест {len(manifest)} файлов — {"OK" if not errors else "ОШИБКИ"}')
    for e in errors:
        print('  ' + e)
    return not errors


def git(*args, cwd, raw=False):
    # без autocrlf: иначе git apply на Windows превращает LF-файлы в CRLF;
    # raw — вывод байтами: текстовый режим subprocess съел бы \r в патчах CRLF-файлов
    cmd = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false', *args]
    if raw:
        return subprocess.run(cmd, cwd=cwd, capture_output=True)
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding='utf-8')


def replay(version, base):
    """Патчи версии поверх tools базовой версии во временном каталоге -> побайтно tools версии."""
    vdir = os.path.join(HERE, f'v{version}')
    with open(os.path.join(vdir, 'patches', 'series.json'), encoding='utf-8') as f:
        series = json.load(f)['series']
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copytree(os.path.join(HERE, f'v{base}', 'tools'), os.path.join(tmp, 'tools'))
        for item in series:
            patch = os.path.join(vdir, 'patches', item['patch'])
            if sha256(patch) != item['sha256']:
                print(f'v{version}: sha256 патча {item["patch"]} не совпадает с series.json')
                return False
            res = git('apply', '--whitespace=nowarn', patch, cwd=tmp)
            if res.returncode:
                print(f'v{version}: {item["patch"]} не применяется: {res.stderr.strip()}')
                return False
        ok = compare_dirs(os.path.join(tmp, 'tools'), os.path.join(vdir, 'tools'))
    print(f'v{version}: {len(series)} патчей поверх v{base} — {"побайтно равно tools" if ok else "РАСХОЖДЕНИЕ"}')
    return ok


def compare_dirs(a, b):
    names_a = {f for f in os.listdir(a) if f != '__pycache__'}
    names_b = {f for f in os.listdir(b) if f != '__pycache__'}
    ok = names_a == names_b
    if not ok:
        print(f'  состав различается: {sorted(names_a ^ names_b)}')
    for name in sorted(names_a & names_b):
        with open(os.path.join(a, name), 'rb') as fa, open(os.path.join(b, name), 'rb') as fb:
            if fa.read() != fb.read():
                print(f'  различается {name}')
                ok = False
    return ok


def build(version, base):
    """Собрать patches/ из tools базовой версии и tools версии, затем MANIFEST.json."""
    vdir = os.path.join(HERE, f'v{version}')
    pdir = os.path.join(vdir, 'patches')
    shutil.rmtree(pdir, ignore_errors=True)
    os.makedirs(pdir)
    covered = set()
    series = []
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copytree(os.path.join(HERE, f'v{base}', 'tools'), os.path.join(tmp, 'a', 'tools'))
        shutil.copytree(os.path.join(vdir, 'tools'), os.path.join(tmp, 'b', 'tools'),
                        ignore=shutil.ignore_patterns('__pycache__'))
        for patch_name, files in SERIES[version]:
            data = b''
            for name in files:
                covered.add(name)
                old = f'a/tools/{name}' if os.path.exists(os.path.join(tmp, 'a', 'tools', name)) else '/dev/null'
                res = git('diff', '--no-index', '--no-prefix', '--binary', old, f'b/tools/{name}', cwd=tmp, raw=True)
                if res.returncode not in (0, 1):
                    raise SystemExit(f'git diff {name}: {res.stderr.decode("utf-8", "replace")}')
                data += res.stdout
            with open(os.path.join(pdir, patch_name), 'wb') as f:
                f.write(data)
            series.append(dict(patch=patch_name, files=[f'tools/{n}' for n in files],
                               sha256=sha256(os.path.join(pdir, patch_name))))
    changed = {f for f in os.listdir(os.path.join(vdir, 'tools')) if f != '__pycache__'}
    base_files = {f for f in os.listdir(os.path.join(HERE, f'v{base}', 'tools')) if f != '__pycache__'}
    for name in sorted(changed | base_files):
        if name in covered:
            continue
        a = os.path.join(HERE, f'v{base}', 'tools', name)
        b = os.path.join(vdir, 'tools', name)
        if not (os.path.exists(a) and os.path.exists(b) and open(a, 'rb').read() == open(b, 'rb').read()):
            raise SystemExit(f'{name} изменён, но не входит ни в один патч SERIES')
    with open(os.path.join(pdir, 'series.json'), 'w', encoding='utf-8') as f:
        json.dump(dict(base=base, version=version, series=series), f, ensure_ascii=False, indent=2)
    write_manifest(version)


def write_manifest(version):
    vdir = os.path.join(HERE, f'v{version}')
    files = {rel: sha256(os.path.join(vdir, rel)) for rel in release_files(vdir)}
    with open(os.path.join(vdir, 'MANIFEST.json'), 'w', encoding='utf-8') as f:
        json.dump(dict(version=version, files=files), f, ensure_ascii=False, indent=2)
    print(f'v{version}: MANIFEST.json — {len(files)} файлов')


def main(argv):
    releases = load_releases()
    if '--build' in argv:
        version = argv[argv.index('--build') + 1]
        rel = next(r for r in releases['releases'] if r['version'] == version)
        if rel.get('base'):
            build(version, rel['base'])
        else:
            write_manifest(version)
        return 0
    ok = True
    for rel in releases['releases']:
        ok &= verify_manifest(rel['version'])
        if '--replay' in argv and rel.get('base'):
            ok &= replay(rel['version'], rel['base'])
    if '--working' in argv:
        latest = releases['releases'][-1]['version']
        same = compare_dirs(os.path.join(PROJECT, 'tools'), os.path.join(HERE, f'v{latest}', 'tools'))
        print(f'tools/ проекта {"= v" + latest if same else "ОТЛИЧАЕТСЯ от v" + latest}')
        ok &= same
    print('ИТОГ: OK' if ok else 'ИТОГ: ЕСТЬ РАСХОЖДЕНИЯ')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
