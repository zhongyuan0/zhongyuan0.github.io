"""Turn on visit counting with GoatCounter (https://www.goatcounter.com), or change the account.

Usage: python3 tools/set_goatcounter.py <code>      e.g. zhongyuan0  ->  https://zhongyuan0.goatcounter.com
       python3 tools/set_goatcounter.py --off       remove it again

Saves the code in tools/goatcounter.txt (build_page.py reads it for the readings pages) and puts one script tag in
the hand-written pages. The script is the self-hosted assets/js/count.js; it sets no cookies and only sends a
page view to <code>.goatcounter.com. Rebuild the readings pages afterwards.
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = ['index.html', 'research/index.html', 'cv/index.html', '404.html']
TAG = re.compile(r'\n?\s*<script data-goatcounter=[^>]*></script>')


def snippet(code):
    return f'    <script data-goatcounter="https://{code}.goatcounter.com/count" async src="/assets/js/count.js"></script>\n'


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    code = None if sys.argv[1] == '--off' else sys.argv[1].strip().lower()
    if code and not re.fullmatch(r'[a-z0-9-]{2,50}', code):
        sys.exit('The code is the first part of your GoatCounter address, e.g. zhongyuan0 for zhongyuan0.goatcounter.com')
    txt = os.path.join(ROOT, 'tools', 'goatcounter.txt')
    if code:
        open(txt, 'w').write(code + '\n')
    elif os.path.exists(txt):
        os.remove(txt)
    for p in PAGES:
        f = os.path.join(ROOT, p)
        s = TAG.sub('', open(f).read())
        if code:
            s = s.replace('  </head>', snippet(code) + '  </head>', 1)
        open(f, 'w').write(s)
    print(('GoatCounter on: https://%s.goatcounter.com' % code) if code else 'GoatCounter off', '- now rebuild the readings pages')


if __name__ == '__main__':
    main()
