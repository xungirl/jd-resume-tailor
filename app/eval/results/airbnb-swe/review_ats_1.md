1. **Result: pass.** I found no problems under items 2–4.

2. **Parsing:** Both extractions got all the text. The PDF is one page, and the only non-ASCII character is the page-break marker at the end.
   - **Characters:** No ligatures (ﬁ, ﬂ) and no garbled or missing characters. Dates use a plain hyphen ("Sep 2020 - Jun 2024").
   - **Order:** Single column, with sections in source order: header → EDUCATION → TECHNICAL SKILLS → PROJECTS → EXPERIENCE. The header stays together on line 2 in both extracts: "Seattle, WA | alex@example.com | linkedin.com/in/example | github.com/example".
   - **Right-aligned locations and dates:** These stay on the correct line. In `-raw` they follow the text after one space: "Example State University Seattle, WA" and "Master of Science in Computer Science | GPA: 3.9/4.0 Expected Dec 2027". That is normal for a single-line layout. Most parsers split the location off correctly.
   - **Bullet markers:** Neither extractor keeps the bullet glyph. Each bullet still starts its own line, so nothing is merged.
   - **Wrapped bullets:** Four bullets wrap onto a second line, and the second half is complete in both extracts. For example, "...raising Recall@5 from 65% to 95% with hybrid / BM25 + vector search." The others are tinykv bullets 1 and 2 ("write-ahead / log with fsync…", "acked key / back through the log.") and throttle bullet 1 ("behind one / interface with…").

3. **Fields:**
   - **Contact:** Name: Alex Rivera. Email: alex@example.com. Location: Seattle, WA. LinkedIn: linkedin.com/in/example. GitHub: github.com/example. **Phone: none.** The source has no phone either, so this isn't a mismatch, but the ATS phone field will be empty.
   - **Education:**
     - Example State University, Seattle, WA. Master of Science in Computer Science, GPA 3.9/4.0, Expected Dec 2027.
     - Example College, Portland, OR. Bachelor of Science in Information Systems, Sep 2020 - Jun 2024.
   - **Experience:** Example Logistics Co., Portland, OR. Data Analyst Intern, Jan 2024 - May 2024.
   - **Projects:** Shopline, DocQA, tinykv and throttle. **None of them has a date**, in the PDF or in the source.
   - **Date formats:** All dates use the same "Mon YYYY" format. Everything matches resume_source.md.

4. **Content:** Every section heading, all 5 skills lines and all 10 bullets in resume_source.md appear in both extracts, complete and in order.
   - **Numbers and symbols:** All present, including 25, 90%, Recall@5, 65%→95%, 12, 60-query, 9.0s→3.5s, 0 of 10,000, 50, 3-node, 80→2,400 writes/s, 250 ms, 4, 3, 1,000 req/s, p50/p99, 3.9/4.0, "BM25 +", "Q&A" and "CI/CD".
   - **Links:** They match the header. The email is mailto:alex@example.com, LinkedIn goes to https://www.linkedin.com/in/example and GitHub goes to https://github.com/example. Each project's "GitHub" label links to its repo (/shopline, /docqa, /tinykv, /throttle).

5. **Keywords:** These JD terms never appear in the extracted text:
   - **Languages:** Scala, Ruby/Rails, C++, HTML/CSS, JavaScript, Objective-C, Swift, Kotlin. TypeScript is listed, but an exact search for "JavaScript" won't match it.
   - **Concepts:** "data structures", "design patterns", "machine learning", "supervised learning", "model evaluation", "large language models". The resume has "LLM" and "LLM evaluation harnesses", but not "large language models" spelled out.

6. **Fixes** (all optional, since this passes):
   1. Add a phone number to the header line so the ATS phone field fills in.
   2. If you know JavaScript, add it to Languages next to TypeScript. Add HTML/CSS too if that's true. Both are literal JD terms.
   3. Add "Data Structures" to Coursework, and add "Design Patterns" or "Machine Learning" only if you took those courses.
   4. Add the spelled-out phrase once, for example "LLM (large language model) evaluation harnesses", so a search for either form matches.
   5. Optionally add a year to each project, such as "| 2026", so parsers that expect dates on every entry don't leave them blank.

VERDICT: pass