"""Числовые разделы отчёта и статьи из summary.json парного замера (bench_pair.py)."""
import json
import re
import sys

SUMMARY, REPORT_TMPL, STYLE, REPORT_OUT, ARTICLE = sys.argv[1:6]
S = json.load(open(SUMMARY, encoding='utf-8'))
V = S['variants']
v1, v2 = V['v1.0.0'], V['v2.0.0']
R = S['rounds']
STAGES = [('1_container', 'Распаковка бинарника'), ('2_decompress', 'Вложенные контейнеры'),
          ('3_decode', 'Разбор объектов'), ('4_organizer', 'Организатор')]
ABL = [('без_fastbrace', 'без <code>fastbrace</code>'), ('без_jsonwrite', 'без <code>jsonwrite</code>'),
       ('без_inplace', 'без <code>inplace</code>'), ('без_io', 'без <code>io</code>'),
       ('без_accum', 'без <code>accum</code>')]
ABL.sort(key=lambda a: -V[a[0]]['cpu'])  # по величине вклада
SHORT = ['Бинарник', 'Контейнеры', 'Разбор', 'Организатор']
ABL_PLAIN = {k: re.sub('<[^>]+>', '', t) for k, t in ABL}


def f(x, d=2):
    return f'{x:.{d}f}'.replace('.', ',')


def pct(new, old):
    return f'{(new / old - 1) * 100:+.0f}%'.replace('-', '−')


cpu_drop = (1 - v2['cpu'] / v1['cpu']) * 100
times = v1['cpu'] / v2['cpu']
trees = S['identical_trees']
all_runs = sum(v['rounds'] for v in V.values())

tiles = f'''<div class="tiles" aria-label="Коротко">
  <div class="tile"><div class="label">CPU распаковки .cfe 3 МБ</div><div class="value">−{cpu_drop:.0f}%</div><div class="sub">2.0.0 против 1.0.0: {f(v1["cpu"])} → {f(v2["cpu"])} с, медиана {R} раундов</div></div>
  <div class="tile"><div class="label">УТ 11.5, 883 МБ, целиком</div><div class="value">8 мин 25 с</div><div class="sub">было 46,5 мин (1.0.0); 68&nbsp;177 файлов побайтно те же</div></div>
  <div class="tile"><div class="label">Тяжёлая форма 2 МБ, разбор</div><div class="value">537 с → 0,06 с</div><div class="sub">CPU, исходный v8unpack против 2.0.0</div></div>
  <div class="tile"><div class="label">Результат распаковки</div><div class="value">тот же</div><div class="sub">{"все" if trees else "НЕ все"} {all_runs} прогонов .cfe — одно дерево</div></div>
</div>'''

stage_rows = ''.join(
    f'<tr><td>{name}</td><td class="num">{f(v1["stages_cpu"][k])}</td><td class="num">{f(v2["stages_cpu"][k])}</td>'
    f'<td class="num">{pct(v2["stages_cpu"][k], v1["stages_cpu"][k])}</td></tr>' for k, name in STAGES)
cfe_table = f'''<div class="table-wrap"><table>
  <thead><tr><th>Показатель (медиана {R} раундов)</th><th class="num">1.0.0</th><th class="num">2.0.0</th><th class="num">Изменение</th></tr></thead>
  <tbody>
    <tr><td><b>CPU прогона целиком, с</b></td><td class="num"><b>{f(v1["cpu"])}</b></td><td class="num"><b>{f(v2["cpu"])}</b></td><td class="num"><b>{pct(v2["cpu"], v1["cpu"])}</b></td></tr>
    <tr><td>— user, с</td><td class="num">{f(v1["user"])}</td><td class="num">{f(v2["user"])}</td><td class="num">{pct(v2["user"], v1["user"])}</td></tr>
    <tr><td>— kernel, с</td><td class="num">{f(v1["kernel"])}</td><td class="num">{f(v2["kernel"])}</td><td class="num">{pct(v2["kernel"], v1["kernel"])}</td></tr>
    {stage_rows}
    <tr><td>Время по часам, с (шум фона)</td><td class="num">{f(v1["wall"], 1)}</td><td class="num">{f(v2["wall"], 1)}</td><td class="num">{pct(v2["wall"], v1["wall"])}</td></tr>
    <tr><td>Пик памяти, МБ</td><td class="num">{v1["peak_mb"]:.0f}</td><td class="num">{v2["peak_mb"]:.0f}</td><td class="num">{pct(v2["peak_mb"], v1["peak_mb"])}</td></tr>
  </tbody>
</table></div>
<p class="caption">CPU всех раундов: 1.0.0 — {", ".join(f(x) for x in v1["cpu_all"])} с; 2.0.0 — {", ".join(f(x) for x in v2["cpu_all"])} с.</p>'''

cfe_chart = {
    'title': 'CPU 2.0.0 относительно 1.0.0',
    'sub': f'медиана {R} раундов с чередованием; ниже 100% — быстрее',
    'max': 1.25, 'ticks': [0, 0.25, 0.5, 0.75, 1], 'ref': 1, 'refLabel': '1.0.0 = 100%', 'tipBase': 'чем у 1.0.0',
    'cats': ['Прогон целиком'] + [n for _, n in STAGES],
    'series': [{'name': '2.0.0', 'color': '--series-1',
                'values': [round(v2['cpu'] / v1['cpu'], 4)] +
                          [round(v2['stages_cpu'][k] / v1['stages_cpu'][k], 4) for k, _ in STAGES]}],
}

abl_vals = [round(V[k]['cpu'] / v2['cpu'], 4) for k, _ in ABL]
abl_chart = {
    'title': 'CPU 2.0.0 без одного ускорения',
    'sub': f'относительно 2.0.0 со всеми ускорениями; медиана {R} раундов; выше 100% — это ускорение что-то даёт',
    'max': max(1.25, max(abl_vals) * 1.1), 'ticks': [0, 0.5, 1, 1.5] if max(abl_vals) > 1.4 else [0, 0.25, 0.5, 0.75, 1, 1.25],
    'ref': 1, 'refLabel': '2.0.0 = 100%', 'tipBase': 'чем у 2.0.0 со всеми',
    'cats': [ABL_PLAIN[k] for k, _ in ABL],
    'series': [{'name': 'CPU без ускорения', 'color': '--series-2', 'values': abl_vals}],
}
abl_rows = ''.join(
    f'<tr><td style="white-space:nowrap">{name}</td><td class="num">{f(V[k]["cpu"])}</td><td class="num">{pct(V[k]["cpu"], v2["cpu"])}</td>'
    + ''.join(f'<td class="num">{f(V[k]["stages_cpu"][s])}</td>' for s, _ in STAGES) + '</tr>' for k, name in ABL)
abl_table = f'''<div class="table-wrap"><table>
  <thead><tr><th>Вариант</th><th class="num">CPU, с</th><th class="num">к 2.0.0</th>{"".join(f'<th class="num">{n}</th>' for n in SHORT)}</tr></thead>
  <tbody>
    <tr><td style="white-space:nowrap">2.0.0 со всеми</td><td class="num">{f(v2["cpu"])}</td><td class="num">—</td>{"".join(f'<td class="num">{f(v2["stages_cpu"][s])}</td>' for s, _ in STAGES)}</tr>
    {abl_rows}
    <tr><td>1.0.0</td><td class="num">{f(v1["cpu"])}</td><td class="num">{pct(v1["cpu"], v2["cpu"])}</td>{"".join(f'<td class="num">{f(v1["stages_cpu"][s])}</td>' for s, _ in STAGES)}</tr>
  </tbody>
</table></div>'''

tree_line = ('Дерево результата во всех ' + str(all_runs) + ' прогонах одно и то же (1483 файла, 598 каталогов, 30 946 055 байт, '
             f'<code>tree_sha</code> <code>{v2["tree_sha"][0][:12]}…</code>) — в том числе с любым выключенным ускорением. '
             'Оно же было у штатного v8unpack и у 1.0.0 в контрольном замере 28.09.') if trees else 'ДЕРЕВЬЯ РАЗЛИЧАЮТСЯ — см. summary.json.'

cfe_body = f'''<p>Расширение <code>ComplexBitrix24_RU_UNF.cfe</code> (3 МБ → 1483 файла), {R} раундов с чередованием, CPU процесса по этапам.</p>
{cfe_table}
<div class="chart" id="chCfe"></div>
<p>{tree_line}</p>
<p>Для сравнения — контрольный замер 28.09 (машина тоже загружена, защита в реальном времени включена): штатный <code>v8unpack -E</code> с параллельным пулом — медиана 33,46 с CPU всего дерева процессов и 218 МБ памяти, 1.0.0 — 23,51 с и 36 МБ (CPU −30%, память −84%).</p>'''

abl_body = f'''<p>Та же серия: 2.0.0, в которой переменной <code>V8UNPACK_DISABLE</code> выключено ровно одно ускорение. Насколько растёт CPU без него — столько оно и даёт на этом файле. Вклады не складываются: ускорения делят одни и те же проходы.</p>
{abl_table}
<div class="chart" id="chAbl"></div>
<p class="caption">На расширении 3 МБ мало длинных модулей, поэтому <code>accum</code> здесь почти не виден. Его эффект — на крупных конфигурациях: модуль 3,2 МБ раскладывался 30 с, теперь 0,08 с.</p>'''

accept_cfe = (f'<tr><td>Контрольный <code>.cfe</code>: 1.0.0, 2.0.0 и 2.0.0 без каждого ускорения (<code>bench_pair.py</code>)</td>'
              f'<td>{all_runs} прогонов, по 1483 файла</td><td><span class="pill">{"одно дерево" if trees else "РАЗЛИЧАЮТСЯ"}</span> '
              f'совпадает с эталоном 28.09</td></tr>')

style = open(STYLE, encoding='utf-8').read()
art = open(ARTICLE, encoding='utf-8').read()
script = art[art.index('<script>') + len('<script>'):art.index('</script>')]
script = re.sub(r"\n  barChart\('ch(Cfe|Abl)', .*?\);", '', script)
calls = f"\n  barChart('chCfe', {json.dumps(cfe_chart, ensure_ascii=False)});\n  barChart('chAbl', {json.dumps(abl_chart, ensure_ascii=False)});\n"
script_report = script.replace('\n})();', calls + '})();')

rep = open(REPORT_TMPL, encoding='utf-8').read()
rep = (rep.replace('/*STYLE*/', style).replace('<!--TILES-->', tiles).replace('<!--CFE-->', cfe_body)
          .replace('<!--ABL-->', abl_body).replace('<!--ACCEPT_CFE-->', accept_cfe).replace('/*SCRIPT*/', script_report))
open(REPORT_OUT, 'w', encoding='utf-8').write(rep)

# Статья: раздел 4 и плитки
bench_article = f'''<div id="benchBody">
<p>Сравнение парами с чередованием на одном файле — расширении 3 МБ (1483 файла), {R} раундов. Машина всё время была загружена чужими процессами, поэтому сравнение идёт по CPU процесса, а не по времени по часам. Методика, все прогоны и проверки — в <a href="Отчёт_замеров_v8unpack.html">отчёте о замерах</a>.</p>
{cfe_table}
<div class="chart" id="chCfe"></div>
<p>{tree_line}</p>
<h3>Что дало каждое ускорение</h3>
<p>В каждом варианте выключено ровно одно ускорение 2.0.0. Чем выше столбец, тем больше CPU без него — тем больше оно даёт.</p>
<div class="chart" id="chAbl"></div>
<h3>Штатный v8unpack против 1.0.0</h3>
<p>Контрольный замер 28.09 на том же файле: штатный <code>v8unpack -E</code> с параллельным пулом — 33,46 с CPU всего дерева процессов и 218 МБ памяти, 1.0.0 — 23,51 с и 36 МБ. Серийный режим экономит 30% CPU и 84% памяти: не нужны шесть процессов с копией интерпретатора и данных в каждом.</p>
<h3>Крупная конфигурация</h3>
<p>УТ 11.5.27.93 (883 МБ, 68 177 файлов): 1.0.0 — 46,5 мин (журнал 28.09), 2.0.0 — 8 мин 25 с (29.09). Организатор — 29 мин против 31 с, разбор объектов — 10,5 против 4,5 мин. Дерево 2.0.0 побайтно равно распаковке 1.0.0. Условия прогонов разные, поэтому это ориентир. Таблица по этапам — в отчёте.</p>
</div>'''
# блоки заменяются по границам разделов — повторный запуск даёт тот же файл
a0 = art.index('<div id="benchBody">')
a1 = art.index('\n\n<h2 id="real">', a0)
art = art[:a0] + bench_article + art[a1:]
t0 = art.index('<div class="tiles"')
t1 = art.index('\n\n<nav', t0)
art = art[:t0] + tiles + art[t1:]
art = re.sub(r"\n  barChart\('ch(Cfe|Abl)', .*?\);", '', art)
art = art.replace('\n})();\n</script>', calls + '})();\n</script>')
open(ARTICLE, 'w', encoding='utf-8').write(art)
print('ok', f'CPU {v1["cpu"]} -> {v2["cpu"]} ({cpu_drop:.0f}%, {times:.2f}x)', 'деревья', trees)
