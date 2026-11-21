"""End-to-end: the extension in Chrome for Testing talks to the host over real native messaging.
The agents are the fake one (tests/fake_agent.py), so it costs nothing and uses a made-up person.

    uv run --with playwright==1.55.0 python tests/e2e.py [--headed]

The host is registered only inside the test's own browser profile (<profile>/NativeMessagingHosts),
so your real Chrome/Edge registration is never touched.
"""
import argparse, glob, json, os, shutil, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'host'))
import jdt  # noqa: E402


class Page(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    frame_url = ''

    def do_GET(self):
        fx = ROOT / 'tests' / 'fixtures'
        if self.path == '/embed':
            body = (fx / 'embed_top.html').read_text().replace('FRAME_URL', Page.frame_url).encode()
        elif self.path == '/frame':
            body = (fx / 'embed_frame.html').read_bytes()
        else:
            body = (fx / 'job.html').read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(body)


def chrome():
    hits = sorted(glob.glob(os.path.expanduser(
        '~/Library/Caches/ms-playwright/chromium-*/chrome-mac*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing')))
    # none cached: use Playwright's own full Chromium (channel='chromium'; the headless shell can't load extensions)
    return hits[-1] if hits else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--headed', action='store_true')
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix='jdt-e2e-'))
    home = tmp / 'home'
    home.mkdir()
    fake = ['python3', str(ROOT / 'tests' / 'fake_agent.py'), '{mode}', '{prompt}']
    (home / 'config.json').write_text(json.dumps({
        'writer': 'claude', 'reviewer': 'same', 'tailor_config': str(tmp / 'no-config.md'),
        'agents': {'claude': {'command': fake}, 'codex': {'command': fake}}}))
    launcher = tmp / 'jdt-host'
    launcher.write_text(f'#!/bin/sh\nexport PATH={json.dumps(os.environ["PATH"])}\nexport JD_RESUME_TAILOR_APP_HOME={json.dumps(str(home))}\n'
                        f'exec {json.dumps(sys.executable)} {json.dumps(str(ROOT / "host" / "jdt.py"))} host "$@"\n')
    launcher.chmod(0o755)
    profile = tmp / 'profile'
    (profile / 'NativeMessagingHosts').mkdir(parents=True)
    (profile / 'NativeMessagingHosts' / f'{jdt.HOST_NAME}.json').write_text(json.dumps({
        'name': jdt.HOST_NAME, 'description': 'test', 'path': str(launcher), 'type': 'stdio',
        'allowed_origins': [f'chrome-extension://{jdt.EXT_ID}/']}))
    ext = tmp / 'ext'
    shutil.copytree(ROOT / 'extension', ext)
    man = json.loads((ext / 'manifest.json').read_text())
    man['host_permissions'] = ['http://127.0.0.1/*', 'http://localhost/*']  # read the local fixture page without the permission prompt
    # Without "tabs", Chrome hides tab URLs from the panel and it shows "Open a job posting" on every page.
    assert 'tabs' in man['permissions'], 'the panel needs the "tabs" permission to see which page is open'
    (ext / 'manifest.json').write_text(json.dumps(man))

    srv = ThreadingHTTPServer(('127.0.0.1', 0), Page)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    job_url = f'http://127.0.0.1:{srv.server_address[1]}/job'
    embed_url = f'http://127.0.0.1:{srv.server_address[1]}/embed'
    Page.frame_url = f'http://localhost:{srv.server_address[1]}/frame'  # another origin, like an embedded Greenhouse board

    fails = []

    def check(name, ok, detail=''):
        print(('PASS ' if ok else 'FAIL ') + name + (f'  [{detail}]' if detail and not ok else ''))
        if not ok:
            fails.append(name)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(profile), executable_path=chrome(), channel=None if chrome() else 'chromium', headless=not args.headed,
            args=[f'--disable-extensions-except={ext}', f'--load-extension={ext}'])
        try:
            sw = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event('serviceworker')
            eid = sw.url.split('/')[2]
            check('extension ID is fixed by the manifest key', eid == jdt.EXT_ID, eid)
            page = ctx.new_page()
            page.goto(job_url)
            tab_id = sw.evaluate('async (u) => (await chrome.tabs.query({url: u}))[0].id', job_url)

            panel = ctx.new_page()
            errors = []
            panel.on('pageerror', lambda e: errors.append(str(e)))
            panel.goto(f'chrome-extension://{eid}/panel.html?tab={tab_id}')
            panel.wait_for_function("() => document.getElementById('connText').textContent === 'Claude Code'", timeout=10000)
            check('connects to the host with no token or login', panel.locator('#install').is_hidden())
            check('says who writes and reviews, on Opus by default', 'Writer: Claude Code Opus · Reviewers: Claude Code Opus · quick' in panel.locator('#who').text_content(),
                  panel.locator('#who').text_content())

            panel.click('#gear')
            items = panel.locator('#agentList li').all_text_contents()
            check('lists the four agents', len(items) == 4 and any('Grok Build' in i for i in items), str(items))
            panel.select_option('#reviewer', 'codex')
            panel.wait_for_function("() => document.getElementById('who').textContent.includes('Reviewers: Codex')", timeout=5000)
            check('reviewer setting saved on the host', json.loads((home / 'config.json').read_text())['reviewer'] == 'codex')
            check('model menu offers Opus first', panel.locator('#writerModel option').first.text_content() == 'Opus (best)')
            panel.select_option('#writerModel', 'sonnet')
            panel.wait_for_function("() => document.getElementById('who').textContent.includes('Writer: Claude Code Sonnet')", timeout=5000)
            check('writer model saved on the host', json.loads((home / 'config.json').read_text())['writer_model'] == 'sonnet')
            panel.select_option('#writerModel', 'opus')
            panel.wait_for_function("() => document.getElementById('who').textContent.includes('Writer: Claude Code Opus')", timeout=5000)
            panel.click('#closeAgents')

            panel.click('#capture')
            panel.wait_for_function("() => document.getElementById('jdLen').textContent.includes('words')", timeout=5000)
            check('capture reads the posting', panel.locator('#pageTitle').text_content() == 'Acme Robotics · Software Engineer Intern, Summer 2027')

            panel.click('#tailor')
            panel.wait_for_selector('#job:not([hidden])', timeout=5000)
            panel.wait_for_function("() => document.getElementById('jobBadge').textContent === 'ready'", timeout=60000)
            stages = panel.locator('#timeline li').evaluate_all('els => els.map(e => e.className)')
            check('each finished stage shows its time', panel.locator('#timeline li .t').count() >= 5)
            check('timeline: every stage done', stages and all(c == 'done' for c in stages), str(stages))
            labels = panel.locator('#timeline li').all_text_contents()
            check('timeline shows both reviewers and the gate',
                  any('Hiring manager review 1' in l for l in labels) and any('ATS review 1' in l for l in labels)
                  and labels[-1].startswith('Gate'), str(labels))
            check('gate banner', 'Passed the gate' in panel.locator('#gate').text_content())
            check('lists numbers to confirm', '14 minutes' in panel.locator('#rLists').text_content())
            panel.locator('#reviews button', has_text='HM 1').click()
            panel.wait_for_selector('#reviewText:not([hidden])')
            check('opens a review', 'VERDICT: unsure' in panel.locator('#reviewText').text_content())
            with ctx.expect_page() as pdf_page:
                panel.click('#openPdf')
            check('opens the PDF', pdf_page.value.url.startswith('blob:chrome-extension://'), pdf_page.value.url)
            pdf_page.value.close()

            panel.reload()
            panel.wait_for_function("() => document.getElementById('jobBadge').textContent === 'ready'", timeout=10000)
            check('finds the job again for this page after reopening', True)

            # a career page whose posting sits in an iframe from another site (Wing-style Greenhouse embed)
            emb = ctx.new_page()
            emb.goto(embed_url)
            emb.wait_for_timeout(500)
            emb_id = sw.evaluate('async (u) => (await chrome.tabs.query({url: u}))[0].id', embed_url)
            panel.goto(f'chrome-extension://{eid}/panel.html?tab={emb_id}')
            panel.wait_for_function("() => !document.getElementById('capture').disabled", timeout=10000)
            panel.click('#capture')
            panel.wait_for_function("() => document.getElementById('jdLen').textContent.includes('words')", timeout=5000)
            jd = panel.locator('#jd').input_value()
            check('reads the posting from the embedded frame, not the nav and footer',
                  'Minimum qualifications' in jd and 'Get delivery' not in jd, jd[:150])
            check('frame capture keeps the page URL', panel.locator('#pageTitle').text_content().startswith('Data Infra'),
                  panel.locator('#pageTitle').text_content())
            check('no page errors', not errors, '; '.join(errors))
        finally:
            ctx.close()
            srv.shutdown()
            shutil.rmtree(tmp, ignore_errors=True)

    print(f'\n{len(fails)} failed' if fails else '\nall passed')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
