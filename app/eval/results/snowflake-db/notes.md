# Notes: Snowflake SWE Intern (Database Engineering), Summer 2027

Bank: snowflake-db/resume.toml, variant `snowflake_db`. A pre-edit copy is in bank_backup/resume.toml.pre_sfdb.
Built PDF: snowflake-db/out/Alex_Rivera_Resume_snowflake_db.pdf, copied to ./resume.pdf. check.py passes (1 page, 2.75 in empty at the bottom).

## Chosen and why
- **tinykv leads (3 bullets).** A Raft key-value store with a WAL is the closest match to "FoundationDB key-value store (FDB storage, FDB Performance)", "Large-scale distributed systems" and "Software frameworks for stability and performance testing". It is also the only dated, most recent project.
  - core: storage plus replication (as in the bank).
  - chaos_short: a shortened copy of `chaos` with the same facts. "back through the log" was cut because it left a 4-word last line.
  - perf_conc: a reworded copy of `perf` with the same facts. "1 to 64 clients" became "as concurrent clients grew from 1 to 64" to answer "concurrency".
- **Shopline (3 bullets).** This is the Java evidence (Spring Boot, JUnit), plus a PostgreSQL schema (database systems), AWS ("cloud infrastructure, AWS") and software-engineering practice (tests, CI).
  - api_conc: a reworded copy of `api`, which now names optimistic locking as "concurrency control".
- **throttle (2 bullets).** Algorithms ("Knowledge of data structures and algorithms"), plus atomic shared state across 3 instances (concurrency, distributed).
- **DocQA (2 bullets, last).** Off-topic for a DB engine, but it shows latency work and benchmarking. It also fits the JD's "experimental mindset" and "AI-native" intro. It fills space the bank has no better bullet for. It is the first thing to cut.
- **Experience.** The Data Analyst Intern SQL pipelines are the closest thing to "big data" / data processing. I shortened that bullet in the bank (shared by all variants) to fix a 1-word last line. It now reads "for daily reporting; built dashboards for 3 planning KPIs", which drops "used in weekly planning". Restore it from the backup if you prefer the old wording.
- **Skills.** I added new groups built only from items already in the bank: lang_sfdb (Java first, TypeScript dropped), db_sfdb, cloud_sfdb (Kubernetes dropped because it is unrelated to the JD), and test_sfdb (labelled with the JD's "Stability & Performance Testing"). The `dist` line is reused as is. The AI/LLM line is left out.
- **Availability line on.** The JD lists start/end date options and a 12-week minimum. The line also shows enrollment during the internship.

## Dropped
- DocQA's AI skills line: unrelated to database engineering.
- Kubernetes, TypeScript, FastAPI, WebSockets, pytest from the skills lines: not relevant to this JD.
- kv.perf, kv.chaos and shop.api originals: replaced by same-fact variants (one fact appears once).

## If a reviewer pushes back
- "Not enough Java": the Shopline title line could say "in Java" if Alex confirms the project is Java (Spring Boot plus JUnit strongly suggest it, but the bank never says so). That would raise Java to 2 mentions.
- "Too much whitespace": the bank has no more relevant true bullets. Options: (a) Alex adds facts, e.g. tinykv implementation details on goroutines/locks, which would also cover "multi-threading", or (b) restore the AI/LLM skills line (weakly relevant).
- "DocQA is noise": remove it. The page still passes, with more whitespace.
- Gaps to prepare honest interview answers for: C++, Java version, multi-threading (threads specifically), operating systems and data structures coursework, big data, Spark/Hadoop, query execution/optimization, compilers, transaction processing, open source.

## Revision 1 (after HM yes-borderline, ATS pass)
Bank backup before this revision: bank_backup/resume.toml.pre_sfdb_rev1. The variant now uses kv.chaos_crash, shop.api_db and gateway.redis_shared, all new keys with the same facts as the originals.

Changed (3 bullets):
- **tinykv chaos -> chaos_crash.** The HM doubted that SIGKILL proves fsync works. The bullet now states the test setup plainly: "SIGKILL process crashes". It no longer implies power-loss durability. "acknowledged" became "acked" to avoid a 2-word last line. A real fix needs a power-loss or fsync-off control run, which the bank doesn't have (see gaps).
- **Shopline api_conc -> api_db.** The HM said an endpoint count says nothing. The schema and optimistic locking for concurrency control now lead, and the 25 endpoints are context at the end.
- **throttle redis -> redis_shared.** I dropped "exactly", which the HM didn't believe and the bank gives no error measurement for.

Other changes:
- **DocQA dropped entirely.** The HM called Recall@5 on 60 queries overfit and off-role, and suggested replacing it with DB-internals work. The bank has none, so the page now has 3.5 in of empty space. I prefer a tight, relevant page to filler. If a reviewer pushes back on the whitespace, restore `{ key = "rag", bullets = ["lat"] }` (latency work only).
- **project_dates turned off.** Only tinykv had a date (Oct 2026). Both reviewers flagged the inconsistency, and the bank has no dates for the other projects. Turn it back on once Alex supplies the dates.
- **Skills:** "optimistic concurrency control" was added to the Databases & Backend line (ATS suggestion; Shopline backs it). Concurrency now appears twice.

Not changed, and why:
- Phone number (ATS): not in the bank profile. It is a question for Alex; the builder template is fine.
- Coursework OS / Data Structures / Software Engineering: not in the bank. Asked again.
- Java version, C++, multi-threading, teamwork, open source, big data, relocation, 16 weeks: not in the bank. Logged under gaps, constraints and questions.
- perf bullet: the bank gives no hardware or group-commit-off control and no failover trial count or p99, so the bullet is unchanged. Listed as a gap and a question.
