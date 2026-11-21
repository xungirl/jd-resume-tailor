"""Tests for the local side, with a fake agent: no model calls, no real resume.

    python3 -m unittest tests/test_host.py -v
"""
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix='jdt-test-'))
os.environ['JD_RESUME_TAILOR_APP_HOME'] = str(TMP / 'home')
sys.path.insert(0, str(ROOT / 'host'))
sys.path.insert(0, str(ROOT / 'tests'))

import check  # noqa: E402
import jdt  # noqa: E402
from make_pdf import ANALYSIS, RESUME_LINES, make_pdf  # noqa: E402

FAKE = ['python3', str(ROOT / 'tests' / 'fake_agent.py'), '{mode}', '{prompt}']
JD = (ROOT / 'tests' / 'fixtures' / 'job.html').read_text()  # contains enough text for a JD
JD_TEXT = ('Acme Robotics builds the fleet software that plans routes for warehouse robots. ' * 6 +
           'Requirements: Python, SQL and REST APIs. We are unable to sponsor visas for this role.')


def wait(jid, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = jdt.handle({'cmd': 'status', 'id': jid})['job']
        if j['status'] not in ('queued', 'running'):
            return j
        time.sleep(0.3)
    raise AssertionError('job did not finish: ' + json.dumps(j)[:500])


def setUpModule():
    jdt.save_config({'writer': 'claude', 'reviewer': 'codex', 'tailor_config': str(TMP / 'no-config.md'),
                     'agents': {'claude': {'command': FAKE}, 'codex': {'command': FAKE}}})


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


class Checks(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(dir=TMP))
        (self.d / 'analysis.md').write_text(ANALYSIS)

    def test_good_resume_passes(self):
        make_pdf(self.d / 'resume.pdf', RESUME_LINES)
        r = check.check(str(self.d / 'resume.pdf'), str(self.d / 'analysis.md'))
        self.assertTrue(r['ok'], r['failures'])
        self.assertEqual(r['pages'], 1)
        self.assertEqual(r['keywords']['Python'], 2)
        self.assertEqual(r['keywords']['Kubernetes/k8s'], 0)  # missing, but listed under Known gaps

    def test_two_pages_fail(self):
        make_pdf(self.d / 'resume.pdf', RESUME_LINES, pages=2)
        r = check.check(str(self.d / 'resume.pdf'), str(self.d / 'analysis.md'))
        self.assertFalse(r['ok'])
        self.assertIn('2 pages', ' '.join(r['failures']))

    def test_missing_keyword_not_in_gaps_fails(self):
        make_pdf(self.d / 'resume.pdf', [l.replace('PostgreSQL', 'Postgres') for l in RESUME_LINES])
        r = check.check(str(self.d / 'resume.pdf'), str(self.d / 'analysis.md'))
        self.assertFalse(r['ok'])
        self.assertIn('"PostgreSQL" never appears', ' '.join(r['failures']))

    def test_stuffing_fails(self):
        make_pdf(self.d / 'resume.pdf', RESUME_LINES + ['Python Python Python'])
        r = check.check(str(self.d / 'resume.pdf'), str(self.d / 'analysis.md'))
        self.assertIn('"Python" appears 5 times', ' '.join(r['failures']))

    def test_bottom_space_warns(self):
        make_pdf(self.d / 'resume.pdf', RESUME_LINES[:17])
        r = check.check(str(self.d / 'resume.pdf'), str(self.d / 'analysis.md'))
        self.assertTrue(r['ok'])
        self.assertTrue(any('empty at the bottom' in w for w in r['warnings']), r)


class Host(unittest.TestCase):
    def test_native_messaging_framing(self):
        msg = json.dumps({'cmd': 'hello'}).encode()
        p = subprocess.run([sys.executable, str(ROOT / 'host' / 'jdt.py'), 'host', 'chrome-extension://x/'],
                           input=struct.pack('<I', len(msg)) + msg, capture_output=True, env=os.environ)
        n = struct.unpack('<I', p.stdout[:4])[0]
        out = json.loads(p.stdout[4:4 + n])
        self.assertTrue(out['ok'])
        self.assertEqual(out['writer'], 'claude')
        self.assertEqual({a['id'] for a in out['agents']}, {'claude', 'codex', 'grok', 'deepseek'})

    def test_bad_ids_and_settings(self):
        with self.assertRaises(ValueError):
            jdt.job_path('../../etc')
        self.assertFalse(jdt.handle({'cmd': 'settings', 'set': {'writer': 'rm -rf'}})['ok'])
        self.assertFalse(jdt.handle({'cmd': 'review', 'id': 'x', 'name': '../config'})['ok'])
        self.assertFalse(jdt.handle({'cmd': 'tailor', 'job': {'text': 'short'}})['ok'])

    def test_activity_names(self):
        ev = lambda name, inp: {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': name, 'input': inp}]}}
        self.assertEqual(jdt.activity(ev('Bash', {'command': 'pdftoppm -r 110 x.pdf', 'description': 'Render the page'})), 'Running: Render the page')
        self.assertEqual(jdt.activity(ev('Read', {'file_path': '/Users/a/resume/resume.toml'})), 'Reading resume.toml')
        self.assertIsNone(jdt.activity({'type': 'user'}))
        cfg = dict(jdt.DEFAULTS)
        cmd, _ = jdt.build_command('claude', 'hi', TMP, False, cfg, stream=True)
        self.assertEqual(cmd[cmd.index('--model') + 1], 'opus')  # the best model unless you pick another
        self.assertIn('stream-json', cmd)
        cmd, _ = jdt.build_command('claude', 'hi', TMP, True, dict(cfg, writer_model='sonnet', reviewer_model='haiku'))
        self.assertEqual(cmd[cmd.index('--model') + 1], 'sonnet')
        cmd, _ = jdt.build_command('claude', 'hi', TMP, False, dict(cfg, writer_model='sonnet', reviewer_model='haiku'))
        self.assertEqual(cmd[cmd.index('--model') + 1], 'haiku')
        _, env = jdt.build_command('deepseek', 'hi', TMP, False, dict(cfg, deepseek_key='k', reviewer_model='deepseek-flash'))
        self.assertEqual(env['ANTHROPIC_MODEL'], 'deepseek-flash')
        cmd, _ = jdt.build_command('codex', 'hi', TMP, True, cfg)
        self.assertNotIn('-m', cmd)  # Codex picks its own default
        self.assertFalse(jdt.handle({'cmd': 'settings', 'set': {'writer_model': 'opus; rm -rf ~'}})['ok'])

    def test_commands(self):
        cfg = dict(jdt.DEFAULTS, deepseek_key='sk-test')
        os.environ['ANTHROPIC_API_KEY'] = 'should-not-leak'
        try:
            cmd, env = jdt.build_command('deepseek', 'hi', TMP, True, cfg)
        finally:
            del os.environ['ANTHROPIC_API_KEY']
        self.assertEqual(cmd[:2], ['claude', '-p'])
        self.assertEqual(env['ANTHROPIC_BASE_URL'], 'https://api.deepseek.com/anthropic')
        self.assertEqual(env['ANTHROPIC_AUTH_TOKEN'], 'sk-test')
        self.assertNotIn('ANTHROPIC_API_KEY', env)
        cmd, _ = jdt.build_command('claude', 'hi', TMP, False, dict(jdt.DEFAULTS))
        self.assertNotIn('--add-dir', cmd)
        self.assertNotIn('acceptEdits', cmd)
        self.assertIn('Read Glob Bash(pdftotext:*)', cmd)
        cmd, _ = jdt.build_command('codex', 'hi', TMP, False, dict(jdt.DEFAULTS))
        self.assertEqual(cmd[cmd.index('-s') + 1], 'read-only')
        cmd, _ = jdt.build_command('grok', 'hi', TMP, True, dict(jdt.DEFAULTS), session='abc')
        self.assertIn('--always-approve', cmd)
        self.assertEqual(cmd[cmd.index('--resume') + 1], 'abc')


class Projects(unittest.TestCase):
    def test_parse_sources(self):
        d = Path(tempfile.mkdtemp(dir=TMP))
        self.assertEqual(jdt.parse_source('https://github.com/xungirl/jd-tailor'), ('repo', 'xungirl', 'jd-tailor'))
        self.assertEqual(jdt.parse_source('github.com/a-b/c.d.git'), ('repo', 'a-b', 'c.d'))
        self.assertEqual(jdt.parse_source('github:xungirl'), ('user', 'xungirl'))
        self.assertEqual(jdt.parse_source('https://github.com/xungirl'), ('user', 'xungirl'))
        self.assertEqual(jdt.parse_source(str(d)), ('dir', d.resolve()))
        for bad in ('relative/path', '/no/such/dir', 'https://evil.com/x/y', 'github:../../etc', ''):
            self.assertIsNone(jdt.parse_source(bad), bad)
        self.assertFalse(jdt.handle({'cmd': 'settings', 'set': {'projects': ['rm -rf /']}})['ok'])

    def test_project_summary(self):
        d = Path(tempfile.mkdtemp(dir=TMP)) / 'telemetry-etl'
        (d / 'src').mkdir(parents=True)
        (d / 'README.md').write_text('# telemetry-etl\n\n![badge](x)\nA Beam pipeline that cleans drone flight telemetry.\n')
        (d / 'src' / 'a.py').write_text('x=1')
        (d / 'src' / 'b.py').write_text('x=1')
        (d / 'BENCHMARK.md').write_text('p50 12 ms')
        out = jdt.describe_project(d, 'bank text mentions Trailmap only')
        self.assertIn('### telemetry-etl', out)
        self.assertIn('in my bank already: no', out)
        self.assertIn('Python (2)', out)
        self.assertIn('evidence files: BENCHMARK.md', out)
        self.assertIn('A Beam pipeline that cleans drone flight telemetry.', out)
        self.assertNotIn('badge', out)
        self.assertIn('in my bank already: yes', jdt.describe_project(d, 'telemetry-etl: built a pipeline'))

    def test_repos_are_readable_not_editable(self):
        cfg = dict(jdt.DEFAULTS, _project_dirs=[Path('/tmp/proj a')])
        cmd, _ = jdt.build_command('claude', 'hi', TMP, True, cfg)
        self.assertIn('/tmp/proj a', cmd[cmd.index('--add-dir'):])
        dis = cmd[cmd.index('--disallowedTools') + 1:]
        self.assertIn('Edit(//tmp/proj a/**)', dis)
        self.assertIn('Write(//tmp/proj a/**)', dis)
        self.assertIn('Bash(curl:*)', dis)
        self.assertIn('Read(~/.ssh/**)', dis)
        self.assertIn(f'Read(/{jdt.home() / "config.json"})', dis)
        self.assertEqual(cmd.count('--disallowedTools'), 1)
        cmd, _ = jdt.build_command('claude', 'hi', TMP, False, cfg)
        self.assertNotIn('/tmp/proj a', cmd)  # reviewers never see your repos


class Flow(unittest.TestCase):
    def setUp(self):
        jdt.save_config({'mode': 'thorough', 'agents': {'claude': {'command': FAKE}, 'codex': {'command': FAKE}}})

    def test_full_flow_with_blind_reviewers(self):
        r = jdt.handle({'cmd': 'tailor', 'job': {'url': 'https://example.com/jobs/1', 'company': 'Acme Robotics',
                                                 'title': 'Software Engineer Intern', 'text': JD_TEXT}})
        self.assertTrue(r['ok'], r)
        j = wait(r['id'])
        self.assertEqual(j['status'], 'ready', j)
        keys = [s['key'] for s in j['stages']]
        # HM round 1 said "unsure", so HM round 2 runs; ATS passed, so it doesn't.
        self.assertEqual(keys, ['write', 'check', 'hm1', 'ats1', 'revise1', 'check1', 'hm2', 'revise2', 'check2', 'gate'])
        self.assertTrue(all(s['status'] == 'done' for s in j['stages']), j['stages'])
        self.assertEqual(j['result']['gate'], 'pass')
        self.assertEqual((j['result']['hm'], j['result']['ats']), ('yes', 'pass'))
        self.assertEqual(j['writer'], 'claude')
        self.assertEqual(j['reviewer'], 'codex')
        self.assertAlmostEqual(j['cost'], 0.05 * 3 + 0.02 * 3, places=5)
        d = Path(j['folder'])
        hm = (d / 'review_hm_1.md').read_text()
        self.assertIn('files: jd.md resume.pdf resume.txt\n', hm)  # the HM sees only the JD and the paper
        ats = (d / 'review_ats_1.md').read_text()
        self.assertIn('files: extract_pdftotext.txt extract_raw.txt jd.md links.txt resume.pdf resume_source.md\n', ats)
        self.assertIn('https://github.com/alexrivera-example', (d / 'reviews' / 'ats_1' / 'links.txt').read_text())
        self.assertIn('Python REST API', (d / 'reviews' / 'hm_1' / 'resume.txt').read_text())
        calls = (d / 'calls.log').read_text().splitlines()
        self.assertEqual([c.split(' |')[0] for c in calls], ['ROLE: writer', 'ROLE: writer (revision 1)', 'ROLE: writer (revision 2)'])
        self.assertIn('Revised:', j['result']['summary'])
        self.assertEqual(jdt.handle({'cmd': 'find', 'url': 'https://example.com/jobs/1'})['job']['id'], j['id'])
        self.assertTrue(jdt.handle({'cmd': 'pdf', 'id': j['id']})['b64'].startswith('JVBERi0'))
        self.assertIn('Direction: backend', jdt.handle({'cmd': 'review', 'id': j['id'], 'name': 'analysis'})['text'])
        self.assertIn(j['id'], [x['id'] for x in jdt.handle({'cmd': 'list'})['jobs']])

    def test_quick_mode_one_round_and_streamed_activity(self):
        jdt.save_config({'mode': 'quick', 'agents': {'claude': {'command': FAKE + ['stream'], 'stream': True},
                                                     'codex': {'command': FAKE}}})
        r = jdt.handle({'cmd': 'tailor', 'job': {'url': 'https://example.com/jobs/3', 'company': 'Quick Co',
                                                 'title': 'Intern', 'text': JD_TEXT}})
        j = wait(r['id'])
        keys = [s['key'] for s in j['stages']]
        self.assertEqual(keys, ['write', 'check', 'hm1', 'ats1', 'revise1', 'check1', 'gate'])
        self.assertEqual(j['status'], 'ready')  # the gate passes an "unsure" HM (only "no" fails it), per the flow
        self.assertEqual(j['result']['hm'], 'unsure')
        self.assertTrue(all('seconds' in s for s in j['stages'] if s['key'] != 'gate'), j['stages'])
        self.assertEqual((j['writer_model'], j['reviewer_model'], j['mode']), ('opus', '', 'quick'))
        self.assertEqual(j['cost'], 0.05 * 2 + 0.02 * 2)  # cost read from the stream's result event
        self.assertTrue(j['has_pdf'])

    def test_projects_feed_the_writer_and_reset(self):
        proj = Path(tempfile.mkdtemp(dir=TMP)) / 'telemetry-etl'
        proj.mkdir()
        (proj / 'README.md').write_text('# telemetry-etl\nA Beam pipeline for drone flight telemetry.\n')
        jdt.save_config({'mode': 'quick', 'projects': [str(proj)], 'agents': {'claude': {'command': FAKE}, 'codex': {'command': FAKE}}})
        try:
            r = jdt.handle({'cmd': 'tailor', 'job': {'url': 'https://example.com/jobs/4', 'company': 'Proj Co', 'title': 'Intern', 'text': JD_TEXT}})
            j = wait(r['id'])
        finally:
            jdt.save_config({'projects': []})
        self.assertEqual(j['stages'][0]['key'], 'projects')
        self.assertEqual(j['stages'][0]['detail'], '1 projects')
        self.assertIn('### telemetry-etl', (Path(j['folder']) / 'projects.md').read_text())
        self.assertEqual(j['result']['new_from_projects'][0]['project'], 'telemetry-etl')
        self.assertFalse((Path(j['folder']) / 'reviews' / 'hm_1' / 'projects.md').exists())
        self.assertTrue(jdt.handle({'cmd': 'reset', 'id': j['id']})['ok'])
        self.assertFalse(Path(j['folder']).exists())
        self.assertTrue(any(p.name.startswith(j['id']) for p in (jdt.home() / 'trash').iterdir()))
        self.assertIsNone(jdt.handle({'cmd': 'find', 'url': 'https://example.com/jobs/4'})['job'])

    def test_bank_backup_diff_and_restore(self):
        d = Path(tempfile.mkdtemp(dir=TMP))
        bank = d / 'resume.toml'
        bank.write_text('[profile]\nname = "Alex Rivera"\n')
        conf = d / 'config.md'
        conf.write_text(f'- Bullet bank: {bank}\n- Tracker: {d}/tracker.toml (do not touch)\n')
        (d / 'tracker.toml').write_text('x=1')
        jdt.save_config({'mode': 'quick', 'tailor_config': str(conf), 'agents': {'claude': {'command': FAKE}, 'codex': {'command': FAKE}}})
        try:
            self.assertEqual(jdt.bank_files(jdt.load_config()), [bank])  # the tracker's line is left out
            r = jdt.handle({'cmd': 'tailor', 'job': {'url': 'https://example.com/jobs/5', 'company': 'Bank Co', 'title': 'Intern', 'text': JD_TEXT}})
            j = wait(r['id'])
        finally:
            jdt.save_config({'tailor_config': str(TMP / 'no-config.md')})
        self.assertTrue(j['bank_changed'])
        diff = jdt.handle({'cmd': 'review', 'id': j['id'], 'name': 'bank_changes'})['text']
        self.assertIn('+[variants.', diff)
        self.assertIn('(before this run)', diff)
        self.assertIn('[variants.', bank.read_text())
        r = jdt.handle({'cmd': 'restore_bank', 'id': j['id']})
        self.assertEqual(r['restored'], [str(bank)])
        self.assertEqual(bank.read_text(), '[profile]\nname = "Alex Rivera"\n')
        self.assertFalse(jdt.handle({'cmd': 'status', 'id': j['id']})['job']['bank_changed'])

    def test_one_writer_at_a_time(self):
        os.environ['FAKE_SLEEP'] = '1.0'
        log = jdt.home() / 'writes.log'
        log.unlink(missing_ok=True)
        try:
            ids = [jdt.handle({'cmd': 'tailor', 'job': {'url': f'https://example.com/jobs/lock{i}', 'company': f'Lock{i}',
                                                        'title': 'Intern', 'text': JD_TEXT}})['id'] for i in range(2)]
            for i in ids:
                wait(i, timeout=90)
        finally:
            del os.environ['FAKE_SLEEP']
        spans, open_ = [], {}
        for line in log.read_text().split('\n'):
            if line:
                kind, name, t = line.split()
                if kind == 'start':
                    open_[name] = float(t)
                else:
                    spans.append((open_.pop(name), float(t)))
        spans.sort()
        self.assertGreaterEqual(len(spans), 4)  # each job: first draft + revision
        for (a0, a1), (b0, b1) in zip(spans, spans[1:]):
            self.assertLessEqual(a1, b0 + 0.05, f'two writers overlapped: {spans}')

    def test_question_then_answer(self):
        r = jdt.handle({'cmd': 'tailor', 'job': {'url': 'https://example.com/jobs/2', 'company': 'Gov Co', 'title': 'Intern',
                                                 'text': JD_TEXT + ' Requires an active SECURITY CLEARANCE.'}})
        j = wait(r['id'])
        self.assertEqual(j['status'], 'needs_user')
        self.assertIn('clearance', j['result']['questions'][0])
        self.assertEqual([s['key'] for s in j['stages']], ['write'])
        r = jdt.handle({'cmd': 'answer', 'id': j['id'], 'text': 'Yes, I hold one.'})
        self.assertTrue(r['ok'])
        j = wait(j['id'])
        self.assertEqual(j['status'], 'ready', j)
        self.assertIn('Yes, I hold one.', (Path(j['folder']) / 'my_answers.md').read_text())


if __name__ == '__main__':
    unittest.main()
