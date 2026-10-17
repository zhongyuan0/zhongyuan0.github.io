"""Build /readings/ (readings in 2+ sources, with the theory tree) and /readings/more/ (single-source readings).

Usage: python3 tools/readings/build_page.py <site-root> <css-version>
"""
import os
import json, html, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from classify import TOPICS
import tree

D = os.path.dirname(os.path.abspath(__file__)) + '/'
ROOT = sys.argv[1].rstrip('/')
CSS_V = sys.argv[2]
CORE = 4

d = json.load(open(D + 'classified.json'))
courses = d['courses']

SHORT_INST = {
    'City University of Hong Kong': 'CityU', 'Wharton': 'Wharton', 'Chinese University of Hong Kong': 'CUHK',
    'Boston University': 'Boston University', 'IESE': 'IESE', 'Harvard Business School': 'HBS', 'Harvard': 'Harvard',
    'Southern California': 'USC', 'British Columbia': 'UBC', 'Texas at Dallas': 'UT Dallas', 'Alberta': 'Alberta',
    'University of Hong Kong': 'HKU', 'Hong Kong University of Science': 'HKUST', 'Columbia': 'Columbia',
    'Stanford': 'Stanford', 'Princeton': 'Princeton', 'MIT': 'MIT', 'NYU': 'NYU', 'Tennessee': 'Tennessee',
    'Berkeley': 'Berkeley',
}


def short_inst(s):
    for k, v in SHORT_INST.items():
        if k in s:
            return v
    return s


def credit(c):
    ins = c['instructor'].strip()
    if 'Lounsbury' in ins:
        return 'Lounsbury & Zhao (Oxford Bibliographies)'
    if ins.startswith('Jane Lu'):
        return 'Lu, Li, Park, Yang & Yan (CityU)'
    first = re.split(r',|;| and ', ins)[0].strip()
    name = first.split()[-1]
    if re.search(r',|;| and ', ins):
        second = re.split(r',|;| and ', ins)[1].strip().split()[-1]
        name = f'{name} & {second}'
    return f"{name} ({short_inst(c['institution'])})" if c['institution'] else name


def esc(s):
    return html.escape(s or '', quote=False)


def fmt_authors(a):
    a = [x.strip() for x in a if x and x.strip()]
    if not a:
        return ''
    if len(a) > 6:
        return esc(a[0]) + ' et al.'
    if len(a) == 1:
        return esc(a[0])
    return ', '.join(esc(x) for x in a[:-1]) + ', &amp; ' + esc(a[-1])


def fmt_ref(r):
    au = fmt_authors(r['authors'])
    y = esc(r['year']) or 'n.d.'
    t = esc(r['title']).rstrip('.')
    end = '' if t.endswith(('?', '!')) else '.'
    v = esc(r['venue']).rstrip('.')
    if r['type'] == 'book':
        body = f'<cite>{t}</cite>{end}' + (f' {v}.' if v else '')
    else:
        body = f'{t}{end}' + (f' <cite>{v}</cite>.' if v else '')
    return f'{au} ({y}). {body}' if au else f'{body} ({y}).'


readings = [r for r in d['readings'] if not r.get('drop')]
used = sorted({c for r in readings for c in r['courses']})
N = len(used)


def li(r, count=True):
    if not count:
        return f'            <li><span class="rl-ref">{fmt_ref(r)}</span></li>\n'
    label = f"Listed in {r['n']} of {N} sources"
    c = f'<span class="rl-count" title="{label}" aria-label="{label}">{r["n"]}</span>'
    return f'            <li><span class="rl-ref">{fmt_ref(r)}</span>{c}</li>\n'


def sortkey(r):
    return (-r['n'], re.sub(r'\D', '', r['year'] or '9999')[:4] or '9999', r['title'])


by_topic = collections.defaultdict(list)
for r in readings:
    by_topic[r['topic']].append(r)

names = {k: n for k, n, _ in TOPICS}
main_sections, more_sections, toc, more_toc = [], [], [], []
counts, more_counts = {}, {}
for key, name, desc in TOPICS:
    rs = sorted(by_topic.get(key, []), key=sortkey)
    core = [r for r in rs if r['n'] >= CORE]
    multi = [r for r in rs if 2 <= r['n'] < CORE]
    single = [r for r in rs if r['n'] < 2]
    counts[key] = len(core) + len(multi)
    more_counts[key] = len(single)
    if core or multi:
        src = collections.Counter(c for r in core + multi for c in r['courses'])
        src_txt = '; '.join(dict.fromkeys(credit(courses[c]) for c, _ in src.most_common()))
        toc.append(f'          <li><a href="#{key}">{esc(name)}</a> <span class="rl-n">{counts[key]}</span></li>\n')
        s = [f'      <section class="band rl-topic" id="{key}" aria-labelledby="{key}-h">\n',
             f'        <h2 class="label" id="{key}-h">{esc(name)}</h2>\n',
             '        <div class="body">\n',
             f'          <p class="rl-desc">{esc(desc)}</p>\n',
             f'          <p class="rl-src">Drawn from: {esc(src_txt)}.</p>\n']
        if core:
            s.append(f'          <h3 class="rl-h">Core readings, in {CORE} or more sources</h3>\n'
                     '          <ol class="rl-list">\n' + ''.join(li(r) for r in core) + '          </ol>\n')
        if multi:
            s.append(f'          <h3 class="rl-h">Also assigned, in 2 to {CORE - 1} sources</h3>\n'
                     '          <ol class="rl-list">\n' + ''.join(li(r) for r in multi) + '          </ol>\n')
        if single:
            s.append(f'          <p class="more"><a href="/readings/more/#{key}">{len(single)} further '
                     f'{"reading" if len(single) == 1 else "readings"} listed in one source</a></p>\n')
        s.append('        </div>\n      </section>\n\n')
        main_sections.append(''.join(s))
    if single:
        more_toc.append(f'          <li><a href="#{key}">{esc(name)}</a> <span class="rl-n">{len(single)}</span></li>\n')
        more_sections.append(
            f'      <section class="band rl-topic" id="{key}" aria-labelledby="{key}-h">\n'
            f'        <h2 class="label" id="{key}-h">{esc(name)}</h2>\n'
            '        <div class="body">\n'
            f'          <p class="rl-src"><a href="/readings/#{key}">Back to the main list for this stream</a></p>\n'
            '          <ol class="rl-list rl-list-plain">\n' + ''.join(li(r, count=False) for r in single) + '          </ol>\n'
            '        </div>\n      </section>\n\n')

srcs = sorted(used, key=lambda i: credit(courses[i]))
src_items = ''.join(
    f'            <li>{esc(courses[i]["instructor"])}. <cite>{esc(courses[i]["course"])}</cite>'
    f'{". " + esc(courses[i]["institution"]) if courses[i]["institution"] else ""}{", " + esc(courses[i]["term"]) if courses[i]["term"] else ""}.</li>\n'
    for i in srcs)

main_total = sum(counts.values())
more_total = sum(more_counts.values())
core_n = sum(r['n'] >= CORE for r in readings)


def page(path, title, desc, current_main, head, body):
    return f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title} | Zhongyuan Sun</title>
    <meta name="description" content="{desc}" />
    <link rel="canonical" href="https://zhongyuan0.github.io{path}" />
    <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
    <link rel="icon" href="/favicon.ico" sizes="any" />
    <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
    <meta name="theme-color" content="#f5f7f9" media="(prefers-color-scheme: light)" />
    <meta name="theme-color" content="#0f1620" media="(prefers-color-scheme: dark)" />
    <meta property="og:type" content="website" />
    <meta property="og:title" content="{title} | Zhongyuan Sun" />
    <meta property="og:description" content="{desc}" />
    <meta property="og:url" content="https://zhongyuan0.github.io{path}" />
    <meta property="og:image" content="https://zhongyuan0.github.io/assets/img/og-image.jpg" />
    <link rel="preload" href="/assets/fonts/crimson-pro-regular.woff" as="font" type="font/woff" crossorigin />
    <link rel="stylesheet" href="/assets/css/site.css?v={CSS_V}" />
  </head>
  <body>
    <a class="skip-link" href="#main">Skip to content</a>

    <header class="site-header">
      <div class="wrap">
        <a class="site-name" href="/">Zhongyuan Sun</a>
        <nav class="site-nav" aria-label="Main">
          <ul>
            <li><a href="/">About</a></li>
            <li><a href="/research/">Research</a></li>
            <li><a href="/cv/">CV</a></li>
            <li><a href="/readings/"{' aria-current="page"' if current_main else ''}>Readings</a></li>
          </ul>
        </nav>
      </div>
    </header>

    <main id="main" class="wrap">
      <header class="page-head">
        <div>
{head}        </div>
      </header>

{body}    </main>

    <footer class="site-footer">
      <div class="wrap">
        <p>Last updated October 2026.</p>
      </div>
    </footer>
  </body>
</html>
'''


sources_section = f'''      <section class="band" id="sources" aria-labelledby="sources-h">
        <h2 class="label" id="sources-h">Sources</h2>
        <div class="body">
          <p class="rl-desc">The syllabi and reading lists these lists are compiled from. Each stream names the sources it draws on.</p>
          <ul class="cites">
{src_items}          </ul>
        </div>
      </section>
'''

tree_names = dict(names, classics='Classical foundations', socialtheory='Social theory')
main_head = f'''          <h1>Reading lists</h1>
          <p>
            {main_total:,} readings that appear in at least two of {N} PhD syllabi and reading lists in organization theory and strategy, merged and regrouped by
            theoretical stream. The number beside each reading is how many sources assign it. Each stream opens with its core readings, the {core_n} that appear in
            {CORE} or more sources. A further {more_total:,} readings listed in only one source are on a <a href="/readings/more/">separate page</a>. Credit for
            the selections belongs to the instructors and authors listed <a href="#sources">at the end of the page</a>.
          </p>
'''
main_body = f'''      <section class="rl-tree" aria-labelledby="tree-h">
        <h2 class="visually-hidden" id="tree-h">Theory tree</h2>
        <div class="rl-tree-figure">
          {tree.svg(counts, tree_names, more_counts)}
        </div>
        <p class="rl-tree-note">
          Each box is a stream, with its number of readings; click a box to jump to its list. Arrows show which streams grew out of which; hover over an arrow
          for a one-line explanation. Social theory, the root most streams draw on, has its readings on the <a href="/readings/more/#socialtheory">further readings page</a>, since each appears in one source.
          Outside the tree: <a href="#theory">Theory and theorizing</a> ({counts.get('theory', 0)}),
          <a href="#methods">Research methods</a> ({counts.get('methods', 0)}) and <a href="#profession">The academic profession</a> ({counts.get('profession', 0)}).
        </p>
        <details class="rl-more rl-lineage">
          <summary>Lineage, in words</summary>
          <ul class="plain-list">
{tree.lineage_list(tree_names)}          </ul>
        </details>
      </section>

      <nav class="band rl-toc" aria-labelledby="toc-h">
        <h2 class="label" id="toc-h">All streams</h2>
        <ol class="body">
{''.join(toc)}        </ol>
      </nav>

{''.join(main_sections)}{sources_section}'''

more_head = f'''          <h1>Further readings</h1>
          <p>
            {more_total:,} readings that appear in only one of the {N} sources, grouped by the same streams as the <a href="/readings/">main reading lists</a>.
            The sources are credited at the end of the page.
          </p>
'''
more_body = f'''      <nav class="band rl-toc" aria-labelledby="toc-h">
        <h2 class="label" id="toc-h">Streams</h2>
        <ol class="body">
{''.join(more_toc)}        </ol>
      </nav>

{''.join(more_sections)}{sources_section}'''

os.makedirs(ROOT + '/readings/more', exist_ok=True)
a = page('/readings/', 'Reading Lists',
         f'Organization theory and strategy readings that appear in two or more of {N} PhD syllabi, grouped by theoretical stream.',
         True, main_head, main_body)
b = page('/readings/more/', 'Further Readings',
         f'Organization theory and strategy readings listed in only one of {N} PhD syllabi, grouped by stream.', False, more_head, more_body)
open(ROOT + '/readings/index.html', 'w').write(a)
open(ROOT + '/readings/more/index.html', 'w').write(b)
print('sources', N, 'main', main_total, 'core', core_n, 'more', more_total, 'bytes', len(a), len(b))
