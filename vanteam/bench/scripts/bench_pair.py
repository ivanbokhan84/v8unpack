"""
Замер парами с чередованием: версии инструментов по очереди, N раундов, медианы, сверка деревьев.

python bench_pair.py <src> <work_dir> <rounds> <summary.json> <имя>=<каталог tools>[:<V8UNPACK_DISABLE>] ...

Пример:
  python bench_pair.py <файл.cfe> <рабочий_каталог> 3 summary.json ^
      v1.0.0=releases\\v8unpack-accel\\v1.0.0\\tools v2.0.0=tools

Каждый прогон — отдельный процесс run_variant.py; temp и out — внутри work_dir (один том: организатор v2
переносит каталог без копирования). Код возврата 1, если деревья результата у вариантов различаются.
"""
import json
import os
import statistics
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC, WORK, ROUNDS, SUMMARY = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
VARIANTS = []
for spec in sys.argv[5:]:
    name, rest = spec.split('=', 1)
    tools, _, disable = rest.partition(':')
    VARIANTS.append((name, tools, disable))

runs = {name: [] for name, _, _ in VARIANTS}
for r in range(1, ROUNDS + 1):
    order = VARIANTS if r % 2 else list(reversed(VARIANTS))  # чередование порядка между раундами
    for name, tools, disable in order:
        # без __pycache__ в каталогах поставок: tools версий запускаются прямо из releases/
        env = dict(os.environ, PYTHONIOENCODING='utf-8', V8UNPACK_DISABLE=disable, PYTHONDONTWRITEBYTECODE='1')
        result = os.path.join(WORK, f'r{r}_{name}.json')
        cmd = [sys.executable, os.path.join(HERE, 'run_variant.py'), tools, SRC,
               os.path.join(WORK, f'out_{name}'), os.path.join(WORK, f'tmp_{name}'), result]
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding='utf-8')
        line = [x for x in proc.stdout.splitlines() if x.startswith('{')]
        if proc.returncode or not line:
            print(f'СБОЙ {name} раунд {r}: код {proc.returncode}\n{proc.stderr[-2000:]}', flush=True)
            sys.exit(2)
        res = json.loads(line[-1])
        runs[name].append(res)
        print(f'раунд {r} {name}: CPU {res["cpu"]} с (user {res["user"]}, kernel {res["kernel"]}), '
              f'wall {res["wall"]} с, пик {res["peak_mb"]} МБ, дерево {res["tree_sha"][:12]}', flush=True)


def med(values):
    return round(statistics.median(values), 2)


summary = {}
for name, v in runs.items():
    stage_names = sorted(v[0]['stages'])
    summary[name] = dict(
        version=v[0]['version'], enabled=v[0]['enabled'], rounds=len(v),
        cpu=med([x['cpu'] for x in v]), user=med([x['user'] for x in v]), kernel=med([x['kernel'] for x in v]),
        wall=med([x['wall'] for x in v]), peak_mb=med([x['peak_mb'] for x in v]),
        cpu_all=[x['cpu'] for x in v], wall_all=[x['wall'] for x in v],
        stages_cpu={s: med([x['stages'][s]['user'] + x['stages'][s]['kernel'] for x in v]) for s in stage_names},
        files=v[0]['files'], dirs=v[0]['dirs'], bytes=v[0]['bytes'],
        tree_sha=sorted({x['tree_sha'] for x in v}))
trees = {sha for s in summary.values() for sha in s['tree_sha']}
out = dict(src=os.path.basename(SRC), rounds=ROUNDS, identical_trees=len(trees) == 1, variants=summary)
with open(SUMMARY, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
base = summary[VARIANTS[0][0]]['cpu']
for name, s in summary.items():
    print(f'{name}: медиана CPU {s["cpu"]} с ({(s["cpu"] / base - 1) * 100:+.0f}% к {VARIANTS[0][0]}), '
          f'wall {s["wall"]} с, пик {s["peak_mb"]} МБ, этапы {s["stages_cpu"]}', flush=True)
print('деревья одинаковые' if out['identical_trees'] else f'ДЕРЕВЬЯ РАЗЛИЧАЮТСЯ: {trees}', flush=True)
sys.exit(0 if out['identical_trees'] else 1)
