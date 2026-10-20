"""Fetch Crossref's full record (authors, title, journal, volume, issue, pages) for every DOI in dois.json.

Usage: python3 tools/readings/works.py
Saves to .cache/works.json (not in git), keyed by lower-case DOI; DOIs already there are skipped.
standardize.py uses these records to write the references in one consistent format.
Needs network access to api.crossref.org (public pool: about five requests a second, one at a time).
"""
import json, os, sys, time, urllib.error, urllib.parse, urllib.request

D = os.path.dirname(os.path.abspath(__file__)) + '/'
CACHE = D + '.cache/works.json'
API = 'https://api.crossref.org/works'
UA = 'zhongyuan0.github.io reading lists (https://zhongyuan0.github.io/readings/; python urllib)'
FIELDS = 'DOI,title,subtitle,author,editor,issued,published-print,published-online,type,container-title,volume,issue,page,publisher'
BATCH = 40


def get(url):
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=60) as f:
                return json.load(f)['message']
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(float(e.headers.get('Retry-After') or 2 ** attempt * 2))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2 ** attempt * 2)
    raise RuntimeError('Crossref did not answer: ' + url)


def main():
    works = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    dois = sorted({v.lower() for v in json.load(open(D + 'dois.json')).values() if v})
    todo = [d for d in dois if d not in works]
    print(f'{len(todo)} of {len(dois)} DOIs to fetch', flush=True)
    batches = [d for d in todo if ',' not in d]
    for i in range(0, len(batches), BATCH):
        chunk = batches[i:i + BATCH]
        url = API + '?' + urllib.parse.urlencode({'filter': ','.join('doi:' + d for d in chunk), 'rows': BATCH * 2, 'select': FIELDS})
        msg = get(url)
        for it in (msg or {}).get('items', []):
            works[it['DOI'].lower()] = it
        time.sleep(0.5)
        if (i // BATCH) % 10 == 0:
            json.dump(works, open(CACHE, 'w'), ensure_ascii=False)
            print(f'  {min(i + BATCH, len(batches))}/{len(batches)}', flush=True)
    for d in [d for d in todo if d not in works]:  # anything the batches missed: one at a time
        it = get(API + '/' + urllib.parse.quote(d, safe=''))
        if it:
            works[d] = {k: it[k] for k in FIELDS.split(',') if k in it}
        time.sleep(0.25)
    json.dump(works, open(CACHE, 'w'), ensure_ascii=False)
    print(f'records: {sum(1 for d in dois if d in works)} of {len(dois)}')


if __name__ == '__main__':
    main()
