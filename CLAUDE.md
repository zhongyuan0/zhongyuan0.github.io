# Notes for editing this site

- Plain static HTML/CSS. No Jekyll, no build step, no JavaScript. `.nojekyll` keeps GitHub Pages from processing files.
- Pages: `index.html` (About), `research/index.html`, `cv/index.html`, `afterimages/index.html` (film stills), `404.html`; `publications/` only redirects to `/research/`.
- Afterimages: one or two stills per film, at most 1600px wide (jpg + webp in `assets/img/afterimages/`), ordered by film year; caption = title (year), director, cinematographer. No commentary per still (owner's choice); the page intro carries the idea.
- Header and footer markup is repeated in every page; change them everywhere at once.
- All styling lives in `assets/css/site.css`; colours and type sizes are tokens at the top (light and dark mode).
- Cache busting: pages link `site.css?v=…`. Bump that version in every HTML page whenever site.css changes, and add/bump `?v=` on any font or image URL whose file is replaced; otherwise returning visitors see stale styles.
- Research page groups every paper by stream (真 authenticity, 善 social issues, 美 aesthetics, plus a Book review section at the end), published first, then under review, then in progress. The CV lists the same papers by type (APA). Home has short stream summaries and News only (no publication list, by the owner's choice). Keep all of them in sync. Unpublished or in-preparation pieces the owner has not released (e.g. invited reviews) stay off the site.
- No CV PDF is published for now (owner's choice). `/cv/` still has print styles at the end of `site.css` if one is wanted later.
- Papers under review and work in progress are listed by short topic only, never by full title (owner's choice). The name is Zhongyuan Sun, without "Jowan".
- Fonts are self-hosted subsets (`assets/fonts/`); the CJK file only contains 孙中源, 真善美 and 影; re-subset it if new characters are needed. Do not switch to Google Fonts (blocked in mainland China).
- Deploy: `.github/workflows/deploy.yml` copies the repo to the `gh-pages` branch on every push to `main`.
- Preview locally with `python3 -m http.server` from the repo root (paths are root-relative).
