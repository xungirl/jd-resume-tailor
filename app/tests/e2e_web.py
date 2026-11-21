"""End-to-end: the web UI (`jdt.py web`) in a real browser, with the fake agent and a temporary data folder.

    uv run --with playwright==1.55.0 python tests/e2e_web.py [--headed]

It starts `jdt.py web --no-open --port 0`, opens the link it prints, fetches a posting from a local
page, pastes a JD, tailors, waits for "ready", opens a review and the PDF, and checks that a page
from another site can't call the server. Also runs in WebKit (Safari's engine) if Playwright's
WebKit happens to be installed; it is not downloaded for you.
"""
import argparse, glob, json, os, re, shutil, subprocess, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
JD_TEXT = ('Acme Robotics builds the fleet software that plans routes for warehouse robots. ' * 6 +
           'Requirements: Python, SQL and REST APIs. We are unable to sponsor visas for this role.')


class Page(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == '/job':  # a posting in plain HTML, the kind fetch_jd.py reads without an ATS API
            body = ('<!doctype html><title>Software Engineer Intern - Acme Robotics</title><main><h1>Software Engineer Intern</h1>'
                    + ''.join(f'<p>{s}.</p>' for s in JD_TEXT.split('. ')) + '</main>').encode()
        else:
            body = b'<!doctype html><title>other site</title>'
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(body)


def chrome():
    hits = sorted(glob.glob(os.path.expanduser(
        '~/Library/Caches/ms-playwright/chromium-*/chrome-mac*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing')))
    return hits[-1] if hits else None


def webkit_installed():
    return bool(glob.glob(os.path.expanduser('~/Library/Caches/ms-playwright/webkit-*')) or glob.glob(os.path.expanduser('~/.cache/ms-playwright/webkit-*')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--headed', action='store_true')
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix='jdt-e2e-web-'))
    home = tmp / 'home'
    home.mkdir()
    fake = ['python3', str(ROOT / 'tests' / 'fake_agent.py'), '{mode}', '{prompt}']
    (home / 'config.json').write_text(json.dumps({
        'writer': 'claude', 'reviewer': 'same', 'tailor_config': str(tmp / 'no-config.md'),
        'agents': {'claude': {'command': fake}, 'codex': {'command': fake}}}))
    env = dict(os.environ, JD_RESUME_TAILOR_APP_HOME=str(home))
    server = subprocess.Popen([sys.executable, str(ROOT / 'host' / 'jdt.py'), 'web', '--no-open', '--port', '0'],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    line = server.stdout.readline()
    m = re.search(r'(http://127\.0\.0\.1:(\d+))/#t=(\S+)', line)
    assert m, f'the server did not print its link: {line!r}'
    base, link = m.group(1), m.group(0)
    threading.Thread(target=lambda: [None for _ in server.stdout], daemon=True).start()  # keep its pipe drained

    srv = ThreadingHTTPServer(('127.0.0.1', 0), Page)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    other = f'http://127.0.0.1:{srv.server_address[1]}'

    fails = []

    def check(name, ok, detail=''):
        print(('PASS ' if ok else 'FAIL ') + name + (f'  [{detail}]' if detail and not ok else ''))
        if not ok:
            fails.append(name)

    def flow(browser, tag, full):
        ctx = browser.new_context(viewport={'width': 1100, 'height': 900})
        page = ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('dialog', lambda d: d.accept())
        page.goto(link)
        page.wait_for_function("() => document.getElementById('connText').textContent === 'Claude Code'", timeout=20000)
        check(f'{tag}: connects with the key from the printed link', page.locator('#connect').is_hidden())
        check(f'{tag}: takes the key out of the address bar', '#t=' not in page.url and 't=' not in page.url, page.url)
        page.reload()
        page.wait_for_function("() => document.getElementById('connText').textContent === 'Claude Code'", timeout=20000)
        check(f'{tag}: still connected after a reload', page.locator('#connect').is_hidden())
        check(f'{tag}: says who writes and reviews', 'Writer: Claude Code Opus · Reviewers: Claude Code Opus · quick' in page.locator('#who').text_content(),
              page.locator('#who').text_content())

        # without the key: the page says how to get the link, and nothing works
        bare = ctx.new_page()
        bare.goto(base + '/')
        bare.wait_for_selector('#connect:not([hidden])', timeout=10000)
        check(f'{tag}: without the key it asks for the printed link', 'link' in bare.locator('#connectTitle').text_content().lower(),
              bare.locator('#connectTitle').text_content())
        bare.close()

        if full:
            # settings round-trip, same as the panel
            page.click('#gear')
            check(f'{tag}: lists the four agents', page.locator('#agentList li').count() == 4)
            page.select_option('#writerModel', 'sonnet')
            page.wait_for_function("() => document.getElementById('who').textContent.includes('Writer: Claude Code Sonnet')", timeout=10000)
            check(f'{tag}: writer model saved on the host', json.loads((home / 'config.json').read_text())['writer_model'] == 'sonnet')
            page.select_option('#writerModel', 'opus')
            page.wait_for_function("() => document.getElementById('who').textContent.includes('Writer: Claude Code Opus')", timeout=10000)
            page.click('#closeAgents')

            # Fetch: a link that fails, then a local posting page (fetch_jd.py's plain-HTML path; no internet)
            page.fill('#url', 'http://127.0.0.1:1/jobs/1')
            page.click('#fetch')
            page.wait_for_selector('#pageMsg:not([hidden])', timeout=30000)
            check(f'{tag}: a link that fails says to paste the JD', 'Paste the job description' in page.locator('#pageMsg').text_content(),
                  page.locator('#pageMsg').text_content())
            page.fill('#url', other + '/job')
            page.click('#fetch')
            page.wait_for_function("() => document.getElementById('jd').value.length > 200", timeout=30000)
            check(f'{tag}: Fetch fills the JD and the title', 'warehouse robots' in page.locator('#jd').input_value()
                  and 'Software Engineer Intern' in page.locator('#title').input_value(), page.locator('#title').input_value())
            page.click('#clear')
            check(f'{tag}: Clear empties the form', page.locator('#jd').input_value() == '' and page.locator('#tailor').is_disabled())

        # paste the JD and tailor
        page.fill('#company', f'Acme {tag}')
        page.fill('#title', 'Software Engineer Intern')
        page.fill('#jd', JD_TEXT)
        check(f'{tag}: Tailor turns on once there is a JD', page.locator('#tailor').is_enabled())
        page.click('#tailor')
        page.wait_for_selector('#job:not([hidden])', timeout=10000)
        page.wait_for_function("() => document.getElementById('jobBadge').textContent === 'ready'", timeout=90000)
        stages = page.locator('#timeline li').evaluate_all('els => els.map(e => e.className)')
        check(f'{tag}: live timeline ends with every stage done', bool(stages) and all(c == 'done' for c in stages), str(stages))
        labels = page.locator('#timeline li').all_text_contents()
        check(f'{tag}: timeline shows both reviewers and the gate', any('Hiring manager review 1' in l for l in labels)
              and any('ATS review 1' in l for l in labels) and labels[-1].startswith('Gate'), str(labels))
        check(f'{tag}: gate banner', 'Passed the gate' in page.locator('#gate').text_content())
        check(f'{tag}: lists numbers to confirm', '14 minutes' in page.locator('#rLists').text_content())
        page.locator('#reviews button', has_text='HM 1').click()
        page.wait_for_selector('#reviewText:not([hidden])')
        check(f'{tag}: opens a review', 'VERDICT: unsure' in page.locator('#reviewText').text_content())
        with ctx.expect_page() as pdf_page:
            page.click('#openPdf')
        pdf_url = pdf_page.value.url
        check(f'{tag}: Open PDF opens the PDF from the server', pdf_url.startswith(base + '/pdf?id='), pdf_url)
        pdf_page.value.close()
        jid = re.search(r'id=([A-Za-z0-9_]+)', pdf_url).group(1)
        r = ctx.request.get(pdf_url)
        check(f'{tag}: the PDF endpoint serves the PDF with the key', r.status == 200 and r.body()[:4] == b'%PDF', str(r.status))
        r = ctx.request.get(f'{base}/pdf?id={jid}')
        check(f'{tag}: and refuses it without the key', r.status == 401, str(r.status))

        # another site in the same browser can't drive the server, even if it guessed the key
        foreign = ctx.new_page()
        foreign.goto(other + '/elsewhere')
        key = link.split('#t=')[1]
        res = foreign.evaluate("""async ([api, key]) => {
            try {
              const r = await fetch(api, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-JDRT-Token': key},
                                          body: JSON.stringify({cmd: 'list'})});
              return 'read ' + r.status;
            } catch (e) { return 'blocked'; }
        }""", [base + '/api', key])
        check(f'{tag}: a page on another site cannot call the API', res == 'blocked', res)
        foreign.close()

        # recent jobs and reset
        page.reload()
        page.wait_for_selector('#recentBox:not([hidden])', timeout=10000)
        page.locator('#recent li', has_text=f'Acme {tag}').first.click()
        page.wait_for_function("() => document.getElementById('jobBadge').textContent === 'ready'", timeout=10000)
        check(f'{tag}: reopens the job from Recent', f'Acme {tag}' in page.locator('#jobTitle').text_content())
        page.click('#reset')
        page.wait_for_selector('#job', state='hidden', timeout=10000)
        check(f'{tag}: Reset moves the job to the trash', any(p.name.startswith(jid) for p in (home / 'trash').iterdir()))

        # phone width: nothing wider than the screen
        page.set_viewport_size({'width': 360, 'height': 780})
        page.wait_for_timeout(200)
        sw = page.evaluate('() => [document.documentElement.scrollWidth, window.innerWidth]')
        check(f'{tag}: fits a phone screen (no sideways scroll)', sw[0] <= sw[1], str(sw))
        check(f'{tag}: no page errors', not errors, '; '.join(errors))
        ctx.close()

    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chrome(), headless=not args.headed)
            try:
                flow(b, 'chrome', True)
            finally:
                b.close()
            if webkit_installed():
                b = p.webkit.launch(headless=not args.headed)
                try:
                    flow(b, 'webkit', False)
                finally:
                    b.close()
            else:
                print('SKIP webkit (Playwright WebKit is not installed; `playwright install webkit` to add it)')
    finally:
        server.terminate()
        server.wait(10)
        srv.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)

    print(f'\n{len(fails)} failed' if fails else '\nall passed')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
