# Notes for editing this site

- Plain static HTML/CSS. No Jekyll, no build step, no JavaScript. `.nojekyll` keeps GitHub Pages from processing files.
- Pages: `index.html` (About), `research/index.html`, `cv/index.html`, `404.html`; `publications/` only redirects to `/research/`.
- Header and footer markup is repeated in every page; change them everywhere at once.
- All styling lives in `assets/css/site.css`; colours and type sizes are tokens at the top (light and dark mode).
- A paper appears in up to three places: `research/index.html`, the CV's Publications list (APA style), and Selected publications on the home page. Keep them in sync.
- No CV PDF is published for now (owner's choice). `/cv/` still has print styles at the end of `site.css` if one is wanted later.
- Papers under review and work in progress are listed by short topic only, never by full title (owner's choice). The name is Zhongyuan Sun, without "Jowan".
- Fonts are self-hosted subsets (`assets/fonts/`); the CJK file only contains 孙中源 and 真善美; re-subset it if new characters are needed. Do not switch to Google Fonts (blocked in mainland China).
- Deploy: `.github/workflows/deploy.yml` copies the repo to the `gh-pages` branch on every push to `main`.
- Preview locally with `python3 -m http.server` from the repo root (paths are root-relative).
