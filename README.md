# jd-resume-tailor

**Paste a job link. Get the best honest one-page resume you already have the facts for.**

A [Claude Code](https://claude.com/claude-code) plugin that tailors your resume to each job description by **choosing and reordering your real bullets**, never by inventing new ones. It reads the JD straight from the ATS, checks the eligibility fine print, builds a one-page PDF, and then checks your application form for the false statements that autofill sneaks in.

![Same bullet bank, two postings, two different resumes](docs/same_bank_two_jds.png)

<sub>Same bullet bank, two job postings. The backend posting gets the API project first; the AI posting gets the retrieval-evaluation project first and an AI skills line on top. Fictional candidate, see `builder/example/resume.toml`.</sub>

```
/plugin marketplace add xungirl/jd-resume-tailor
/plugin install jd-resume-tailor@jd-resume-tailor
```

Then, in Claude Code: *"tailor my resume for https://job-boards.greenhouse.io/acme/jobs/123"*

## What it will not do

Most "AI resume" tools make you look better by writing things you didn't do. Recruiters and interviewers catch that, and the form you sign at the end says it's all true. This one has rules:

- It **only reuses bullets from your bank**, or rewrites one with a fact it has verified in your repo or benchmark file.
- It **never adds a skill because the JD wants it.** A JD keyword you have no evidence for is reported to you as a gap to prepare for, not slipped into the PDF.
- It **never changes numbers, dates, titles, or degrees**, and it won't back-date a project.
- It **answers sponsorship and work-authorization questions truthfully**, every time.

## What it does that saves you time

- **Reads the JD from the source.** `fetch_jd.py` pulls the posting from Greenhouse, Ashby, Lever, Workday, Oracle Recruiting Cloud, or SmartRecruiters through their public JSON endpoints, follows referral and short links, and tells you if the posting is already closed before you spend 20 minutes on it.
- **Catches the fine print.** Graduation windows, "two semesters remaining after the internship", fixed program dates, onsite-only, "you may apply to at most 2 roles across our affiliates per cycle". It flags conflicts before you apply.
- **Leads with what this team builds.** One sentence on the team's actual work decides which project goes first. A storage team sees your write-ahead log; a product team sees your API design.
- **Stays one page, and looks at it.** The builder fails on overflow, warns when a skills line wraps, and Claude renders the PDF and checks it visually.
- **Neutral filenames.** The upload copy is `First_Last_Resume.pdf`, so "Acme_Storage" in a filename never reaches a different company's recruiter.
- **Checks the form.** Workday-style autofill pastes your project bullets into a past job's description, picks the wrong field of study, leaves start dates blank. Paste the review page and it walks `checklist.md` before you hit Submit.

## Why

Sending one generic resume everywhere is the default, and it works badly: the project a database team cares about is buried under the one a product team cares about. Hand-editing a Word file per job is slow and drifts. The fix here is boring on purpose:

- **Bullet bank, not documents.** Write each true bullet once, with a key. A tailored resume is a 6-line *variant* that chooses skill groups and bullets.
- **Tailoring = choosing and ordering.** The skill is not allowed to add skills you have no evidence for, change numbers, or back-date anything. Gaps get reported to you as interview prep, not hidden in the PDF.
- **The form matters as much as the PDF.** ATS autofill quietly writes false statements into your application (project bullets pasted into a past job, the wrong field of study). The skill checks the review page before you sign the "everything is true" box.

## What's inside

| Path | What it does |
|---|---|
| `skills/jd-resume-tailor/SKILL.md` | The workflow Claude follows: fetch JD → hard constraints → map to bullet bank → build → visual check → neutral filename → form review → record |
| `skills/jd-resume-tailor/fetch_jd.py` | Gets the JD as text from a posting URL through each ATS's public JSON endpoint: Greenhouse, Ashby, Lever, Workday, Oracle Recruiting Cloud, SmartRecruiters. Follows referral/short links, reports if the posting is closed. Standard library only. |
| `skills/jd-resume-tailor/checklist.md` | Application form checklist: autofill damage, truthful answers, duplicates, application limits |
| `builder/build_resume.py` | One-page resume builder (ReportLab) driven by a TOML bullet bank. Fails on overflow, warns when a skills line wraps, embeds fonts so ATS parsers and viewers don't substitute them. |
| `builder/example/resume.toml` | A complete example bank with 3 variants (fictional person) |
| `scripts/smoke_test.py` | Live check: finds an open posting on each of the 6 ATSs, fetches it, checks a closed one exits 2, builds the example bank |
| `config.example.md` | Template for your personal config (paths stay on your machine) |
| `.claude-plugin/` | Plugin + marketplace manifests for `/plugin install` |

## Quick start

**As a plugin (recommended):**
```
/plugin marketplace add xungirl/jd-resume-tailor
/plugin install jd-resume-tailor@jd-resume-tailor
```

**Skill only, any agent** (via [skills.sh](https://skills.sh)): `npx skills add xungirl/jd-resume-tailor`. This copies just the skill folder, so clone the repo too if you want the builder.

**Or clone it** (to hack on it, or to use the builder and fetcher on their own):
```bash
git clone https://github.com/xungirl/jd-resume-tailor.git
cd jd-resume-tailor
./install.sh                     # links the skill into ~/.claude/skills/

# try the builder on the example
cd builder
uv run --with reportlab python build_resume.py example/resume.toml
# -> example/out/Alex_Rivera_Resume_{backend,infra,ai}.pdf

# try the JD fetcher
python3 ../skills/jd-resume-tailor/fetch_jd.py "https://job-boards.greenhouse.io/<company>/jobs/<id>"
```

Then copy `builder/example/resume.toml` somewhere private (not inside the plugin folder: plugin updates replace it), replace it with your own facts, and copy `config.example.md` to `~/.config/jd-resume-tailor/config.md` with your paths. In Claude Code, paste a job link and say *"tailor my resume for this"*.

**Only have a PDF or Word resume?** Say so on the first run. The skill copies it into a bullet bank word for word (no polishing, no invented numbers), rebuilds your current resume from the bank so you can check nothing changed, and tailors from there.

Requirements: Python 3.11+, `reportlab` (the example uses [uv](https://docs.astral.sh/uv/) to pull it in), optionally `pdftoppm` (poppler) so Claude can look at the rendered page. Fonts are embedded: Arial on macOS/Windows, Liberation Sans on Linux. For nicer typography put the Carlito fonts (SIL OFL, metric-compatible with Calibri) in a folder and set `FONT_DIR`.

Already have your own resume script? Keep it. Point the config at it; the skill only needs to know how to add a variant and run a build.

## How a tailoring run goes

1. `fetch_jd.py` → title, location, **OPEN/closed**, JD text.
2. Hard constraints first: graduation window, semesters left, program dates, onsite city, sponsorship wording, "max 2 applications per cycle". Conflicts are reported plainly.
3. One sentence for *what this team builds*; the project that best proves it leads. Languages line is reordered for the JD; off-topic projects are dropped.
4. New variant → build → `OVERFLOW` is a failure, spare room gets the next true bullet → render PNG and look at it.
5. Copy to `submit_<variant>/First_Last_Resume.pdf` so one company's name never reaches another company's recruiter.
6. Paste the form's review page and the skill checks it against `checklist.md`.

## Tested

`fetch_jd.py` was checked against live internship postings on all six supported ATSs (including a Greenhouse `token=` embed link that doesn't name the company, and a closed posting returning exit code 2). Re-run it any time: `python3 scripts/smoke_test.py`.

End to end (2026-11-20), as a new user would get it: installed from GitHub with `/plugin marketplace add` + `/plugin install` into an empty Claude Code config, then driven with `claude -p --plugin-dir` and no user settings or other skills loaded. From one sentence ("Tailor my resume for <link>") Claude invoked the skill on its own, fetched the JD and read the example bank. On a Staff posting (10+ years) and on an internship limited to third-year undergrads, it stopped before building and explained the failed hard constraint. When told to build anyway, it added exactly one variant to the bank, built a one-page PDF led by the matching Go project, listed the JD's unmatched keywords (GraphQL, React) as gaps instead of adding them, and copied the PDF to a filename without the company. The run also turned up two fixes, now in: fonts weren't embedded (poppler drew bold as regular, so the visual check misreported), and the skill didn't say where the builder lives after a plugin install. `npx skills add` was checked to find and install the skill. Three runs cost about $0.83 in total.

## License

MIT

---

## 中文说明

一个 Claude Code skill，再加两个小脚本，用来**按岗位 JD 微调一页简历，而且不编造任何东西**。

**思路：**
- **素材库，而不是文档。** 每条真实的 bullet 只写一次，给它起个 key。针对一个岗位的简历，就是一个只有 6 行的「版本」，挑选用哪些技能组、哪些 bullet，按什么顺序排。
- **微调 = 挑选 + 排序。** 不许加没有证据的技能，不许改数字，不许倒填日期。JD 要求而你没有的东西，作为「面试要准备的短板」告诉你，不会偷偷写进简历。
- **申请表和简历一样重要。** Workday 这类系统会自动解析简历，经常把项目经历塞进实习描述、选错本科专业。勾「以上信息真实」之前，让 Claude 按 checklist 查一遍。

**流程：** 抓 JD（6 种招聘系统的公开接口，顺便判断岗位还开不开）→ 先看硬性条件（毕业时间、剩几个学期、实习日期、限投数量）→ 用一句话概括「这个组做什么」，最能证明这一点的项目放第一 → 生成新版本，超过一页算失败，有空位就补下一条真实的 bullet → 转成图片检查 → 复制一份文件名不带公司名的 → 检查申请表 → 记录投递。

**用法：** 在 Claude Code 里运行 `/plugin marketplace add xungirl/jd-resume-tailor`，再运行 `/plugin install jd-resume-tailor@jd-resume-tailor`（只要 skill 也可以用 `npx skills add xungirl/jd-resume-tailor`，但这样不带 builder；或者克隆后 `./install.sh`），把 `builder/example/resume.toml` 复制到插件目录以外的地方（插件更新会覆盖插件目录），换成你自己的内容，在 Claude Code 里贴岗位链接，说「按这个 JD 改简历」。只有 PDF 或 Word 简历的话，第一次用时说一声，skill 会把它逐字搬进素材库（不润色、不补数字），先还原出你现在这份简历让你核对，再开始微调。

**测试：** `python3 scripts/smoke_test.py` 会在 6 种招聘系统上各找一个在招岗位来抓，再检查已关闭的岗位返回 2，最后用示例素材库生成 PDF。2026-11-20 按新用户的方式从 GitHub 装插件做了端到端测试：遇到不符合硬性条件的岗位，它会先停下来说明原因；坚持要生成时，只新增一个版本，PDF 是一页，JD 要求但素材库里没有的关键词列为短板，不会写进简历。这次测试还发现并修了两个问题：字体没嵌入，以及插件安装后 skill 找不到 builder。
