# Notes: Airbnb SWE Intern (BS/MS), variant `airbnb_swe`

Bank: alex-rivera/resume.toml (backup before this run: resume.toml.bak_airbnb, next to it)
Built PDF: airbnb-swe/out/Alex_Rivera_Resume_airbnb_swe.pdf, copied to ./resume.pdf. check.py: PASS, 1 page, 2.92 in empty at the bottom.

## Eligibility
- Graduation Dec 2027 falls inside the JD's window ("graduating between December 2027 - June 2028"). The program (May 24 - Aug 13, 2027) ends before graduation. MS pay band applies ($8100/mo).
- Less than 2 years of full-time work: the bank shows only one internship, so this holds.
- **No sponsorship, now or in the future.** The bank has no work-authorization fact. The user must confirm US work authorization before applying.
- SF onsite 3 days/week; the candidate is in Seattle, and the JD offers domestic relocation support.

## Choices
- Direction backend, second ai. The JD's titles and examples are generic, but its requirements lean to product backend (Java/SQL, end-to-end gift-card backend + UI), plus a separate AI-awareness requirement. That is why DocQA sits second and not last.
- Order: Shopline (product backend, SQL, testing) -> DocQA (AI requirement) -> tinykv (fundamentals, testing) -> throttle (algorithms, interface design) -> SQL internship.
- Skills: Languages (Java first) / Backend / AI / LLM / Testing / Cloud & DevOps. The "Distributed Systems" skills line was dropped: the JD never mentions it, and tinykv's bullets already carry Raft.
- Availability line turned on, because the JD sets fixed program dates.
- Weak bullets kept only to fill space: shopline.aws (deploy = end-to-end ownership), kv.perf_s, gateway.redis. Each one proves only "problem solving". They are the first to cut if space is needed.

## Bank edits (bullets_changed = 3)
- Added `projects.shop.bullets.api_s` (= `api` without "normalized") so "locking." no longer sits alone on a second line.
- Added `projects.kv.bullets.perf_s` (= `perf` without "(1 to 64 clients)") so "leader failover." no longer sits alone on a second line.
- Experience bullet edited in place: removed "operational" ("joining 3 operational systems" -> "joining 3 systems") so "planning." no longer sits alone. This affects every variant (experience is not per-variant) and fixed the same orphan everywhere.
- No numbers, dates, titles or technologies changed.

## Known weak spots / if a reviewer pushes back
- "Java" appears only once, on the Languages line. Shopline's Spring Boot/JUnit stack suggests Java, but the bank never says it. If the user confirms Shopline is written in Java, rewrite `api_s` as "...in Java" (bank fact needed first).
- Nothing on responsible AI (fairness/privacy/safety), supervised learning, frontend (HTML/CSS/JavaScript), code reviews or mentoring. These are interview-prep gaps; Airbnb lists responsible AI as a requirement, so the user should prepare a real answer about it.
- "group commit" appears in both tinykv core and perf_ab (r1; was perf_s) (feature vs. its measured effect). If a reviewer flags duplication, drop "and group commit" from core (needs a new short key).
- 2.9 in of white space remains; the bank has no other relevant true bullets. The best fill would be a real frontend or LLM-API bullet (e.g. if DocQA's answer step calls an LLM API, a bullet saying so would hit "APIs backed by large language models" head-on).

## Revision 1 (after HM yes / ATS pass)
Bank backup before r1: airbnb-swe/resume.toml.bak_airbnb_r1. check.py: PASS, 1 page, 2.92 in at the bottom (unchanged: the bank still has no other relevant bullets).

Changed (2 bullets, both new keys; the originals are untouched):
- `gateway.redis_ab` = `redis` without "exactly". HM: "exactly is a red flag". The bank has no over-admission figure, so the word was dropped instead of being backed up.
- `kv.perf_ab` brings back the load setup "(1 to 64 clients)" that `perf_s` had cut. HM asked for an anchor for 80 -> 2,400 writes/s. "cluster", "measured" and "leader" were cut so the bullet stays one line ("250 ms median failover"; in Raft this means leader failover).
- Skills: switched to trimmed lines `backend_ab`, `ai_ab`, `test_ab`, `cloud_ab`. These are subsets of the bank lines, plus Testcontainers (Shopline bullet) and chaos testing (bank `dist` line + tinykv bullet). Removed gRPC, WebSockets, Kubernetes, S3, IAM, tool-calling agents and Go race detector, because no bullet on the page backs them (HM). Spelled out "LLM (large language model)" once (ATS).
- TypeScript stays on Languages: it's a true bank skill and the nearest thing to the JD's JavaScript.
- These bullets prove only "problem-solving", which is on the JD's requirement list, so touched_hard_requirement = true (conservative).

Not done, because the bank has no fact (now in analysis.md Known gaps + writer.json gaps/questions):
- Work authorization line in the header (HM #1). Truth rule: bank-only lines, and the user decides. Highest-value question.
- Collaboration / mentoring / communication item (HM #2), responsible-AI bullet such as PII redaction or low-confidence refusal (HM #3), frontend / UI work (HM #4), Shopline measured result (HM #4).
- DocQA held-out split (HM #3): kept the bullet as-is. If the user confirms the 95% was measured on a split not used to choose the configuration, add "held-out" to it. If it wasn't, rephrase it as "best of 12 configurations reached 95% Recall@5".
- Latency attribution (caching vs. removing the call): the bank doesn't split it; left as-is.
- Project dates (HM #5, ATS #5): only tinykv has one (Oct 2026). I didn't turn on project_dates, because one dated project among three undated ones looks worse. Turn it on once the user gives all the dates.
- Phone number (ATS #1), JavaScript / HTML/CSS (ATS #2), Data Structures coursework (ATS #3): not in the bank.
- No builder template problems found; the ATS review passed parsing.
