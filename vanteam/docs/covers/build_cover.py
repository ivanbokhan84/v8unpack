"""Страница проекта для GitHub Pages (docs/index.html) из доказательств поставки 2.0.0.

python vanteam/docs/covers/build_cover.py        (из корня репозитория)

Данные:
- vanteam/releases/v8unpack-accel/v2.0.0/evidence/bench_cfe_summary.json — парный замер .cfe (5 раундов, 7 вариантов);
- vanteam/releases/v8unpack-accel/v2.0.0/evidence/ut_v2_result.json — УТ 11.5 целиком на 2.0.0;
- УТ 11.5 на 1.0.0 — журнал распаковки 28.09 (этапы по часам), константы ниже.
Графики — статичный встроенный SVG. Обложка docs/cover.png 1280×640 — снимок блока #cover этой страницы.
Оформление повторяет страницу ivanbokhan84/vanteam-bsl-check.
"""
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
EV = ROOT / 'vanteam' / 'releases' / 'v8unpack-accel' / 'v2.0.0' / 'evidence'
OUT = ROOT / 'docs' / 'index.html'
PAGES = 'https://ivanbokhan84.github.io/v8unpack/'
REPO = 'https://github.com/ivanbokhan84/v8unpack'
BRANCH = 'vanteam-accel-2.0'

S = json.loads((EV / 'bench_cfe_summary.json').read_text(encoding='utf-8'))
UT2 = json.loads((EV / 'ut_v2_result.json').read_text(encoding='utf-8'))
V = S['variants']
V1, V2 = V['v1.0.0'], V['v2.0.0']
STAGES = [('1_container', 'Распаковка бинарника'), ('2_decompress', 'Вложенные контейнеры'),
          ('3_decode', 'Разбор объектов'), ('4_organizer', 'Организатор')]
# УТ 11.5.27.93 на 1.0.0: журнал распаковки 28.09, минуты по часам
UT1 = {'1_container': 35 / 60, '2_decompress': 6 + 23 / 60, '3_decode': 10 + 27 / 60, '4_organizer': 29 + 1 / 60}
UT1_TOTAL = 46.5
UT2_MIN = {k: UT2['stages'][k]['wall'] / 60 for k, _ in STAGES}
UT2_TOTAL = sum(UT2_MIN.values())


def ru(x, d=2):
    return f'{x:.{d}f}'.replace('.', ',')


def minsec(m):
    s = round(m * 60)
    return f'{s // 60}:{s % 60:02d}'


def dumbbell(rows, vmax, ticks, unit, label, c1, c2, ink, muted, line, panel, width=520, left=190, step=38):
    """Гантели «было → стало»: rows = [(подпись, было, стало)]."""
    right, top = width - 24, 14
    h = top + step * len(rows) + 30
    x = lambda v: left + (right - left) * v / vmax
    out = [f'<svg viewBox="0 0 {width} {h}" role="img" aria-label="{html.escape(label)}" xmlns="http://www.w3.org/2000/svg">']
    for t in ticks:
        out.append(f'<line x1="{x(t):.1f}" y1="6" x2="{x(t):.1f}" y2="{h - 26}" stroke="var({line})" stroke-width="1"/>'
                   f'<text x="{x(t):.1f}" y="{h - 10}" text-anchor="middle" font-size="12" fill="var({muted})">{ru(t, 0)} {unit}</text>')
    for i, (name, a, b) in enumerate(rows):
        y = top + step * i + 12
        out.append(f'<text x="{left - 12}" y="{y + 4.5}" text-anchor="end" font-size="13.5" fill="var({ink})">{html.escape(name)}</text>')
        out.append(f'<line x1="{x(a):.1f}" y1="{y}" x2="{x(b):.1f}" y2="{y}" stroke="var({muted})" stroke-width="2" stroke-opacity=".55"/>')
        for v, c, who in ((a, c1, 'было'), (b, c2, 'стало')):
            out.append(f'<circle cx="{x(v):.1f}" cy="{y}" r="6.5" fill="var({c})" stroke="var({panel})" stroke-width="2">'
                       f'<title>{html.escape(name)} — {who}: {ru(v)} {unit}</title></circle>')
        lx = x(max(a, b)) + 12
        anchor = 'start'
        if lx > right - 40:
            lx, anchor = x(min(a, b)) - 12, 'end'
        out.append(f'<text x="{lx:.1f}" y="{y + 4.5}" text-anchor="{anchor}" font-size="12.5" fill="var({muted})">'
                   f'{ru(a, 1)} → {ru(b, 1)}</text>')
    out.append('</svg>')
    return ''.join(out)


def bars(rows, vmax, ticks, unit, label, width=520):
    """Горизонтальные столбцы: rows = [(подпись, значение, цвет)]."""
    left, right, top, step = 170, width - 60, 10, 34
    h = top + step * len(rows) + 28
    x = lambda v: left + (right - left) * v / vmax
    out = [f'<svg viewBox="0 0 {width} {h}" role="img" aria-label="{html.escape(label)}" xmlns="http://www.w3.org/2000/svg">']
    for t in ticks:
        out.append(f'<line x1="{x(t):.1f}" y1="4" x2="{x(t):.1f}" y2="{h - 24}" stroke="var(--grid)" stroke-width="1"/>'
                   f'<text x="{x(t):.1f}" y="{h - 8}" text-anchor="middle" font-size="12" fill="var(--faint)">{ru(t, 0)} {unit}</text>')
    for i, (name, v, c) in enumerate(rows):
        y = top + step * i
        out.append(f'<text x="{left - 12}" y="{y + 15}" text-anchor="end" font-size="13.5" fill="var(--ink)">{html.escape(name)}</text>'
                   f'<rect x="{left}" y="{y + 4}" width="{x(v) - left:.1f}" height="16" rx="4" fill="var({c})">'
                   f'<title>{html.escape(name)}: {ru(v)} {unit}</title></rect>'
                   f'<text x="{x(v) + 8:.1f}" y="{y + 16.5}" font-size="12.5" fill="var(--muted)">{ru(v)} {unit}</text>')
    out.append('</svg>')
    return ''.join(out)


cpu_drop = (1 - V2['cpu'] / V1['cpu']) * 100
SHORT = {'1_container': 'Бинарник', '2_decompress': 'Контейнеры', '3_decode': 'Разбор', '4_organizer': 'Организатор'}
hero_chart = dumbbell(
    [('Весь прогон', V1['cpu'], V2['cpu'])] + [(SHORT[k], V1['stages_cpu'][k], V2['stages_cpu'][k]) for k, _ in STAGES],
    24, [0, 6, 12, 18, 24], 'с', 'CPU по этапам распаковки: 1.0.0 против 2.0.0',
    '--h-s1', '--h-s2', '--h-ink', '--h-muted', '--h-line', '--h-panel', left=120, step=58)
ut_chart = dumbbell(
    [('Прогон целиком', UT1_TOTAL, UT2_TOTAL)] + [(n, UT1[k], UT2_MIN[k]) for k, n in STAGES],
    60, [0, 10, 20, 30, 40, 50, 60], 'мин', 'УТ 11.5 по этапам, минуты по часам: 1.0.0 против 2.0.0',
    '--s1', '--s2', '--ink', '--muted', '--grid', '--surface')
ABL = [('без_accum', 'без accum'), ('без_io', 'без io'), ('без_jsonwrite', 'без jsonwrite'),
       ('без_fastbrace', 'без fastbrace'), ('без_inplace', 'без inplace')]
abl_rows = ([('2.0.0 со всеми', V2['cpu'], '--s2')] + [(n, V[k]['cpu'], '--s2') for k, n in ABL]
            + [('1.0.0', V1['cpu'], '--s1')])
abl_chart = bars(abl_rows, 24, [0, 6, 12, 18, 24], 'с', 'CPU распаковки .cfe: 2.0.0 без одного ускорения')

stage_rows = ''.join(
    f'<tr><td>{n}</td><td class=n>{ru(V1["stages_cpu"][k])}</td><td class=n>{ru(V2["stages_cpu"][k])}</td></tr>' for k, n in STAGES)
abl_data = ''.join(f'<tr><td>{n}</td><td class=n>{ru(v)}</td><td class=n>{(v / V2["cpu"] - 1) * 100:+.0f}%</td></tr>'
                   .replace('-', '−') for n, v, _ in abl_rows)
ut_rows = ''.join(f'<tr><td>{n}</td><td class=n>{minsec(UT1[k])}</td><td class=n>{minsec(UT2_MIN[k])}</td></tr>' for k, n in STAGES)

CSS = r"""
:root {
  --ground: #f2f4f7; --surface: #ffffff; --raised: #f7f8fa; --ink: #141b24; --muted: #566270; --faint: #8a95a2;
  --line: #d9dee5; --grid: #e8ebef; --accent: #b4461b; --s1: #2a78d6; --s2: #eb6834;
  --good: #0f8a3c; --good-soft: #e2f4e8; --bad: #c53030; --bad-soft: #fbe7e7; --code: #f5f6f8;
  --sans: "Golos Text", "Segoe UI", system-ui, sans-serif; --mono: "JetBrains Mono", "Cascadia Mono", Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --ground: #0e1318; --surface: #161c23; --raised: #1b222a; --ink: #e4e9ef; --muted: #9ba7b4; --faint: #6e7a88;
    --line: #28313c; --grid: #222a33; --accent: #e3905f; --s1: #3987e5; --s2: #d95926;
    --good: #4cc47a; --good-soft: #15301f; --bad: #f07a72; --bad-soft: #3a1c1c; --code: #121820;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --ground: #0e1318; --surface: #161c23; --raised: #1b222a; --ink: #e4e9ef; --muted: #9ba7b4; --faint: #6e7a88;
  --line: #28313c; --grid: #222a33; --accent: #e3905f; --s1: #3987e5; --s2: #d95926;
  --good: #4cc47a; --good-soft: #15301f; --bad: #f07a72; --bad-soft: #3a1c1c; --code: #121820;
}
* { box-sizing: border-box; }
html, body { margin: 0; }
body { background: var(--ground); color: var(--ink); font: 16px/1.6 var(--sans); }
code, pre { font-family: var(--mono); font-variant-ligatures: none; }
a { color: var(--s1); }
/* Обложка: один тёмный вид в обеих темах и в PNG */
.hero { --h-ground: #10161d; --h-panel: #172029; --h-ink: #eef2f6; --h-muted: #9fb0c0; --h-line: #2a3642;
  --h-s1: #3987e5; --h-s2: #d95926; --h-accent: #f0a06c;
  background: radial-gradient(1200px 600px at 85% 20%, #1c2a38 0%, var(--h-ground) 60%); color: var(--h-ink);
  width: 100%; max-width: 1280px; margin: 0 auto; aspect-ratio: 2 / 1; padding: 52px 60px 44px;
  display: grid; grid-template-columns: 1fr 1.02fr; gap: 44px; align-items: stretch; overflow: hidden; position: relative; }
.hero::after { content: ""; position: absolute; inset: 0; pointer-events: none;
  background-image: linear-gradient(var(--h-line) 1px, transparent 1px), linear-gradient(90deg, var(--h-line) 1px, transparent 1px);
  background-size: 40px 40px; opacity: .18; mask-image: linear-gradient(90deg, transparent 0%, #000 55%, transparent 100%); }
.hero > * { position: relative; z-index: 1; }
.hero .left { display: grid; align-content: space-between; gap: 20px; min-width: 0; }
.kicker { font: 600 13px/1.3 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--h-accent); }
.hero h1 { margin: 14px 0 0; font: 800 50px/1.04 var(--sans); letter-spacing: -.025em; }
.hero .tag { margin: 16px 0 0; color: var(--h-muted); font-size: 19px; line-height: 1.45; max-width: 32ch; }
.hero .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
.hero .stat { border-top: 2px solid var(--h-line); padding-top: 10px; display: grid; gap: 4px; align-content: start; }
.hero .stat b { font: 800 28px/1.05 var(--sans); font-variant-numeric: tabular-nums; letter-spacing: -.01em; }
.hero .stat span { color: var(--h-muted); font-size: 13.5px; line-height: 1.35; }
.hero .right { background: var(--h-panel); border: 1px solid var(--h-line); border-radius: 16px; padding: 24px 26px 18px;
  display: grid; grid-template-rows: auto 1fr auto; gap: 10px; min-width: 0; }
.hero .right h2 { margin: 0; font: 700 17px/1.3 var(--sans); }
.hero .right .sub { color: var(--h-muted); font-size: 13px; margin-top: 2px; }
.hero .right svg { width: 100%; height: 100%; }
.hero .legend { display: flex; gap: 18px; flex-wrap: wrap; font-size: 13px; color: var(--h-muted); }
.hero .legend i, .legend2 i { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { font: 600 13px/1 var(--mono); padding: 7px 10px; border-radius: 8px; border: 1px solid var(--h-line); background: rgba(255,255,255,.03); }
.page { max-width: 1120px; margin: 0 auto; padding-inline: 20px; padding-block: 48px 72px; display: grid; gap: 56px; }
section { display: grid; gap: 18px; }
.head { display: grid; gap: 6px; max-width: 76ch; }
.eyebrow { font: 600 12px/1.2 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--accent); }
h2.t { margin: 0; font: 750 28px/1.2 var(--sans); letter-spacing: -.01em; }
.head p { margin: 0; color: var(--muted); }
.grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 480px), 1fr)); gap: 18px; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 20px 22px; display: grid; gap: 12px; align-content: start; min-width: 0; }
.card h3 { margin: 0; font: 650 17px/1.3 var(--sans); }
.card .note { color: var(--muted); font-size: 14px; margin: 0; }
.chart { overflow-x: auto; }
.chart svg { display: block; width: 100%; height: auto; min-width: 440px; }
.chart text { font-family: var(--sans); }
.legend2 { display: flex; gap: 16px; flex-wrap: wrap; font-size: 13.5px; color: var(--muted); }
details { font-size: 14px; color: var(--muted); }
details summary { cursor: pointer; }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { color: var(--muted); font-weight: 600; font-size: 12.5px; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
.tbl { overflow-x: auto; background: var(--surface); border: 1px solid var(--line); border-radius: 14px; }
pre.block { margin: 0; background: var(--code); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; overflow-x: auto; font-size: 13.5px; line-height: 1.6; }
p code, td code, li code { font-size: .88em; background: var(--code); border: 1px solid var(--line); border-radius: 4px; padding: 0 4px; }
.pill { display: inline-flex; gap: 5px; align-items: center; font: 600 12.5px/1 var(--sans); padding: 4px 8px; border-radius: 999px; white-space: nowrap; }
.pill.good { color: var(--good); background: var(--good-soft); }
.links { display: flex; flex-wrap: wrap; gap: 10px; }
.links a { text-decoration: none; font-weight: 600; padding: 9px 14px; border-radius: 10px; border: 1px solid var(--line); background: var(--surface); color: var(--ink); }
.links a:hover, .links a:focus-visible { border-color: var(--s1); outline: none; }
footer { color: var(--faint); font-size: 13px; border-top: 1px solid var(--line); padding-top: 16px; }
@media (max-width: 900px) {
  .hero { aspect-ratio: auto; grid-template-columns: 1fr; padding: 32px 22px; gap: 26px; }
  .hero h1 { font-size: 36px; }
  .hero .stats { grid-template-columns: 1fr; }
  .hero .right { min-height: 320px; }
}
"""

ARTICLE = 'vanteam/Оптимизация_распаковки_v8unpack.html'
REPORT = 'vanteam/Отчёт_замеров_v8unpack.html'
DESC = ('Обёртки над v8unpack: распаковка .cf, .cfe и .epf без Конфигуратора в разы быстрее и без сбоев на Windows, '
        'результат побайтно тот же.')

page = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>v8unpack-accel</title>
<meta name="description" content="{html.escape(DESC)}">
<meta property="og:title" content="v8unpack-accel">
<meta property="og:description" content="{html.escape(DESC)}">
<meta property="og:image" content="{PAGES}cover.png">
<meta property="og:url" content="{PAGES}">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap">
<style>{CSS}</style>
</head>
<body>
<header class="hero" id="cover">
  <div class="left">
    <div>
      <div class="kicker">Python · MIT · форк saby-integration/v8unpack</div>
      <h1>v8unpack-accel 2.0</h1>
      <p class="tag">Распаковка .cf, .cfe и .epf без Конфигуратора: в разы быстрее, без сбоев на Windows, результат побайтно тот же.</p>
    </div>
    <div class="chips"><span class="chip">json.loads вместо автомата</span><span class="chip">без копирования</span><span class="chip">серийный пул</span></div>
    <div class="stats">
      <div class="stat"><b>8:25</b><span>УТ 11.5, 883 МБ, целиком; было 46,5 мин</span></div>
      <div class="stat"><b>−{cpu_drop:.0f}%</b><span>CPU на расширении 3 МБ, медиана 5 раундов</span></div>
      <div class="stat"><b>0</b><span>расхождений: 68 177 файлов дерева, 11 130 файлов разбора</span></div>
    </div>
  </div>
  <div class="right">
    <div><h2>CPU по этапам, секунды</h2><div class="sub">расширение 3 МБ → 1483 файла, медиана 5 раундов с чередованием</div></div>
    {hero_chart}
    <div class="legend"><span><i style="background:var(--h-s1)"></i>1.0.0</span><span><i style="background:var(--h-s2)"></i>2.0.0</span></div>
  </div>
</header>
<main class="page">

<section>
  <div class="head"><div class="eyebrow">Что это</div><h2 class="t">Обёртки, а не новый распаковщик</h2>
  <p>Пакет <a href="https://github.com/saby-integration/v8unpack">v8unpack</a> 1.2.13 не изменён. Исправления и ускорения — модули в <code>vanteam/tools</code>, они подменяют методы v8unpack во время запуска. Каждое ускорение выключается переменной <code>V8UNPACK_DISABLE</code>, результат при любом наборе одинаковый.</p></div>
  <div class="links">
    <a href="{REPO}/tree/{BRANCH}/vanteam">Код и README</a>
    <a href="{ARTICLE}">Статья: как это устроено</a>
    <a href="{REPORT}">Отчёт о замерах</a>
    <a href="{REPO}/tree/{BRANCH}/vanteam/releases/v8unpack-accel">Поставки и патчи</a>
  </div>
</section>

<section>
  <div class="head"><div class="eyebrow">Замер</div><h2 class="t">Что даёт каждое ускорение</h2>
  <p>Расширение 3 МБ, пять раундов с чередованием, CPU процесса. В каждом варианте выключено ровно одно ускорение. Машина была загружена чужими процессами, поэтому сравнение идёт по CPU, а не по времени по часам. Дерево результата во всех 35 прогонах одно и то же.</p></div>
  <div class="grid2">
    <div class="card"><h3>CPU распаковки, секунды</h3><div class="chart">{abl_chart}</div>
      <div class="legend2"><span><i style="background:var(--s2)"></i>2.0.0</span><span><i style="background:var(--s1)"></i>1.0.0</span></div>
      <details><summary>Данные</summary><table><thead><tr><th>Вариант</th><th class=n>CPU, с</th><th class=n>к 2.0.0</th></tr></thead><tbody>{abl_data}</tbody></table></details></div>
    <div class="card"><h3>По этапам, CPU в секундах</h3>
      <table><thead><tr><th>Этап</th><th class=n>1.0.0</th><th class=n>2.0.0</th></tr></thead><tbody>
      <tr><td><b>Прогон целиком</b></td><td class=n><b>{ru(V1['cpu'])}</b></td><td class=n><b>{ru(V2['cpu'])}</b></td></tr>{stage_rows}
      <tr><td>Пик памяти, МБ</td><td class=n>{V1['peak_mb']:.0f}</td><td class=n>{V2['peak_mb']:.0f}</td></tr></tbody></table>
      <p class="note">Организатор больше не копирует дерево: <code>decode_stage_3</code> переносится в результат одним переименованием. Разбор скобочного формата идёт через <code>json.loads</code>, запись JSON — одной строкой.</p></div>
  </div>
</section>

<section>
  <div class="head"><div class="eyebrow">Крупная конфигурация</div><h2 class="t">УТ 11.5: 46,5 мин → 8 мин 25 с</h2>
  <p>Полная распаковка 883 МБ → 68 177 файлов, время по часам. 1.0.0 — журнал 28.09, 2.0.0 — прогон 29.09: условия разные, это ориентир. Дерево 2.0.0 побайтно равно распаковке 1.0.0.</p></div>
  <div class="grid2">
    <div class="card"><h3>По этапам, минуты</h3><div class="chart">{ut_chart}</div>
      <div class="legend2"><span><i style="background:var(--s1)"></i>1.0.0</span><span><i style="background:var(--s2)"></i>2.0.0</span></div>
      <p class="note">Код первого этапа не менялся; он медленнее, вероятно, из-за фоновой нагрузки во время прогона.</p></div>
    <div class="card"><h3>Этапы, мин:с</h3>
      <table><thead><tr><th>Этап</th><th class=n>1.0.0</th><th class=n>2.0.0</th></tr></thead><tbody>{ut_rows}
      <tr><td><b>Всего</b></td><td class=n><b>46:30</b></td><td class=n><b>{minsec(UT2_TOTAL)}</b></td></tr></tbody></table>
      <p class="note">Тяжёлая форма 2 МБ разбирается за 0,06 с CPU; исходный разборщик v8unpack — 537 с, 1.0.0 — 0,53 с.</p></div>
  </div>
</section>

<section>
  <div class="head"><div class="eyebrow">Приёмка</div><h2 class="t">Результат тот же, байт в байт</h2>
  <p>Критерии заданы до замеров. Доказательства — <code>vanteam/releases/v8unpack-accel/v2.0.0/evidence</code>.</p></div>
  <div class="tbl"><table><thead><tr><th>Проверка</th><th>Объём</th><th>Итог</th></tr></thead><tbody>
    <tr><td>Разбор против исходного <code>JsonContainerDecoder</code></td><td>400 случайных файлов и 3 тяжёлые формы</td><td><span class="pill good">0 расхождений</span></td></tr>
    <tr><td>Разбор через <code>json.loads</code> против 1.0.0</td><td>11 130 файлов двух распаковок УНФ</td><td><span class="pill good">0 расхождений</span></td></tr>
    <tr><td>Запись JSON против <code>json.dumps</code></td><td>4060 файлов УТ 11.5</td><td><span class="pill good">0 расхождений</span></td></tr>
    <tr><td>Расширение 3 МБ, все варианты</td><td>35 прогонов</td><td><span class="pill good">одно дерево</span></td></tr>
    <tr><td>УТ 11.5 против распаковки 1.0.0</td><td>68 177 файлов, 24 075 каталогов</td><td><span class="pill good">побайтно</span></td></tr>
    <tr><td>Патчи 2.0.0 поверх 1.0.0</td><td>9 патчей</td><td><span class="pill good">побайтно</span></td></tr>
  </tbody></table></div>
</section>

<section>
  <div class="head"><div class="eyebrow">Запуск</div><h2 class="t">Три команды</h2>
  <p>Python 3.11, <code>pip install v8unpack==1.2.13</code>; <code>psutil</code> нужен только для продолжения после обрыва. Не передавайте <code>--descent</code>: это номер версии для инкрементальной сборки, а не глубина.</p></div>
  <pre class="block">python vanteam/tools/check_cf.py "файл.cf"
python vanteam/tools/run_unpack.py "файл.cf" "каталог_результата" "каталог_temp"
python vanteam/tools/v8unpack_serial.py "файл.cfe" "каталог_результата"

rem выключить отдельные ускорения, результат тот же
set V8UNPACK_DISABLE=fastbrace,inplace</pre>
</section>

<footer>v8unpack-accel 2.0.0 · Ivan Bokhan · код — MIT, статьи и отчёты — CC BY 4.0 · основано на <a href="https://github.com/saby-integration/v8unpack">saby-integration/v8unpack</a> (MIT, © 2015 infactum)</footer>
</main>
</body>
</html>
"""
OUT.write_text(page, encoding='utf-8', newline='\n')
print('docs/index.html', len(page))
