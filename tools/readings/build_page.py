import os
import json, html, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from classify import TOPICS

D = os.path.dirname(os.path.abspath(__file__)) + '/'
OUT = sys.argv[1]
CORE = 4
CSS_V = sys.argv[2]

d = json.load(open(D + 'classified.json'))
courses = d['courses']
N = len(courses)

SHORT_INST = {
    'City University of Hong Kong': 'CityU', 'Wharton': 'Wharton', 'Chinese University of Hong Kong': 'CUHK', 'Boston University': 'Boston University',
    'IESE': 'IESE', 'Harvard': 'Harvard', 'Southern California': 'USC', 'British Columbia': 'UBC',
    'Texas at Dallas': 'UT Dallas', 'Alberta': 'Alberta', 'University of Hong Kong': 'HKU',
    'Hong Kong University of Science': 'HKUST',
}


def short_inst(s):
    for k, v in SHORT_INST.items():
        if k in s:
            return v
    return s


def credit(c):
    ins = c['instructor'].strip()
    if not ins:
        return 'an organization theory reading list (instructor not stated)'
    if c['instructor'].startswith('Jane Lu'):
        name = 'Lu, Li, Park, Yang & Yan'
    else:
        name = ins.split(',')[0].split(' and ')[0].split()[-1]
    return f"{name} ({short_inst(c['institution'])})"


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


def li(r):
    label = f"Listed in {r['n']} of {N} syllabi"
    count = f'<span class="rl-count" title="{label}" aria-label="{label}">{r["n"]}</span>'
    return f'              <li><span class="rl-ref">{fmt_ref(r)}</span>{count}</li>\n'


by_topic = collections.defaultdict(list)
for r in d['readings']:
    by_topic[r['topic']].append(r)

sections, toc = [], []
for key, name, desc in TOPICS:
    rs = by_topic.get(key, [])
    if not rs:
        continue
    rs.sort(key=lambda r: (-r['n'], re.sub(r'\D', '', r['year'] or '9999')[:4] or '9999', r['title']))
    core = [r for r in rs if r['n'] >= CORE]
    multi = [r for r in rs if 2 <= r['n'] < CORE]
    single = [r for r in rs if r['n'] < 2]
    src = collections.Counter(c for r in rs for c in r['courses'])
    src_txt = '; '.join(credit(courses[c]) for c, _ in src.most_common())
    toc.append(f'          <li><a href="#{key}">{esc(name)}</a> <span class="rl-n">{len(rs)}</span></li>\n')
    s = [f'      <section class="band rl-topic" id="{key}" aria-labelledby="{key}-h">\n',
         f'        <h2 class="label" id="{key}-h">{esc(name)}</h2>\n',
         '        <div class="body">\n',
         f'          <p class="rl-desc">{esc(desc)}</p>\n',
         f'          <p class="rl-src">Drawn from: {esc(src_txt)}.</p>\n']
    if core:
        s.append(f'          <h3 class="rl-h">Core readings, in {CORE} or more syllabi</h3>\n'
                 '          <ol class="rl-list">\n' + ''.join(li(r) for r in core) + '          </ol>\n')
    if multi:
        s.append(f'          <h3 class="rl-h">Also assigned, in 2 to {CORE - 1} syllabi</h3>\n'
                 '          <ol class="rl-list">\n' + ''.join(li(r) for r in multi) + '          </ol>\n')
    if single:
        s.append(f'          <details class="rl-more"{" open" if not (core or multi) else ""}>\n'
                 f'            <summary>{len(single)} more {"reading" if len(single) == 1 else "readings"} listed in one syllabus</summary>\n'
                 '            <ol class="rl-list">\n' + ''.join('  ' + li(r) for r in single) + '            </ol>\n'
                 '          </details>\n')
    s.append('        </div>\n      </section>\n\n')
    sections.append(''.join(s))

srcs = sorted(range(N), key=lambda i: credit(courses[i]))
src_items = ''.join(
    f'            <li>{esc(courses[i]["instructor"] or "Instructor not stated")}. <cite>{esc(courses[i]["course"])}</cite>'
    f'{". " + esc(courses[i]["institution"]) if courses[i]["institution"] else ""}{", " + esc(courses[i]["term"]) if courses[i]["term"] else ""}.</li>\n'
    for i in srcs)

total = len(d['readings'])
core_n = sum(r['n'] >= CORE for r in d['readings'])

page = f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Reading Lists | Zhongyuan Sun</title>
    <meta name="description" content="Readings from {N} PhD seminar syllabi in organization theory and strategy, merged and grouped by theoretical stream." />
    <link rel="canonical" href="https://zhongyuan0.github.io/readings/" />
    <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
    <link rel="icon" href="/favicon.ico" sizes="any" />
    <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
    <meta name="theme-color" content="#f5f7f9" media="(prefers-color-scheme: light)" />
    <meta name="theme-color" content="#0f1620" media="(prefers-color-scheme: dark)" />
    <meta property="og:type" content="website" />
    <meta property="og:title" content="Reading Lists | Zhongyuan Sun" />
    <meta property="og:description" content="Organization theory and strategy readings from {N} PhD syllabi, grouped by stream." />
    <meta property="og:url" content="https://zhongyuan0.github.io/readings/" />
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
            <li><a href="/readings/" aria-current="page">Readings</a></li>
          </ul>
        </nav>
      </div>
    </header>

    <main id="main" class="wrap">
      <header class="page-head">
        <div>
          <h1>Reading lists</h1>
          <p>
            {total:,} readings from {N} PhD seminar syllabi in organization theory and strategy, merged and regrouped by theoretical stream. The number beside each
            reading is how many of the {N} syllabi assign it. Each stream opens with its core readings, the {core_n} that appear in {CORE} or more syllabi,
            followed by those assigned in two or three; readings that appear in only one syllabus are folded away at the end. Credit for the selections belongs to the instructors listed
            <a href="#sources">at the end of the page</a>.
          </p>
        </div>
      </header>

      <nav class="band rl-toc" aria-labelledby="toc-h">
        <h2 class="label" id="toc-h">Streams</h2>
        <ol class="body">
{''.join(toc)}        </ol>
      </nav>

{''.join(sections)}      <section class="band" id="sources" aria-labelledby="sources-h">
        <h2 class="label" id="sources-h">Sources</h2>
        <div class="body">
          <p class="rl-desc">The syllabi these lists are compiled from. Each stream above names the syllabi it draws on.</p>
          <ul class="cites">
{src_items}          </ul>
        </div>
      </section>
    </main>

    <footer class="site-footer">
      <div class="wrap">
        <p>Last updated October 2026.</p>
      </div>
    </footer>
  </body>
</html>
'''
open(OUT, 'w').write(page)
print('topics', len(sections), 'readings', total, 'core', core_n, 'bytes', len(page))
