import os
"""Merge per-syllabus JSON into deduplicated readings with source counts."""
import json, glob, re, sys, unicodedata
from difflib import SequenceMatcher

D = os.path.dirname(os.path.abspath(__file__)) + '/'

STOP = set('a an the of and in on for to from by with at as or is are be its their into toward towards'.split())


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode()
    s = s.lower().replace('&', ' and ')
    return re.sub(r'[^a-z0-9 ]+', ' ', s)


def surname(a):
    a = (a or '').strip()
    if not a:
        return ''
    s = a.split(',')[0] if ',' in a else a.split()[-1]
    return norm(s).strip().split(' ')[-1] if norm(s).strip() else ''


def title_key(t):
    w = [x for x in norm(t).split() if x not in STOP]
    return ' '.join(w)


def year_num(y):
    m = re.search(r'(1[89]\d\d|20\d\d)', y or '')
    return int(m.group(1)) if m else None


courses = []
items = []
for f in sorted(glob.glob(D + 'syllabi/*.json')):
    d = json.load(open(f))
    cid = len(courses)
    courses.append({k: d.get(k, '') for k in ('file', 'course', 'instructor', 'institution', 'term')})
    for r in d['readings']:
        r = dict(r)
        r['cid'] = cid
        items.append(r)

clusters = []  # each: {'first': surname, 'tkey':..., 'year':..., 'members': [...]}
index = {}
for r in items:
    fs = surname((r.get('authors') or [''])[0])
    tk = title_key(r.get('title', ''))
    if not tk:
        continue
    y = year_num(r.get('year'))
    match = None
    for c in index.get(fs, []):
        ratio = SequenceMatcher(None, tk, c['tkey']).ratio()
        short = min(len(tk), len(c['tkey']))
        prefix = short >= 25 and (tk.startswith(c['tkey'][:short]) or c['tkey'].startswith(tk[:short]))
        close_year = y is None or c['year'] is None or abs(y - c['year']) <= 2
        if (ratio >= 0.88 or prefix) and (close_year or ratio >= 0.97):
            match = c
            break
    if match is None:
        match = {'first': fs, 'tkey': tk, 'year': y, 'members': []}
        clusters.append(match)
        index.setdefault(fs, []).append(match)
    match['members'].append(r)

out = []
for c in clusters:
    ms = c['members']
    # representative: the most complete record
    rep = max(ms, key=lambda m: (len(m.get('authors') or []), bool(m.get('venue')), len(m.get('title', ''))))
    cids = sorted({m['cid'] for m in ms})
    out.append({
        'authors': rep.get('authors') or [],
        'year': rep.get('year', ''),
        'title': rep.get('title', ''),
        'venue': rep.get('venue', ''),
        'type': rep.get('type', ''),
        'n': len(cids),
        'courses': cids,
        'sessions': sorted({f"{m['cid']}|{m.get('session','')}" for m in ms}),
    })
out.sort(key=lambda x: (-x['n'], x['authors'][0] if x['authors'] else ''))
json.dump({'courses': courses, 'readings': out}, open(D + 'merged.json', 'w'), ensure_ascii=False, indent=1)
print('courses', len(courses), 'raw items', len(items), 'unique', len(out))
from collections import Counter
print(Counter(min(x['n'], 6) for x in out))
