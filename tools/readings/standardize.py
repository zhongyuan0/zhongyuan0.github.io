"""Put every reading's reference in one format (close to APA 7) and merge readings that share a DOI.

Usage: python3 tools/readings/standardize.py
Reads classified.json, dois.json, .cache/works.json (from works.py) and fixes.json; writes standardized.json, which
build_page.py uses. Each reading keeps its original fields (so reading_key and the sub-stream assignments still
match) and gains `ref`: the fields to print.

- Readings with a DOI take authors, title, journal, volume, issue and pages from the Crossref record. The year is
  the print year; when Crossref only has an online date far from the syllabus year (old Wiley journals were put
  online in 2007), the syllabus year is kept. Books and chapters keep the syllabus year, since a book DOI often
  belongs to a later e-book edition.
- Readings without a DOI are cleaned: initials spaced, page and chapter notes from the syllabi ("Chapters 1-3",
  "pp. 1-44", "skim") removed, publisher locations dropped, journal volume and pages parsed.
- fixes.json (by reading_key) fills or corrects fields by hand: any of authors, year, title, venue, type.
"""
import collections, difflib, html, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from subtopics import reading_key

D = os.path.dirname(os.path.abspath(__file__)) + '/'
SMALL = {'a', 'an', 'the', 'and', 'but', 'or', 'nor', 'for', 'on', 'at', 'to', 'from', 'by', 'of', 'in', 'with', 'as', 'vs', 'via', 'into', 'over'}


# ---------- text helpers ----------
def squash(s):
    return re.sub(r'\s+', ' ', s or '').strip()


def clean_markup(s):
    s = re.sub(r'<sup>.*?</sup>', '', s or '', flags=re.S)  # footnote markers
    s = re.sub(r'</scp>\s+(?=[a-z.,;:\'’)])', '</scp>', s)  # small capitals: "<scp>A</scp>\n rnold" is "Arnold"
    s = re.sub(r'(?<=\w)<(i|em|b)>', r' <\1>', s)  # "Publishing in<i>AMJ</i>" keeps its spaces
    s = re.sub(r'</(i|em|b)>(?=\w)', r'</\1> ', s)
    s = re.sub(r'<[^>]+>', '', s)
    return squash(html.unescape(s))


def norm(s):
    s = re.sub(r'[^a-z0-9 ]+', ' ', clean_markup(s).lower().replace('&', ' and '))
    return ' '.join(s.split())


def is_caps(s):
    letters = [c for c in s if c.isalpha()]
    return len(letters) > 8 and sum(c.isupper() for c in letters) / len(letters) > 0.8


def title_case(s):
    out, cap = [], True
    for w in s.lower().split(' '):
        core = re.sub(r'^\W+', '', w)
        if cap or core not in SMALL:
            i = len(w) - len(core)
            w = w[:i] + core[:1].upper() + core[1:]
        out.append(w)
        cap = w.endswith((':', '?', '!', '.', '—'))
    return ' '.join(out)


def dash(pages):
    p = re.sub(r'\s*[-‐‑–—]+\s*', '–', pages.strip())
    a, _, b = p.partition('–')
    return a if a == b else p


LABEL = re.compile(r'^(?:[A-Z][A-Z ]{3,}\s*[—–-]\s*|[A-Z][A-Z ]{3,}\.\s+|\d+\w*\s+Anniversa\w*\s+Article:\s*|chapter\s+\d+[.:]?\s+|\d+\.\s+)', re.I)


def clean_title(t):
    t = clean_markup(t)
    for _ in range(3):  # labels can stack: "RESEARCH NOTES. ..."
        m = LABEL.match(t)
        if not m or len(t) - m.end() < 8:
            break
        lab = m.group(0).strip()
        if lab[0].isdigit() or lab.lower().startswith('chapter') or 'anniversa' in lab.lower() or lab.rstrip('.—–-').strip().isupper():
            t = t[m.end():]
        else:
            break
    t = re.sub(r'^\d{1,2}\s+(?=[A-Z][a-z])', '', t)  # "4 The Physical Environment..." (Annals chapters)
    return re.sub(r'\s*[*†‡]+$', '', t).rstrip(' .')


NOTE = re.compile(r'\s*\((?=[^)]*(?:\bchapters?\b|\bchapt?\.|\bchs?\.|\bch\.|\bchp\b|\bpp?\.\s*\d|\bpages?\b|\bpart\s+[ivx\d]|\bparts?\s+\d|'
                  r'\bskim\b|\bselections?\b|\bappendix\b|\bepilogue\b|\bespecially\b))[^)]*\)', re.I)
RANGES = r'\d+\s*[-–]\s*\d+(?:\s*(?:,|and|&)\s*\d+(?:\s*[-–]\s*\d+)?)*'
TAIL_NOTE = re.compile(r'(?:^|[,.;:]\s*|\s+)(?:(?:especially\s+)?(?:chapters?|chapt?\.?|chs?\.|ch\.)\s*[\divxlc][\w\s,&–\-]*?(?:,\s*[A-Z][\w ]+)?|(?:p?p\.?|pages?)\s*' + RANGES + r'(?:\s*\([^)]*\))?|selections?|skim)\.?\s*$', re.I)
EDITION = re.compile(r'[,.]?\s*\(?\b(\d+)(?:st|nd|rd|th)\.?\s+(?:revised\s+|rev\.\s+|updated\s+)?ed(?:ition|n)?\b\.?\)?\.?|[,.]?\s*\(?\b(second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+edition\)?\.?', re.I)
ORD = {'Second': '2nd', 'Third': '3rd', 'Fourth': '4th', 'Fifth': '5th', 'Sixth': '6th', 'Seventh': '7th', 'Eighth': '8th', 'Ninth': '9th', 'Tenth': '10th'}


def take_edition(s):
    m = EDITION.search(s or '')
    if not m:
        return s, None
    n = m.group(1)
    ed = (n + {'1': 'st', '2': 'nd', '3': 'rd'}.get(n[-1] if n[-2:-1] != '1' else '', 'th') if n else ORD[m.group(2).title()]) + ' ed.'
    before, after = s[:m.start()].rstrip(), s[m.end():].lstrip()
    joint = '. ' if before and after and m.group(0).rstrip().endswith('.') else ' '
    return squash(before + joint + after).strip(' ,.'), ed


def strip_notes(s):
    prev = None
    s = squash(s)
    while prev != s:
        prev = s
        s = NOTE.sub('', s)
        s = TAIL_NOTE.sub('', s).strip(' ,;:')
    return s


PLACE = re.compile(r'^(?:[A-Z][\w.\'’ ]*?(?:,\s*[A-Z][\w.]*\.?)*)\s*:\s*(?=\S)')


def strip_place(v):
    """'Cambridge, MA: Harvard University Press' -> 'Harvard University Press' (APA 7 leaves out the location)."""
    m = PLACE.match(v)
    if m and len(m.group(0)) < 40 and re.search(r'[A-Za-z]', v[m.end():]):
        return v[m.end():]
    return v


def fix_pub(p):
    p = squash(html.unescape(p or ''))
    p = re.sub(r'\bUniv\.(?=\s)', 'University', p)
    p = re.sub(r'(Press)(?=[A-Z])', r'\1 ', p)  # "Oxford University PressOxford"
    return re.sub(r'(University Press|Press)\s+(?:New York|Oxford|Cambridge)[\w ,]*$', r'\1', p)


# ---------- authors ----------
def initials(given):
    parts = []
    for tok in re.split(r'\s+', given.replace('.', '. ').strip()):
        if not tok:
            continue
        sub = [x for x in tok.split('-') if x]
        parts.append('-'.join(x[0].upper() + '.' for x in sub if x[0].isalpha()))
    return ' '.join(p for p in parts if p)


def fmt_person(family, given, suffix='', hint=None):
    family = squash(family)
    if hint and family.lower().endswith(' ' + hint.lower()) and family.lower() != hint.lower():
        given, family = f'{given} {family[:-len(hint)].strip()}', family[-len(hint):]
    if family.isupper() and len(family) > 2:
        family = hint if hint and hint.lower() == family.lower() else family.title()
    s = family + (', ' + initials(given) if given and initials(given) else '')
    return s + (', ' + suffix if suffix else '')


def clean_author(a):
    a = squash(a)
    if a in ('et al.', 'et al'):
        return 'et al.'
    if ',' in a:
        fam, _, giv = a.partition(',')
        giv = giv.strip()
        if re.fullmatch(r"(?:[A-Z]\.?\s*-?\s*)+(?:,?\s*Jr\.?)?", giv) or re.fullmatch(r'[A-Z][a-z]+(?:\s+[A-Z]\.?)*', giv):
            suffix = 'Jr.' if 'Jr' in giv else ''
            return fmt_person(fam, re.sub(r',?\s*Jr\.?', '', giv), suffix)
        return a
    return a


def authors_from_record(it, hint):
    people = [p for p in it.get('author') or [] if (p.get('family') or '').lower() not in ('editor', 'editors')]
    out = []
    for i, p in enumerate(people):
        if p.get('name') and not p.get('family'):
            out.append(squash(p['name']))
        elif p.get('family'):
            out.append(fmt_person(p['family'], p.get('given', ''), p.get('suffix', ''), hint if i == 0 else None))
    return out


# ---------- years ----------
def year_int(s):
    m = re.search(r'(1[6-9]\d\d|20\d\d)', str(s or ''))
    return int(m.group(1)) if m else None


def record_year(it, field):
    try:
        return int(it[field]['date-parts'][0][0])
    except (KeyError, IndexError, TypeError, ValueError):
        return None


# ---------- venues ----------
JOURNAL_VENUE = re.compile(r'^(?P<j>.*?[A-Za-z&].*?)(?:,\s*|\s+)(?:vol\.?\s*)?(?P<v>\d{1,4}|[IVXLC]{1,6})\s*(?:\((?P<i>[^)]{1,30})\))?\s*(?:[:,]\s*(?:pp?\.\s*)?(?P<p>[A-Za-z]?\d+(?:\s*[-–]\s*[A-Za-z]?\d+)?))?\s*\.?$')


def parse_journal(v):
    v = squash(v).rstrip('.')
    m = JOURNAL_VENUE.match(v)
    if m and not re.search(r'\b(?:19|20)\d\d$', m.group('v') or ''):
        return squash(m.group('j')).rstrip(','), m.group('v'), m.group('i'), dash(m.group('p')) if m.group('p') else None
    return v, None, None, None


PUBLISHER = re.compile(r'\b(?:Press|Publications?|Publishing|Publishers|Books|Sage|SAGE|Wiley|Blackwell|Routledge|Elsevier|JAI|Jossey-Bass|Emerald|'
                       r'Springer|Macmillan|Palgrave|Penguin|Norton|Doubleday|Basic|Russell Sage|Harper|Aldine|Polity|Verso|Free Press|Pergamon)\b')
PLACE_TOKEN = re.compile(r"^[A-Z][\w.'’]*(?:\s+[A-Z][\w.'’]*){0,2}(?:;\s*[A-Z][\w.'’]*(?:\s+[A-Z][\w.'’]*){0,2})*$")


def short_name(n):
    """'Walter W. Powell' -> 'W. W. Powell'; leaves names with particles or already in initials alone."""
    toks = n.split()
    suffix = ''
    if len(toks) > 2 and toks[-1] in ('Jr.', 'Jr', 'Sr.', 'II', 'III', 'IV'):
        suffix, toks = ' ' + toks[-1].rstrip('.') + ('.' if toks[-1].startswith(('Jr', 'Sr')) else ''), toks[:-1]
    if 2 <= len(toks) <= 4 and all(t[:1].isupper() for t in toks) and any(re.fullmatch(r'[A-Z][a-z\'’-]+', t) for t in toks[:-1]):
        return ' '.join(t[0] + '.' if not t.endswith('.') else t for t in toks[:-1]) + ' ' + toks[-1] + suffix
    return ' '.join(toks) + suffix


def fmt_eds(e):
    e = re.sub(r'([A-Z]\.)(?=[A-Z])', r'\1 ', squash(e))
    m = re.match(r'^(.*?)\s*(\((?:eds?|editors?)\.?\))$', e, re.I)
    if m:
        names = [short_name(x.strip()) for x in re.split(r',\s*(?:and\s+|&\s*)?|\s+and\s+|\s*&\s*', m[1]) if x.strip()]
        joined = names[0] if len(names) == 1 else (' & '.join(names) if len(names) == 2 else ', '.join(names[:-1]) + ', & ' + names[-1])
        e = joined + ' ' + m[2]
    return re.sub(r'\((eds?|editors?)\.?\)', lambda m: '(Eds.)' if m[1].lower().startswith(('eds', 'editors')) else '(Ed.)', e, flags=re.I)


def clean_chapter_venue(v):
    """APA-style parts of a chapter's 'In EDS (Eds.), BOOK, pp. 1-10. City: Publisher' text: (eds, book, vol, pages, publisher)."""
    v = squash(v).rstrip('.')
    pages = vol = pub = eds = None
    m = re.match(r'^p?p\.?\s*(\d+)\s*[-–]\s*(\d+)\s+in\s+(.*)$', v, re.I)
    if m:
        pages, v = f'{m[1]}–{m[2]}', m[3]
    v = re.sub(r'^In:?\s+', '', v)
    v = re.sub(r'^(?:Chapter|Chp?\.?|Ch\.)\s*\d+[,:]?\s*(?:(?:pp?\.\s*)?(\d+)\s*[-–]\s*(\d+)\s*)?(?:in\s+)?', '', v, flags=re.I)
    m = re.match(r'^(.{3,160}?\((?:[Ee]ds?|[Ee]ditors?)\.?\)),?\s*(.*)$', v)
    if m:
        eds, v = m[1], m[2]
        m2 = re.match(r'^(.*\w{3,})\.\s+([A-Z][a-z]+\s.*)$', eds)  # "BOOK. Full Name, ... (eds.)"
        if m2:
            v = (m2[1] + ('. ' + v if v else '')).strip()
            eds = m2[2]
    if not pages:
        m = (re.search(r'(?:,\s*|\s*\(|:\s*|\.\s*)p?p\.?\s*(\d+)\s*[-–]\s*(\d+)\)?', v, re.I)
             or re.search(r'(?:[:,]\s*)(\d+)\s*[-–]\s*(\d+)\b', v))
        if m:
            pages, v = f'{m[1]}–{m[2]}', (v[:m.start()] + v[m.end():]).strip(' ,.')
    # publisher: "... . City, ST: Publisher" or "..., City: Publisher"
    head, sep, tail = v.rpartition(': ')
    if sep and tail and ':' not in tail and len(tail) < 60 and re.search(r'[A-Za-z]', tail):
        if '. ' in head:
            book_part, _, place = head.rpartition('. ')
        else:
            book_part, place = head, ''
        segs = re.split(r',\s+', place or book_part)
        if place:
            ok = all(PLACE_TOKEN.match(x) for x in segs) and len(place) < 40
        else:
            k = 0
            while k < 2 and len(segs) - k > 1 and PLACE_TOKEN.match(segs[-1 - k]) and len(segs[-1 - k]) < 20:
                k += 1
            ok = k > 0
            book_part = ', '.join(segs[:len(segs) - k])
        if ok:
            pub, v = tail.strip(' .'), book_part.strip(' ,.')
    if not pub:  # "..., Sage Publications" or ". MIT Press" or ", Blackwell Publishers, Malden, MA"
        segs = re.split(r'(?:,|\.)\s+', v)
        k = 0
        while k < 2 and len(segs) - k > 2 and PLACE_TOKEN.match(segs[-1 - k]) and len(segs[-1 - k]) < 20 and not PUBLISHER.search(segs[-1 - k]):
            k += 1
        if k and PUBLISHER.search(segs[-1 - k]):
            v = re.sub(r'(?:,\s*[^,]+){%d}$' % k, '', v)
            segs = re.split(r'(?:,|\.)\s+', v)
        if len(segs) > 1 and PUBLISHER.search(segs[-1]) and len(segs[-1]) < 45:
            pub = segs[-1].strip(' .')
            v = v[:len(v) - len(segs[-1])].strip(' ,.')
    m = re.search(r',\s*([^,]{2,60}\((?:[Ee]ds?|[Ee]ditors?)\.?\))$', v)  # "BOOK, D. Teece (Ed.)"
    if m and not eds:
        eds, v = m[1], v[:m.start()].strip(' ,.')
    m = re.search(r'[.,]\s*(?:[Ee]dited by|[Ee]ds?\.)\s+(.+)$', v)
    if m:
        names = m[1].strip(' .')
        v = v[:m.start()].strip(' ,.')
        if not eds and names:
            eds = names + (' (Eds.)' if re.search(r'\band\b|&', names) else ' (Ed.)')
    v = strip_notes(v)
    m = re.search(r'(?:,\s*(?:Vol\.?\s*|Volume\s+)?|\s+Vol\.?\s*|\s+)(\d{1,3})$', v)
    if m:
        vol, v = m[1], v[:m.start()].strip(' ,.')
    v, ed = take_edition(v)
    pub = re.sub(r'\s*\((?:forthcoming|in press)\)', '', pub or '', flags=re.I).strip(' .') or None
    return (fmt_eds(eds) if eds else None), v.strip(' ,.'), vol, pages, (fix_pub(pub) if pub else None), ed


# ---------- one reading ----------
def standardize(r, it, journals_alias):
    rtype = r['type']
    syear = squash(r.get('year')) or ''
    title, ed = take_edition(strip_notes(clean_markup(r['title'])).rstrip(' .'))
    title = re.sub(r'^(?:Chapter|Ch\.)\s*\d+\s*[:.]\s+', '', title)
    venue = strip_notes(clean_markup(r.get('venue') or '')).rstrip(' .')
    ed2 = None
    if rtype != 'chapter':
        venue, ed2 = take_edition(venue)
    ref = {'authors': [clean_author(a) for a in r['authors'] if squash(a)], 'year': syear, 'title': title, 'kind': rtype,
           'venue': venue, 'edition': ed or ed2}
    hint = (r['authors'][0].split(',')[0].strip() if r['authors'] else None)
    if it:
        itype = it.get('type')
        auth = authors_from_record(it, hint)
        if not auth and it.get('editor') and itype in ('book', 'monograph', 'edited-book', 'reference-book'):
            auth = authors_from_record({'author': it['editor']}, hint)
            ref['editors'] = bool(auth)
        if auth:
            ref['authors'] = auth
        t = clean_title((it.get('title') or [''])[0])
        sub = clean_title((it.get('subtitle') or [''])[0])
        if sub and norm(sub) not in norm(t):
            t = f"{t.rstrip(' :')}: {sub}"
        t, ed3 = take_edition(t)
        ref['edition'] = ref['edition'] or ed3
        if t:
            if is_caps(t):
                own = title
                t = own if own and not is_caps(own) and difflib.SequenceMatcher(None, norm(own), norm(t)).ratio() > 0.75 else title_case(t)
            ref['title'] = t
        print_y, issued_y, sy = record_year(it, 'published-print'), record_year(it, 'issued'), year_int(syear)
        if itype == 'journal-article':
            y = print_y or (issued_y if (sy is None or (issued_y and abs(issued_y - sy) <= 1)) else None)
            ref['year'] = str(y) if y else syear
            j = clean_markup((it.get('container-title') or [''])[0])
            if j and 'ssrn' not in j.lower() and 'proceedings' not in j.lower():
                ref.update(kind='article', venue=journals_alias.get(j, j), volume=it.get('volume'), issue=it.get('issue'),
                           pages=dash(it['page']) if it.get('page') else None)
        elif itype in ('book-chapter', 'book-part', 'book-section', 'reference-entry', 'other') and rtype != 'book':
            ref['kind'] = 'chapter'
            c = clean_markup((it.get('container-title') or [''])[0])
            cw, vw = set(norm(c).split()), set(norm(ref['venue']).split())
            if c and (not ref['venue'] or rtype == 'article' or len(cw & vw) < len(cw) / 2):
                ref.update(eds=None, book=c, vol=it.get('volume'), pages=dash(it['page']) if it.get('page') else None,
                           publisher=fix_pub(it.get('publisher')), venue_done=True)
            elif ref['venue']:
                eds, book, vol, pages, pub, ed4 = clean_chapter_venue(ref['venue'])
                ref.update(eds=eds, book=book, vol=vol, pages=pages or (dash(it['page']) if it.get('page') else None),
                           publisher=pub or fix_pub(it.get('publisher')), venue_done=True, edition=ref['edition'] or ed4)
        elif itype in ('book', 'monograph', 'edited-book', 'reference-book'):
            ref['kind'] = 'book'
            if not ref['venue'] and it.get('publisher'):
                ref['venue'] = fix_pub(it['publisher'])
        elif itype == 'report' and it.get('DOI', '').startswith('10.3386/w'):
            ref.update(kind='other', venue=f"National Bureau of Economic Research Working Paper No. {it['DOI'].split('/w')[-1]}")
        if itype != 'journal-article' and not sy:  # no year in the syllabus: the record's earliest date
            ys = [y for y in (print_y, issued_y) if y]
            ref['year'] = str(min(ys)) if ys else syear
        ref['doi'] = it['DOI'].lower()
    # venues without a record to rely on
    if ref['kind'] == 'article' and 'volume' not in ref:
        j, v, i, p = parse_journal(ref['venue'])
        ref.update(venue=journals_alias.get(j, j), volume=v, issue=i, pages=p)
    elif ref['kind'] == 'book':
        v = ref['venue']
        if ': ' in v:
            v = v.rpartition(': ')[2]
        ref['venue'] = fix_pub(strip_place(v)).strip(' .')
    elif ref['kind'] == 'chapter' and not ref.get('venue_done'):
        eds, book, vol, pages, pub, ed4 = clean_chapter_venue(ref['venue'])
        ref.update(eds=eds, book=book, vol=vol, pages=pages, publisher=pub, edition=ref['edition'] or ed4)
    ref.pop('venue_done', None)
    return ref


def main():
    d = json.load(open(D + 'classified.json'))
    dois = json.load(open(D + 'dois.json'))
    works = json.load(open(D + '.cache/works.json')) if os.path.exists(D + '.cache/works.json') else {}
    fixes = json.load(open(D + 'fixes.json')) if os.path.exists(D + 'fixes.json') else {}
    readings = [r for r in d['readings'] if not r.get('drop')]

    # 1. hand fixes to the source fields (before keys are used for anything else)
    for r in readings:
        f = fixes.get(reading_key(r))
        if f:
            r['fixed'] = f

    # 2. merge readings that share a DOI: keep the most-listed one, pool the sources
    by_doi = collections.defaultdict(list)
    for r in readings:
        doi = (dois.get(reading_key(r)) or '').lower()
        r['doi'] = doi
        if doi:
            by_doi[doi].append(r)
    merged_away = set()
    for doi, group in by_doi.items():
        if len(group) < 2:
            continue
        group.sort(key=lambda r: (-r['n'], r['title']))
        keep = group[0]
        for other in group[1:]:
            keep['courses'] = sorted(set(keep['courses']) | set(other['courses']))
            keep['sessions'] = list(dict.fromkeys((keep.get('sessions') or []) + (other.get('sessions') or [])))
            merged_away.add(id(other))
        keep['n'] = len(keep['courses'])
    readings = [r for r in readings if id(r) not in merged_away]

    # 3. journal names: prefer "Academy of Management Review" over "The Academy of Management Review"
    names = {clean_markup((w.get('container-title') or [''])[0]) for w in works.values()}
    alias = {n: n[4:] for n in names if n.startswith('The ') and n[4:] in names}

    # 4. references
    for r in readings:
        src = dict(r, **{k: v for k, v in (r.get('fixed') or {}).items() if k != 'ref'})
        it = works.get(r['doi']) if r['doi'] else None
        r['ref'] = standardize(src, it, alias)
        r['ref'].update((r.get('fixed') or {}).get('ref', {}))
        if r['doi']:
            r['ref']['doi'] = r['doi']
    # 5. merge readings that now print the same (same first author, year and title), e.g. after hand fixes
    seen, out = {}, []
    for r in sorted(readings, key=lambda r: -r['n']):
        f = r['ref']
        k = (norm((f['authors'] or [''])[0].split(',')[0]), f['year'], norm(f['title']))
        if f['authors'] and k in seen:
            keep = seen[k]
            keep['courses'] = sorted(set(keep['courses']) | set(r['courses']))
            keep['n'] = len(keep['courses'])
            merged_away.add(id(r))
            continue
        seen[k] = r
        out.append(r)
    readings = [r for r in readings if id(r) not in merged_away]
    d['readings'] = readings
    json.dump(d, open(D + 'standardized.json', 'w'), ensure_ascii=False, indent=0)
    kinds = collections.Counter(r['ref']['kind'] for r in readings)
    print(f'readings {len(readings)} (merged {len(merged_away)} duplicates sharing a DOI); kinds {dict(kinds)}; '
          f'no year {sum(1 for r in readings if not year_int(r["ref"]["year"]))}; no author {sum(1 for r in readings if not r["ref"]["authors"])}')


if __name__ == '__main__':
    main()
