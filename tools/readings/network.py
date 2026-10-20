"""Co-assignment network of the readings: two readings are linked when a syllabus assigns them in the same session.

Used by build_page.py for /readings/network/. Nodes are the readings in two or more sources; the layout is a
force-directed layout on all links, drawn with the links that recur in two or more syllabi. Also finds the
bridging readings (betweenness) and the communities in the data (Louvain), to compare with the hand-drawn streams.
"""
import collections, itertools, math, re
import networkx as nx
from networkx.algorithms import community

FAMILY_OF = {  # stream -> family (the theory tree's columns, plus the roots and the streams outside it)
    'contingency': 'env', 'rdt': 'env', 'ecology': 'env', 'entre': 'env',
    'culture': 'inst', 'institutional': 'inst', 'categories': 'inst', 'movements': 'inst',
    'networks': 'rel', 'status': 'rel', 'work': 'rel', 'nonmarket': 'rel',
    'carnegie': 'beh', 'evolution': 'beh', 'stratproc': 'beh',
    'stratecon': 'strat', 'rbv': 'strat', 'international': 'strat',
    'orgecon': 'econ', 'corporate': 'econ', 'governance': 'econ',
}
FAMILIES = [('env', 'Environment'), ('inst', 'Institutions and culture'), ('rel', 'Relations'),
            ('beh', 'Behavior and evolution'), ('strat', 'Strategy'), ('econ', 'Economics'), ('found', 'Foundations, theory and methods')]
MAX_SESSION = 30  # a "session" bigger than this is a whole reading list, not a week's readings


def family(key):
    return FAMILY_OF.get(key, 'found')


def build(readings):
    """readings: the list with 'sessions' (course|heading), 'n', 'topic', 'ref'. Returns (graph, info)."""
    by_session = collections.defaultdict(list)
    for i, r in enumerate(readings):
        for s in set(r['sessions']):
            by_session[s].append(i)
    w = collections.Counter()
    for v in by_session.values():
        if len(v) > MAX_SESSION:
            continue
        for a, b in itertools.combinations(sorted(v), 2):
            w[(a, b)] += 1
    g = nx.Graph()
    g.add_nodes_from(range(len(readings)))
    for (a, b), n in w.items():
        g.add_edge(a, b, weight=n)
    giant = max(nx.connected_components(g), key=len)
    core = g.subgraph(giant).copy()
    # layout: recurring links pull much harder than one-off ones, so the clusters come from what syllabi agree on
    lay = core.copy()
    for a, b, d in lay.edges(data=True):
        d['weight'] = d['weight'] ** 2
    pos = nx.forceatlas2_layout(lay, weight='weight', max_iter=600, scaling_ratio=4.0, gravity=1.2, distributed_action=True, seed=7)
    # pull in far-flung outliers so they do not set the scale of the picture
    import numpy as np
    arr = np.array([pos[i] for i in core.nodes])
    c = arr.mean(axis=0)
    d = np.linalg.norm(arr - c, axis=1)
    lim = np.percentile(d, 97)
    for i in core.nodes:
        v = np.array(pos[i]) - c
        n = np.linalg.norm(v)
        if n > lim:
            pos[i] = tuple(c + v / n * (lim + (n - lim) * 0.15))
    bc = nx.betweenness_centrality(core, seed=7)
    comms = sorted(community.louvain_communities(core, weight='weight', seed=1), key=len, reverse=True)
    return core, {'pos': pos, 'betweenness': bc, 'communities': comms, 'sessions': len(by_session)}


def short(r):
    a = (r['ref']['authors'] or ['?'])[0].split(',')[0]
    more = len([x for x in r['ref']['authors'] if x != 'et al.'])
    y = re.search(r'\d{4}', r['ref']['year'] or '')
    return f"{a}{' & ' + r['ref']['authors'][1].split(',')[0] if more == 2 else (' et al.' if more > 2 else '')} ({y.group() if y else 'n.d.'})"


def svg(core, pos, readings, names, W=1000, H=760, pad=28):
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    sx = lambda x: pad + (x - min(xs)) / (max(xs) - min(xs)) * (W - 2 * pad)
    sy = lambda y: pad + (y - min(ys)) / (max(ys) - min(ys)) * (H - 2 * pad)
    radius = lambda n: 3.2 + 1.9 * math.sqrt(n - 1)
    edges = []
    for a, b, d in sorted(core.edges(data=True), key=lambda e: e[2]['weight']):
        if d['weight'] < 2:
            continue
        edges.append(f'<line class="nw-e w{min(d["weight"], 4)}" data-a="{a}" data-b="{b}" x1="{sx(pos[a][0]):.1f}" y1="{sy(pos[a][1]):.1f}" '
                     f'x2="{sx(pos[b][0]):.1f}" y2="{sy(pos[b][1]):.1f}"/>')
    nodes = []
    for i in sorted(core.nodes, key=lambda i: readings[i]['n']):
        r = readings[i]
        x, y = sx(pos[i][0]), sy(pos[i][1])
        tip = f"{short(r)}: {r['ref']['title']} — {names[r['topic']]}; in {r['n']} sources"
        nodes.append(f'<circle class="nw-n f-{family(r["topic"])}" data-i="{i}" cx="{x:.1f}" cy="{y:.1f}" r="{radius(r["n"]):.1f}" tabindex="0">'
                     f'<title>{tip}</title></circle>')
    labels, boxes = [], []
    for i in sorted(core.nodes, key=lambda i: -readings[i]['n']):
        if len(labels) >= 28:
            break
        r = readings[i]
        t = short(r)
        x, y = sx(pos[i][0]), sy(pos[i][1])
        yl = y - radius(r['n']) - 3
        w, h = len(t) * 5.6, 12
        box = (x - w / 2, yl - h, x + w / 2, yl)
        if any(not (box[2] < b[0] or box[0] > b[2] or box[3] < b[1] or box[1] > b[3]) for b in boxes):
            continue
        boxes.append(box)
        labels.append(f'<text class="nw-l" x="{x:.1f}" y="{yl:.1f}" text-anchor="middle">{t}</text>')
    return (f'<svg class="nw" viewBox="0 0 {W} {H}" role="img" aria-labelledby="nw-title nw-desc">'
            f'<title id="nw-title">Co-assignment network of the readings</title>'
            f'<desc id="nw-desc">{core.number_of_nodes()} readings; a line joins two readings that at least two syllabi assign in the same session. '
            f'Colour is the stream family, size the number of sources. The lists below the figure give the same information in words.</desc>'
            f'<g class="nw-edges">{"".join(edges)}</g><g class="nw-nodes">{"".join(nodes)}</g><g class="nw-labels">{"".join(labels)}</g></svg>')


def neighbours(core, i, k=6):
    return sorted(((j, d['weight']) for j, d in core[i].items()), key=lambda x: (-x[1], -core.degree(x[0])))[:k]
