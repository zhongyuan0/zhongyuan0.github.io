# Reading lists: how the /readings/ page is built

1. `syllabi/*.json`: one file per syllabus, with every reading extracted (authors, year, title, venue, session heading).
2. `merge.py`: merges all syllabi and deduplicates readings (same first author, similar title, close year). It also counts how many syllabi list each reading.
3. `classify.py`: assigns each reading to a stream, based on the session headings it was listed under. `RULES` maps headings to streams, and `OVERRIDES` fixes individual readings.
4. `subtopics.py` and `subtopics.json`: the larger streams are split into sub-streams. `subtopics.py` defines them; `subtopics.json` assigns each reading (by `reading_key`) to one, or moves a misfiled reading with `@stream` / `@stream:sub`. `assemble_subtopics.py` merges new per-stream assignments into it. Readings without an assignment fall under "Other readings".
5. `build_page.py`: writes `readings/index.html` (readings in 2+ sources, with the theory tree from `tree.py`) and `readings/more/index.html` (single-source readings).

To rebuild after adding or changing a syllabus JSON:

    python3 tools/readings/merge.py && python3 tools/readings/classify.py && python3 tools/readings/build_page.py . <css-version>
