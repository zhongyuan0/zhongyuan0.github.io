"""Theory tree for the Readings page: streams as nodes, intellectual lineage as edges.

Layout is hand-placed on a 6-column grid. Edit NODES / EDGES to change the tree.
"""
import html

W, H = 1000, 590
COLX = [100, 260, 420, 580, 740, 900]  # column centres
ROWY = {1: 170, 2: 280, 3: 390, 4: 500}
BW, BH = 140, 54  # box size

FAMILIES = [  # column header labels
    (0, 'Environment'), (1, 'Institutions and culture'), (2, 'Relations'),
    (3, 'Behavior and evolution'), (4, 'Strategy'), (5, 'Economics'),
]

# key -> (column index, row, label lines)
NODES = {
    'contingency': (0, 1, ['Contingency', 'theory']),
    'rdt': (0, 2, ['Resource', 'dependence']),
    'ecology': (0, 3, ['Organizational', 'ecology']),
    'entre': (0, 4, ['Entrepreneurship']),
    'culture': (1, 1, ['Culture and', 'cognition']),
    'institutional': (1, 2, ['Institutional', 'theory']),
    'categories': (1, 3, ['Categories and', 'identity']),
    'movements': (1, 4, ['Social movements', 'and power']),
    'networks': (2, 1, ['Social', 'networks']),
    'status': (2, 2, ['Status and', 'evaluation']),
    'work': (2, 3, ['Work and', 'careers']),
    'nonmarket': (2, 4, ['Nonmarket', 'strategy and CSR']),
    'carnegie': (3, 1, ['Behavioral theory', 'and learning']),
    'evolution': (3, 2, ['Evolution and', 'innovation']),
    'stratproc': (3, 3, ['Strategy process', 'and cognition']),
    'stratecon': (4, 1, ['Economics of', 'strategy']),
    'rbv': (4, 2, ['Resource-based', 'view']),
    'international': (4, 3, ['International', 'business']),
    'orgecon': (5, 1, ['Organizational', 'economics']),
    'corporate': (5, 2, ['Corporate', 'strategy']),
    'governance': (5, 3, ['Corporate', 'governance']),
}

# (from, to, routing). routing: 'v' straight down, 'h' straight across,
# 'side:x' runs down a vertical gap at x, 'fan' from the classics root, 'line' straight.
EDGES = [
    ('socialtheory', 'culture', 'fan'), ('socialtheory', 'networks', 'fan'),
    ('classics', 'contingency', 'fan'),
    ('classics', 'carnegie', 'fan'), ('classics', 'orgecon', 'fan'),
    ('contingency', 'rdt', 'v'), ('contingency', 'ecology', 'side:16'),
    ('ecology', 'entre', 'v'), ('ecology', 'categories', 'h'),
    ('culture', 'institutional', 'v'), ('institutional', 'categories', 'v'),
    ('institutional', 'movements', 'side:180'),
    ('networks', 'status', 'v'), ('status', 'categories', 'line'),
    ('movements', 'nonmarket', 'h'),
    ('carnegie', 'evolution', 'v'), ('carnegie', 'stratproc', 'side:660'),
    ('evolution', 'rbv', 'h'), ('stratecon', 'rbv', 'v'),
    ('orgecon', 'corporate', 'v'), ('orgecon', 'governance', 'side:986'),
    ('orgecon', 'international', 'line'),
]

# Narrative version of each edge, used in the text list and as accessible description.
LINEAGE = {
    ('classics', 'contingency'): 'Open-systems thinking turned attention to fit with the environment.',
    ('socialtheory', 'culture'): 'Weber, Durkheim, Berger and Luckmann on meaning and the social construction of reality.',
    ('socialtheory', 'networks'): 'Simmel and structural sociology on the form of social ties.',
    ('classics', 'carnegie'): 'Barnard and Simon on bounded rationality in administration.',
    ('classics', 'orgecon'): 'Coase asked why firms exist at all.',
    ('contingency', 'rdt'): 'From adapting to the environment to managing dependence on it.',
    ('contingency', 'ecology'): 'From adaptation to selection by the environment.',
    ('ecology', 'entre'): 'Founding rates and the liability of newness.',
    ('ecology', 'categories'): 'Organizational forms as socially coded identities.',
    ('culture', 'institutional'): 'Taken-for-granted meaning becomes structure.',
    ('institutional', 'categories'): 'Classification and identity as institutional processes.',
    ('institutional', 'movements'): 'Contesting and changing institutions.',
    ('networks', 'status'): 'Ties as prisms that signal quality.',
    ('status', 'categories'): 'Audiences evaluate actors through categories.',
    ('movements', 'nonmarket'): 'Firms respond to activists, publics and the state.',
    ('carnegie', 'evolution'): 'Routines and search, scaled up to industries.',
    ('carnegie', 'stratproc'): 'Attention and decision making in strategy.',
    ('evolution', 'rbv'): 'Capabilities and dynamic capabilities.',
    ('stratecon', 'rbv'): 'From industry position to firm-specific resources.',
    ('orgecon', 'corporate'): 'Make-or-buy, alliances and the scope of the firm.',
    ('orgecon', 'governance'): 'Agency problems between owners and managers.',
    ('orgecon', 'international'): 'Internalization theory of the multinational.',
}

ROOTS = {'socialtheory': (260, 62, 'Social theory'), 'classics': (660, 62, 'Classical foundations')}


def box(key):
    c, r, _ = NODES[key]
    return COLX[c], ROWY[r]


def edge_path(a, b, how):
    if a in ROOTS:
        x2, y2 = box(b)
        x1, y1 = ROOTS[a][0], ROOTS[a][1] + 22
        top = y2 - BH / 2
        return f'M{x1},{y1} C{x1},{y1 + 40} {x2},{top - 50} {x2},{top}'
    x1, y1 = box(a)
    x2, y2 = box(b)
    if how == 'v':
        return f'M{x1},{y1 + BH / 2} L{x2},{y2 - BH / 2}'
    if how == 'h':
        return f'M{x1 + BW / 2},{y1} L{x2 - BW / 2},{y2}' if x2 > x1 else f'M{x1 - BW / 2},{y1} L{x2 + BW / 2},{y2}'
    if how.startswith('side:'):
        gx = float(how.split(':')[1])
        sx = x1 + (BW / 2 if gx > x1 else -BW / 2)
        ex = x2 + (BW / 2 if gx > x2 else -BW / 2)
        r = 10
        d = 1 if gx > sx else -1
        return (f'M{sx},{y1} L{gx - d * r},{y1} Q{gx},{y1} {gx},{y1 + r} '
                f'L{gx},{y2 - r} Q{gx},{y2} {gx - (1 if gx > ex else -1) * r},{y2} L{ex},{y2}')
    # straight line between nearest corners
    sx = x1 + (BW / 2 if x2 > x1 else -BW / 2) * 0.6
    sy = y1 + BH / 2
    ex = x2 + (-BW / 2 if x2 > x1 else BW / 2) * 0.6
    ey = y2 - BH / 2
    return f'M{sx},{sy} L{ex},{ey}'


def svg(counts, names, more=None):
    more = more or {}
    e = lambda s: html.escape(s, quote=True)
    out = [f'<svg class="tree" viewBox="0 0 {W} {H}" role="group" aria-labelledby="tree-title tree-desc">',
           '<title id="tree-title">Theory tree</title>',
           '<desc id="tree-desc">Streams of organization theory and strategy, arranged by intellectual tradition and growing from social theory and the classics. '
           'Lines show which streams grew out of which; the list below the tree spells each link out.</desc>',
           '<defs><marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
           '<path d="M0,0 L8,4 L0,8 z" class="tree-arrowhead"/></marker></defs>']
    for c, label in FAMILIES:
        out.append(f'<text class="tree-family" x="{COLX[c]}" y="128" text-anchor="middle">{e(label)}</text>')
    for a, b, how in EDGES:
        out.append(f'<path class="tree-edge" d="{edge_path(a, b, how)}" marker-end="url(#arrow)"><title>{e(LINEAGE[(a, b)])}</title></path>')
    for key, (rx, ry, label) in ROOTS.items():
        n = counts.get(key, 0)
        href, sub = (f'#{key}', f'{n} reading' + ('s' if n != 1 else '')) if n else (f'/readings/more/#{key}', f'{more.get(key, 0)} further readings')
        out.append(f'<a href="{href}" class="tree-node tree-root"><rect x="{rx - 100}" y="{ry - 22}" width="200" height="44" rx="4"/>'
                   f'<text x="{rx}" y="{ry - 1}" text-anchor="middle">{e(label)}</text>'
                   f'<text class="tree-count" x="{rx}" y="{ry + 15}" text-anchor="middle">{sub}</text></a>')
    for key, (c, r, lines) in NODES.items():
        x, y = COLX[c], ROWY[r]
        out.append(f'<a href="#{key}" class="tree-node"><rect x="{x - BW / 2}" y="{y - BH / 2}" width="{BW}" height="{BH}" rx="4"/>')
        top = y - (8 if len(lines) == 2 else 0) - 4
        for i, ln in enumerate(lines):
            out.append(f'<text x="{x}" y="{top + i * 16}" text-anchor="middle">{e(ln)}</text>')
        out.append(f'<text class="tree-count" x="{x}" y="{top + len(lines) * 16 + 1}" text-anchor="middle">{counts.get(key, 0)}</text></a>')
    out.append('</svg>')
    return ''.join(out)


def lineage_list(names):
    e = lambda s: html.escape(s, quote=False)
    items = ''.join(
        f'            <li>{e(names[a])} → <a href="#{b}">{e(names[b])}</a>. {e(LINEAGE[(a, b)])}</li>\n'
        for a, b, _ in EDGES)
    return items
