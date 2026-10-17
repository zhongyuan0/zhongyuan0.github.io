"""Sub-streams within the larger streams. Order here is display order.

Assignments live in subtopics.json, keyed by reading_key(); readings with no assignment fall under 'other'.
A value of the form '@stream' or '@stream:sub' moves the reading to another stream (used for misfiled readings).
"""
import re, unicodedata

SUBTOPICS = {
    'networks': [
        ('embeddedness', 'Embeddedness and network forms of organization'),
        ('markets', 'Networks and markets'),
        ('ties', 'Strong and weak ties, social capital'),
        ('brokerage', 'Structural holes, brokerage and closure'),
        ('interorg', 'Interorganizational networks, alliances and interlocks'),
        ('intraorg', 'Networks inside organizations and careers'),
        ('formation', 'Homophily and how networks form'),
        ('diffusion', 'Diffusion and contagion'),
        ('centrality', 'Centrality, power and exchange'),
        ('roles', 'Roles, positions and duality'),
        ('topology', 'Small worlds and network topology'),
        ('relational', 'Relational sociology: networks, culture, identity and fields'),
    ],
    'institutional': [
        ('foundations', 'Foundations: myth, ceremony and isomorphism'),
        ('legitimacy', 'Legitimacy and decoupling'),
        ('diffusion', 'Diffusion, adoption and translation of practices'),
        ('logics', 'Institutional logics and complexity'),
        ('change', 'Institutional change, entrepreneurship, work and microfoundations'),
        ('fields', 'Organizational fields, communities and world society'),
        ('law', 'Law, regulation and the state'),
        ('national', 'National business systems and comparative institutions'),
        ('ibv', 'The institution-based view and emerging markets'),
    ],
    'culture': [
        ('foundations', 'Culture and cognition: foundations'),
        ('sensemaking', 'Sensemaking and enactment'),
        ('cognition', 'Managerial and strategic cognition'),
        ('symbolic', 'Impression and symbolic management'),
        ('discourse', 'Discourse, rhetoric and narrative'),
        ('orgculture', 'Culture in organizations and groups'),
        ('practice', 'Practice, materiality and technology'),
        ('production', 'Production and consumption of culture'),
        ('meaning', 'Meaning, boundaries and evaluation in social life'),
    ],
    'entre': [
        ('theory', 'The entrepreneur and opportunity: theories'),
        ('founding', 'Founding and early growth of new ventures'),
        ('resources', 'Resources, social capital and founding teams'),
        ('finance', 'Entrepreneurial finance and venture capital'),
        ('corporate', 'Corporate entrepreneurship and spinoffs'),
        ('social', 'Social entrepreneurship and diversity'),
        ('context', 'Entrepreneurship, institutions and the economy'),
    ],
    'evolution': [
        ('evolutionary', 'Evolutionary economics and routines'),
        ('techchange', 'Technological change and discontinuities'),
        ('innovation', 'Innovation in firms: search, knowledge and R&D'),
        ('creativity', 'Creativity in individuals and teams'),
        ('ecosystems', 'Business models, platforms and ecosystems'),
        ('managerial', 'Organizational and managerial innovation'),
    ],
    'orgecon': [
        ('firm', 'Theory of the firm and its boundaries'),
        ('tce', 'Transaction cost economics'),
        ('agency', 'Agency theory and corporate control'),
        ('contracts', 'Property rights and incomplete contracts'),
        ('design', 'Incentives, hierarchy and organizational design'),
        ('critique', 'Assessments and critiques'),
    ],
    'carnegie': [
        ('foundations', 'Foundations: the behavioral theory of the firm'),
        ('bounded', 'Bounded rationality, goals, coalitions and decision making'),
        ('feedback', 'Aspirations and performance feedback'),
        ('learning', 'Organizational learning'),
        ('exploration', 'Exploration and exploitation'),
        ('knowledge', 'Knowledge, absorptive capacity and transfer'),
        ('attention', 'Cognition, attention, search and adaptation'),
    ],
    'stratecon': [
        ('field', 'What strategy is: the field and its foundations'),
        ('industry', 'Industry structure and positioning'),
        ('competition', 'Competitive dynamics and game theory'),
        ('value', 'Value creation and capture'),
        ('performance', 'Firm heterogeneity and performance'),
    ],
    'methods': [
        ('design', 'Qualitative research design and theory building'),
        ('ethnography', 'Ethnography and fieldwork'),
        ('interviewing', 'Interviewing and sampling'),
        ('archival', 'Archival, visual and online data'),
        ('mixed', 'Mixed methods and data analysis'),
        ('quant', 'Quantitative methods and experiments'),
    ],
}
OTHER = ('other', 'Other readings')


def reading_key(r):
    a = (r.get('authors') or [''])[0]
    s = a.split(',')[0] if ',' in a else (a.split()[-1] if a.split() else '')
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z]', '', s)
    y = (re.search(r'(1[89]\d\d|20\d\d)', r.get('year') or '') or [''])[0]
    t = unicodedata.normalize('NFKD', r.get('title') or '').encode('ascii', 'ignore').decode().lower()
    t = re.sub(r'[^a-z0-9 ]+', ' ', t)
    t = '-'.join(t.split()[:8])
    return f'{s}|{y}|{t}'
