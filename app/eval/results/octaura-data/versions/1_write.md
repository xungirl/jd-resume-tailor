# Alex Rivera
Seattle, WA | alex@example.com | linkedin.com/in/example | github.com/example

## EDUCATION
Example State University | Seattle, WA
Master of Science in Computer Science | GPA: 3.9/4.0 | Expected Dec 2027
Coursework: Algorithms, Distributed Systems, Databases
Availability: Summer 2027 internship, full-time (12 weeks); returning to school in Fall 2027
Example College | Portland, OR
Bachelor of Science in Information Systems | Sep 2020 - Jun 2024

## TECHNICAL SKILLS
Languages: Python, SQL, Java, Go, TypeScript
Data Engineering: SQL pipelines, data analysis, metrics dashboards, PostgreSQL schema design, Redis
GenAI & Search: RAG, embeddings, hybrid BM25 + vector search, retrieval evaluation, LLM evaluation harnesses
Backend & Systems: REST, WebSockets, FastAPI, Spring Boot, Raft, write-ahead logs, Testcontainers
Cloud & DevOps: AWS (ECS Fargate, RDS), Docker, Terraform, GitHub Actions CI/CD

## PROJECTS
DocQA | Retrieval-Augmented Q&A over Support Tickets | GitHub
- Raised Recall@5 from 65% to 95% for GenAI Q&A over support tickets by benchmarking 12 retrieval configurations with hybrid BM25 + vector search.
- Cut RAG p50 answer latency from 9.0s to 3.5s by caching embeddings and removing a redundant retrieval call.

Shopline | E-Commerce Backend (Spring Boot, PostgreSQL, AWS) | GitHub
- Added cart, order and inventory features to an e-commerce platform via 25 REST endpoints on a normalized PostgreSQL schema with optimistic locking.
- Reached 90% line coverage with JUnit and Testcontainers; CI on GitHub Actions blocks merges on failing tests.
- Deployed with Docker on AWS ECS Fargate behind an ALB with RDS PostgreSQL, defined as code in Terraform.

tinykv | Raft-Replicated Key-Value Store in Go | GitHub
- Implemented the Raft replication protocol in Go (stdlib only) for a key-value store: leader election, log replication, and a CRC-checked write-ahead log.
- Lost 0 of 10,000 acknowledged writes across 50 SIGKILL faults by building a chaos harness that reads every acked key back through the log.
- Scaled a 3-node cluster from 80 to 2,400 writes/s via group commit; measured 250 ms median leader failover.

throttle | Rate-Limiting API Gateway in Go | GitHub
- Implemented 4 rate-limiting algorithms (token bucket, fixed window, sliding log, sliding counter) behind one interface with in-memory and Redis backends.
- Held 3 gateway instances to a shared 1,000 req/s limit exactly under load with atomic Redis Lua scripts.

## EXPERIENCE
Example Logistics Co. | Portland, OR
Data Analyst Intern | Jan 2024 - May 2024
- Wrote SQL pipelines joining 3 operational systems for daily reporting; built dashboards for 3 KPIs used in weekly planning.
