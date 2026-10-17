"""Look up a DOI on Crossref for every reading and store it in dois.json.

Usage:
  python3 tools/readings/dois.py               look up readings not yet in dois.json (main-page readings first)
  python3 tools/readings/dois.py --limit 50    stop after 50 lookups
  python3 tools/readings/dois.py --retry-missing   look again at readings stored with no DOI
  python3 tools/readings/dois.py --selftest    check the matching rules offline

dois.json maps reading_key -> DOI, or "" when Crossref had no confident match (many books, chapters and
working papers have no DOI). Readings already in the file are skipped, so the script can be stopped and
resumed, and a DOI fixed or added by hand in dois.json stays as it is. Near misses (right author, title close
but not close enough, or the year or type off) go to dois_review.json for a look by hand.

A match needs all of: the title (with or without its subtitle) nearly the same, the first author's surname
among the record's first authors or editors, the year within one, and a compatible record type (a book only
matches a book record, so reviews of a book in a journal are not taken for the book).
Needs network access to api.crossref.org.
"""
import difflib, html, json, os, re, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from subtopics import reading_key

D = os.path.dirname(os.path.abspath(__file__)) + '/'
API = 'https://api.crossref.org/works'
UA = 'zhongyuan0.github.io reading lists (https://zhongyuan0.github.io/readings/; python urllib)'
FIELDS = 'DOI,title,subtitle,author,editor,issued,published-print,published-online,type,container-title'
MIN_INTERVAL = 0.35  # seconds between requests (Crossref's public pool allows a few per second)

BOOKISH = {'book', 'monograph', 'edited-book', 'reference-book', 'book-set', 'book-series'}
OK_TYPES = {
    'article': {'journal-article', 'proceedings-article', 'book-chapter', 'posted-content', 'report'},
    'book': BOOKISH,
    'chapter': {'book-chapter', 'book-part', 'book-section', 'reference-entry', 'journal-article', 'other'},
    'other': None,  # anything
}


def ascii_lower(s):
    return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()


def norm_title(s):
    s = re.sub(r'<[^>]+>', ' ', html.unescape(s or ''))
    s = ascii_lower(s).replace('&', ' and ')
    s = re.sub(r'[^a-z0-9 ]+', ' ', s)
    s = re.sub(r'^(the|a|an) ', '', ' '.join(s.split()))
    return s


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


def title_score(rt, it):
    t = (it.get('title') or [''])[0]
    sub = (it.get('subtitle') or [''])[0]
    full = f'{t}: {sub}' if sub else t
    a = norm_title(rt)
    best = 0.0
    for c in {norm_title(t), norm_title(full)}:
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
    if s < 0.75:
        return s, None, 'title'
    sn, names = surname(r), item_names(it)
    author_ok = bool(sn) and any(sn == n or (len(sn) > 3 and (n.endswith(sn) or sn.endswith(n)) and len(n) > 3) for n in names)
    if names and not author_ok:
        return s, None, 'author'
    y, ys = year_of(r.get('year')), item_years(it)
    gap = min((abs(y - v) for v in ys), default=99) if y else 99
    types = OK_TYPES.get(r.get('type'), None)
    type_ok = types is None or it.get('type') in types
    if r.get('type') != 'book' and it.get('type') in BOOKISH and r.get('type') != 'other':
        type_ok = False
    reasons = []
    if s < 0.9:
        reasons.append(f'title {s:.2f}')
    if gap > 1:
        reasons.append(f'year {sorted(ys)}')
    if not type_ok:
        reasons.append(f"type {it.get('type')}")
    if not names:
        if s >= 0.95 and gap == 0 and type_ok:
            return s, 'accept', 'no authors on record'
        reasons.append('no authors on record')
    if not reasons:
        return s, 'accept', ''
    return s, 'review', '; '.join(reasons)


def best_match(r, items):
    acc, rev = [], []
    for it in items:
        s, v, why = judge(r, it)
        y = year_of(r.get('year'))
        exact = 1 if y in item_years(it) else 0
        if v == 'accept':
            acc.append((s, exact, it))
        elif v == 'review':
            rev.append((s, exact, it, why))
    if acc:
        acc.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return acc[0][2]['DOI'].lower(), None
    if rev:
        rev.sort(key=lambda x: (x[0], x[1]), reverse=True)
        s, _, it, why = rev[0]
        return '', {'doi': it['DOI'].lower(), 'record': f"{(it.get('title') or [''])[0]} ({sorted(item_years(it))}, {it.get('type')})",
                    'score': round(s, 3), 'why': why}
    return '', None


_last = [0.0]


def query(r):
    q = ' '.join(x for x in (r.get('title', ''), surname(r), str(year_of(r.get('year')) or '')) if x)
    url = API + '?' + urllib.parse.urlencode({'query.bibliographic': q, 'rows': 5, 'select': FIELDS})
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
    assert best_match(book, [reprint]) [0] == '' and best_match(book, [reprint])[1]['why'].startswith('year')
    sub = {'authors': ['Uzzi, B.'], 'year': '1997', 'type': 'article', 'title': 'Social structure and competition in interfirm networks'}
    it = {'DOI': '10.2307/2393808', 'title': ['Social Structure and Competition in Interfirm Networks'],
          'subtitle': ['The Paradox of Embeddedness'], 'author': [{'family': 'Uzzi'}], 'issued': {'date-parts': [[1997, 3]]},
          'type': 'journal-article'}
    assert best_match(sub, [it])[0] == '10.2307/2393808'
    print('selftest ok')


def main():
    args = sys.argv[1:]
    if '--selftest' in args:
        return selftest()
    limit = int(args[args.index('--limit') + 1]) if '--limit' in args else None
    retry = '--retry-missing' in args
    d = json.load(open(D + 'classified.json'))
    rs = sorted((r for r in d['readings'] if not r.get('drop')), key=lambda r: -r['n'])
    out = json.load(open(D + 'dois.json')) if os.path.exists(D + 'dois.json') else {}
    review = json.load(open(D + 'dois_review.json')) if os.path.exists(D + 'dois_review.json') else {}
    todo = [r for r in rs if reading_key(r) not in out or (retry and not out[reading_key(r)])]
    todo = list({reading_key(r): r for r in todo}.values())[:limit]
    print(f'{len(todo)} to look up; {sum(1 for v in out.values() if v)} DOIs already stored')

    def save():
        json.dump(dict(sorted(out.items())), open(D + 'dois.json', 'w'), ensure_ascii=False, indent=0)
        json.dump(dict(sorted(review.items())), open(D + 'dois_review.json', 'w'), ensure_ascii=False, indent=1)

    found = 0
    try:
        for i, r in enumerate(todo, 1):
            k = reading_key(r)
            doi, rev = best_match(r, query(r))
            out[k] = doi
            found += bool(doi)
            if rev:
                review[k] = dict(rev, reading=f"{'; '.join(r['authors'][:3])} ({r['year']}). {r['title']}. {r['venue']} [{r['type']}]")
            else:
                review.pop(k, None)
            if i % 25 == 0:
                save()
                print(f'  {i}/{len(todo)}  found {found}', flush=True)
    finally:
        save()
    print(f'done: {found} of {len(todo)} found; {sum(1 for v in out.values() if v)} DOIs stored; {len(review)} to review')


if __name__ == '__main__':
    main()
