# Reading lists: how the /readings/ page is built

1. `syllabi/*.json`: one file per syllabus, with every reading extracted (authors, year, title, venue, session heading).
2. `merge.py`: merges all syllabi and deduplicates readings (same first author, similar title, close year). It also counts how many syllabi list each reading.
3. `classify.py`: assigns each reading to a stream, based on the session headings it was listed under. `RULES` maps headings to streams, and `OVERRIDES` fixes individual readings.
4. `subtopics.py` and `subtopics.json`: the larger streams are split into sub-streams. `subtopics.py` defines them; `subtopics.json` assigns each reading (by `reading_key`) to one, or moves a misfiled reading with `@stream` / `@stream:sub`. `assemble_subtopics.py` merges new per-stream assignments into it. Readings without an assignment fall under "Other readings".
5. `dois.py`: finds DOIs on Crossref by title, first author and year, and writes `dois.json` (by `reading_key`; an empty string means no confident match, as for most classic books and many chapters). Crossref's answers are kept in `.cache/crossref.json` (not in git), so `--offline` re-runs the matching without querying again. `dois_manual.json` holds DOIs checked by hand (or "" to suppress a wrong match) and always wins; near misses go to `dois_review.json`. Matching rules: same title (subtitle optional), first author among the record's authors, compatible type (a book never matches a journal record, which would be a book review), year within one or the same journal, and the published version rather than a preprint, conference abstract or later reprint. Needs network access to api.crossref.org.
6. `build_page.py`: writes `readings/index.html` (readings in 2+ sources, with the theory tree from `tree.py`) and `readings/more/index.html` (single-source readings). Streams are numbered in the order of `ORDER` (the tree's columns, left to right) and sub-streams N.1, N.2 ... in the order they appear on each page; readings with a DOI get a doi.org link.

To rebuild after adding or changing a syllabus JSON:

    python3 tools/readings/merge.py && python3 tools/readings/classify.py && python3 tools/readings/dois.py && python3 tools/readings/build_page.py . <css-version>
