"""Build /readings/ (navigation: theory tree, numbered stream index, sources) and one page per stream at /readings/<slug>/.

On a stream page each sub-stream lists the readings assigned in two or more sources, with the number of sources;
those listed in only one source are folded underneath. /readings/more/ (an older single-source page) redirects to /readings/.

Usage: python3 tools/readings/build_page.py <site-root> <css-version>
"""
import os
import json, html, re, sys, collections, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from classify import TOPICS
from subtopics import SUBTOPICS, OTHER, reading_key
import tree
import network
import standardize

D = os.path.dirname(os.path.abspath(__file__)) + '/'
ROOT = sys.argv[1].rstrip('/')
CSS_V = sys.argv[2]
CORE = 4
_gc = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'goatcounter.txt')  # see tools/set_goatcounter.py
GOATCOUNTER = (f'    <script data-goatcounter="https://{open(_gc).read().strip()}.goatcounter.com/count" async src="/assets/js/count.js"></script>\n'
               if os.path.exists(_gc) else '')
BUILT = __import__('datetime').date.today().strftime('%B %Y')  # the deploy workflow resets it from git history

d = json.load(open(D + 'standardized.json'))  # classified.json after standardize.py
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
    """APA 7: up to 20 authors, '&' before the last; 21 or more: the first 19, an ellipsis, the last."""
    a = [x.strip() for x in a if x and x.strip()]
    etal = bool(a) and a[-1] == 'et al.'
    a = [x for x in a if x != 'et al.']
    if not a:
        return ''
    if len(a) > 20:
        return ', '.join(esc(x) for x in a[:19]) + ', . . . ' + esc(a[-1])
    if etal:
        return ', '.join(esc(x) for x in a) + ' et al.'
    if len(a) == 1:
        return esc(a[0])
    return ', '.join(esc(x) for x in a[:-1]) + ', &amp; ' + esc(a[-1])


def fmt_doi(f):
    doi = f.get('doi')
    if not doi:
        return ''
    url = 'https://doi.org/' + urllib.parse.quote(doi, safe="/()._-:;")
    return f' <a class="rl-doi" href="{html.escape(url, quote=True)}">https://doi.org/{esc(doi)}</a>'


def stop(s):
    """Text followed by a full stop, unless its visible text already ends with one (or ? or !)."""
    s = s.rstrip(' ,;:')
    return s if re.sub(r'<[^>]+>', '', s).rstrip().endswith(('.', '?', '!')) else s + '.'


def fmt_ref(r):
    """One reference in APA 7 style, from the fields standardize.py prepared."""
    f = r['ref']
    au = fmt_authors(f['authors'])
    if au and f.get('editors'):
        au += ' (Eds.).' if len(f['authors']) > 1 else ' (Ed.).'
    y = esc(f['year']) or 'n.d.'
    t = esc(f['title'])
    ed = f' ({esc(f["edition"])})' if f.get('edition') else ''
    k = f['kind']
    rest = ''
    if k == 'article':
        head = stop(t)
        if f.get('venue'):
            j = f'<cite>{esc(f["venue"])}</cite>'
            if f.get('volume'):
                j += f', <i>{esc(f["volume"])}</i>' + (f'({esc(f["issue"])})' if f.get('issue') else '')
            if f.get('pages'):
                j += f', {esc(f["pages"])}'
            rest = stop(j)
    elif k == 'book':
        head = stop(f'<cite>{t}</cite>{ed}')
        rest = stop(esc(f['venue'])) if f.get('venue') else ''
    elif k == 'chapter' and f.get('book'):
        head = stop(t)
        inn = 'In ' + (esc(f['eds']) + ', ' if f.get('eds') else '') + f'<cite>{esc(f["book"])}</cite>'
        bits = ', '.join(x for x in [esc(f['edition']) if f.get('edition') else '', f'Vol. {esc(f["vol"])}' if f.get('vol') else '',
                                     f'pp. {esc(f["pages"])}' if f.get('pages') else ''] if x)
        rest = stop(inn + (f' ({bits})' if bits else '')) + (' ' + stop(esc(f['publisher'])) if f.get('publisher') else '')
    else:
        head = stop(t + ed)
        rest = stop(esc(f['venue'])) if f.get('venue') else ''
    if au:
        return f'{au}{"" if au.endswith(".") else ""} ({y}). {head}' + (f' {rest}' if rest else '') + fmt_doi(f)
    return f'{head} ({y}).' + (f' {rest}' if rest else '') + fmt_doi(f)  # APA: no author, the title moves first


readings = [r for r in d['readings'] if not r.get('drop')]
used = sorted({c for r in readings for c in r['courses']})
N = len(used)


def li(r, count=True):
    if not count:
        return f'            <li><span class="rl-ref">{fmt_ref(r)}</span></li>\n'
    label = f"Listed in {r['n']} of {N} sources"
    c = f'<span class="rl-count" title="{label}" aria-label="{label}">{r["n"]}</span>'
    cls = ' class="core"' if r['n'] >= CORE else ''
    return f'            <li{cls}><span class="rl-ref">{fmt_ref(r)}</span>{c}</li>\n'


def year_num(r):
    m = re.search(r'(1[6-9]\d\d|20\d\d)', r['ref'].get('year') or '')
    return int(m.group(1)) if m else 0


def sortkey(r):
    return (-r['n'], year_num(r) or 9999, r['ref']['title'])


SUBMAP = json.load(open(D + 'subtopics.json')) if os.path.exists(D + 'subtopics.json') else {}
for r in readings:
    v = SUBMAP.get(reading_key(r))
    if v and v.startswith('@'):  # misfiled: move to another stream
        r['topic'], _, v = v[1:].partition(':')
    r['sub'] = v or None

by_topic = collections.defaultdict(list)
for r in readings:
    by_topic[r['topic']].append(r)

names = {k: n for k, n, _ in TOPICS}
descs = {k: d for k, _, d in TOPICS}
# Display order, which also gives each stream its number: theory first, then the two roots of the tree,
# then the tree's columns left to right (each top to bottom), then the streams outside the tree.
ORDER = (['theory', 'socialtheory', 'classics'] + sorted(tree.NODES, key=lambda k: tree.NODES[k][:2])
         + ['methods', 'profession'])
assert sorted(ORDER) == sorted(names), set(names) ^ set(ORDER)
NUM = {k: i + 1 for i, k in enumerate(ORDER)}
SLUG = {
    'theory': 'theory', 'socialtheory': 'social-theory', 'classics': 'classics', 'contingency': 'contingency',
    'rdt': 'resource-dependence', 'ecology': 'ecology', 'entre': 'entrepreneurship', 'culture': 'culture-cognition',
    'institutional': 'institutional-theory', 'categories': 'categories-identity', 'movements': 'social-movements',
    'networks': 'social-networks', 'status': 'status', 'work': 'work-careers', 'nonmarket': 'nonmarket-csr',
    'carnegie': 'behavioral-theory', 'evolution': 'evolution-innovation', 'stratproc': 'strategy-process',
    'stratecon': 'economics-of-strategy', 'rbv': 'resource-based-view', 'international': 'international-business',
    'orgecon': 'organizational-economics', 'corporate': 'corporate-strategy', 'governance': 'corporate-governance',
    'methods': 'methods', 'profession': 'profession',
}
assert set(SLUG) == set(names)


def url(key):
    return f'/readings/{SLUG[key]}/'


def numbered(key):
    return f'{NUM[key]} {names[key]}'


def subgroups(key, rs):
    """(sub-key, label, number, readings in 2+ sources, readings in one source) for each non-empty sub-stream."""
    by = collections.defaultdict(list)
    valid = {k for k, _ in SUBTOPICS[key]}
    for r in rs:
        by[r['sub'] if r['sub'] in valid else 'other'].append(r)
    gs = [(k, lab, by[k]) for k, lab in SUBTOPICS[key] + [OTHER] if by.get(k)]
    return [(k, lab, f'{NUM[key]}.{i}', [r for r in g if r['n'] >= 2], [r for r in g if r['n'] < 2])
            for i, (k, lab, g) in enumerate(gs, 1)]


def ol(rs, count=True):
    return '          <ol class="rl-list">\n' + ''.join(li(r, count) for r in rs) + '          </ol>\n'


def further(single, main_n):
    if not single:
        return ''
    n = len(single)
    what = f'{n} {"reading" if n == 1 else "readings"} listed in one source' if not main_n else f'{n} more, listed in one source'
    opened = ' open' if not main_n else ''
    return (f'          <details class="rl-more rl-further"{opened}>\n            <summary>{what}</summary>\n'
            + ol(single, count=False) + '          </details>\n')


def band(id_, label_html, body):
    return (f'      <section class="band rl-topic" id="{id_}" aria-labelledby="{id_}-h">\n'
            f'        <h2 class="label" id="{id_}-h">{label_html}</h2>\n'
            f'        <div class="body">\n{body}        </div>\n      </section>\n\n')


tree_names = dict(names, classics='Classical foundations', socialtheory='Social theory')
streams = {}
for key in ORDER:
    rs = by_topic.get(key, [])
    main = sorted((r for r in rs if r['n'] >= 2), key=sortkey)
    single = sorted((r for r in rs if r['n'] < 2), key=sortkey)
    streams[key] = (main, single)
totals = {k: len(m) + len(s) for k, (m, s) in streams.items()}


def lineage_line(key):
    def links(ks):
        ks = [f'<a href="{url(k)}">{esc(numbered(k))}</a>' for k in ks]
        return ks[0] if len(ks) == 1 else ', '.join(ks[:-1]) + ' and ' + ks[-1]
    src = [a for a, b, _ in tree.EDGES if b == key]
    dst = [b for a, b, _ in tree.EDGES if a == key]
    parts = ([f'Grows out of {links(src)}'] if src else []) + ([f'leads to {links(dst)}'] if dst else [])
    if not parts:
        return ''
    txt = '; '.join(parts)
    return f'          <p class="rl-tree-line">In the theory tree: {txt[0].lower() + txt[1:]}.</p>\n'


# ---------- Readings by decade: a small column chart (inline SVG, no script) ----------
DECADES = [('Before 1950', None, 1949)] + [(f'{y}s', y, y + 9) for y in range(1950, 2030, 10)]


def decade_counts(rs):
    out = []
    for label, lo, hi in DECADES:
        out.append((label, sum(1 for r in rs if year_num(r) and (lo is None or year_num(r) >= lo) and year_num(r) <= hi)))
    return out


def decade_chart(rs, what='readings'):
    """Columns by decade of publication. Tooltips come from <title>; a hidden table repeats the numbers for screen readers."""
    counts = decade_counts(rs)
    ys = sorted(year_num(r) for r in rs if year_num(r))
    if not ys:
        return ''
    W, H, base, top = 640, 118, 92, 22
    band, bw = W / len(counts), 24
    peak = max(n for _, n in counts)
    marks = []
    for i, (label, n) in enumerate(counts):
        cx = band * i + band / 2
        x = cx - bw / 2
        tip = f'{label}: {n} {what[:-1] if n == 1 else what}'
        g = [f'<g><title>{tip}</title><rect class="rl-dec-hit" x="{band * i:.1f}" y="4" width="{band:.1f}" height="{H - 4}"/>']
        if n:
            h = max(2.0, (base - top) * n / peak)
            yt = base - h
            r = min(4.0, h)
            g.append(f'<path class="rl-dec-bar" d="M{x:.1f},{base} L{x:.1f},{yt + r:.1f} Q{x:.1f},{yt:.1f} {x + r:.1f},{yt:.1f} '
                     f'L{x + bw - r:.1f},{yt:.1f} Q{x + bw:.1f},{yt:.1f} {x + bw:.1f},{yt + r:.1f} L{x + bw:.1f},{base} Z"/>')
            if n == peak:
                g.append(f'<text class="rl-dec-val" x="{cx:.1f}" y="{yt - 6:.1f}" text-anchor="middle">{n}</text>')
        g.append(f'<text class="rl-dec-lab" x="{cx:.1f}" y="{H - 6}" text-anchor="middle">{label.replace("Before ", "&lt;")}</text></g>')
        marks.append(''.join(g))
    med = ys[len(ys) // 2]
    peak_label = max(counts, key=lambda c: c[1])[0]
    peak_txt = 'before 1950' if peak_label.startswith('Before') else f'the {peak_label}'
    summary = f'Most date from {peak_txt}; half were published in {med} or later.'
    table = ''.join(f'<tr><th scope="row">{l}</th><td>{n}</td></tr>' for l, n in counts)
    return (f'          <figure class="rl-dec">\n'
            f'            <svg viewBox="0 0 {W} {H}" role="img" aria-label="{len(ys)} {what} by decade of publication. {summary}">'
            f'<line class="rl-dec-base" x1="0" x2="{W}" y1="{base}" y2="{base}"/>{"".join(marks)}</svg>\n'
            f'            <figcaption>{summary}</figcaption>\n'
            f'            <table class="visually-hidden"><caption>{what.capitalize()} by decade</caption><tr><th scope="col">Decade</th><th scope="col">Readings</th></tr>{table}</table>\n'
            f'          </figure>\n')


def decade_band(rs, label='By decade'):
    c = decade_chart(rs)
    return ('      <section class="band rl-decades" aria-labelledby="dec-h">\n'
            f'        <h2 class="label" id="dec-h">{label}</h2>\n'
            f'        <div class="body">\n{c}        </div>\n      </section>\n\n') if c else ''


def stream_page(i, key):
    main, single = streams[key]
    rs = main + single
    src = collections.Counter(c for r in rs for c in r['courses'])
    src_txt = '; '.join(dict.fromkeys(credit(courses[c]) for c, _ in src.most_common()))
    head = (f'          <p class="rl-crumb"><a href="/readings/">Reading lists</a> <span aria-hidden="true">›</span> Stream {NUM[key]}'
            f'<a class="rl-crumb-search" href="/readings/search/">Search all readings</a></p>\n'
            f'          <h1>{esc(names[key])}</h1>\n'
            f'          <p>{esc(descs[key])}</p>\n'
            f'          <p class="rl-key">Of its {len(rs)} readings, {len(main)} {"is" if len(main) == 1 else "are"} assigned in two or more sources and listed first, '
            f'with the number of sources beside each (in bold for the core readings, in {CORE} or more)'
            + (f'; the {len(single)} listed in only one source are folded under each heading.' if single else '.') + '</p>\n'
            + lineage_line(key) +
            f'          <p class="rl-src">Drawn from: {esc(src_txt)}. Full details of the sources are on the <a href="/readings/#sources">reading lists page</a>.</p>\n')
    body = [decade_band(rs)]
    if key in SUBTOPICS:
        gs = subgroups(key, rs)
        idx = ''.join(f'          <li><span class="rl-no">{no}</span><span><a href="#{k}">{esc(lab)}</a> <span class="rl-n">{len(m) + len(s)}</span></span></li>\n'
                      for k, lab, no, m, s in gs)
        body.append('      <nav class="band rl-toc rl-subindex" aria-labelledby="sub-h">\n'
                    '        <h2 class="label" id="sub-h">Sub-streams</h2>\n'
                    f'        <ol class="body">\n{idx}        </ol>\n      </nav>\n\n')
        for k, lab, no, m, s in gs:
            content = (ol(m) if m else '          <p class="rl-none">No reading here is assigned in more than one source.</p>\n') + further(s, len(m))
            body.append(band(k, f'<span class="rl-num">{no}</span> {esc(lab)}', content))
    else:
        core = [r for r in main if r['n'] >= CORE]
        multi = [r for r in main if r['n'] < CORE]
        if core:
            body.append(band('core', 'Core readings', f'          <p class="rl-desc">In {CORE} or more sources.</p>\n' + ol(core)))
        if multi:
            body.append(band('also', 'Also assigned', f'          <p class="rl-desc">In 2 to {CORE - 1} sources.</p>\n' + ol(multi)))
        if single:
            body.append(band('further', 'Further readings', further(single, len(main))))
    prev_k = ORDER[i - 1] if i > 0 else None
    next_k = ORDER[i + 1] if i + 1 < len(ORDER) else None
    pager = ('      <nav class="band rl-pager" aria-label="Other streams">\n        <div class="body">\n'
             + (f'          <a class="rl-prev" href="{url(prev_k)}" rel="prev"><span aria-hidden="true">←</span> {esc(numbered(prev_k))}</a>\n' if prev_k else '')
             + '          <a class="rl-all" href="/readings/#streams">All streams</a>\n'
             + (f'          <a class="rl-next" href="{url(next_k)}" rel="next">{esc(numbered(next_k))} <span aria-hidden="true">→</span></a>\n' if next_k else '')
             + '        </div>\n      </nav>\n')
    mark = f'        <p class="page-mark rl-mark" aria-hidden="true">{NUM[key]}</p>\n'
    return page(url(key), f'{names[key]} | Reading Lists', esc(f'{names[key]}: {descs[key]} Readings compiled from {N} PhD syllabi.'),
                True, head, ''.join(body) + pager, mark)


srcs = sorted(used, key=lambda i: credit(courses[i]))
src_items = ''.join(
    f'            <li>{esc(courses[i]["instructor"])}. <cite>{esc(courses[i]["course"])}</cite>'
    f'{". " + esc(courses[i]["institution"]) if courses[i]["institution"] else ""}{", " + esc(courses[i]["term"]) if courses[i]["term"] else ""}.</li>\n'
    for i in srcs)

CANON = 6
canon = sorted((r for r in readings if r['n'] >= CANON), key=sortkey)
total = len(readings)
main_total = sum(len(m) for m, _ in streams.values())
core_n = sum(r['n'] >= CORE for r in readings)


def page(path, title, desc, current_main, head, body, mark='', extra_head=''):
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
{extra_head}{GOATCOUNTER}  </head>
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
{mark}        <div>
{head}        </div>
      </header>

{body}    </main>

    <footer class="site-footer">
      <div class="wrap">
        <p>Last updated {BUILT}.</p>
      </div>
    </footer>
  </body>
</html>
'''


sources_section = f'''      <section class="band" id="sources" aria-labelledby="sources-h">
        <h2 class="label" id="sources-h">Sources</h2>
        <div class="body">
          <p class="rl-desc">The syllabi and reading lists these lists are compiled from. Each stream page names the sources it draws on.</p>
          <ul class="cites">
{src_items}          </ul>
        </div>
      </section>
'''


def toc_item(key):
    gs = subgroups(key, streams[key][0] + streams[key][1]) if key in SUBTOPICS else []
    sub = ''.join(f'              <li><span class="rl-no">{no}</span><span><a href="{url(key)}#{k}">{esc(lab)}</a> '
                  f'<span class="rl-n">{len(m) + len(s)}</span></span></li>\n' for k, lab, no, m, s in gs)
    return (f'          <li id="{key}"><span class="rl-no">{NUM[key]}</span><span><a href="{url(key)}">{esc(names[key])}</a> <span class="rl-n">{totals[key]}</span></span>'
            + (f'\n            <ol class="rl-subtoc">\n{sub}            </ol>\n          ' if sub else '') + '</li>\n')


hub_head = f'''          <h1>Reading lists</h1>
          <p>
            {total:,} readings in organization theory and strategy, compiled from {N} PhD syllabi and reading lists and grouped into {len(ORDER)} numbered streams.
            Each stream has its own page, where the readings assigned in two or more sources come first and those in only one are folded underneath.
            Credit for the selections belongs to the instructors and authors listed <a href="#sources">at the end of this page</a>.
          </p>
          <form class="rl-search-form" action="/readings/search/" method="get" role="search">
            <label for="rl-q">Search all readings</label>
            <span class="rl-search-row"><input id="rl-q" name="q" type="search" placeholder="Author, title, journal or year" autocomplete="off" /><button type="submit">Search</button></span>
          </form>
          <p class="rl-canon-link">Where to start: <a href="/readings/canon/">the {len(canon)} most assigned readings</a>, those in {CANON} or more of the {N} sources.
            Or see <a href="/readings/network/">how the readings are assigned together</a>, a map drawn from the syllabi themselves.</p>
          <p class="rl-canon-link">Writing one: <a href="/readings/writing/">what to read before writing each part of a paper</a>, from the introduction to the response to reviewers.</p>
'''
outside = ', '.join(f'{NUM[k]} <a href="{url(k)}">{esc(names[k])}</a>' for k in ('theory', 'methods'))
hub_body = f'''      <section class="rl-tree" aria-labelledby="tree-h">
        <h2 class="visually-hidden" id="tree-h">Theory tree</h2>
        <div class="rl-tree-figure">
          {tree.svg(totals, tree_names, NUM, href=url)}
        </div>
        <p class="rl-tree-note">
          Each box is a stream, with its number and its number of readings; click a box to open its page. Arrows show which streams grew out of which;
          hover over an arrow for a one-line explanation. Three streams sit outside the tree: {outside}
          and {NUM['profession']} <a href="{url('profession')}">{esc(names['profession'])}</a>.
        </p>
        <details class="rl-more rl-lineage">
          <summary>Lineage, in words</summary>
          <ul class="plain-list">
{tree.lineage_list(tree_names, NUM, href=url)}          </ul>
        </details>
      </section>

      <nav class="band rl-toc" id="streams" aria-labelledby="toc-h">
        <h2 class="label" id="toc-h">All streams</h2>
        <ol class="body">
{''.join(toc_item(k) for k in ORDER)}        </ol>
      </nav>

{sources_section}'''

# ---------- Search: a data file of every reading and a page that searches it in the browser ----------
def anchor_of(key):
    a = {}
    if key in SUBTOPICS:
        for k, lab, no, m, s_ in subgroups(key, streams[key][0] + streams[key][1]):
            for r in m + s_:
                a[id(r)] = (k, f'{no} {lab}')
    else:
        main, single = streams[key]
        for r in main:
            a[id(r)] = ('core' if r['n'] >= CORE else 'also', f'{NUM[key]} {names[key]}')
        for r in single:
            a[id(r)] = ('further', f'{NUM[key]} {names[key]}')
    return a


search_items = []
for key in ORDER:
    anchors = anchor_of(key)
    for r in streams[key][0] + streams[key][1]:
        k, lab = anchors[id(r)]
        search_items.append({'h': fmt_ref(r), 'n': r['n'], 'y': year_num(r), 'u': f'{url(key)}#{k}', 'l': lab,
                             's': f'{NUM[key]} {names[key]}' if key in SUBTOPICS else ''})
# ---------- The canon: readings in CANON or more sources ----------
where = {}
for key in ORDER:
    for rid, (k, lab) in anchor_of(key).items():
        where[rid] = (key, k, lab)


def canon_li(r):
    key, k, lab = where[id(r)]
    label = f"Listed in {r['n']} of {N} sources"
    loc = f'<a href="{url(key)}#{k}">{esc(lab)}</a>' + (f' · {NUM[key]} {esc(names[key])}' if key in SUBTOPICS else '')
    return (f'            <li class="core"><span class="rl-ref">{fmt_ref(r)} <span class="rl-where">{loc}</span></span>'
            f'<span class="rl-count" title="{label}" aria-label="{label}">{r["n"]}</span></li>\n')


by_stream = collections.Counter(where[id(r)][0] for r in canon)
top_streams = ', '.join(f'<a href="{url(k)}">{NUM[k]} {esc(names[k])}</a> ({n})' for k, n in by_stream.most_common(4))
canon_head = f'''          <p class="rl-crumb"><a href="/readings/">Reading lists</a> <span aria-hidden="true">›</span> Most assigned</p>
          <h1>The most assigned readings</h1>
          <p>The {len(canon)} readings that {CANON} or more of the {N} PhD syllabi and reading lists assign: a rough canon of doctoral training in
            organization theory and strategy. The number beside each is how many sources assign it; the line below gives its stream.</p>
          <p class="rl-key">The streams with the most of them: {top_streams}.</p>
'''
canon_body = (decade_band(canon) + '      <section class="band rl-topic" id="list" aria-labelledby="list-h">\n'
              '        <h2 class="label" id="list-h">Readings</h2>\n        <div class="body">\n          <ol class="rl-list">\n'
              + ''.join(canon_li(r) for r in canon) + '          </ol>\n        </div>\n      </section>\n')

# ---------- Co-assignment network ----------
net_readings = [r for r in readings if r['n'] >= 2]
core, info = network.build(net_readings)
pos, bc, comms = info['pos'], info['betweenness'], info['communities']
nw_where = {}
for key in ORDER:
    for rid, (k, lab) in anchor_of(key).items():
        nw_where[rid] = (key, k)


def nw_item(i):
    r = net_readings[i]
    key, k = nw_where[id(r)]
    return {'s': network.short(r), 'h': fmt_ref(r), 'n': r['n'], 'u': f'{url(key)}#{k}', 'st': f'{NUM[key]} {names[key]}',
            'nb': [[j, w] for j, w in network.neighbours(core, i)]}


nw_data = {str(i): nw_item(i) for i in core.nodes}
bridges = sorted(core.nodes, key=lambda i: -bc[i])[:12]
bridge_items = ''.join(
    f'            <li><span class="rl-ref">{fmt_ref(net_readings[i])} <span class="rl-where">{NUM[net_readings[i]["topic"]]} {esc(names[net_readings[i]["topic"]])} · '
    f'linked to {core.degree(i)} readings</span></span><span class="rl-count" title="Listed in {net_readings[i]["n"]} of {N} sources">{net_readings[i]["n"]}</span></li>\n'
    for i in bridges)
comm_rows = []
for c in comms:
    if len(c) < 12:
        continue
    cnt = collections.Counter(net_readings[i]['topic'] for i in c)
    top = cnt.most_common(3)
    main_key, main_n = top[0]
    share = main_n / len(c)
    others = ', '.join(f'{NUM[k]} {esc(names[k])} ({n})' for k, n in top[1:] if n >= 3)
    comm_rows.append(f'            <tr><td>{len(c)}</td><td><a href="{url(main_key)}">{NUM[main_key]} {esc(names[main_key])}</a> ({share:.0%})</td><td>{others or "—"}</td></tr>\n')
fam_legend = ''.join(f'            <li><span class="nw-sw f-{k}" aria-hidden="true"></span>{esc(lab)}</li>\n' for k, lab in network.FAMILIES)
links_shown = sum(1 for _, _, d in core.edges(data=True) if d['weight'] >= 2)
nw_head = f'''          <p class="rl-crumb"><a href="/readings/">Reading lists</a> <span aria-hidden="true">›</span> Network</p>
          <h1>How the readings are assigned together</h1>
          <p>A map of the {core.number_of_nodes()} readings in two or more sources. Two readings are linked when a syllabus assigns them in the same
            session; the figure draws the {links_shown:,} links that recur in at least two syllabi ({core.number_of_edges():,} in all place the points). Readings
            that are taught together sit close together, so the clusters are the streams as the {N} syllabi themselves draw them, not as I drew them.</p>
          <p class="rl-key">Colour is the stream's family in the theory tree; size is the number of sources. Click or tap a reading to see it and what it is most
            often assigned with; the lists below the figure give the same in words.</p>
'''
nw_body = f'''      <section class="rl-tree nw-figure" aria-labelledby="nw-h">
        <h2 class="visually-hidden" id="nw-h">Map</h2>
        <div class="rl-tree-figure">
          {network.svg(core, pos, net_readings, names)}
        </div>
        <ul class="nw-legend plain-list" aria-label="Colours">
{fam_legend}        </ul>
        <div class="nw-panel" id="nw-panel" hidden>
          <p class="rl-desc" id="nw-sel"></p>
          <p class="rl-src">Most often assigned with:</p>
          <ol class="rl-list" id="nw-nb"></ol>
        </div>
      </section>

      <section class="band" id="bridges" aria-labelledby="bridges-h">
        <h2 class="label" id="bridges-h">Bridges</h2>
        <div class="body">
          <p class="rl-desc">The readings that most often lie on the shortest path between two others (betweenness centrality): the ones that
            connect streams, and that a reader of one stream is most likely to meet again in another.</p>
          <ol class="rl-list">
{bridge_items}          </ol>
        </div>
      </section>

      <section class="band" id="communities" aria-labelledby="comm-h">
        <h2 class="label" id="comm-h">Clusters in the data</h2>
        <div class="body">
          <p class="rl-desc">Communities found in the network by the Louvain method, compared with the hand-drawn streams. Each row is one cluster:
            its size, the stream most of its readings belong to, and other streams with three or more readings in it.</p>
          <table class="nw-table">
            <thead><tr><th scope="col">Readings</th><th scope="col">Mainly</th><th scope="col">Also</th></tr></thead>
            <tbody>
{''.join(comm_rows)}            </tbody>
          </table>
          <p class="rl-src">Links counted within one session of one syllabus; sessions listing more than {network.MAX_SESSION} readings (whole reading lists) are left out.
            Layout: force-directed (Fruchterman–Reingold). Computed with NetworkX.</p>
        </div>
      </section>
'''


# ---------- Writing the paper: hand-picked readings by section of a paper ----------
WR = json.load(open(D + 'writing.json'))
WORKS = json.load(open(D + '.cache/works.json')) if os.path.exists(D + '.cache/works.json') else {}
by_doi = {r['doi']: r for r in readings if r.get('doi')}


def writing_ref(it):
    v = it.get('venue') or ''
    r = {'authors': it.get('authors') or [it['author']], 'year': str(it['year']), 'title': it['title'], 'venue': v,
         'type': 'chapter' if v.startswith('In ') else ('book' if v else 'article')}
    ref = standardize.standardize(r, WORKS.get(it.get('doi', '')), {'The Academy of Management Review': 'Academy of Management Review'})
    if it.get('authors'):  # a correction by hand beats the Crossref record
        ref['authors'] = it['authors']
    if it.get('editors'):
        ref['editors'] = True
    if it.get('doi'):
        ref['doi'] = it['doi']
    return ref


def writing_li(it):
    ref = writing_ref(it)
    known = by_doi.get(it.get('doi', ''))
    where = ''
    if known:
        key, k = nw_where.get(id(known)) or (None, None)
        if key:
            where = f' <span class="rl-where"><a href="{url(key)}#{k}">In the reading lists</a> · assigned in {known["n"]} of {N} sources</span>'
        else:
            where = f' <span class="rl-where">In the reading lists · assigned in {known["n"]} of {N} sources</span>'
    return (f'            <li><span class="rl-ref">{fmt_ref({"ref": ref})}</span>'
            f'<p class="rl-note">{esc(it["note"])}</p>{where}</li>\n')


wr_sections = []
for key, title, desc in WR['sections']:
    its = [i for i in WR['items'] if i['section'] == key]
    wr_sections.append(f'      <section class="band rl-topic" id="{key}" aria-labelledby="{key}-h">\n'
                       f'        <h2 class="label" id="{key}-h">{esc(title)}</h2>\n        <div class="body">\n'
                       f'          <p class="rl-desc">{esc(desc)}</p>\n          <ol class="rl-list rl-writing">\n'
                       + ''.join(writing_li(i) for i in its) + '          </ol>\n        </div>\n      </section>\n\n')
wr_toc = ''.join(f'          <li><a href="#{key}">{esc(title)}</a> <span class="rl-n">{sum(1 for i in WR["items"] if i["section"] == key)}</span></li>\n'
                 for key, title, _ in WR['sections'])
wr_in_lists = sum(1 for i in WR['items'] if i.get('doi') in by_doi)
writing_head = f'''          <p class="rl-crumb"><a href="/readings/">Reading lists</a> <span aria-hidden="true">›</span> Writing</p>
          <h1>Writing the paper</h1>
          <p>What to read before writing each part of a paper: {len(WR['items'])} pieces, mostly editors' essays from the journals that will
            review it, arranged by the section they help with. Unlike the reading lists, these are chosen by hand rather than counted
            from syllabi, though {wr_in_lists} of them appear there too. The one-line notes are mine.</p>
'''
writing_body = f'''      <nav class="band rl-toc rl-writing-toc" aria-labelledby="wtoc-h">
        <h2 class="label" id="wtoc-h">Sections</h2>
        <ol class="body">
{wr_toc}        </ol>
      </nav>

{''.join(wr_sections)}'''


search_json = json.dumps({'sources': N, 'core': CORE, 'items': search_items}, ensure_ascii=False, separators=(',', ':'))

search_head = f'''          <p class="rl-crumb"><a href="/readings/">Reading lists</a> <span aria-hidden="true">›</span> Search</p>
          <h1>Search the readings</h1>
          <p>Search all {total:,} readings by author, title, journal, year or DOI. Every word must match; results assigned in more sources come first.</p>
          <form class="rl-search-form" action="/readings/search/" method="get" role="search">
            <label class="visually-hidden" for="rl-q">Search</label>
            <span class="rl-search-row"><input id="rl-q" name="q" type="search" placeholder="e.g. Granovetter, legitimacy, Organization Science 2010" autocomplete="off" autofocus /><button type="submit">Search</button></span>
            <label class="rl-check"><input id="rl-multi" name="multi" type="checkbox" value="1" /> Only readings assigned in two or more sources</label>
          </form>
'''
search_body = '''      <section class="band" aria-labelledby="res-h">
        <h2 class="label" id="res-h">Results</h2>
        <div class="body">
          <p class="rl-desc" id="rl-status" aria-live="polite">Type to search.</p>
          <noscript><p class="rl-desc">Search needs JavaScript. You can browse the streams from the <a href="/readings/">reading lists page</a>.</p></noscript>
          <ol class="rl-list rl-results" id="rl-results"></ol>
        </div>
      </section>
'''

redirect = '''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Reading Lists | Zhongyuan Sun</title>
    <meta http-equiv="refresh" content="0; url=/readings/" />
    <link rel="canonical" href="https://zhongyuan0.github.io/readings/" />
    <meta name="robots" content="noindex" />
  </head>
  <body>
    <p>The further readings are now on each stream's page, linked from the <a href="/readings/">reading lists</a>.</p>
  </body>
</html>
'''


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w').write(text)


write(ROOT + '/readings/index.html',
      page('/readings/', 'Reading Lists', f'Organization theory and strategy readings from {N} PhD syllabi, grouped into numbered streams and sub-streams.',
           True, hub_head, hub_body))
for i, key in enumerate(ORDER):
    write(ROOT + url(key) + 'index.html', stream_page(i, key))
write(ROOT + '/readings/more/index.html', redirect)
write(ROOT + '/readings/search/readings.json', search_json)
write(ROOT + '/readings/network/index.html',
      page('/readings/network/', 'How the Readings Are Assigned Together', f'A co-assignment network of {core.number_of_nodes()} organization theory and strategy readings from {N} PhD syllabi.',
           True, nw_head, nw_body,
           extra_head=f'    <script src="/assets/js/readings-network.js?v={CSS_V}" defer></script>\n'
                      f'    <script type="application/json" id="nw-data">{json.dumps(nw_data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")}</script>\n'))
write(ROOT + '/readings/writing/index.html',
      page('/readings/writing/', 'Writing the Paper', f'{len(WR["items"])} readings on writing each part of a management paper: introduction, theory, hypotheses, methods, discussion, qualitative research, style and reviewing.',
           True, writing_head, writing_body))
write(ROOT + '/readings/canon/index.html',
      page('/readings/canon/', 'The Most Assigned Readings', f'The {len(canon)} organization theory and strategy readings assigned in {CANON} or more of {N} PhD syllabi.',
           True, canon_head, canon_body))
write(ROOT + '/readings/search/index.html',
      page('/readings/search/', 'Search the Readings', f'Search {total:,} organization theory and strategy readings compiled from {N} PhD syllabi.',
           True, search_head, search_body,
           extra_head=f'    <script src="/assets/js/readings-search.js?v={CSS_V}" data-index="/readings/search/readings.json?v={CSS_V}" defer></script>\n'))
sitemap = ['https://zhongyuan0.github.io' + p for p in ['/', '/research/', '/cv/', '/readings/', '/readings/canon/', '/readings/writing/', '/readings/network/', '/readings/search/'] + [url(k) for k in ORDER]]
write(ROOT + '/sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
      + ''.join(f'  <url><loc>{u}</loc></url>\n' for u in sitemap) + '</urlset>\n')
print('sources', N, 'readings', total, 'in 2+ sources', main_total, 'core', core_n, 'pages', len(ORDER) + 1)
