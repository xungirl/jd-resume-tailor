## 1. 10-second impression
This is a backend/distributed-systems MS CS student (3.9 GPA, graduating Dec 2027) who also has hands-on RAG/LLM evaluation work. All the substance is in four personal projects; the only job is a 5-month data analyst internship. Match: **medium-strong**. CS fundamentals and the AI requirement are clearly covered. There is no product or frontend work, and nothing shows the candidate working with other people.

## 2. Move to next round
**Yes.** The projects are technically deep and backed by measured numbers, and the DocQA project directly covers the JD's LLM/model-evaluation requirement. The weak spots (all solo work, no responsible-AI signal, work authorization not stated) are things a phone screen can check.

## 3. Hard requirements vs. evidence
| JD requirement | Evidence |
|---|---|
| Enrolled BS/MS, graduating Dec 2027 – Jun 2028 | "Master of Science in Computer Science … Expected Dec 2027". This is inside the window, but only just. |
| Less than 2 years full-time relevant experience | Met: the only job is "Data Analyst Intern, Jan 2024 – May 2024". There is an unexplained gap between the BS ending in Jun 2024 and the MS start date, which isn't listed. |
| CS fundamentals (DS, algorithms, design patterns) | "Coursework: Algorithms, Distributed Systems, Databases"; "4 rate-limiting algorithms … behind one interface"; Raft "leader election, log replication" |
| One or more languages/tools | "Java, Go, Python, SQL, TypeScript". Java and Go are clearly used in the projects. TypeScript has no project behind it. |
| AI foundations (model evaluation, LLM APIs) | "Benchmarked 12 retrieval configurations on a 60-query test set, raising Recall@5 from 65% to 95%"; "LLM evaluation harnesses" |
| Responsible AI (fairness, privacy, safety) | **No evidence** |
| Problem-solving and collaboration | Problem-solving is strong (tinykv chaos harness). Collaboration: **no evidence**. Every project reads as solo. |
| Written and verbal communication | **No evidence** beyond the resume being clear |
| Time management / adaptability | **No evidence** |
| Leadership / teaching / community (plus) | **No evidence** |
| US work authorization, no sponsorship ever | **No evidence.** The resume doesn't say. This is a hard gate for this role. |
| Based in SF, in office 3 days a week | The candidate is in Seattle, WA. Relocation is provided, so this is fine if they're willing to move. |

## 4. Bullets I can't follow or don't believe
- **"enforced a shared 1,000 req/s limit exactly under load"**: "Exactly" is a red flag. Distributed limiters always have some error at window edges. I'd want to see the measured over-admission rate.
- **"raising Recall@5 from 65% to 95%" on "a 60-query test set" after "12 retrieval configurations"**: If you pick the best of 12 configs on the same 60 queries, you are tuning on the test set. A 30-point gain on n=60 is probably overfit unless there was a held-out split.
- **"Cut p50 answer latency from 9.0s to 3.5s by caching embeddings and removing a redundant retrieval call"**: Removing a redundant call is fixing your own bug, not optimizing. I can't tell how much of the gain came from which change.
- **"Scaled a 3-node cluster from 80 to 2,400 writes/s via group commit"**: 30x is believable if the baseline did one fsync per write. Without the hardware and batch size, the number has no anchor.
- **Shopline (all three bullets)**: Endpoints, coverage and a deploy, but no result. Nobody uses it, there's no load number, and nothing explains why optimistic locking mattered. It reads like a tutorial project.
- **Skills listed with no supporting work**: Kubernetes, gRPC, WebSockets, TypeScript, "tool-calling agents" and "Go race detector" don't appear in any bullet.
- **No dates on any project**: I can't tell what's recent, or what the candidate did between Jun 2024 and the MS.

## 5. Interview questions
1. "In tinykv, walk me through a SIGKILL that happens after the leader appends to its log but before a majority acks. What does the client see, and how does your harness tell 'lost' apart from 'never acknowledged'?"
2. "For DocQA, how did you build the 60 queries and their relevance labels? Did you choose the winning configuration on the same set you report 95% on?"
3. "Imagine your support-ticket Q&A ran on real Airbnb guest messages. What privacy or safety problems would you design for? Also, tell me about a time you built something with other people and disagreed on the approach."

## 6. Suggested changes (highest impact first)
1. **State work authorization** in the header (for example, "US work authorized, no sponsorship required"). If this isn't clear, the resume gets filtered out before any technical screen.
2. **Add one collaborative or people-facing item**: a team project, TA or mentoring role, open-source PR, or hackathon. Right now every line is solo, and the JD explicitly asks for collaboration, communication and leadership.
3. **Fix the DocQA evaluation claim**: report results on a held-out split, or rephrase the bullet. Then add one bullet on responsible AI, such as PII redaction in tickets, refusing to answer when retrieval confidence is low, or hallucination checks. This covers a JD requirement that currently has zero evidence.
4. **Replace or shorten Shopline with something user-facing** (TypeScript/React plus a backend), or give Shopline a measured result. Airbnb's example intern projects are full-stack product features, and this resume has no UI work.
5. **Add dates to the projects, explain the 2024–MS gap, and trim unused skills** (Kubernetes, gRPC, WebSockets) so every listed skill has a bullet behind it. Change "exactly" to the measured error figure.

VERDICT: yes