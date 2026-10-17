import os
import json, re, collections

D = os.path.dirname(os.path.abspath(__file__)) + '/'

TOPICS = [
    ('theory', 'Theory and theorizing', 'What counts as theory, how theoretical contributions are made, and the state of the field.'),
    ('classics', 'Classical foundations', 'Bureaucracy, rational, natural and open systems, and the early classics of organization theory.'),
    ('contingency', 'Contingency and configurational theory', 'Fit between structure, strategy and environment.'),
    ('carnegie', 'Behavioral theory of the firm and organizational learning', 'The Carnegie School: bounded rationality, aspirations, search, routines and learning.'),
    ('evolution', 'Evolutionary theory, technology and innovation', 'Routines, technological change, innovation and industry dynamics.'),
    ('rdt', 'Resource dependence and power', 'Interdependence, power and how organizations manage their environments.'),
    ('ecology', 'Organizational ecology and demography', 'Founding, mortality, inertia, niches and density dependence.'),
    ('institutional', 'Institutional theory', 'Isomorphism, legitimacy, diffusion, institutional change, logics and entrepreneurship.'),
    ('networks', 'Social networks and embeddedness', 'Embeddedness, weak ties, structural holes, brokerage and interorganizational networks.'),
    ('status', 'Status and social evaluation', 'Status, reputation, and how audiences evaluate actors in markets.'),
    ('categories', 'Categories, identity and authenticity', 'Market categories, organizational identity and authenticity.'),
    ('culture', 'Culture, cognition and sensemaking', 'Culture, sensemaking, framing and symbolic management.'),
    ('movements', 'Social movements, power and inequality', 'Social movements, politics, elites, conflict and inequality.'),
    ('work', 'Work, occupations and careers', 'Professions, occupations, careers, gender and human capital.'),
    ('entre', 'Entrepreneurship and new organizations', 'Founding and early development of new organizations.'),
    ('orgecon', 'Organizational economics', 'Theory of the firm, transaction costs, agency and property rights.'),
    ('rbv', 'Resource-based view and capabilities', 'Resources, knowledge and dynamic capabilities as sources of advantage.'),
    ('stratecon', 'Economic perspectives on strategy', 'Industrial organization, competitive dynamics, signaling and real options.'),
    ('stratproc', 'Strategy process, practice and cognition', 'Strategic decision making, managerial cognition, strategy as practice and rhetoric.'),
    ('corporate', 'Corporate strategy and interfirm relationships', 'Diversification, M&A, alliances and interfirm exchange.'),
    ('governance', 'Corporate governance and upper echelons', 'Boards, top management teams, executives and shareholders.'),
    ('nonmarket', 'Nonmarket strategy and corporate social responsibility', 'Political strategy, stakeholders, CSR and the moral economy.'),
    ('international', 'International business and multinationals', 'Internationalization, MNEs, FDI, trade and institutions across countries.'),
    ('socialtheory', 'Social theory', 'General sociological theory: action, structure, rational choice, critical theory and their successors.'),
    ('methods', 'Research methods', 'Qualitative and field methods, research design and data for organizational research.'),
    ('profession', 'The academic profession', 'Publishing, writing and management scholarship as a profession.'),
]
GENERIC = 'generic'

# (regex on session heading, topic). First match wins. Order matters.
RULES = [
    (r'qualitative|ethnograph|interviewing|theoretical sampling|visual methods|mixed methods|deductive inductive|method papers|experiments in entrepreneurship|high-frequency data|getting started', 'methods'),
    (r'microsociolog|habermas|postmodern|complex system|visions of theory|individualism and rational choice|structuralism|conflict theory|parsons', 'socialtheory'),
    (r'bourdieu|cultural consumption|programs and prescriptions|meanings? and meaning', 'culture'),
    (r'entrepreneur|startups|founding of new|founders|origins i', 'entre'),
    (r'key concepts and themes|reference resources|world society|decoupling|organizational field|institutional school|national institutions', 'institutional'),
    (r'social capital|centrality|properties of nodes|mutual support|friendship|small worlds|random graphs|algebras|probability models|peer effects|contagion|diffusion|economic relations|learning and information aggregation', 'networks'),
    (r'market competition|positioning and value|what is strategy|industry and market structure|strategic choices|productivity, management practices|non-profit or governmental', 'stratecon'),
    (r'organizational capabilities', 'rbv'),
    (r'behavioral strategy|social and cognitive processes', 'stratproc'),
    (r'organizational decision-making|knowledge and learning', 'carnegie'),
    (r'creativity', 'evolution'),
    (r'models of competition i: ecolog', 'ecology'),
    (r'stratification|labor markets', 'work'),
    (r'modern corporation and power|power and purpose|values, ideology', 'movements'),
    (r'identity and impression', 'categories'),
    (r'division of labor|rationalization|human relations|natural system|rational system|sociological foundations of management', 'classics'),
    (r'appendix 5|useful references|final paper|publishing|writing theory|course requirements', 'profession'),
    (r'publishing game|rigor-relevance|search for impact|process and professionalism|social/intellectual movement|global competition in management scholarship|overview of management scholarship|programmatic research', 'profession'),
    (r'what is theory|theoretical contribution|research on organizational theory|philosophy of science|theorizing strategy|future of organization theory', 'theory'),
    (r'appendix 1|appendix 2|recommended books|required texts|textbooks|books and materials|omitted topics|^s1\. overview|introduction|overview|contemporary topics|organization and interactive', GENERIC),
    (r'bureaucracy|classical management|rational models|natural models', 'classics'),
    (r'contingency theory, carnegie school, and resource dependence theory - carnegie', 'carnegie'),
    (r'contingency theory, carnegie school, and resource dependence theory - resource', 'rdt'),
    (r'contingency theory, carnegie school', 'contingency'),
    (r'early classics: contingency', 'contingency'),
    (r'contingency and configurational|configurational approaches|contingency theory \(the first', 'contingency'),
    (r'^session 2: contingency|contingency theory$|stakeholder, stewardship, and contingency', 'contingency'),
    (r'behavioral decision|carnegie|behavioral theory|organizational learning|exploration and exploitation|theories of choice|problem of goals|learning perspectives|capability and learning|evolutionary and learning', 'carnegie'),
    (r'evolutionary theory|technolog|innovation|digitalization|technological change|firm and industry dynamics', 'evolution'),
    (r'resource dependen|power-dependence|power \(i\)|power and issues|resource dependence and power', 'rdt'),
    (r'ecology|organizational demography', 'ecology'),
    (r'institutional logic|institutionalism|institutional theory|institutional perspective|institution-based view|sociological perspective of institutional|institutions? of the markets|institutional entrepreneurship|legitimacy, fairness', 'institutional'),
    (r'network|embeddedness|structuralist|brokerage', 'networks'),
    (r'status|signaling|stigma', 'status'),
    (r'categor|identity and authenticity|cognition and identity', 'categories'),
    (r'culture|cognition|sense-?making|framing|cultural approaches|rhetoric|discourse|practice theory', 'culture'),
    (r'social movement|power relations|elite theory|political sociology|contested', 'movements'),
    (r'professions|occupations|jobs and careers|gender|human capital|employment, and career', 'work'),
    (r'entrepreneurship and organizational founding', 'entre'),
    (r'transaction cost|agency|property rights|economics of organization|organizational economics|markets and hierarchies|boundaries of the firm|firm boundaries|capital allocation|aggregation of knowledge|interdependent systems|organizational forms and collective|views of production', 'orgecon'),
    (r'resource[- ]based|resources and rent|knowledge-based view|dynamic capabilities|upper echelon', 'rbv'),
    (r'economics-based perspectives|industrial organization|competitive dynamics|real options|economic theories of strategy|theories of strategic management|foundation theories of strategy|airport business books|mba curriculum|introduction to the field of strategic', 'stratecon'),
    (r'strategy process|strategy as practice|strategic decision process|behavioral and cognitive perspectives|strategic change|cognitive perspectives of technology', 'stratproc'),
    (r'diversif|alliance|interfirm|mergers|vertical integration|b2g|contracting', 'corporate'),
    (r'governance|boards of directors', 'governance'),
    (r'non-?market|political strategy|political institutions|social responsibility|moral market|competition, politics, and regulation|corporate political', 'nonmarket'),
    (r'international|multinational|fdi|mode of entry|trade|immigration|spillovers|mncs|internationalization|global', 'international'),
]

# keyword fallback for readings that appear only under generic headings
KEYWORDS = [
    (r'theory is not|what theory|interesting|theory building|theoretical contribution|good theory|theorizing', 'theory'),
    (r'bureaucra|administrative behavior|functions of the executive|organizations in action|social psychology of organizations|organizations: rational|management and the worker|scientific management|organizations\b$', 'classics'),
    (r'behavioral theory|bounded|learning|routine|search|aspiration|decision', 'carnegie'),
    (r'ecolog|population|density|inertia|founding|mortality', 'ecology'),
    (r'institution|legitima|isomorphism|logics', 'institutional'),
    (r'network|ties|structural holes|embedded|social capital', 'networks'),
    (r'status', 'status'),
    (r'categor|identity|authentic', 'categories'),
    (r'external control|resource dependence|power', 'rdt'),
    (r'transaction|agency|theory of the firm|nature of the firm|markets and hierarchies|economic institutions of capitalism|property rights|contracts?\b', 'orgecon'),
    (r'resource-based|resources|capabilit|growth of the firm|competitive advantage', 'rbv'),
    (r'evolutionary|innovation|technolog', 'evolution'),
    (r'competitive strategy|industr|strategy|strategic', 'stratecon'),
    (r'environment|contingency|design', 'contingency'),
    (r'culture|sensemaking|making sense|cognition|symbolic', 'culture'),
    (r'movement|elite|inequality|class|politic', 'movements'),
    (r'career|occupation|profession|labor|gender', 'work'),
    (r'entrepreneur', 'entre'),
    (r'governance|board|executive|ceo', 'governance'),
    (r'stakeholder|social responsibility|csr', 'nonmarket'),
    (r'international|multinational|foreign|global|trade', 'international'),
    (r'writing|publish|research design|case study|methods|journal', 'profession'),
]


# Fallback stream for headings no rule recognizes, by course title.
COURSE_DEFAULT = [
    (r'innovation|creativity', 'evolution'), (r'entrepreneurship', 'entre'), (r'social networks|economic networks', 'networks'),
    (r'neo-institutional', 'institutional'), (r'qualitative|prosem', 'methods'), (r'contemporary theory', 'socialtheory'),
    (r'sociology of culture', 'culture'), (r'strategy', 'stratecon'),
]


def topic_for_session(h, course=''):
    t = h.lower()
    for rx, k in RULES:
        if re.search(rx, t):
            return k
    for rx, k in COURSE_DEFAULT:
        if re.search(rx, course.lower()):
            return k
    return None


def main():
    d = json.load(open(D + 'merged.json'))
    unmatched = collections.Counter()
    for r in d['readings']:
        votes = collections.Counter()
        for s in r['sessions']:
            cid, h = s.split('|', 1)
            k = topic_for_session(h, d['courses'][int(cid)]['course'])
            if k is None:
                unmatched[s] += 1
                continue
            if k != GENERIC:
                votes[k] += 1
        if votes:
            top = votes.most_common()
            best = top[0][1]
            r['topic'] = sorted(k for k, v in top if v == best)[0] if len(top) > 1 and top[1][1] == best else top[0][0]
            r['how'] = 'session'
        else:
            t = (r['title'] + ' ' + (r.get('venue') or '')).lower()
            r['topic'] = next((k for rx, k in KEYWORDS if re.search(rx, r['title'].lower())), 'classics')
            r['how'] = 'keyword'
    json.dump(d, open(D + 'classified.json', 'w'), ensure_ascii=False, indent=1)
    print('unmatched sessions:', len(unmatched))
    for s, n in unmatched.most_common():
        print('  ', n, s[:100])
    c = collections.Counter(r['topic'] for r in d['readings'])
    names = {k: n for k, n, _ in TOPICS}
    for k, _, _ in TOPICS:
        print(f'{c[k]:4d}  {names[k]}')
    print('keyword-assigned:', sum(r['how'] == 'keyword' for r in d['readings']))


if __name__ == '__main__':
    main()

OVERRIDES = {  # (first-author surname, year) -> topic, for readings outside any topical session
    ('pfeffer', '1997'): 'theory', ('davis', '2015'): 'theory', ('hedstrom', '1998'): 'theory',
    ('smith', '2005'): 'theory', ('davis', '2017'): 'theory', ('hinings', '2002'): 'theory',
    ('lounsbury', '2015'): 'theory', ('march', '1997'): 'theory', ('kuhn', '1970'): 'theory',
    ('shenhav', '2003'): 'theory', ('scott', '2004'): 'theory', ('burrell', '1979'): 'theory',
    ('fligstein', '2001'): 'theory', ('zuckerman', '2010'): 'theory', ('scott', '2006'): 'theory',
    ('ashford', '2013'): 'profession', ('bansal', '2012'): 'profession', ('varadarajan', '1996'): 'profession',
    ('turco', '2011'): 'profession',
    ('weick', '1995'): 'culture', ('ouchi', '1980'): 'orgecon', ('hirshleifer', '1999'): 'orgecon',
    ('williamson', '1985'): 'orgecon', ('williamson', '1996'): 'orgecon', ('reitzig', '2015'): 'orgecon',
    ('salganik', '2008'): 'status', ('chandler', '1990'): 'stratecon', ('child', '1972'): 'contingency',
    ('bartlett', '1989'): 'international', ('north', '2005'): 'institutional',
    ('bureau', '2019'): 'international', ('melitz', '2003'): 'international', ('woodhouse', '2006'): 'international',
    ('henisz', '2018'): 'nonmarket', ('hill', '1998'): 'nonmarket', ('henisz', '2016'): 'nonmarket',
    ('lifshitz', '2017'): 'evolution', ('mintzberg', '2008'): 'stratproc', ('augier', '2005'): 'carnegie',
    ('penrose', '2009'): 'rbv', ('penrose', '1959'): 'rbv', ('barney', '1986'): 'rbv', ('podolny', '1993'): 'status',
    ('amit', '1993'): 'entre', ('bono', '2011'): 'profession', ('dodds', '2003'): 'networks', ('erdos', '1960'): 'networks',
    ('fisher', '1989'): 'stratecon', ('gartner', '1985'): 'entre', ('haidt', '2001'): 'culture', ('katz', '1988'): 'entre',
    ('kilduff', '2003'): 'networks', ('knight', '1921'): 'entre', ('mcclelland', '1961'): 'entre', ('mcgee', '1986'): 'stratecon',
    ('schumpeter', '1947'): 'entre', ('suddaby', '2011'): 'theory', ('carroll', '1993'): 'stratecon', ('cannella', '1994'): 'theory',
    ('berger', '1991'): 'culture', ('barnett', '2012'): 'status', ('barney', '1989'): 'rbv',
}


def apply_overrides():
    import unicodedata
    d = json.load(open(D + 'classified.json'))
    hits = 0
    for r in d['readings']:
        a = (r['authors'] or [''])[0]
        s = (a.split(',')[0] if ',' in a else a.split()[-1] if a else '').lower()
        s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
        s = re.sub(r'[^a-z]', '', s)
        y = re.sub(r'\D', '', r['year'] or '')[:4]
        key = next((k for k in OVERRIDES if s.startswith(k[0]) and y == k[1]), None)
        if key and (r['how'] == 'keyword' or key in {('penrose', '2009'), ('barney', '1986'), ('podolny', '1993')}):
            r['topic'] = OVERRIDES[key]; hits += 1
        if 'boundaries of the firm revisited' in r['title'].lower():
            r['authors'] = ['Holmström, B.', 'Roberts, J.']
    json.dump(d, open(D + 'classified.json', 'w'), ensure_ascii=False, indent=1)
    print('overrides applied', hits)


# Courses whose readings are mostly economics (trade, FDI, network economics). Their readings are kept
# only if another syllabus also lists them, or they appeared in a management or sociology outlet.
ECON_COURSE_PAT = r'Multinational Firms in the Global Economy|Social and Economic Networks'
MGMT_VENUES = (r'management|organization|administrative science|strateg|sociolog|business|academy|journal of '
               r'international business|research policy|entrepreneur|industrial and corporate change|harvard business|'
               r'california management|sloan|annual review of sociology|social networks|social forces|science\b')


def mark_drops():
    d = json.load(open(D + 'classified.json'))
    econ = {i for i, c in enumerate(d['courses']) if re.search(ECON_COURSE_PAT, c['course'])}
    dropped = 0
    math = re.compile(r'random graphs|algebras|probability models|advanced module')
    for r in d['readings']:
        if set(r['courses']) <= econ and not re.search(MGMT_VENUES, (r.get('venue') or '').lower()):
            r['drop'] = True
            dropped += 1
        elif all(math.search(x.split('|', 1)[1].lower()) for x in r['sessions']):
            r['drop'] = True  # mathematical network modelling, out of scope
            dropped += 1
    json.dump(d, open(D + 'classified.json', 'w'), ensure_ascii=False, indent=1)
    print('dropped (economics-only)', dropped)


if __name__ == '__main__':
    apply_overrides()
    mark_drops()
