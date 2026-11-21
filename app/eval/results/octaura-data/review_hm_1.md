**1. 10-second impression**
This is an MS CS student (graduating Dec 2027) who leans toward backend and distributed systems. The resume has Raft, a rate limiter, a Spring Boot backend and a RAG Q&A project, plus one 5-month Data Analyst internship that involved SQL pipelines and dashboards. **Match: medium.** The engineering is solid and the GenAI/search work maps well to the JD's projects. But the data-engineering experience is thin (one bullet), and nothing shows interest in finance or trading.

**2. Move to the next round: yes.** The JD's example projects are a metrics dashboard, GenAI analysis of trading data and advanced search, and this resume has real evidence for all three. The one open item to confirm in the screen call is that the candidate will work in the NYC office.

**3. Hard requirements**
- **Graduation between Dec 2027 and May 2028:** "Master of Science in Computer Science … Expected Dec 2027". The date is in the window. The JD says "undergraduate graduation" and this is a master's, which is probably fine but needs a check with recruiting.
- **Major in Computer Science / Data Engineering:** "Master of Science in Computer Science". The undergrad degree is "Information Systems".
- **Strong communication and analytical skills:** The analytical side is covered indirectly: "benchmarking 12 retrieval configurations", "dashboards for 3 KPIs used in weekly planning". There is **no evidence** of communication: no presenting, writing, client contact or teamwork.
- **June–August 2027 time frame:** "Summer 2027 internship, full-time (12 weeks)". Matches.
- **In office in NYC, Monday through Friday:** **No evidence.** The candidate is in Seattle, WA, and the resume doesn't mention relocating.

**4. Bullets I can't follow or don't believe**
- "Raised Recall@5 from 65% to 95%…": The resume doesn't say how big the eval set or the ticket set is, or where the data came from. A 30-point gain on an unnamed benchmark could come from 20 hand-written questions.
- "Held 3 gateway instances to a shared 1,000 req/s limit **exactly**": "Exactly" makes me suspicious. What was measured, over what window, and how much did it overshoot?
- "Scaled a 3-node cluster from 80 to 2,400 writes/s via group commit": A 30× gain is believable with fsync batching. Still, the resume doesn't give the hardware, the batch size, or what happened to latency.
- "Added cart, order and inventory features to an e-commerce platform": This reads like a team product, but it's a personal project. Whose platform is it, and does anyone use it?
- "Wrote SQL pipelines joining 3 operational systems… dashboards for 3 KPIs": This is the only real work experience and the bullet that matters most for this role. It gives no data volume, tools, schedule, users or outcome. "WebSockets" appears in skills but no bullet backs it up, and the JD stresses real-time data.

**5. Interview questions**
1. On DocQA: how did you build the eval set behind the 65%→95% Recall@5 figure? How many queries were there and who labeled them? What did the winning configuration change?
2. At Example Logistics: walk me through one pipeline end to end. What were the source systems and data volume, how was it scheduled, what broke, and how did you find out?
3. Say we want to show clients live loan prices and trade activity on a dashboard. How would you design ingestion through to display, and how would you handle late or duplicate quotes?

**6. Suggested changes (biggest effect on the decision first)**
1. Add a line on location: "Relocating to NYC for Summer 2027; available in-office M–F." Without it, a Seattle address on an in-office NYC role is an easy reason to reject.
2. Expand the Data Analyst internship into 2–3 bullets with tools (warehouse, scheduler, BI tool), data scale, who used the output, and one result such as time saved or a decision it changed. This is the most relevant experience on the page.
3. Reorder the projects so data and GenAI come first: DocQA first, and cut or shorten throttle. Use the space for a data project, ideally real-time or streaming on public market data, which would also back up the WebSockets skill.
4. Give DocQA some scope: corpus size, eval-set size, what the 12 configurations varied, and what the data was.
5. Add one sign of interest in fintech or trading, whether a project, a course or a single line. The JD is clearly looking for people "interested in fintech and electronic trading."

VERDICT: yes