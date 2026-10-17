"""Sub-streams within the larger streams. Order here is display order.

Assignments live in subtopics.json, keyed by reading_key(); readings with no assignment fall under 'other'.
"""
import re, unicodedata

SUBTOPICS = {
    'networks': [
        ('embeddedness', 'Embeddedness and network forms of organization'),
        ('ties', 'Strong and weak ties, social capital'),
        ('brokerage', 'Structural holes, brokerage and closure'),
        ('interorg', 'Interorganizational networks, alliances and interlocks'),
        ('intraorg', 'Networks inside organizations and careers'),
        ('diffusion', 'Diffusion and contagion'),
        ('structure', 'Network structure: centrality, power, exchange and small worlds'),
        ('formation', 'Homophily and how networks form'),
    ],
    'institutional': [
        ('foundations', 'Foundations: myth, ceremony and isomorphism'),
        ('legitimacy', 'Legitimacy and decoupling'),
        ('diffusion', 'Diffusion and adoption of practices'),
        ('logics', 'Institutional logics and complexity'),
        ('change', 'Institutional change, entrepreneurship and work'),
        ('fields', 'Organizational fields and world society'),
        ('comparative', 'Comparative institutions and the institution-based view'),
    ],
    'culture': [
        ('foundations', 'Culture and cognition: foundations'),
        ('sensemaking', 'Sensemaking and enactment'),
        ('framing', 'Framing, rhetoric and symbolic management'),
        ('orgculture', 'Organizational culture and control'),
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
        ('bounded', 'Bounded rationality and decision making'),
        ('feedback', 'Aspirations and performance feedback'),
        ('learning', 'Organizational learning'),
        ('exploration', 'Exploration and exploitation'),
        ('knowledge', 'Knowledge, absorptive capacity and transfer'),
        ('attention', 'Attention, search and adaptation'),
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
