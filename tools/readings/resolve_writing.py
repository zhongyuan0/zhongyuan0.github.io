"""Look up each item of writing_seed.py on Crossref and write writing.json (checked by hand afterwards).

Usage: python3 tools/readings/resolve_writing.py        (items already in writing.json with a doi or venue are kept)
"""
import json, os, sys, time, urllib.error, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from writing_seed import ITEMS, SECTIONS
from dois import norm_title, title_score, item_names, item_years, UA, FIELDS

D = os.path.dirname(os.path.abspath(__file__)) + '/'
OUT = D + 'writing.json'


def query(title, author, year):
    url = 'https://api.crossref.org/works?' + urllib.parse.urlencode(
        {'query.bibliographic': f'{title} {author} {year}', 'rows': 4, 'select': FIELDS})
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as f:
                return json.load(f)['message']['items']
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            time.sleep(float(e.headers.get('Retry-After') or 3 * (attempt + 1)))
    return []


def main():
    old = {(it['section'], it['title']): it for it in json.load(open(OUT))['items']} if os.path.exists(OUT) else {}
    items = []
    for row in ITEMS:
        section, author, year, title, note = row[:5]
        venue = row[5] if len(row) > 5 else None
        it = dict(section=section, author=author, year=year, title=title, note=note)
        if venue:
            it['venue'] = venue
        prev = old.get((section, title))
        if prev and (prev.get('doi') or prev.get('venue')):
            items.append(prev)
            continue
        if not venue:
            best = None
            for cand in query(title, author, year):
                s = title_score(title, cand)
                names = item_names(cand)
                ok_author = any(author.lower().replace('-', '') in n or n in author.lower().replace('-', '') for n in names) if names else True
                ys = item_years(cand)
                if s >= 0.8 and ok_author and (not ys or min(abs(y - year) for y in ys) <= 1 or cand.get('type') == 'journal-article'):
                    if not best or s > best[0]:
                        best = (s, cand)
            if best:
                c = best[1]
                it['doi'] = c['DOI'].lower()
                it['check'] = f"{(c.get('title') or [''])[0][:70]} | {(c.get('container-title') or [''])[0][:30]} | {sorted(item_years(c))} | {c.get('type')} | {best[0]:.2f}"
            else:
                it['check'] = 'NO MATCH'
            time.sleep(1.0)
        items.append(it)
        json.dump({'sections': SECTIONS, 'items': items + [o for k, o in old.items() if k not in {(i['section'], i['title']) for i in items}]}, open(OUT, 'w'), ensure_ascii=False, indent=1)
        print(f"{section:11s} {author:14s} {year} -> {it.get('check', 'book: ' + (venue or ''))}")
    json.dump({'sections': SECTIONS, 'items': items}, open(OUT, 'w'), ensure_ascii=False, indent=1)
    print(len(items), 'items;', sum(1 for i in items if i.get('doi')), 'with a DOI')


if __name__ == '__main__':
    main()
