"""Find a DOI on Crossref for every reading and write dois.json for build_page.py.

Usage:
  python3 tools/readings/dois.py               query Crossref for readings not yet looked up, then match all
  python3 tools/readings/dois.py --offline     match again from the saved Crossref answers only (after changing the rules)
  python3 tools/readings/dois.py --limit 50    query at most 50 readings this run
  python3 tools/readings/dois.py --selftest    check the matching rules

Files (all keyed by reading_key):
  .cache/crossref.json  Crossref's top five records for each reading (not in git; delete an entry to query it again)
  dois_manual.json      DOIs checked by hand: a DOI, or "" for a reading with none. Always wins over the automatic match.
  dois.json             the result: a DOI, or "" when there is no confident match (many books and chapters have none)
  dois_review.json      near misses (right author, title close, but the year, type or title not close enough), to check by hand

A match needs all of: the title (with or without its subtitle) nearly the same, the first author's surname among the
record's authors or editors, a compatible record type (a book only matches a book record, so reviews of a book in a
journal are not taken for the book), and either the year within one or, for a journal article or chapter, the same
journal or series (publishers sometimes date old articles by when they went online). Needs access to api.crossref.org.
"""
import difflib, html, json, os, re, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from subtopics import reading_key

D = os.path.dirname(os.path.abspath(__file__)) + '/'
CACHE = D + '.cache/crossref.json'
API = 'https://api.crossref.org/works'
UA = 'zhongyuan0.github.io reading lists (https://zhongyuan0.github.io/readings/; python urllib)'
FIELDS = 'DOI,title,subtitle,author,editor,issued,published-print,published-online,type,container-title,publisher'
MIN_INTERVAL = 0.35  # seconds between requests

BOOKISH = {'book', 'monograph', 'edited-book', 'reference-book', 'book-set', 'book-series'}
OK_TYPES = {
    'article': {'journal-article', 'proceedings-article', 'book-chapter', 'posted-content', 'report'},
    'book': BOOKISH,
    'chapter': {'book-chapter', 'book-part', 'book-section', 'reference-entry', 'journal-article', 'other'},
    'other': None,  # anything except the types in NEVER
}
NEVER = {'component', 'peer-review', 'dataset', 'grant', 'database', 'standard', 'journal-issue', 'journal-volume', 'journal'}
# Preferred record type when several match: the published journal version over a conference paper or preprint.
PREF = {
    'article': ['journal-article', 'book-chapter', 'proceedings-article', 'report', 'posted-content'],
    'chapter': ['book-chapter', 'book-part', 'book-section', 'reference-entry', 'journal-article'],
    'book': ['book', 'monograph', 'edited-book', 'reference-book'],
    'other': ['journal-article', 'book-chapter', 'report', 'posted-content'],
}
WORKING = re.compile(r'work|paper|proceed|ssrn|nber|manuscript|mimeo|draft|unpublished|conference|meeting', re.I)
NOTICE = re.compile(r'^(erratum|errata|correction|corrigendum|addendum|retraction|retracted|expression of concern|reply|rejoinder|comment on)\b')


def ascii_lower(s):
    return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()


def norm_title(s):
    s = re.sub(r'<[^>]+>', ' ', html.unescape(s or ''))
    s = ascii_lower(s).replace('&', ' and ')
    s = re.sub(r'[^a-z0-9 ]+', ' ', s)
    s = re.sub(r'^(the|a|an) ', '', ' '.join(s.split()))
    return s


def strip_label(t):
    t = html.unescape(t or '')
    m = re.match(r'^\s*([A-Z][A-Z ]{3,})\s*[—–-]\s*(.+)$', t)  # all-caps section label before a dash
    if m:
        return m.group(2)
    return re.sub(r'^\s*(chapter\s+\d+\.?|\d+\.)\s+', '', t, flags=re.I)


def main_title(s):
    return norm_title(re.split(r'[:?.]\s', html.unescape(s or '') + ' ')[0])


def surname(r):
    a = (r.get('authors') or [''])[0]
    s = a.split(',')[0] if ',' in a else (a.split()[-1] if a.split() else '')
    return re.sub(r'[^a-z]', '', ascii_lower(s))


def year_of(s):
    m = re.search(r'(1[6-9]\d\d|20\d\d)', str(s or ''))
    return int(m.group(1)) if m else None


def item_years(it):
    ys = set()
    for f in ('issued', 'published-print', 'published-online'):
        try:
            ys.add(int(it[f]['date-parts'][0][0]))
        except (KeyError, IndexError, TypeError, ValueError):
            pass
    return ys


def item_names(it):
    people = (it.get('author') or [])[:4] + (it.get('editor') or [])[:4]
    return {re.sub(r'[^a-z]', '', ascii_lower(p.get('family') or p.get('name') or '')) for p in people} - {''}


def same_venue(r, it):
    """The reading's journal or series is the record's container (abbreviations aside)."""
    v = norm_title(re.split(r',\s*\d|\(|\d{1,3}\s*\(', r.get('venue') or '')[0])
    cs = [norm_title(c) for c in it.get('container-title') or []]
    return bool(v) and len(v) >= 6 and any(c and (c == v or (len(c) >= 10 and (c in v or v in c))) for c in cs)


def title_score(rt, it):
    t = strip_label((it.get('title') or [''])[0])
    sub = (it.get('subtitle') or [''])[0]
    full = f'{t}: {sub}' if sub else t
    a = norm_title(rt)
    cands = {norm_title(t), norm_title(full)}
    if len(norm_title(sub)) >= 20:
        cands.add(norm_title(sub))  # "Editorial Essay: What Is Organizational Research For?"
    best = 0.0
    for c in cands:
        if not c:
            continue
        best = max(best, difflib.SequenceMatcher(None, a, c).ratio())
        short, long_ = sorted((a, c), key=len)
        if len(short) >= 30 and long_.startswith(short):
            best = max(best, 0.93)
    ma, mc = main_title(rt), main_title(t)
    if len(ma) >= 15 and ma == mc:
        best = max(best, 0.94)
    return best


def judge(r, it):
    """Return (score, verdict, reason): verdict is 'accept', 'review' or None."""
    s = title_score(r.get('title', ''), it)
    if it.get('type') in NEVER or (NOTICE.match(norm_title((it.get('title') or [''])[0])) and not NOTICE.match(norm_title(r.get('title', '')))):
        return s, None, 'notice'
    if s < 0.75:
        return s, None, 'title'
    sn, names = surname(r), item_names(it)
    author_ok = bool(sn) and any(sn == n or (len(sn) > 3 and len(n) > 3 and (n.endswith(sn) or sn.endswith(n))) for n in names)
    if names and not author_ok:
        return s, None, 'author'
    rtype, itype = r.get('type'), it.get('type')
    types = OK_TYPES.get(rtype)
    type_ok = types is None or itype in types
    if rtype in ('article', 'chapter') and itype in BOOKISH:
        type_ok = False
    y, ys = year_of(r.get('year')), item_years(it)
    gap = min((abs(y - v) for v in ys), default=99) if y else 99
    venue = itype in ('journal-article', 'book-chapter') and rtype != 'book' and same_venue(r, it)
    reasons = []
    container = ' '.join(it.get('container-title') or []).lower()
    preprint = (itype in ('posted-content', 'report') or 'proceedings' in container or 'ssrn' in container
                or it.get('DOI', '').lower().startswith(('10.2139/ssrn', '10.3386/w', '10.5465/ambpp')))
    if preprint and not WORKING.search(r.get('venue') or '') and rtype != 'other':
        reasons.append('preprint or conference version of a published paper')
    if s < 0.9:
        reasons.append(f'title {s:.2f}')
    if gap > 1 and not (venue and s >= 0.95):
        reasons.append(f'year {sorted(ys)}')
    if not type_ok:
        reasons.append(f'type {itype}')
    if not names:
        if not (s >= 0.95 and (gap == 0 or venue) and type_ok):
            reasons.append('no authors on record')
    if not reasons:
        return s, 'accept', ''
    return s, 'review', '; '.join(reasons)


def best_match(r, items):
    acc, rev = [], []
    y = year_of(r.get('year'))
    for it in items:
        s, v, why = judge(r, it)
        exact = 1 if y in item_years(it) else 0
        if v == 'accept':
            acc.append((s, exact, it))
        elif v == 'review':
            rev.append((s, exact, it, why))
    if acc:
        pref = PREF.get(r.get('type'), [])
        rank = lambda t: pref.index(t) if t in pref else len(pref)
        acc.sort(key=lambda x: (rank(x[2].get('type')), -x[1], -x[0]))
        return acc[0][2]['DOI'].lower(), None
    if rev:
        rev.sort(key=lambda x: (x[0], x[1]), reverse=True)
        s, _, it, why = rev[0]
        rec = (f"{(it.get('title') or [''])[0]} | {'; '.join((it.get('container-title') or [])[:1])} | "
               f"{it.get('publisher', '')} | {sorted(item_years(it))} | {it.get('type')}")
        return '', {'doi': it['DOI'].lower(), 'record': rec, 'score': round(s, 3), 'why': why}
    return '', None


_last = [0.0]


def query(r, second=False):
    if second:  # narrower second try for articles: title and author separately, journal articles only
        params = {'query.bibliographic': r.get('title', ''), 'query.author': surname(r), 'filter': 'type:journal-article'}
    else:
        params = {'query.bibliographic': ' '.join(x for x in (r.get('title', ''), surname(r), str(year_of(r.get('year')) or '')) if x)}
    url = API + '?' + urllib.parse.urlencode(dict(params, rows=5, select=FIELDS))
    for attempt in range(6):
        wait = _last[0] + MIN_INTERVAL - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=30) as f:
                return json.load(f)['message']['items']
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(float(e.headers.get('Retry-After') or 2 ** attempt * 2))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2 ** attempt * 2)
    raise RuntimeError('Crossref did not answer: ' + url)


def selftest():
    r = {'authors': ['Granovetter, M.'], 'year': '1985', 'type': 'article',
         'title': 'Economic action and social structure: The problem of embeddedness'}
    good = {'DOI': '10.1086/228311', 'title': ['Economic Action and Social Structure: The Problem of Embeddedness'],
            'author': [{'family': 'Granovetter', 'given': 'Mark'}], 'issued': {'date-parts': [[1985, 11]]},
            'type': 'journal-article'}
    review = dict(good, DOI='10.1/review', author=[{'family': 'Someone'}])
    assert best_match(r, [review, good])[0] == '10.1086/228311'
    book = {'authors': ['Thompson, J. D.'], 'year': '1967', 'type': 'book', 'title': 'Organizations in Action'}
    rev = {'DOI': '10.2307/x', 'title': ['Organizations in Action'], 'author': [{'family': 'Thompson'}],
           'issued': {'date-parts': [[1967]]}, 'type': 'journal-article'}
    assert best_match(book, [rev])[0] == ''
    reprint = dict(rev, DOI='10.4324/y', type='book', issued={'date-parts': [[2017]]})
    assert best_match(book, [reprint])[0] == '' and best_match(book, [reprint])[1]['why'].startswith('year')
    sub = {'authors': ['Uzzi, B.'], 'year': '1997', 'type': 'article', 'title': 'Social structure and competition in interfirm networks',
           'venue': 'Administrative Science Quarterly'}
    it = {'DOI': '10.2307/2393808', 'title': ['Social Structure and Competition in Interfirm Networks'],
          'subtitle': ['The Paradox of Embeddedness'], 'author': [{'family': 'Uzzi'}], 'issued': {'date-parts': [[1997, 3]]},
          'type': 'journal-article'}
    assert best_match(sub, [it])[0] == '10.2307/2393808'
    proc = dict(it, DOI='10.5465/proc', type='proceedings-article', issued={'date-parts': [[1996, 8]]})
    err = dict(it, DOI='10.2307/err', title=['Erratum: Social Structure and Competition in Interfirm Networks'])
    assert best_match(sub, [proc, err, it])[0] == '10.2307/2393808'
    smj = {'authors': ['Barnett, W. P.'], 'year': '1996', 'type': 'article', 'title': 'The Red Queen in Organizational Evolution',
           'venue': 'Strategic Management Journal, 17: 139-157'}
    rec = {'DOI': '10.1002/smj.4250171010', 'title': ['The red queen in organizational evolution'], 'author': [{'family': 'Barnett'}],
           'issued': {'date-parts': [[2007]]}, 'type': 'journal-article', 'container-title': ['Strategic Management Journal']}
    assert best_match(smj, [rec])[0] == '10.1002/smj.4250171010'
    other_j = dict(rec, **{'container-title': ['Some Other Journal']})
    assert best_match(smj, [other_j])[0] == ''
    g = {'authors': ['Gavetti, G.'], 'year': '2012', 'type': 'article', 'title': 'Toward a Behavioral Theory of Strategy', 'venue': 'Organization Science'}
    rec = {'DOI': '10.1287/orsc.1110.0644', 'title': ['PERSPECTIVE—Toward a Behavioral Theory of Strategy'], 'author': [{'family': 'Gavetti'}],
           'issued': {'date-parts': [[2012]]}, 'type': 'journal-article'}
    assert best_match(g, [rec])[0] == '10.1287/orsc.1110.0644'
    print('selftest ok')


def load(p, default):
    return json.load(open(p)) if os.path.exists(p) else default


def main():
    args = sys.argv[1:]
    if '--selftest' in args:
        return selftest()
    limit = int(args[args.index('--limit') + 1]) if '--limit' in args else None
    d = json.load(open(D + 'classified.json'))
    rs = sorted((r for r in d['readings'] if not r.get('drop')), key=lambda r: -r['n'])
    rs = list({reading_key(r): r for r in reversed(rs)}.values())[::-1]  # one per key, most-listed first
    cache, manual = load(CACHE, {}), load(D + 'dois_manual.json', {})
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)

    def save_cache():
        json.dump(cache, open(CACHE, 'w'), ensure_ascii=False)

    if '--offline' not in args:
        todo = [r for r in rs if reading_key(r) not in cache and reading_key(r) not in manual][:limit]
        print(f'{len(todo)} readings to query', flush=True)
        try:
            for i, r in enumerate(todo, 1):
                cache[reading_key(r)] = query(r)
                if i % 50 == 0:
                    save_cache()
                    print(f'  {i}/{len(todo)}', flush=True)
        finally:
            save_cache()
        # Second try for articles the first query did not settle.
        todo = [r for r in rs if r.get('type') in ('article', 'other') and reading_key(r) in cache and reading_key(r) not in manual
                and '2|' + reading_key(r) not in cache and not best_match(r, cache[reading_key(r)])[0] and surname(r)][:limit]
        print(f'{len(todo)} articles to query again', flush=True)
        try:
            for i, r in enumerate(todo, 1):
                cache['2|' + reading_key(r)] = query(r, second=True)
                if i % 50 == 0:
                    save_cache()
                    print(f'  {i}/{len(todo)}', flush=True)
        finally:
            save_cache()

    out, review = {}, {}
    for r in rs:
        k = reading_key(r)
        if k in manual:
            out[k] = manual[k]
            continue
        if k not in cache:
            continue
        doi, rev = best_match(r, cache[k] + cache.get('2|' + k, []))
        out[k] = doi
        if rev:
            review[k] = dict(rev, reading=f"{'; '.join(r['authors'][:3])} ({r['year']}). {r['title']}. {r['venue']} [{r['type']}] n={r['n']}")
    json.dump(dict(sorted(out.items())), open(D + 'dois.json', 'w'), ensure_ascii=False, indent=0)
    json.dump(dict(sorted(review.items())), open(D + 'dois_review.json', 'w'), ensure_ascii=False, indent=1)
    main_n = [r for r in rs if r['n'] >= 2]
    print(f'DOIs: {sum(1 for v in out.values() if v)} of {len(rs)} readings '
          f'(main page {sum(1 for r in main_n if out.get(reading_key(r)))} of {len(main_n)}); {len(review)} to review')


if __name__ == '__main__':
    main()
