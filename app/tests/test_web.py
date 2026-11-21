"""Tests for `jdt.py web`: the key, Host and Origin checks, /api, fetch_url and /pdf.
No network, no model calls (the fake agent), and a temporary data folder: never your real resume.

    python3 -m unittest tests/test_web.py -v
"""
import http.client
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'host'))
sys.path.insert(0, str(ROOT / 'tests'))

import jdt  # noqa: E402
from make_pdf import RESUME_LINES, make_pdf  # noqa: E402

FAKE = ['python3', str(ROOT / 'tests' / 'fake_agent.py'), '{mode}', '{prompt}']
KEY = 'k3y-' + 'x' * 28
JD_TEXT = ('Acme Robotics builds the fleet software that plans routes for warehouse robots. ' * 6 +
           'Requirements: Python, SQL and REST APIs.')
TMP = None
OLD_HOME = None


def setUpModule():
    global TMP, OLD_HOME
    TMP = Path(tempfile.mkdtemp(prefix='jdt-web-test-'))
    OLD_HOME = os.environ.get('JD_RESUME_TAILOR_APP_HOME')
    os.environ['JD_RESUME_TAILOR_APP_HOME'] = str(TMP / 'home')
    jdt.save_config({'writer': 'claude', 'reviewer': 'same', 'mode': 'quick', 'tailor_config': str(TMP / 'no-config.md'),
                     'agents': {'claude': {'command': FAKE}, 'codex': {'command': FAKE}}})


def tearDownModule():
    if OLD_HOME is None:
        os.environ.pop('JD_RESUME_TAILOR_APP_HOME', None)
    else:
        os.environ['JD_RESUME_TAILOR_APP_HOME'] = OLD_HOME
    shutil.rmtree(TMP, ignore_errors=True)


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = jdt.make_web_server(0, token=KEY)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def req(self, method, path, body=None, headers=None, host=None):
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=30)
        h = {'Host': f'127.0.0.1:{self.port}' if host is None else host}
        h.update(headers or {})
        if body is not None and not isinstance(body, bytes):
            body = json.dumps(body).encode()
        c.request(method, path, body=body, headers=h)
        r = c.getresponse()
        data = r.read()
        c.close()
        headers = {k.lower(): v for k, v in r.getheaders()}
        self.assertNotIn('access-control-allow-origin', headers)  # never any CORS
        return r.status, headers, data

    def api(self, msg, key=KEY, headers=None, **kw):
        h = {'Content-Type': 'application/json'}
        if key is not None:
            h['X-JDRT-Token'] = key
        h.update(headers or {})
        status, hd, data = self.req('POST', '/api', msg, h, **kw)
        return status, json.loads(data)

    # ---- the page itself

    def test_ui_and_only_the_ui_is_served(self):
        status, h, body = self.req('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn(b'id="fetchForm"', body)
        self.assertIn("frame-ancestors 'none'", h['content-security-policy'])
        self.assertEqual(h['x-content-type-options'], 'nosniff')
        for path, kind in (('/web.js', 'javascript'), ('/lib/ui.js', 'javascript'), ('/panel.css', 'css'), ('/icons/32.png', 'png')):
            status, h, _ = self.req('GET', path)
            self.assertEqual((status, kind in h['content-type']), (200, True), path)
        for path in ('/../host/jdt.py', '/host/jdt.py', '/config.json', '/lib/../../host/jdt.py', '/extension/manifest.json', '//etc/passwd'):
            self.assertEqual(self.req('GET', path)[0], 404, path)

    # ---- the key

    def test_api_needs_the_key(self):
        status, r = self.api({'cmd': 'hello'}, key=None)
        self.assertEqual((status, r['ok'], r.get('auth')), (401, False, True))
        status, r = self.api({'cmd': 'hello'}, key='wrong')
        self.assertEqual((status, r['ok']), (403, False))
        status, r = self.api({'cmd': 'hello'}, key=KEY[:-1])
        self.assertEqual(status, 403)
        status, r = self.api({'cmd': 'hello'})
        self.assertEqual(status, 200)
        self.assertTrue(r['ok'])
        self.assertEqual({a['id'] for a in r['agents']}, {'claude', 'codex', 'grok', 'deepseek'})
        self.assertEqual(r['home'], str(TMP / 'home'))

    # ---- DNS rebinding: a site that points its own name at 127.0.0.1

    def test_wrong_host_is_refused(self):
        for host in (f'evil.example:{self.port}', 'evil.example', f'127.0.0.1:{self.port + 1}', '127.0.0.1', f'0.0.0.0:{self.port}',
                     f'localhost.evil.example:{self.port}', ''):
            status, r = self.api({'cmd': 'hello'}, host=host)
            self.assertEqual(status, 403, host)
            self.assertEqual(self.req('GET', '/', host=host)[0], 403, host)
        status, r = self.api({'cmd': 'hello'}, host=f'localhost:{self.port}')
        self.assertEqual((status, r['ok']), (200, True))

    # ---- other sites the user has open

    def test_foreign_origin_is_refused(self):
        for origin in ('https://evil.example', 'null', f'http://127.0.0.1:{self.port + 1}', f'https://127.0.0.1:{self.port}',
                       f'http://localhost:{self.port}.evil.example'):
            status, r = self.api({'cmd': 'hello'}, headers={'Origin': origin})
            self.assertEqual(status, 403, origin)
            self.assertIn('other sites', r['error'])
        for origin in (f'http://127.0.0.1:{self.port}', f'http://localhost:{self.port}'):
            self.assertEqual(self.api({'cmd': 'list'}, headers={'Origin': origin})[0], 200, origin)
        status, r = self.api({'cmd': 'list'}, headers={'Sec-Fetch-Site': 'cross-site'})
        self.assertEqual(status, 403)

    def test_json_only_and_size_cap(self):
        status, _, _ = self.req('POST', '/api', b'cmd=hello', {'Content-Type': 'application/x-www-form-urlencoded', 'X-JDRT-Token': KEY})
        self.assertEqual(status, 415)
        status, _, _ = self.req('POST', '/api', b'{"cmd": "hello"}', {'Content-Type': 'text/plain', 'X-JDRT-Token': KEY})
        self.assertEqual(status, 415)
        status, _, _ = self.req('POST', '/api', b'{not json', {'Content-Type': 'application/json', 'X-JDRT-Token': KEY})
        self.assertEqual(status, 400)
        status, _, _ = self.req('POST', '/api', b'["hello"]', {'Content-Type': 'application/json', 'X-JDRT-Token': KEY})
        self.assertEqual(status, 400)
        status, _, _ = self.req('POST', '/api', b'{}', {'Content-Type': 'application/json', 'X-JDRT-Token': KEY,
                                                        'Content-Length': str(jdt.MAX_BODY + 1)})
        self.assertEqual(status, 413)
        self.assertEqual(self.req('PUT', '/api', b'{}', {'X-JDRT-Token': KEY})[0], 405)
        self.assertEqual(self.req('OPTIONS', '/api', None, {'Origin': 'https://evil.example'})[0], 405)
        status, r = self.api({'cmd': 'nope'})
        self.assertEqual((status, r['ok']), (200, False))

    # ---- fetch_url

    def test_fetch_url_errors(self):
        status, r = self.api({'cmd': 'fetch_url', 'url': 'file:///etc/passwd'})
        self.assertEqual(status, 200)
        self.assertFalse(r['ok'])
        self.assertIn('https://', r['error'])
        self.assertFalse(self.api({'cmd': 'fetch_url', 'url': ''})[1]['ok'])
        t0 = time.time()
        status, r = self.api({'cmd': 'fetch_url', 'url': 'http://127.0.0.1:1/jobs/1'})  # nothing listens on port 1: fails fast
        self.assertFalse(r['ok'])
        self.assertIn('Could not read that page', r['error'])
        self.assertIn('Paste the job description', r['error'])
        self.assertLess(time.time() - t0, 30)

    def test_fetch_url_results(self):
        done = lambda code, out='', err='': subprocess.CompletedProcess([], code, out, err)
        with mock.patch.object(jdt.subprocess, 'run', return_value=done(2, json.dumps({'open': False, 'text': ''}))):
            r = jdt.handle({'cmd': 'fetch_url', 'url': 'https://boards.greenhouse.io/acme/jobs/1'})
        self.assertEqual((r['ok'], r.get('closed')), (False, True))
        with mock.patch.object(jdt.subprocess, 'run', return_value=done(0, json.dumps({'text': 'too short', 'title': 'x'}))):
            r = jdt.handle({'cmd': 'fetch_url', 'url': 'https://boards.greenhouse.io/acme/jobs/1'})
        self.assertFalse(r['ok'])
        self.assertIn('Paste the job description', r['error'])
        with mock.patch.object(jdt.subprocess, 'run', return_value=done(0, 'not json')):
            self.assertFalse(jdt.handle({'cmd': 'fetch_url', 'url': 'https://boards.greenhouse.io/acme/jobs/1'})['ok'])
        good = {'ats': 'greenhouse', 'title': 'Software Engineer Intern', 'location': 'Seattle, WA', 'open': True,
                'text': JD_TEXT, 'url': 'https://boards.greenhouse.io/acmerobotics/jobs/123'}
        with mock.patch.object(jdt.subprocess, 'run', return_value=done(0, json.dumps(good))) as run:
            r = jdt.handle({'cmd': 'fetch_url', 'url': 'https://boards.greenhouse.io/acmerobotics/jobs/123?utm=x'})
        self.assertTrue(r['ok'], r)
        self.assertEqual(run.call_args[0][0][1:], [str(jdt.skill_dir() / 'fetch_jd.py'), 'https://boards.greenhouse.io/acmerobotics/jobs/123?utm=x', '--json'])
        self.assertEqual({k: r['job'][k] for k in ('url', 'title', 'company', 'location')},
                         {'url': good['url'], 'title': 'Software Engineer Intern', 'company': 'Acmerobotics', 'location': 'Seattle, WA'})
        self.assertEqual(r['job']['text'], JD_TEXT)

    def test_company_from_url(self):
        for url, want in (('https://boards.greenhouse.io/airbnb/jobs/1', 'Airbnb'), ('https://jobs.ashbyhq.com/octaura/x', 'Octaura'),
                          ('https://jobs.lever.co/palantir/x', 'Palantir'), ('https://snowflake.wd1.myworkdayjobs.com/en-US/c/job/x', 'Snowflake'),
                          ('https://careers.roblox.com/jobs/7', 'Roblox'), ('https://job-boards.greenhouse.io/embed/job_app?for=anduril&token=1', 'Anduril'),
                          ('http://127.0.0.1:8000/job', '')):
            self.assertEqual(jdt.company_from_url(url), want, url)

    # ---- the PDF

    def _pdf_job(self):
        d = jdt.jobs_dir() / 'Pdf_Co_Intern_abc123'
        d.mkdir(parents=True, exist_ok=True)
        make_pdf(d / 'resume.pdf', RESUME_LINES)
        (d / 'state.json').write_text(json.dumps({'id': d.name, 'status': 'ready'}))
        return d.name

    def test_pdf_needs_the_key(self):
        jid = self._pdf_job()
        self.assertEqual(self.req('GET', f'/pdf?id={jid}')[0], 401)
        self.assertEqual(self.req('GET', f'/pdf?id={jid}&t=wrong')[0], 403)
        self.assertEqual(self.req('GET', f'/pdf?id={jid}&t={KEY}', host=f'evil.example:{self.port}')[0], 403)
        self.assertEqual(self.req('GET', f'/pdf?id={jid}&t={KEY}', headers={'Sec-Fetch-Site': 'cross-site'})[0], 403)
        status, h, body = self.req('GET', f'/pdf?id={jid}&t={KEY}')
        self.assertEqual(status, 200)
        self.assertEqual(h['content-type'], 'application/pdf')
        self.assertTrue(body.startswith(b'%PDF'))
        self.assertTrue(h['content-disposition'].startswith('inline'))
        status, h, _ = self.req('GET', f'/pdf?id={jid}&t={KEY}&download=1')
        self.assertTrue(h['content-disposition'].startswith('attachment'))
        self.assertEqual(self.req('GET', f'/pdf?id=../../etc&t={KEY}')[0], 400)
        self.assertEqual(self.req('GET', f'/pdf?id=No_such_job_000000&t={KEY}')[0], 404)

    # ---- the whole flow through the server

    def test_tailor_through_the_api(self):
        status, r = self.api({'cmd': 'tailor', 'job': {'company': 'Web Co', 'title': 'Intern', 'text': JD_TEXT}})
        self.assertTrue(r['ok'], r)
        jid = r['id']
        t0 = time.time()
        while time.time() - t0 < 60:
            j = self.api({'cmd': 'status', 'id': jid})[1]['job']
            if j['status'] not in ('queued', 'running'):
                break
            time.sleep(0.3)
        self.assertEqual(j['status'], 'ready', j)
        self.assertIn('VERDICT: unsure', self.api({'cmd': 'review', 'id': jid, 'name': 'review_hm_1'})[1]['text'])
        status, _, body = self.req('GET', f'/pdf?id={jid}&t={KEY}')
        self.assertEqual((status, body[:4]), (200, b'%PDF'))
        self.assertIn(jid, [x['id'] for x in self.api({'cmd': 'list'})[1]['jobs']])
        self.assertTrue(self.api({'cmd': 'reset', 'id': jid})[1]['ok'])
        time.sleep(0.2)
        jdt.reap_children()
        self.assertEqual(jdt._CHILDREN, [])  # finished workers don't linger as zombies


class Startup(unittest.TestCase):
    def test_busy_port_and_free_port(self):
        a = jdt.make_web_server(0, token=KEY)
        try:
            with self.assertRaises(OSError):  # a port in use is not shared
                jdt.make_web_server(a.server_address[1])
            b = jdt.make_web_server(None)  # 8790-8799, or any free port if those are busy
            try:
                self.assertNotEqual(b.server_address[1], a.server_address[1])
                self.assertEqual(b.server_address[0], '127.0.0.1')
                self.assertGreaterEqual(len(b.token), 30)
                self.assertNotEqual(b.token, a.token)
            finally:
                b.server_close()
        finally:
            a.server_close()

    def test_cli_prints_the_link(self):
        p = subprocess.Popen([sys.executable, str(ROOT / 'host' / 'jdt.py'), 'web', '--no-open', '--port', '0'],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=os.environ)
        try:
            line = p.stdout.readline()
            m = re.search(r'http://127\.0\.0\.1:(\d+)/#t=([A-Za-z0-9_-]{30,})', line)
            self.assertTrue(m, line)
            c = http.client.HTTPConnection('127.0.0.1', int(m.group(1)), timeout=10)
            c.request('POST', '/api', body=b'{"cmd": "list"}', headers={'Content-Type': 'application/json', 'X-JDRT-Token': m.group(2)})
            self.assertEqual(c.getresponse().status, 200)
            c.close()
        finally:
            p.terminate()
            p.wait(10)
            p.stdout.close()
            p.stderr.close()
        r = subprocess.run([sys.executable, str(ROOT / 'host' / 'jdt.py'), 'web', '--port', 'abc'], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)


if __name__ == '__main__':
    unittest.main()
