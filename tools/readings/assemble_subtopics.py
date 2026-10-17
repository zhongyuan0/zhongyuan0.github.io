"""Combine per-stream sub-stream assignments (out_<stream>.json) into subtopics.json and report problems.

Usage: python3 tools/readings/assemble_subtopics.py <dir with out_*.json>
"""
import glob, json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from subtopics import SUBTOPICS
from classify import TOPICS

D = os.path.dirname(os.path.abspath(__file__)) + '/'
STREAMS = {k for k, _, _ in TOPICS}
REMAP = {'@networks:structure': '@networks:topology'}  # sub-stream renamed after assignment

out = json.load(open(D + 'subtopics.json')) if os.path.exists(D + 'subtopics.json') else {}
problems = collections.Counter()
for f in sorted(glob.glob(os.path.join(sys.argv[1], 'out_*.json'))):
    stream = os.path.basename(f)[4:-5]
    valid = {k for k, _ in SUBTOPICS[stream]} | {'other'}
    for key, v in json.load(open(f)).items():
        v = REMAP.get(v, v)
        if v.startswith('@'):
            st, _, sub = v[1:].partition(':')
            if st not in STREAMS:
                problems[f'unknown stream {v}'] += 1
                v = 'other'
            elif sub and sub not in {k for k, _ in SUBTOPICS.get(st, [])}:
                problems[f'unknown sub {v}'] += 1
                v = '@' + st
        elif v not in valid:
            problems[f'{stream}: unknown sub {v}'] += 1
            v = 'other'
        out[key] = v
json.dump(dict(sorted(out.items())), open(D + 'subtopics.json', 'w'), ensure_ascii=False, indent=0)
print('assignments', len(out))
for p, n in problems.items():
    print('  fixed:', n, p)
