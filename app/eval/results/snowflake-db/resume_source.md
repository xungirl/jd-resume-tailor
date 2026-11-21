# Alex Rivera
Seattle, WA | alex@example.com | linkedin.com/in/example | github.com/example

## EDUCATION
**Example State University** | Seattle, WA
*Master of Science in Computer Science | GPA: 3.9/4.0* | Expected Dec 2027
Coursework: Algorithms, Distributed Systems, Databases
Availability: Summer 2027 internship, full-time (12 weeks); returning to school in Fall 2027

**Example College** | Portland, OR
*Bachelor of Science in Information Systems* | Sep 2020 - Jun 2024

## TECHNICAL SKILLS
Languages: Java, Go, SQL, Python
Distributed Systems: Raft, leader election, log replication, write-ahead logs, rate limiting, chaos testing
Databases & Backend: PostgreSQL, Redis, optimistic concurrency control, Spring Boot, REST, gRPC
Cloud: AWS (ECS, RDS, S3, IAM), Docker, Terraform, GitHub Actions CI/CD
Stability & Performance Testing: fault injection, load testing (p50/p99), Go race detector, JUnit 5

## PROJECTS
**tinykv** | *Raft-Replicated Key-Value Store in Go* | GitHub
- Built a Raft key-value store in Go (stdlib only): leader election, log replication, and a CRC-checked write-ahead log with fsync and group commit.
- Lost 0 of 10,000 acked writes in 50 SIGKILL process crashes; a chaos harness re-reads every acked key.
- Scaled a 3-node cluster from 80 to 2,400 writes/s as concurrent clients grew from 1 to 64 via group commit; measured 250 ms median leader failover.

**Shopline** | *E-Commerce Backend (Spring Boot, PostgreSQL, AWS)* | GitHub
- Designed a normalized PostgreSQL schema for carts, orders and inventory with optimistic locking for concurrency control, served by 25 REST endpoints.
- Deployed with Docker on AWS ECS Fargate behind an ALB with RDS PostgreSQL, defined as code in Terraform.
- Reached 90% line coverage with JUnit and Testcontainers; CI on GitHub Actions blocks merges on failing tests.

**throttle** | *Rate-Limiting API Gateway in Go* | GitHub
- Implemented 4 rate-limiting algorithms (token bucket, fixed window, sliding log, sliding counter) behind one interface with in-memory and Redis backends.
- Used atomic Redis Lua scripts so 3 gateway instances enforced one shared 1,000 req/s limit under load.

## EXPERIENCE
**Example Logistics Co.** | Portland, OR
*Data Analyst Intern* | Jan 2024 - May 2024
- Wrote SQL pipelines joining 3 operational systems for daily reporting; built dashboards for 3 planning KPIs.
