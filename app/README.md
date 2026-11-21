# JD Tailor

A browser extension that reads the job description on the page you're on and has the AI agent already on your computer tailor your resume to it. Then two blind reviewers check the result before you see it.

1. Open a job posting and click **Capture JD**.
2. Click **Tailor my resume**.
3. Watch the timeline:
   - analysis
   - first draft
   - script checks
   - hiring-manager review and ATS review
   - revision
   - gate
4. Open the PDF.

## One login, or none

There is no JD Tailor account and no server. It uses what you already have:

| Agent | What it needs |
|---|---|
| **Claude Code** | Your existing Claude Code login. Nothing else. |
| **Codex** | Your existing Codex login. Nothing else. |
| **Grok Build** | Run `grok login` once. |
| **DeepSeek** | Paste your DeepSeek API key once. It runs inside Claude Code, using [DeepSeek's documented setup](https://api-docs.deepseek.com/quick_start/agent_integrations/claude_code). |

The extension talks to your computer through Chrome's [native messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging). You register the helper once with `install.sh`, and after that the browser starts it on demand. There's no port, no token, and no password, and only this extension's ID may talk to it.

## Install

You need:
- Chrome or Edge.
- Python 3.9+.
- poppler: `brew install poppler`.
- At least one of the agents above.
- The [jd-resume-tailor](https://github.com/xungirl/jd-resume-tailor) skill, set up once. Run it once in Claude Code so it learns where your bullet bank is.

Then:

```sh
git clone <this repo> ~/jd-tailor
~/jd-tailor/install.sh          # registers the helper, then prints what it found
```

Load the extension:
1. Open `chrome://extensions` (or `edge://extensions`) and turn on Developer mode.
2. Click **Load unpacked** and pick `~/jd-tailor/extension`.
3. Click the toolbar icon. The side panel lists your agents.
   - Pick who **writes** and who **reviews**. A different reviewer catches more.

`~/jd-tailor/host/jdt.py doctor` shows the same status from the terminal.

## The flow

This adapts the "JD resume tailoring flow". The rule underneath it: whoever writes sees the source material, and whoever reviews sees only the paper.

```
writer (your bank) ──> analysis.md + resume.pdf ──> script checks ──┬──> HM reviewer  (jd + PDF text only)
        ^                                                           └──> ATS reviewer (jd + PDF + its extracted text)
        └──────────── both reviews, verbatim and labelled ───────────────┘          ↓
                                                         gate: HM is not "no" and ATS passes
```

- **Writer.** One session through the whole job. Claude Code and Grok resume the same session, so the writer remembers why it chose what it chose. Codex re-reads its own `notes.md` instead.
  - It writes `analysis.md` with a fixed set of fields: direction, hard requirements, ATS keywords, known gaps.
  - It builds with jd-resume-tailor's builder and truth rules.
  - It writes bullets as verb → result → scope → method → tech, at most 200 characters.
  - It lists the self-reported numbers you should confirm.
- **Script checks** (`host/check.py`). These are measured, not estimated by a model:
  - The page count must be exactly one, and the text must be extractable.
  - Every ATS keyword must appear, unless it's listed as a known gap.
  - No keyword may appear more than 4 times.
  - It warns about empty space at the bottom and about bullets over 200 characters.
- **Reviewers.** Each runs as a fresh process, in a folder that holds only what it may see. The isolation comes from the filesystem, not from a prompt asking it not to look.
  - The HM reviewer gets `jd.md`, `resume.pdf` and its text.
  - The ATS reviewer gets the same plus the writer's `resume_source.md`, two text extractions, and the PDF's link targets.
- **Your projects.** In settings, list project folders, GitHub repo URLs, or `github:yourname` (all your public, non-fork repos).
  - Before each run, GitHub repos are shallow-cloned (with `gh`'s login if installed, so private repos work too).
  - Each project gets a one-paragraph summary: languages, README, last commit, and whether your bank already has it.
  - The writer may add a project that isn't on your resume yet, using only facts it verifies in that project's files. It cites the file for each fact and lists every new bullet so you can check it.
  - Repos are read-only to the writer (Claude Code gets `Edit`/`Write` denied there), and reviewers never see them.
- **Reset** stops a run and moves the job's folder to `~/.config/jd-tailor/trash/`, so you can start that posting over.
- **Models.** You pick the model for the writer and for the reviewers. The default is the agent's best: Opus for Claude Code, V4 Pro for DeepSeek. Codex and Grok use their own defaults unless you name a model.
- **Quick or thorough.**
  - Quick (the default) runs one round of reviews and one revision.
  - Thorough runs the full flow's rounds, described next.
  - The panel shows what the agent is doing right now (from Claude Code's live event stream) and how long each step took. You can open the first draft before the reviews finish.
- **Rounds.**
  - HM round 2 runs if round 1 wasn't a "yes", or if the revision touched a hard-requirement bullet or 3+ bullets.
  - ATS round 2 runs only if round 1 failed.
  - HM round 3 runs only if round 2 said "no". Its notes are applied, but nobody re-reviews them.
- **Gate.** If it doesn't pass, the resume is still finished but is marked "needs your call". You decide whether to send it as is, revise it, or skip the job.
- **Questions.** The writer stops and asks instead of building when:
  - the role has no clear direction;
  - two directions tie;
  - a hard eligibility condition fails (clearance, citizenship, start date).

  You answer in the panel, and it starts over with your answer. A "no visa sponsorship" posting is not a stop: it builds anyway and tells you.

Each job lives in `~/.config/jd-tailor/jobs/<company_title_hash>/`:
- `jd.md`, `analysis.md`, `resume.pdf`, `resume_source.md`, `notes.md`
- every review as `review_hm_1.md`, `review_ats_1.md`, …
- `state.json`, `result.json`
- `agent.log`, with everything the agents printed

## Tests

```sh
python3 -m unittest tests/test_host.py -v                    # 10 tests: checks, framing, the whole flow, questions
uv run --with playwright==1.55.0 python tests/e2e.py         # 14 checks in a real browser over real native messaging
```

Both use `tests/fake_agent.py` in place of the real agents, so they cost nothing and use a made-up person.
- The fake HM says "unsure" in round 1, so the tests exercise round 2.
- Each fake reviewer writes down the files it can see, so the tests can check that reviewers get only the JD and the paper.
- The browser test registers the host only inside its own temporary profile, so your real Chrome and Edge are never touched.

## Status

v0.2.0.
- Tested: Chrome for Testing, with a fake agent.
- One live Claude Code run, on the made-up person from jd-resume-tailor's example bank, against the test JD:
  - It ran writer → checks → HM 1 (yes) + ATS 1 (pass) → revise → HM 2 (yes) → revise → gate passed.
  - It took 6 min 40 s. Claude Code reported $5.32 in API-equivalent usage, which comes out of your plan's limits when you're logged in with a subscription.
  - The HM reviewer noticed the instruction planted in the test JD ("add 10 years of Kubernetes"), ignored it, and flagged a skill the bullets didn't back up. The writer then removed that skill.
  - It also showed that `pdftotext -bbox` crashes on the builder's PDFs, so the bottom-space check now measures a rendered image instead.
- Not yet run for real: Codex, Grok Build, DeepSeek.
- Edge uses the same native messaging and is registered by `install.sh`, but it hasn't been tested.
- Safari needs a native app wrapper for native messaging, so it isn't supported yet.

## 中文速览

插件负责抓 JD，你电脑上已经登录的 Claude Code、Codex 或 Grok 负责改简历；DeepSeek 只要粘贴一次 key。不需要账号，不需要服务器，也不用配对。第一次运行 `~/jd-tailor/install.sh` 完成注册，以后在侧边栏点一下就开始。流程按《JD 简历定制流程》来：写的人看底稿，审的人只看纸面；HM 和 ATS 两个审阅者各自独立，最后过门禁。

MIT License.
