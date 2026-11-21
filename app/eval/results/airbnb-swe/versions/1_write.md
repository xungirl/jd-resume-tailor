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

**Languages:** Java, Go, Python, SQL, TypeScript
**Backend:** REST, gRPC, WebSockets, Spring Boot, FastAPI; PostgreSQL, Redis
**AI / LLM:** RAG, embeddings, retrieval evaluation, tool-calling agents, LLM evaluation harnesses
**Testing:** JUnit 5, pytest, Go race detector, fault injection, load testing (p50/p99)
**Cloud & DevOps:** AWS (ECS, RDS, S3, IAM), Docker, Kubernetes, GitHub Actions CI/CD, Terraform

## PROJECTS

**Shopline** | *E-Commerce Backend (Spring Boot, PostgreSQL, AWS)* | GitHub
- Designed 25 REST endpoints and a PostgreSQL schema for carts, orders and inventory with optimistic locking.
- Reached 90% line coverage with JUnit and Testcontainers; CI on GitHub Actions blocks merges on failing tests.
- Deployed with Docker on AWS ECS Fargate behind an ALB with RDS PostgreSQL, defined as code in Terraform.

**DocQA** | *Retrieval-Augmented Q&A over Support Tickets* | GitHub
- Benchmarked 12 retrieval configurations on a 60-query test set, raising Recall@5 from 65% to 95% with hybrid BM25 + vector search.
- Cut p50 answer latency from 9.0s to 3.5s by caching embeddings and removing a redundant retrieval call.

**tinykv** | *Raft-Replicated Key-Value Store in Go* | GitHub
- Built a Raft key-value store in Go (stdlib only): leader election, log replication, and a CRC-checked write-ahead log with fsync and group commit.
- Lost 0 of 10,000 acknowledged writes across 50 SIGKILL faults in a chaos harness that reads every acked key back through the log.
- Scaled a 3-node cluster from 80 to 2,400 writes/s via group commit; measured 250 ms median leader failover.

**throttle** | *Rate-Limiting API Gateway in Go* | GitHub
- Implemented 4 rate-limiting algorithms (token bucket, fixed window, sliding log, sliding counter) behind one interface with in-memory and Redis backends.
- Used atomic Redis Lua scripts so 3 gateway instances enforced a shared 1,000 req/s limit exactly under load.

## EXPERIENCE

**Example Logistics Co.** | Portland, OR
*Data Analyst Intern* | Jan 2024 - May 2024
- Wrote SQL pipelines joining 3 systems for daily reporting; built dashboards for 3 KPIs used in weekly planning.
