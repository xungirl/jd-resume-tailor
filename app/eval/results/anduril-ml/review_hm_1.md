## Anduril 2027 MLE Intern: hiring manager screen of Alex Rivera's resume

**1. 10-second impression**
This is a backend / distributed-systems engineer (Go Raft store, rate limiter, Spring Boot on AWS) with one RAG retrieval project. It reads like an SWE resume, not an ML one. There's no trained model, no PyTorch and no vision, graph or 3D work. **Match: weak.**

**2. Move to the next round: no.**
The resume doesn't show anyone training and evaluating models, which is the core of the job. The single ML-adjacent project is retrieval tuning, and it doesn't say whether the candidate is a U.S. Person, which is required.

**3. Hard requirements**
| Requirement | Evidence |
|---|---|
| Pursuing BS/MS in CS or related field | "Master of Science in Computer Science \| GPA: 3.9/4.0 … Expected Dec 2027" ✅ |
| Returning to school after the internship | "returning to school in Fall 2027" ✅ |
| U.S. Person (export control) | **No evidence** |
| In person in Santa Ana, CA, for 12 weeks in summer 2027 | Partial: "Summer 2027 internship, full-time (12 weeks)". The candidate lives in Seattle, and there's nothing about working on-site or relocating. |

The preferred qualifications where they matter most:
- **PyTorch/TensorFlow:** no evidence.
- **ML, probability or statistics coursework:** no evidence. Listed coursework is "Algorithms, Distributed Systems, Databases".
- **CV, GNN or VLM:** no evidence.
- **NLP/LLM:** partial ("RAG, embeddings, LLM evaluation harnesses").
- **Experiments vs. baselines:** "65% baseline to 95% across 12 retrieval experiments" ✅
- **Git/Docker:** ✅
- **GPU, C++/CUDA, CAD or manufacturing data:** no evidence.

**4. Bullets I can't follow or don't believe**
- **"Raised Recall@5 from a 65% baseline to 95% across 12 retrieval experiments"**
  - No eval-set size, no source for the labels and no description of what the 12 experiments changed.
  - A 30-point gain on what may be a small, self-labeled query set reads like overfitting to the eval set.
  - "BM25 + vector search" is a standard hybrid setup, not something the candidate invented.
- **"Cut p50 LLM pipeline latency from 9.0s to 3.5s"**
  - The gain came from removing a redundant call, which is a bug fix, not an ML result. It's fine, but it tells me nothing about ML skill.
- **"Scaled a 3-node cluster from 80 to 2,400 writes/s via group commit"**
  - A 30× jump with no hardware, payload or fsync settings given. An 80 writes/s baseline means one fsync per write on one machine (or localhost), which isn't a real deployment.
- **throttle: "Implemented 4 rate-limiting algorithms…"**
  - No visible result: no load numbers and no correctness tests.
- **"built dashboards for 3 KPIs used in weekly planning"**
  - No scope: no data volume, and no decision the dashboards changed.

**5. Interview questions**
1. "Walk me through how you built the DocQA eval set. How many queries were there, who labeled them, and how did you keep from tuning to the test set across 12 experiments?"
2. "Have you trained a neural network end to end, picking the loss, architecture and training loop? What did it beat, and how did you know?"
3. "Suppose you're given 5,000 engineering drawings as PDFs, and engineers want a model that pulls out tolerance callouts. How would you frame the problem, label the data, pick a baseline, and design the step where engineers review predictions?"

**6. Suggested changes, by effect on the hiring decision**
1. **Add a line on work authorization and location:** "U.S. Person (U.S. citizen/permanent resident); able to work in person in Santa Ana, CA, Summer 2027." Only add it if it's true. Without it, many screeners at a defense company reject automatically.
2. **Add one real model-training project in PyTorch** that compares against a simple baseline. The closest fit is vision or document understanding on drawings/PDFs, or a GNN on 3D meshes or CAD (for example ABC or Fusion 360 Gallery). This single gap decides the screen.
3. **Rewrite DocQA in this job's terms:** dataset size and how it was labeled, metric and baseline, what each experiment varied, and a review step where people check the outputs. Put it first.
4. **List ML, probability, statistics or linear algebra coursework** if taken, and add PyTorch, GPU or Colab training, and C++ to the skills if they're real.
5. **Shrink Shopline and throttle to one line each, or cut them.** Use the space for the ML project and for a line on using AI coding tools and checking their output.

VERDICT: no