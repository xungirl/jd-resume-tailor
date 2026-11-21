Company: Snowflake
Role: Software Engineer Intern (Database Engineering) - Summer 2027
Level: Intern (basis: "Desired class level: 3rd/4th year Undergraduates, Masters, or PhD"; no years required; pay band not in the JD, it points to careers.snowflake.com)
Direction: infra (distributed systems / storage / key-value store, systems programming)
Second direction: backend (Java is the JD's named language and the Java evidence sits in the Spring Boot/PostgreSQL project; infra wins on the hard requirements: concurrency, distributed systems, key-value storage)
Location / visa / start date: "US-CA-Menlo Park"; "Required to work from designated office full time"; "Must be actively enrolled in an accredited college/university program during the time of the internship"; "Eligible start date options: May 10, 2027; May 24, 2027, June 21, 2027"; "Duration: 12 week minimum, 16 weeks recommended (12 month maximum)". No sponsorship statement in the JD.
Hard requirements: enrolled during the internship, 3rd/4th-year undergrad or Masters/PhD, CS or related major, coursework in algorithms, data structures, software engineering and operating systems, excellent programming in C++ or Java, data structures and algorithms, systems programming (multi-threading, concurrency), experience working with big data, teamwork, full-time onsite
Nice to have: C++20/C++17 or Java 20/Java 17, coursework in cloud computing, compilers, database systems, distributed systems, functional PL, networking, research or publications in databases or distributed systems, open source contributions, SQL / Spark / Hadoop, query compilation / query optimization / query execution, FoundationDB key-value store, transaction processing, AWS/Azure/Google Cloud, stability and performance testing
ATS keywords: Java, C++, C++17/C++20, Distributed Systems, Databases/database, Key-Value Store/key-value, SQL, Concurrency, Multi-threading, Algorithms, Data Structures, Operating Systems, Big Data, AWS, Cloud, Performance Testing, Query Execution, Query Optimization, Compilers, Transaction Processing, Spark, Hadoop, Open Source
Ideal candidate: A Masters or senior CS student with strong Java or C++ and real systems programming (concurrency, storage, distributed protocols) who has built or tested a database-like system. They can measure performance and correctness under failure, and they learn new parts of a query engine or key-value store quickly.
Strategy: Lead with tinykv, a Raft-replicated key-value store with a write-ahead log, as the closest match to "FoundationDB key-value store (FDB storage, FDB Performance)" and "Large-scale distributed systems"; show correctness under faults (stability testing) and throughput as concurrent clients scale (performance, concurrency). Then Shopline for Java/Spring Boot, a PostgreSQL schema with optimistic locking (database systems, concurrency control) and AWS. Then throttle for algorithms plus atomic shared state across instances. DocQA dropped in revision 1 (off-topic; the HM flagged its eval as overfit). Java leads the Languages line; skills labels reuse the JD's "Distributed Systems", "Databases", "Cloud", "Stability & Performance Testing".
Known gaps:
- C++ / C++17 / C++20: the bank has no C++ code
- Java 17 / Java 20: the bank lists Java but never a version
- multi-threading: concurrency is shown (concurrent clients, optimistic locking, race detector), but threads are never named
- data structures: not in the listed coursework, and no bullet names one
- operating systems: not in the listed coursework (required coursework in the JD)
- big data: no big-data engineering or processing in the bank; the closest is SQL reporting pipelines
- query execution / query optimization / compilers: no query-engine or compiler work in the bank
- transaction processing: optimistic locking only; no transaction engine
- spark / hadoop: not in the bank
- open source: no open-source contributions in the bank
- teamwork: every project reads as solo; the bank has no team project, code review or open-source work
- software engineering coursework: not in the listed coursework (the JD requires it)
- FoundationDB / Azure / Google Cloud: not in the bank
- durability under power loss: tinykv was tested with SIGKILL process crashes only; the bank has no power-loss, disk-fault or fsync-off control run
- benchmark setup: the bank gives no hardware or with/without group commit comparison for 80 to 2,400 writes/s, and no trial count or p99 for the 250 ms failover
