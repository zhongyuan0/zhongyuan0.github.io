# Reading lists: how the /readings/ page is built

1. `syllabi/*.json`: one file per syllabus, with every reading extracted (authors, year, title, venue, session heading).
2. `merge.py`: merges all syllabi and deduplicates readings (same first author, similar title, close year). It also counts how many syllabi list each reading.
3. `classify.py`: assigns each reading to a stream, based on the session headings it was listed under. `RULES` maps headings to streams, and `OVERRIDES` fixes individual readings.
4. `subtopics.py` and `subtopics.json`: the larger streams are split into sub-streams. `subtopics.py` defines them; `subtopics.json` assigns each reading (by `reading_key`) to one, or moves a misfiled reading with `@stream` / `@stream:sub`. `assemble_subtopics.py` merges new per-stream assignments into it. Readings without an assignment fall under "Other readings".
5. `dois.py` and `dois.json`: DOIs looked up on Crossref by title, first author and year, stored by `reading_key` (an empty string means no confident match; many books and chapters have no DOI). Readings already in `dois.json` are skipped, so a DOI corrected there by hand stays; near misses go to `dois_review.json` for a look by hand. Needs network access to api.crossref.org; run it after `classify.py` whenever readings are added.
6. `build_page.py`: writes `readings/index.html` (readings in 2+ sources, with the theory tree from `tree.py`) and `readings/more/index.html` (single-source readings). Streams are numbered in the order of `ORDER` (the tree's columns, left to right) and sub-streams N.1, N.2 ... in the order they appear on each page; readings with a DOI get a doi.org link.

To rebuild after adding or changing a syllabus JSON:

    python3 tools/readings/merge.py && python3 tools/readings/classify.py && python3 tools/readings/dois.py && python3 tools/readings/build_page.py . <css-version>
