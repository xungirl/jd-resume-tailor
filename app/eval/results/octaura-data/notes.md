# Notes: Octaura, Intern Data Engineering (variant `octaura_data`)

## Files
- Bank: `octaura-data/resume.toml` (backup before edits: `octaura-data/resume.toml.bak_octaura`)
- Built PDF: `octaura-data/out/Alex_Rivera_Resume_octaura_data.pdf`, copied to `./resume.pdf`; copy to upload: `out/submit_octaura_data/Alex_Rivera_Resume.pdf`
- check.py: PASS, 1 page, bottom gap 2.58 in (warning only)

## What I added to the bank (targeted inserts; existing bullets and variants untouched)
- Skills: `lang_python` (Python first), `data_eng`, `genai_search`, `backend_rt`, `cloud_lean` (no Kubernetes/IAM/S3, which no bullet backs).
- Rewritten bullets under new keys, same facts and numbers as the originals, in JD wording and verb→result→method order:
  `rag.eval_genai` (from eval; dropped "60-query test set"), `rag.lat_rag` (from lat), `shop.api_features` (from api),
  `kv.core_protocol` (from core; dropped "fsync and group commit" because group commit is in perf_tp), `kv.chaos_data` (from chaos),
  `kv.perf_tp` (from perf; dropped "(1 to 64 clients)" to fix a 2-word last line), `gateway.redis_shared` (from redis).
- Variant `octaura_data`, with availability on because the JD gives "Time frame: June – August 2027".

## Choices
- Direction ai (GenAI/search over data), second backend. The JD's hard requirements name no technology, so I ranked by its project list: GenAI appears twice, plus "advance search", "metrics dashboard", "trading data analysis".
- Lead: DocQA → "utilize GenAI or advance search capabilities to analyze market data" / "trading data analysis using GenAI".
- Shopline → "enhance trading platform adding new features"; tinykv → "new features or protocols" plus data integrity; throttle → platform under load (weakest; first to cut).
- The Data Analyst Intern bullet (SQL pipelines, KPI dashboards) is the strongest "metrics dashboard" / data engineering evidence, but the builder always puts Experience last.
- Skills use the JD's words: "Data Engineering", "data analysis", "metrics dashboards", "GenAI".

## Dropped
- Original duplicates (eval, lat, api, core, chaos, perf, redis): replaced by the rewrites; one fact per page.
- Skill groups `dist`, `test`, `ai`, `backend`, `cloud`: replaced by the regrouped lines above. Removed Kubernetes, gRPC, IAM, S3, Go race detector, load-testing details as unrelated to this JD or not backed by any bullet.
- The page has every relevant bank fact, so the 2.6 in gap stays: the bank has nothing else true to add.

## Known issues / if a reviewer pushes back
- Experience bullet ends with a 1-word last line ("planning."). It is shared by every variant, so I didn't edit it. Fix it in the bank if the user agrees, e.g. "…built dashboards for 3 KPIs for weekly planning" (still wraps) or drop "for daily reporting".
- "Within one year of undergraduate graduation": Alex's undergrad ended Jun 2024, but the MS (Expected Dec 2027) is inside the Dec 2027 – May 2028 window. It's listed under "Ideal Candidate", so I didn't treat it as a gate. Flagged as a question.
- Domain gaps: real-time data, market data, trading, fintech, admin tools. If the reviewer wants "real-time" on the page, there's no honest bullet. WebSockets is a skill only.
- If space is needed: cut the throttle algo bullet first, then the Shopline test bullet.
- If a reviewer says Cloud & DevOps is off-JD: drop that line (it is tier 2: tools from the Shopline aws bullet).

## Revision 1 (after HM: yes, ATS: pass)
Backup before this round: `octaura-data/resume.toml.bak_octaura_r1`. check.py: PASS, 1 page, bottom gap 3.5 in.

Changed (3 bullets reworded, 2 removed):
- `rag.eval_genai`: put back "on a 60-query test set" (bank fact) because the HM didn't believe the 65%→95% without the eval size. This bullet also backs "analytical skills", so touched_hard_requirement = true.
- `kv.perf_tp`: put back "(1 to 64 clients)" (bank fact) for the HM's "what was measured"; cut "measured"/"leader" so the last line isn't a single word.
- Shopline: replaced `api_features` ("Added … features to an e-commerce platform", which the HM read as a team product) with the new key `api_tight`: "Designed 25 REST endpoints and a normalized PostgreSQL schema for carts, orders and inventory." Dropped "optimistic locking" so the last line isn't a single word.
- Dropped the throttle project (algo, redis_shared). The HM suggested cutting it and doubted "exactly 1,000 req/s", and the bank has no measurement setup to defend it. It was already the weakest match for this JD.
- Skills: removed WebSockets (the HM flagged that no bullet backs it while the JD stresses real-time data) and Redis (no bullet left on the page after dropping throttle); added JUnit (named in the Shopline test bullet).
- analysis.md: dropped the ATS keyword "platform" (no longer used, and a personal backend isn't a "platform"); added "communication" and "real-time" as keywords listed under Known gaps; added the HM/ATS gaps the bank can't fill.

Not done (no bank facts, or a truth rule):
- Relocation / in-office NYC line: truth rules keep relocation, availability extras and work authorization off the page unless the user asks. Asked as a question.
- Phone number: not in the bank's profile. Asked.
- Expanding the Data Analyst internship (tools, volume, users, outcome), DocQA corpus size and what the 12 configs varied, tinykv hardware/batch size, a fintech or real-time project: none of this is in the bank. Listed as gaps.
- Bullet glyph not extractable as text: the builder draws bullets as circles. That's the template, so I reported it as a question and didn't edit the builder.
- Project dates: only tinykv has a date in the bank (Oct 2026), so turning on project_dates would date one project and leave the others blank. Skipped.
- Experience bullet still ends on a 1-word line ("planning."); it's shared by every variant (question from round 0 still open).

If space is wanted back: the throttle `algo` bullet is true and believable (no "exactly" claim). It's the only unused bank fact, and I'd add it back only if the user wants the page fuller.
