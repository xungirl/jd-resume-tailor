# Notes: Anduril 2027 ML Engineer Intern (writer run, 2026-11-21)

## Build
- Bank: anduril-ml/resume.toml (backup: resume.toml.bak_anduril_20261121014838). Variant `anduril_ml`.
- PDF: anduril-ml/out/Alex_Rivera_Resume_anduril_ml.pdf, copied to ./resume.pdf. check.py: PASS, 1 page, ~3.3 in empty at the bottom.
- Added to the bank (all reorderings or rewordings of existing facts, nothing new):
  - skills `lang_py`, `ai_ml` (label "LLM / NLP"), `test_ml`, `tools_ml` (adds "Git", see below), `data_ml`
  - bullets `rag.eval_ml`, `rag.lat_ml`, `kv.chaos_ml`, `kv.perf_ml`, `kv.core_ml`

## Fit
The bank has no model training at all: no PyTorch/TensorFlow, no CV/GNN/VLM, no labeled training dataset, no GPU. The JD's core work (train graph/vision/VLM models on CAD, drawings, production records) is a gap. The page does the most it honestly can: it presents the candidate as someone who runs measured experiments against a baseline, builds pipelines, and verifies results.

## Chosen, and why
- DocQA leads (eval_ml, lat_ml): the closest match to "train and evaluate models ... compare them against simple baselines", "language ... models for document understanding", "designing experiments, analyzing results". The 65% starting Recall@5 is presented as the "baseline" (it is the starting configuration the bank reports). I dropped the "60-query test set" sample size and the word "hybrid" so the bullet fits on one line.
- tinykv (chaos_ml, perf_ml, core_ml): the most recent work (Oct 2026). "Independently perform experiments", "test, verify". core_ml gives algorithms (Raft). Group commit now appears only in perf_ml (one fact once on the page). The "1 to 64 clients" range was cut as a configuration detail.
- Shopline (aws, test): Docker, cloud (AWS), Git/CI.
- throttle (algo): "foundation in data structures, algorithms".
- Experience (SQL pipelines): real operational data, pipelines. The builder always prints the experience bullet as it is in the bank, so its last line holds only the word "planning." Fixing that means editing the shared experience bullet, which changes every variant, so I left it.

## Dropped
- shop.api (REST endpoints/schema), gateway.redis (shared limit): true, but they prove no JD requirement.
- Original rag.eval/lat, kv.chaos/perf/core: replaced by the reworded *_ml versions (same facts).
- Skills: Kubernetes, Spring Boot, gRPC, WebSockets, Raft/distributed-systems line: not related to the JD.

## Judgment calls a reviewer might push on
- "Git" in Tools: the bank has GitHub repos and GitHub Actions CI that blocks merges, so I treated Git as evidenced. If that's too loose, remove it and add Git to Known gaps.
- "LLM / NLP" label and "LLM pipeline latency": the DocQA retrieval and RAG Q&A over ticket text is NLP/LLM application work. If a reviewer reads "NLP" as implying model training, rename the label to "LLM / Retrieval".
- "experiments" for the 12 benchmarked configurations and the 50 SIGKILL faults: a rewording of "benchmarked" / "faults".
- "Python" appears only once (skills). The bank never says what language DocQA is written in, so I didn't add it to a bullet.
- White space: about 3 in empty, and the bank has no other relevant true bullet. The real fix is a real ML project (for example, a PyTorch vision or GNN model on public CAD data such as ABC/Fusion 360 Gallery, compared against a baseline) that would lead the page.

## Revision 1 (after HM "no" / ATS "pass")
Bank backup before rev1: anduril-ml/resume.toml.bak_anduril_rev1. Same variant, check.py PASS, ~2.8 in free.
Changed (3 bullets plus 1 skills line, all from facts already in the bank):
- rag.eval_ml: the HM didn't believe the Recall gain, so I put the test setup back: "on a 60-query test set by benchmarking 12 retrieval configurations, landing on hybrid BM25 + vector search" (bank rag.eval wording). I couldn't add who labeled the queries or what each configuration varied, because the bank doesn't say. Those are listed as gaps and as interview prep.
- rag.lat_ml: "large language model (LLM) Q&A pipeline" spelled out for ATS, and "answer latency" restored (bank wording).
- kv.perf_ml: the HM doubted the 30x jump, so I put the bank's "1 to 64 clients" back as the load-test setup. Hardware, payload and fsync settings aren't in the bank.
- Skills: label "LLM / NLP" became "Natural Language Processing (NLP)" (ATS full phrase). "tool-calling agents" was dropped so the line stays on one line.
Not done, and why:
- U.S. Person / on-site Santa Ana line (HM #1): not in the bank. It's an application-form fact and a user question.
- PyTorch model-training project (HM #2), ML/probability/stats/linear algebra coursework, Data Structures in coursework, Linux/GPU/C++/CUDA/PyTorch/TensorFlow in skills (ATS #3-4): no evidence. Listed as gaps.
- "machine learning" written in literally (ATS #2): the only ML-adjacent work is retrieval/RAG with no model training, so labeling it "machine learning" would overclaim. It stays a gap.
- Shrinking Shopline/throttle (HM #5): there's nothing true and ML-related to put in the freed space, and they carry Docker/AWS/Git and algorithms.
- throttle "no visible result": the bank's gateway.redis result (shared 1,000 req/s limit across 3 instances) is true but proves no JD requirement, so it's still left out. Add it if a reviewer wants a result on throttle.
- Dashboards scope (HM): the bank has nothing more.
- ATS separator before right-aligned location/dates, and bullet glyphs not extracted: these are builder-template issues, so they're reported as questions and the builder is unedited.

## Eligibility
- "Must be a U.S. Person" (export control); clearance eligibility may be required. The bank doesn't record citizenship or permanent residency. This is a hard gate the user must confirm; if they aren't a U.S. Person, don't apply.
- In-person in Santa Ana, CA, 12 weeks, summer 2027; must return to school for one more term afterward. The bank says Expected Dec 2027 and "returning to school in Fall 2027", so this passes.
