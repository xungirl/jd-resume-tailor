**1. Result: pass.** I found no problems under items 2–4.

**2. Parsing**
- Both extractors got all the text. I found no garbled characters, no ﬁ/ﬂ ligatures, no words glued together and no columns out of order.
- The header stays intact on line 2 in both: "Seattle, WA | alex@example.com | linkedin.com/in/example | github.com/example".
- In the source, the right-aligned items have a "|" before them. In the extracted text that "|" becomes spaces in `-layout` and a single space in `-raw`, for example `Example State University Seattle, WA` and `Data Analyst Intern Jan 2024 - May 2024`. The text is complete and in the right order. A parser might still read "Seattle, WA" as part of the school name.
- No bullet character (•) shows up in either extraction. Wrapped bullets continue on a new line with nothing marking it as part of the bullet above, for example `...with a chaos harness that` / `reads every acked key back through the log.` This happens 4 times. The text is still in the right place and in order.

**3. Fields**
- Name: Alex Rivera
- Email: alex@example.com
- Phone: none (the source has none either)
- Location: Seattle, WA
- LinkedIn: linkedin.com/in/example
- GitHub: github.com/example
- Education:
  - Example State University, MS in Computer Science, Expected Dec 2027
  - Example College, BS in Information Systems, Sep 2020 – Jun 2024
- Job: Example Logistics Co., Data Analyst Intern, Portland, OR, Jan 2024 – May 2024
- Projects: DocQA, tinykv, Shopline, throttle. None has a date, and neither does the source.
- Every field matches resume_source.md. Dates all use "Mon YYYY".

**4. Content**
- Every heading, all 5 skills lines and all 9 bullets are there, complete and in source order. Nothing is merged into another line.
- Numbers and symbols all came through: 65%, 95%, Recall@5, BM25 +, 9.0s, 3.5s, 10,000, 2,400 writes/s, 250 ms, 90%, p50/p99, 3.9/4.0, JUnit 5.
- The links match: mailto:alex@example.com, linkedin.com/in/example and github.com/example. Each project's "GitHub" points to its own repo (docqa, tinykv, shopline, throttle).

**5. Keywords from the JD that never appear in the extracted text:** PyTorch, TensorFlow, C++, CUDA, Linux, GPU, machine learning, deep learning, computer vision, graph neural networks, natural language processing (only "NLP" appears), large language models / vision-language (only "LLM" appears), CAD, 3D, statistics, probability, data structures.

**6. Fixes**
1. Spell out "natural language processing (NLP)" and "large language models (LLMs)" in the LLM / NLP skills line. An ATS searching for the full phrase will miss the abbreviations.
2. Add "machine learning" literally somewhere true, for example in the skills heading or the DocQA project line. It is the job title and currently appears nowhere.
3. Add Linux, PyTorch, TensorFlow, C++ or CUDA to Tools or Languages, but only those you have actually used.
4. Add "Data Structures" (and Probability/Statistics if you took them) to the Coursework line.
5. Optional: put a visible separator such as " | " before the right-aligned location and date text. Then the school/company name and location stay apart in the extracted text instead of running together with one space.

VERDICT: pass