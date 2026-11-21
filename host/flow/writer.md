ROLE: writer

Use the jd-resume-tailor skill to make a one-page resume for one job. You run unattended: nobody answers questions during this run. Work in this folder: {jobdir}

Job: {company} - {title}
Posting: {url}
The job description is in ./jd.md. Work only from it.
{answers}{projects}
Follow the skill for setup (my config, my bullet bank, the builder, where PDFs go) and for its truth rules, which come first. Skip its application-form and record steps: don't touch any tracker, Notion page or spreadsheet; I record applications myself after I apply. On top of the skill, follow these steps.

## 1. Analysis: write ./analysis.md

Use exactly these labels, one per line (lists comma-separated):

Company: ...
Role: ...
Level: ... (basis: years / pay band)
Direction: <the track in my bank this job fits, e.g. ml_infra, backend>
Second direction: <track or "none"> (why)
Location / visa / start date: ... (quote the JD's own sentences)
Hard requirements: ...
Nice to have: ...
ATS keywords: ... (the JD's own spelling; join spellings of one thing with "/", e.g. Kubernetes/k8s)
Ideal candidate: 2-3 sentences
Strategy: what to emphasize and from which angle
Known gaps:
- <keyword>: why I have no evidence for it

Judge by the requirements, not the title. Stop and ask me (step 6) instead of building when: the role is generic with no clear direction, two directions tie on hard requirements, or a hard eligibility condition fails (clearance, US citizenship, start date before my graduation, years far above mine). Sponsorship is not a gate: if the JD says it won't sponsor, build anyway and say so in "constraints". A location entirely outside the US: answer "skip".

## 2. Choose experiences and write bullets

- Map every hard requirement and nice-to-have to facts in my bank. Each bullet proves at least one. A fact that proves none is left out.
- Write each bullet as: verb -> result -> scope (2-6 words) -> method (by / with + one technique) -> tech. About 120-170 characters, never more than 200, at most 2 lines on the page. If the last line would hold only 1-3 words, cut words to pull it back.
- When too long, cut in this order: configuration details (instance types, runners, cache state, round counts, TTLs), supporting numbers, measurement details (sample sizes, percentile method), minor tech names.
- Use the JD's own words, not synonyms. Each core keyword appears 2-3 times in total across bullets and skills, no more.
- One fact appears once on the page. Recent work gets at least as many bullets as older work.
- No negative phrasing ("does not claim production gains") on the page.
- List every number that I reported myself and that the bank does not show as re-measured, under "unverified_numbers" in step 6.

## 3. Skills section

Group by category (names follow the JD). Pick in tiers: JD words I really know -> tools named in my bullets -> other skills related to the JD's domain. Order each line by relevance. Nothing unrelated, nothing added just to fill a line. If a line wraps after building, drop its last filler skill.

## 4. Build and check

Build as the skill says (a new variant for this job), then run:

    {check} ./resume.pdf ./analysis.md

Copy the built PDF to ./resume.pdf first. Fix every failure it prints and rebuild until it passes:
- more than one page or no extractable text: drop the least relevant section or bullet;
- a keyword missing: write it in with the JD's word if my bank has the fact; otherwise add it to "Known gaps" in analysis.md;
- a keyword used more than 4 times: remove the extra repetitions (usually in skills).
If the check reports more than about 3 empty lines at the bottom and my bank has another relevant true bullet, add it; otherwise leave the space.

## 5. Write ./resume_source.md and ./notes.md

resume_source.md is the exact text on the page in reading order: the header with contact details, each section heading, each entry's title line, every bullet, every skills line. The ATS reviewer compares the PDF against it.

notes.md is for you later: which experiences you chose and why, what you dropped, what you would change if a reviewer pushes back. Revision runs read it.

## 6. Last, write ./writer.json (nothing after it)

{{"status": "built" | "needs_user" | "skip",
  "direction": "<track>",
  "lead": "<which project leads and the JD line it answers>",
  "dropped": ["<left out and why>"],
  "gaps": ["<JD keyword with no evidence>"],
  "constraints": ["<eligibility notes for me, e.g. no sponsorship, onsite city>"],
  "unverified_numbers": ["<self-reported number on the page and where it came from>"],
  "new_from_projects": [{{"project": "<name>", "bullet": "<the bullet as on the page>", "source": "<file(s) the facts came from>"}}],
  "questions": ["<what only I can decide>"],
  "bullets_changed": 0,
  "touched_hard_requirement": false,
  "summary": "<two sentences for me>"}}
