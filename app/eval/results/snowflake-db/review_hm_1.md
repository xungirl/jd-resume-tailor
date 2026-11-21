## 1. 10-second impression
This is an MS CS student (BS in Information Systems) who builds backend and distributed systems, mostly in Go and Java. The headline project is a Raft KV store with a WAL, which is close to what our FDB and storage teams do. There is no C++, no big-data work, and the only job is a data analyst internship. **Match: medium.**

## 2. Move to next round
**Yes, but it's borderline.** tinykv (WAL, fsync, group commit, crash testing) is the most relevant thing on the page for a database engine role. A tech screen can check whether the depth is real and cover the gaps in coursework, C++ and teamwork.

## 3. Hard requirements vs. evidence
| Requirement | Evidence |
|---|---|
| Enrolled during internship | "Master of Science in Computer Science … Expected Dec 2027"; "returning to school in Fall 2027" ✅ |
| 3rd/4th yr / Masters / PhD | MS ✅ |
| CS / CE / related major | MS CS ✅ (BS is Information Systems) |
| Required coursework: algorithms, data structures, software engineering, OS | "Coursework: Algorithms, Distributed Systems, Databases". Algorithms only. **No evidence** for data structures, software engineering or **operating systems** |
| Big data engineering/processing | **No real evidence.** "SQL pipelines joining 3 operational systems for daily reporting" has no stated scale |
| Excellent C++ or Java | "Languages: Java…"; Shopline in Spring Boot. Java is used for CRUD/REST, not systems work. **No C++.** No Java version given (17/20) |
| DS&A knowledge | Algorithms coursework only |
| Systems programming / multithreading / concurrency | "group commit", "concurrent clients grew from 1 to 64", "Go race detector", "optimistic locking". This is real, but it's in Go, not C++ or Java |
| Teamwork | **No evidence.** All projects look solo |
| Full-time in designated office | "full-time (12 weeks)". Based in Seattle with no mention of relocating to Menlo Park. 12 weeks is the minimum; we recommend 16 |

## 4. Bullets I can't follow or don't believe
- **"Lost 0 of 10,000 acknowledged writes across 50 SIGKILL faults"**: SIGKILL kills the process, but the OS page cache survives. So this doesn't show that fsync works. A test with fsync turned off might also lose 0 writes. It needs a control run or a power-loss or disk-fault style test.
- **"Scaled … from 80 to 2,400 writes/s as concurrent clients grew from 1 to 64 via group commit"**: Two effects are mixed together here: more clients and group commit. There is no with/without comparison and no hardware stated. Were all 3 nodes on one laptop? 2,400 writes/s is modest without that context.
- **"250 ms median leader failover"**: This mostly depends on the election timeout chosen. Over how many trials, and what was the p99?
- **"enforced a shared 1,000 req/s limit exactly under load"**: "Exactly" is a big claim. What load, measured over what window, and with what error?
- **"Designed 25 REST endpoints"**: An endpoint count says nothing about results. The project also has no date, which is true of three of the four projects.
- **"Recall@5 from 65% to 95%"**: The test set has only 60 queries and 12 configs were tried, so this is probably overfit. It also has nothing to do with this role.
- **tinykv dated Oct 2026**: It's very recent and the other projects have no dates, so I'd check how well the candidate really owns this code.

## 5. Interview questions
1. In tinykv, walk me through a write from the client to the ack. When exactly do you fsync? How would you prove that a write acked before a crash survives, given that SIGKILL leaves the page cache intact?
2. Separate out group commit's share of the 80 → 2,400 writes/s gain. What was the throughput at 64 clients with group commit off, and where was the bottleneck?
3. Have you taken or self-studied operating systems? Explain what happens on `write()` vs. `fsync()`, and how you would build a thread-safe structure like your WAL buffer in Java or C++.

## 6. Suggested changes (highest impact first)
1. **Close the coursework gap.** List Operating Systems, Data Structures and Software Engineering if they were taken in the BS or MS (or are planned before summer). OS is required, and missing it can get the resume filtered out automatically.
2. **Show systems work in Java or C++.** Add concurrency work in Java (thread pools, locks, `java.util.concurrent`) or port a piece of tinykv. Name the Java version (17 or 21).
3. **Make the tinykv numbers defensible.** State the setup (machines vs. localhost), add a control run with group commit off, and add a power-loss or fsync-disabled test that shows the WAL actually matters.
4. **Add teamwork evidence.** Describe a team project, a code review, or the cross-team work in the analyst internship. An open-source contribution would cover teamwork and a bonus item at once.
5. **Replace DocQA with database-internals work,** such as a B-tree or LSM, a query executor, or a SQL parser. Date every project and say you will relocate to Menlo Park.

VERDICT: yes