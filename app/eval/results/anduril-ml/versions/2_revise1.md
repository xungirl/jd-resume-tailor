# Alex Rivera
Seattle, WA | alex@example.com | linkedin.com/in/example | github.com/example

## EDUCATION
**Example State University** | Seattle, WA
*Master of Science in Computer Science | GPA: 3.9/4.0* | Expected Dec 2027
**Coursework:** Algorithms, Distributed Systems, Databases
**Availability:** Summer 2027 internship, full-time (12 weeks); returning to school in Fall 2027
**Example College** | Portland, OR
*Bachelor of Science in Information Systems* | Sep 2020 - Jun 2024

## TECHNICAL SKILLS
**Languages:** Python, SQL, Go, Java, TypeScript
**Natural Language Processing (NLP):** RAG, embeddings, retrieval evaluation, LLM evaluation harnesses
**Testing & Experiments:** pytest, JUnit 5, fault injection, load testing (p50/p99), Go race detector
**Tools:** Git, Docker, AWS (ECS, RDS, S3, IAM), GitHub Actions CI/CD, Terraform
**Data & Backend:** PostgreSQL, Redis, FastAPI, REST APIs

## PROJECTS
**DocQA** | *Retrieval-Augmented Q&A over Support Tickets* | GitHub
- Raised Recall@5 from a 65% baseline to 95% on a 60-query test set by benchmarking 12 retrieval configurations, landing on hybrid BM25 + vector search.
- Cut p50 answer latency of the large language model (LLM) Q&A pipeline from 9.0s to 3.5s by caching embeddings and removing a redundant retrieval call.

**tinykv** | *Raft-Replicated Key-Value Store in Go* | GitHub
- Verified 0 of 10,000 acknowledged writes lost across 50 SIGKILL fault experiments with a chaos harness that reads every acked key back through the log.
- Scaled a 3-node cluster from 80 to 2,400 writes/s in load tests from 1 to 64 clients by adding group commit; measured 250 ms median leader failover.
- Built a Raft key-value store in Go (stdlib only) with leader election, log replication, and a CRC-checked write-ahead log with fsync.

**Shopline** | *E-Commerce Backend (Spring Boot, PostgreSQL, AWS)* | GitHub
- Deployed with Docker on AWS ECS Fargate behind an ALB with RDS PostgreSQL, defined as code in Terraform.
- Reached 90% line coverage with JUnit and Testcontainers; CI on GitHub Actions blocks merges on failing tests.

**throttle** | *Rate-Limiting API Gateway in Go* | GitHub
- Implemented 4 rate-limiting algorithms (token bucket, fixed window, sliding log, sliding counter) behind one interface with in-memory and Redis backends.

## EXPERIENCE
**Example Logistics Co.** | Portland, OR
*Data Analyst Intern* | Jan 2024 - May 2024
- Wrote SQL pipelines joining 3 operational systems for daily reporting; built dashboards for 3 KPIs used in weekly planning.
