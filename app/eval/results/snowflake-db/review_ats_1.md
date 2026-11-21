**1. Result: pass.** I found no problems under 2–4. The notes below are advisory.

**2. Parsing**
- Both extractors got all the text. It's a single-page US Letter PDF made with ReportLab, with embedded Arial fonts that map to Unicode. Every character is plain ASCII, so there are no ligatures (ﬁ/ﬂ) and nothing garbled. Words like "fixed", "fault injection" and "configurations" came through intact.
- Reading order is correct in both extracts. There are no columns, and the header line stays together as one line: "Seattle, WA | alex@example.com | linkedin.com/in/example | github.com/example".
- Right-aligned locations and dates stay on the same line as their headings, for example "Example State University Seattle, WA" and "Data Analyst Intern Jan 2024 - May 2024". That's normal for ATS parsers.
- Long bullets wrap onto a second line at word boundaries ("...write-ahead / log with fsync"). No word is split in the middle, and the source hyphen stays.
- Bullet markers don't come through as characters; bullets show up as indented lines. Parsers handle that fine.

**3. Fields**
- Name: Alex Rivera. Email: alex@example.com. Location: Seattle, WA. LinkedIn: linkedin.com/in/example. GitHub: github.com/example.
- **Phone: none.** It isn't in resume_source.md either, so the PDF matches the source, but the ATS phone field will be empty.
- Education:
  - Example State University, Master of Science in Computer Science, GPA 3.9/4.0, Expected Dec 2027.
  - Example College, Bachelor of Science in Information Systems, Sep 2020 - Jun 2024.
- Experience: Example Logistics Co., Data Analyst Intern, Portland, OR, Jan 2024 - May 2024.
- Projects: tinykv (Oct 2026), Shopline, throttle and DocQA. The last three have no date, which matches the source.
- Every field matches the source. All dates use the same "Mon YYYY" format.

**4. Content**
- Every heading, all 5 skills lines, the coursework and availability lines, and all 11 bullets are present, complete and in source order. None is cut off or merged into another line.
- Numbers and symbols all survived: 3.9/4.0, 0 of 10,000, 50, 80 to 2,400 writes/s, 1 to 64, 250 ms, 25, 90%, 4, 3, 1,000 req/s, p50/p99, 9.0s to 3.5s, 12, 60-query, Recall@5, 65% to 95%, BM25 + vector, Q&A, JUnit 5, CI/CD.
- Links: mailto:alex@example.com, https://www.linkedin.com/in/example and https://github.com/example match the header. The four project "GitHub" links point to /tinykv, /shopline, /throttle and /docqa, each matching its project.

**5. Keywords from the JD that never appear in the extracted text**
- C++, C++17, C++20
- Java 17 and Java 20 (Java appears, but without a version)
- Multi-threading (only "concurrency control" and "concurrent clients" appear)
- Spark, Hadoop
- Azure, Google Cloud / GCP
- FoundationDB
- Required coursework: data structures, operating systems, software engineering
- Recommended coursework: compilers, cloud computing, networking
- Query optimization, query execution, transaction processing, data warehouse, big data

**6. Fixes** (none is needed for parsing)
1. Add a phone number to the header line so the ATS contact field fills in.
2. If you took them, add Data Structures, Operating Systems and Software Engineering to the Coursework line. They are the JD's required coursework, and an ATS will search for them literally.
3. If it's true, name the specific skills the JD lists: C++ (with a version), a Java version (e.g., "Java 17"), or "multi-threading" in the tinykv or throttle bullets.
4. Optionally, give Shopline, throttle and DocQA a date ("Mon YYYY" or a year) so every project entry is filled in the same way.
5. Optionally, add "transaction"/"concurrency control" wording to the Databases & Backend skills line, where it is already backed by the Shopline bullet, so the keyword sits in the skills section.

VERDICT: pass