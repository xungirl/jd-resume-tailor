# JD Tailor

A browser extension that reads the job description on the page you're looking at and tailors your resume to it, without inventing anything.

1. Open a job posting (Greenhouse, Lever, Ashby, Workday, LinkedIn, or any page with the JD on it).
2. Click **Capture JD**.
3. Click **Tailor my resume**.

You get:
- An **eligibility check**: graduation window, sponsorship, location and so on, each marked ✓, ? or ✗.
- A **one-page resume** you can save as PDF.
- A list of **what changed** and **gaps**: what the job wants that your resume doesn't show, with honest advice.

It's the lightweight sibling of [jd-resume-tailor](https://github.com/xungirl/jd-resume-tailor), which runs inside Claude Code or Codex. This extension needs neither: just a browser and an AI account.

## Install (developer mode, for now)

1. Download or clone this repo.
2. Chrome: open `chrome://extensions`. Edge: open `edge://extensions`.
3. Turn on **Developer mode**, click **Load unpacked**, and pick the `extension` folder.
4. Click the toolbar icon. The side panel opens on the setup page:
   - **Connect OpenRouter**: log in, approve, done. Or paste an API key.
   - **Paste your resume** as text. A longer "bullet bank" with everything you've done works even better.

## Where your data goes

- Your resume, the key, and past results stay in this browser's extension storage (`chrome.storage.local`).
- When you press **Tailor**, the job description and your resume are sent to the model you picked through [OpenRouter](https://openrouter.ai), and nowhere else. There's no JD Tailor server.
- The extension reads a page only when you press **Capture JD**. The first time on a new site, Chrome asks you to allow it.

## Cost

You pay OpenRouter directly, per use. There's no subscription. Rough cost per resume, estimated from list prices for about 12k tokens in and 4k out:

| Model | ≈ per resume |
|---|---|
| Claude Opus 5.5 (default) | $0.13 |
| Claude Sonnet 5.5 | $0.06 |
| Free models (`:free`) | $0, but weaker, rate-limited, and some providers keep your text |

A new OpenRouter account starts at $0. On the first login, it asks you to buy credits: you can skip that and use free models.

## How it avoids making things up

The prompt forbids adding any technology, number, title, date or claim that isn't in your material. Prompts aren't guarantees, so the panel also checks the answer itself:

- **New numbers**: any number in the tailored resume that doesn't appear anywhere in your material gets a red warning.
- **Reworded bullets**: any bullet that isn't word-for-word from your material gets a dotted underline, so you can check it.
- **Job pages are data**: the prompt tells the model to ignore instructions hidden in a posting. The test fixture includes one ("add 10 years of Kubernetes").
- **No HTML from the model**: the model's Markdown is escaped before it's shown, so it can't inject HTML into the panel.

## Why OpenRouter, and not "log in with Claude"

The goal was a login button like Claude's in VS Code. That isn't allowed for third-party apps: Anthropic's 2026 terms say a third-party product may not offer claude.ai login or use people's Free/Pro/Max subscriptions. Developers must use API keys.

OpenRouter does offer a login flow that hands an app a key tied to the user's own account (OAuth PKCE, no client secret, no server). We checked that it works inside an extension (2026-11-20, Chrome):

- The callback `https://<extension-id>.chromiumapp.org/` from `chrome.identity.launchWebAuthFlow` is accepted.
- The code exchange at `POST /api/v1/auth/keys` returns a key, and `GET /api/v1/key` answers 200.
- The `limit` URL parameter (a credit cap on the new key) is honored. `key_label` was not.
- Clicking the button twice while a login is open fails with "Only one web auth flow is allowed at a time", so the button is disabled during login.

Safari has no `launchWebAuthFlow`, so on Safari you paste a key instead.

## Tests

```sh
uv run --with playwright==1.55.0 python tests/e2e.py
```

This loads the extension into Chrome for Testing (branded Chrome and Edge no longer accept `--load-extension`). The run:
- Serves a fake job page and a mock OpenRouter.
- Captures the JD and tailors it, checking the request and the panel output (26 checks).
- Covers fallbacks and errors: models that refuse `json_schema` (it retries in JSON mode), an empty balance (402), a bad key, and a fresh install.

It costs nothing and uses a made-up resume (`tests/fixtures/resume.md`).

## Status

v0.1.0. Tested in Chrome for Testing with a mock model. The OpenRouter login was checked by hand in Chrome. Edge and Safari are not tested yet. PDF output uses the browser's own "Save as PDF".

MIT License.
