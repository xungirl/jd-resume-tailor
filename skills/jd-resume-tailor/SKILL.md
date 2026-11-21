---
name: jd-resume-tailor
description: Tailor a one-page resume to a specific job description (JD) without inventing anything. Fetches the JD from the posting URL (Greenhouse, Ashby, Lever, Workday, Oracle, SmartRecruiters), checks hard eligibility constraints, reorders and selects true bullets from the user's bullet bank into a new variant, builds and visually checks a one-page PDF, gives a neutrally named copy to upload, and helps with the application form (why-us answers, autofill pitfalls). Use when the user pastes a job link or JD and says "tailor my resume", "改简历适合这个岗位", "按 JD 微调简历", "这个岗位用哪个简历", or pastes an application form / review page to check.
---

# jd-resume-tailor

Goal: for one job posting, produce the strongest **honest** one-page resume the user already has the facts for, and get the application submitted cleanly. Tailoring means **choosing and ordering**, not writing new claims.

## 0. Setup (read first)

Look for the user's config at `$JD_RESUME_TAILOR_CONFIG` if that variable is set (`echo $JD_RESUME_TAILOR_CONFIG`; tools like jd-apply set it for unattended runs), otherwise at `~/.config/jd-resume-tailor/config.md`. When the variable is set, that file is the only config: don't open the default one or look for other banks, even if the bank it names looks like an example. It says where their bullet bank lives, how to build, where PDFs go, and (optionally) a tracker to record applications in. If it does not exist, ask once for:
- the resume source: a bullet-bank file (this repo's `builder/` TOML format, see `builder/example/resume.toml`) **or** their own build script;
- the output folder;
then write the config so the next run skips the questions.

**Where the builder is.** When installed as a plugin or with `install.sh`, it sits two levels up from this skill's real folder: resolve symlinks first (`install.sh` links this folder into `~/.claude/skills` and `~/.agents/skills`), e.g. `cd "$(cd <skill_dir> && pwd -P)/../../builder"`, and find `build_resume.py` there, with the example bank next to it. Build with `cd <builder dir> && OUTDIR=<output folder> uv run --with reportlab python build_resume.py <bank.toml> --variant <name>` (without `uv`: `pip install reportlab`, then `python3 build_resume.py ...`). If `builder/` is missing (installed with `npx skills add`, which copies only this folder), ask the user to `git clone https://github.com/xungirl/jd-resume-tailor` and use the builder from there, or point the config at their own build script.

**Keep the user's bank outside the plugin folder** (e.g. `~/resume/resume.toml`). Plugin updates replace the plugin folder, so a bank or variant saved inside it would be lost. If the user names the example bank as theirs, copy it out first and work on the copy.

**No bullet bank yet?** Most people arrive with a PDF or Word resume. Offer to start one from it:
1. Read the existing resume (PDF, DOCX or pasted text).
2. Copy `builder/example/resume.toml` to the user's chosen path and replace its content with theirs, **word for word**: same numbers, dates, titles, degrees. Give each bullet a short key. Don't polish, merge or "improve" bullets in this step, and don't fill in missing numbers. Where a bullet has no number, leave it as is and list it for the user as "worth measuring".
3. Add one variant that reproduces their current resume, build it, and have the user confirm the bank matches what they already had before tailoring anything.
4. Then ask whether they have true bullets that didn't fit on the old page (more projects, more results). Those are what make tailoring worth it.

## 1. Get the JD

- Run `python3 <skill_dir>/fetch_jd.py "<url>"`. It follows referral/short links, detects the ATS, and prints title, location, **OPEN / NOT FOUND**, and the JD text. Exit code 2 = posting gone: tell the user before doing any work.
- If the fetcher can't read it (custom career site), ask the user to paste the JD. Never guess a JD from the job title.

## 2. Read it like a recruiter

Extract, in this order:
1. **Hard constraints** (pass/fail): graduation window, degree level, "N semesters remaining after the internship", program dates / duration, onsite city, work authorization or "no sponsorship", application limits ("max 2 applications per cycle"), "must have prior internship".
2. **Must-haves**: languages, domains, fundamentals.
3. **Nice-to-haves**: named technologies, domains (e.g. "vector DB", "CI/CD", "AI coding assistants").
4. **What the team actually builds** (one sentence). This decides which project leads.

Report constraint conflicts plainly (e.g. "JD says 2 semesters left after the internship; you have 1, but its graduation window explicitly includes Dec 2027, so applying is fine"). If a hard constraint fails, say so and suggest skipping.

## 3. Map JD → bullet bank

- Score each project in the bank by how directly it demonstrates the "what the team builds" sentence, then must-haves, then nice-to-haves. The best match leads, with the most bullets.
- Reorder the **Languages** line so the JD's language comes first; pick skill groups whose keywords appear in the JD; keep every skill line to **one line**.
- Drop projects that are impressive but off-topic for this team (they cost space and dilute the story).
- **Header tags** (the italic words after each project title, `tags` in the bank): re-pick them for this JD and put them in the variant's `tags = { key = "..." }`. Use **2-3 tags**: the project's main language, then the core capability in the JD's own words (e.g. `C++20 · Query Engine · Concurrency` for a database team, `Go · Kubernetes · Container Security` for a security team). No benchmarks, test frameworks or wire protocols as tags (`TPC-H`, `JUnit`, `TCP`): they describe how it was checked, not what it is. A tag must be something the repo really is or uses; the title line must not wrap.
- Mention a strong but non-obvious hook if there is one (e.g. the user's degree matches the company's domain) for the form's "why us" question, not for the resume.

### Truth rules (non-negotiable)
- Only reuse bullets that already exist in the bank, or rewrite one using facts you **verify in the repo or its benchmark/results file** (grep the code; read the README/BENCHMARK). Cite where the fact came from when you add a new bullet to the bank.
- Never add a technology to skills because the JD wants it. If the JD's keyword has no evidence (e.g. C++, Kubernetes), leave it out and tell the user it's a gap to prepare an honest interview answer for, or a project to build.
- Never change numbers, dates, titles or degrees. Never back-date a project.
- Don't add lines that aren't in the bank, even true facts the user mentions in chat (work authorization, availability, relocation). Those go on the application form; put them on the resume only if the user asks for it.
- If the user asks you to fabricate, decline and offer the honest alternative (reorder, or build the thing for real).

## 4. Build and check

- Use the builder in place. Don't copy it into the user's folder or edit it to change the layout; if the page doesn't fit, change the variant (fewer or other bullets).
- Add a new variant (named after the company/role family) instead of editing an existing one. If the build script is shared with other sessions, make **targeted** edits (insert one block), never rewrite the whole file. Back it up first.
- Build. Treat `OVERFLOW` as a failure: cut the weakest bullet. If there is room for 2+ lines, add the next most relevant true bullet rather than leaving white space.
- Render to PNG (`pdftoppm -r 110 -png -singlefile file.pdf out`) and **look at it**: one page, no orphan words on skill lines, headings not wrapped, links present. If bold text looks regular in the render, check `pdffonts file.pdf` before calling it a layout bug: fonts that aren't embedded get substituted, and poppler draws them without bold. The builder embeds fonts by default and prints `font: ... (NOT embedded)` when it couldn't. Without `pdftoppm`, use `sips -s format png file.pdf --out out.png` on macOS.
- If the JD asks for availability dates, turn on the availability line.

## 5. Hand off

- Copy the PDF to a neutral name (e.g. `submit_<variant>/<First>_<Last>_Resume.pdf`): the variant name ("Acme_Storage") must not reach another company's recruiter.
- Tell the user, briefly: which project leads and why (map to JD lines), what was dropped, which JD keywords are honest gaps, any constraint caveats.

## 6. The application form

When the user pastes a form or a Workday "Review" page, check it against `checklist.md` in this folder. The usual catches:
- ATS **autofill** stuffs project bullets into a job's "Role Description", picks a wrong field of study, leaves start dates blank. Fix these: they become false statements once the user signs the certification checkbox.
- "Why us" answers: build them from the user's real story and real numbers; ask before adding feelings or events you can't verify ("I still remember..." only if true).
- Sponsorship / work authorization questions: answer truthfully, every time.
- Before applying, check the company's own portal for an existing application to the same posting (duplicates look bad and tailoring is wasted).

## 7. Record

If the config names a tracker (Notion database, spreadsheet, Markdown table), record: company, role, link, date, which variant was used. Note company-level application limits you learned from the JD so the next run respects them.
