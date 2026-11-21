#!/usr/bin/env python3
"""JD Tailor's local side: the browser's native messaging host, and the worker that runs the agents.

    jdt.py install      register with Chrome / Edge (once); prints what it did
    jdt.py uninstall    remove that registration
    jdt.py doctor       which agents are installed and ready, and where things are
    jdt.py host         (started by the browser) answer one message on stdin/stdout
    jdt.py work <dir>   (started by the host) run the tailoring flow for one job

No server, no port, no token: the browser starts `host` itself, and only for this extension's ID.
The agents are the CLIs you already logged in to (Claude Code, Codex, Grok Build), or Claude Code
pointed at DeepSeek with your DeepSeek key. Data lives in ~/.config/jd-tailor ($JD_TAILOR_HOME).
Python 3.9+, standard library only.
"""
import base64
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import signal
import struct
import subprocess
import sys
import time
from pathlib import Path

VERSION = '0.2.0'
HERE = Path(__file__).resolve().parent
FLOW = HERE / 'flow'
CHECK = HERE / 'check.py'
HOST_NAME = 'io.github.xungirl.jd_tailor'
EXT_ID = 'hmjpobnjbippkgjgnmopcbnbhipcadfj'  # fixed by the "key" in extension/manifest.json

sys.path.insert(0, str(HERE))
import check as checks  # noqa: E402

DEFAULTS = {
    'writer': 'claude',
    'reviewer': 'same',
    'max_budget_usd': 4,       # per agent run (Claude Code only)
    'timeout_minutes': 25,     # per agent run
    'extra_dirs': [],          # more folders the writer may read (your bank and build script are found from the skill config)
    'tailor_config': '',       # use this jd-resume-tailor config instead of the default (tests use a made-up person)
    'deepseek_key': '',
    'deepseek_model': 'deepseek-v4-pro',
    'agents': {},              # per-agent overrides, e.g. {"grok": {"model": "grok-4.6"}} or a full {"command": [...]}
}

AGENTS = {
    'claude': {'name': 'Claude Code', 'bin': 'claude', 'login': 'Uses your Claude Code login.'},
    'codex': {'name': 'Codex', 'bin': 'codex', 'login': 'Uses your Codex login.'},
    'grok': {'name': 'Grok Build', 'bin': 'grok', 'login': 'Uses your Grok Build login (run "grok login" once).'},
    'deepseek': {'name': 'DeepSeek (in Claude Code)', 'bin': 'claude', 'login': 'Needs your DeepSeek API key, once.'},
}


# ---------------------------------------------------------------- config and paths

def home() -> Path:
    return Path(os.environ.get('JD_TAILOR_HOME') or '~/.config/jd-tailor').expanduser()


def load_config() -> dict:
    p = home() / 'config.json'
    cfg = dict(DEFAULTS)
    if p.exists():
        try:
            cfg.update(json.loads(p.read_text()))
        except ValueError:
            pass
    return cfg


def save_config(patch: dict) -> dict:
    cfg = load_config()
    cfg.update(patch)
    p = home() / 'config.json'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg, indent=2))
    os.chmod(p, 0o600)  # it may hold a DeepSeek key
    return cfg


def now() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%S')


def skill_dir():
    for d in ['~/.claude/skills/jd-resume-tailor', '~/.agents/skills/jd-resume-tailor', '~/jd-resume-tailor/skills/jd-resume-tailor']:
        p = Path(d).expanduser()
        if (p / 'SKILL.md').exists():
            return p.resolve()
    return None


def tailor_config_path(cfg) -> Path:
    return Path(cfg.get('tailor_config') or '~/.config/jd-resume-tailor/config.md').expanduser()


def reading_dirs(cfg) -> list:
    """Folders the writer needs besides its own: the skill and builder, and the folders your
    jd-resume-tailor config names (your bullet bank, build script, output folder)."""
    dirs = [Path(d).expanduser() for d in cfg.get('extra_dirs', [])]
    s = skill_dir()
    if s:
        dirs.append(s.parent.parent)  # the repo: the skill and builder/
    tc = tailor_config_path(cfg)
    if tc.exists():
        dirs.append(tc.parent)
        for m in re.findall(r'(~/[^\s`\'")\]]+|/Users/[^\s`\'")\]]+|/home/[^\s`\'")\]]+)', tc.read_text()):
            p = Path(m.rstrip('.,;:')).expanduser()
            d = p if p.is_dir() else p.parent
            if d.exists() and d != Path.home():
                dirs.append(d)
    out = []
    for d in dirs:
        if d.exists() and d not in out:
            out.append(d)
    return out


# ---------------------------------------------------------------- agents

def _works(binary: str) -> bool:
    path = shutil.which(binary)
    if not path:
        return False
    try:
        return subprocess.run([path, '--version'], capture_output=True, timeout=20).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def agent_status(cfg=None) -> list:
    cfg = cfg or load_config()
    out = []
    for aid, a in AGENTS.items():
        override = cfg.get('agents', {}).get(aid, {})
        found = bool(override.get('command')) or _works(a['bin'])
        ready, note = found, a['login']
        if not found:
            note = {'claude': 'Install Claude Code: https://claude.com/claude-code',
                    'codex': 'Install Codex: npm i -g @openai/codex (installed but not starting? reinstall it)',
                    'grok': 'Install Grok Build: https://docs.x.ai/build/overview',
                    'deepseek': 'Needs Claude Code installed (it runs DeepSeek inside Claude Code).'}[aid]
        if aid == 'deepseek' and found and not cfg.get('deepseek_key'):
            ready, note = False, 'Paste your DeepSeek API key once (platform.deepseek.com/api_keys).'
        out.append({'id': aid, 'name': a['name'], 'found': found, 'ready': ready, 'note': note})
    return out


def build_command(agent: str, prompt: str, cwd: Path, writing: bool, cfg: dict, session=None):
    """The command line and environment for one unattended run."""
    env = dict(os.environ)
    if cfg.get('tailor_config'):
        env['JD_RESUME_TAILOR_CONFIG'] = str(Path(cfg['tailor_config']).expanduser())
    over = cfg.get('agents', {}).get(agent, {})
    if over.get('command'):  # tests, or your own wrapper
        fill = lambda s: s.replace('{prompt}', prompt).replace('{cwd}', str(cwd)).replace('{mode}', 'write' if writing else 'review')
        return [fill(x) for x in over['command']], env
    dirs = [str(d) for d in reading_dirs(cfg)] if writing else []
    if agent in ('claude', 'deepseek'):
        tools = 'Bash Read Write Edit Glob Grep Skill' if writing else 'Read Glob Bash(pdftotext:*)'
        cmd = ['claude', '-p', prompt, '--allowedTools', tools, '--output-format', 'json',
               '--max-budget-usd', str(cfg.get('max_budget_usd', 4))]
        if writing:
            cmd += ['--permission-mode', 'acceptEdits']
        for d in dirs:
            cmd += ['--add-dir', d]
        if session:
            cmd += ['--resume', session]
        if over.get('model'):
            cmd += ['--model', over['model']]
        if agent == 'deepseek':
            # DeepSeek's documented setup for Claude Code (api-docs.deepseek.com, "Integrate with Claude Code").
            for k in ('ANTHROPIC_API_KEY', 'CLAUDE_CODE_OAUTH_TOKEN'):
                env.pop(k, None)
            m = cfg.get('deepseek_model') or 'deepseek-v4-pro'
            env.update({'ANTHROPIC_BASE_URL': 'https://api.deepseek.com/anthropic',
                        'ANTHROPIC_AUTH_TOKEN': cfg.get('deepseek_key', ''),
                        'ANTHROPIC_MODEL': m, 'ANTHROPIC_DEFAULT_OPUS_MODEL': m, 'ANTHROPIC_DEFAULT_SONNET_MODEL': m,
                        'ANTHROPIC_DEFAULT_HAIKU_MODEL': 'deepseek-flash', 'CLAUDE_CODE_SUBAGENT_MODEL': 'deepseek-flash'})
        return cmd, env
    if agent == 'codex':
        cmd = ['codex', 'exec', '--skip-git-repo-check', '-C', str(cwd),
               '-s', 'workspace-write' if writing else 'read-only',
               '--output-last-message', str(cwd / '.last_message.txt')]
        if writing:
            cmd += ['-c', 'sandbox_workspace_write.network_access=true']
        for d in dirs:
            cmd += ['--add-dir', d]
        if over.get('model'):
            cmd += ['-m', over['model']]
        return cmd + [prompt], env
    if agent == 'grok':
        cmd = ['grok', '--no-auto-update', '-p', prompt, '--cwd', str(cwd), '--output-format', 'json', '--always-approve']
        if session:
            cmd += ['--resume', session]
        if over.get('model'):
            cmd += ['-m', over['model']]
        return cmd, env
    raise ValueError(f'unknown agent "{agent}"')


def run_agent(agent: str, prompt: str, cwd: Path, writing: bool, cfg: dict, log: Path, session=None) -> dict:
    cmd, env = build_command(agent, prompt, cwd, writing, cfg, session)
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                           timeout=int(cfg.get('timeout_minutes', 25)) * 60)
        out, err, code = p.stdout, p.stderr, p.returncode
    except subprocess.TimeoutExpired as e:
        out, err, code = (e.stdout or b'').decode() if isinstance(e.stdout, bytes) else (e.stdout or ''), 'timed out', -1
    except OSError as e:
        out, err, code = '', str(e), -1
    with open(log, 'a') as f:
        f.write(f'\n===== {now()} {agent} {"write" if writing else "review"} in {cwd.name} (exit {code}, {time.time() - t0:.0f}s)\n')
        f.write(out[-20000:])
        if err.strip():
            f.write('\n--- stderr\n' + err[-5000:])
    res = {'ok': code == 0, 'text': out, 'session': None, 'cost': None, 'error': '' if code == 0 else (err.strip() or out.strip())[-400:]}
    try:
        j = json.loads(out)
        if isinstance(j, dict):
            res['text'] = j.get('result') or j.get('text') or ''
            res['session'] = j.get('session_id') or j.get('sessionId')
            res['cost'] = j.get('total_cost_usd')
            if j.get('is_error'):
                res['ok'], res['error'] = False, str(j.get('result') or j.get('subtype') or 'agent error')[-400:]
    except ValueError:
        pass
    last = cwd / '.last_message.txt'
    if last.exists():
        res['text'] = last.read_text()
        last.unlink()
    return res


# ---------------------------------------------------------------- jobs

def jobs_dir() -> Path:
    d = home() / 'jobs'
    d.mkdir(parents=True, exist_ok=True)
    return d


def job_id(job: dict) -> str:
    name = re.sub(r'[^A-Za-z0-9]+', '_', f"{job.get('company', '')}_{job.get('title', '')}").strip('_')[:50] or 'job'
    return f"{name}_{hashlib.sha1((job.get('url') or job.get('text', '')[:500]).encode()).hexdigest()[:6]}"


def job_path(jid: str) -> Path:
    if not re.fullmatch(r'[A-Za-z0-9_]+', jid or ''):
        raise ValueError('bad job id')
    return jobs_dir() / jid


def read_json(p: Path, default=None):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def write_json(p: Path, data):
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(p)


class Job:
    def __init__(self, d: Path):
        self.d = d
        self.state = read_json(d / 'state.json', {})

    def save(self):
        self.state['updated'] = now()
        write_json(self.d / 'state.json', self.state)

    def stage(self, key, label, status='running', detail=''):
        st = self.state.setdefault('stages', [])
        for s in st:
            if s['key'] == key:
                s.update({'label': label, 'status': status, 'detail': detail})
                break
        else:  # a new stage goes before the ones still to do
            at = next((i for i, s in enumerate(st) if s['status'] == 'todo'), len(st))
            st.insert(at, {'key': key, 'label': label, 'status': status, 'detail': detail})
        if status == 'running':
            self.state['stage'] = key
        self.save()

    def plan(self, keys_labels):
        """Show upcoming stages as gray dots."""
        st = self.state.setdefault('stages', [])
        have = {s['key'] for s in st}
        for k, l in keys_labels:
            if k not in have:
                at = next((i for i, s in enumerate(st) if s['key'] == 'gate'), len(st))  # the gate stays last
                st.insert(at, {'key': k, 'label': l, 'status': 'todo', 'detail': ''})
        self.save()

    def drop_todo(self):
        self.state['stages'] = [s for s in self.state.get('stages', []) if s['status'] != 'todo']
        self.save()

    def finish(self, status, **extra):
        self.drop_todo()
        self.state.update(status=status, stage='', finished=now(), **extra)
        self.save()


def create_job(job: dict, cfg: dict) -> str:
    text = (job.get('text') or '').strip()
    if len(text) < 200:
        raise ValueError('the job description is too short')
    jid = job_id(job)
    d = job_path(jid)
    d.mkdir(parents=True, exist_ok=True)
    head = f"# {job.get('title', '')}\n{job.get('company', '')} | {job.get('location', '')}\n{job.get('url', '')}\n\n"
    (d / 'jd.md').write_text(head + text + '\n')
    old = read_json(d / 'state.json', {})
    writer = job.get('writer') or cfg['writer']
    reviewer = job.get('reviewer') or cfg['reviewer']
    write_json(d / 'state.json', {
        'id': jid, 'url': job.get('url', ''), 'company': job.get('company', ''), 'title': job.get('title', ''),
        'location': job.get('location', ''), 'writer': writer, 'reviewer': writer if reviewer == 'same' else reviewer,
        'status': 'queued', 'stage': '', 'stages': [], 'created': old.get('created') or now(), 'updated': now(),
        'started': '', 'finished': '', 'error': '', 'session': None, 'cost': 0, 'pid': None,
    })
    for f in ('result.json', 'writer.json'):
        (d / f).unlink(missing_ok=True)
    return jid


def spawn_worker(jid: str):
    d = job_path(jid)
    log = open(d / 'worker.log', 'a')
    p = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'work', str(d)],
                         stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True, cwd=str(d))
    st = read_json(d / 'state.json', {})
    st['pid'] = p.pid
    write_json(d / 'state.json', st)


def alive(pid) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------- the flow

def fmt(name: str, **kw) -> str:
    return (FLOW / name).read_text().format(**kw)


def verdict(text: str, allowed) -> str:
    found = re.findall(r'VERDICT:\s*\**\s*(' + '|'.join(allowed) + r')\b', text or '', re.I)
    return found[-1].lower() if found else 'unknown'


def pdf_links(pdf: Path) -> list:
    data = pdf.read_bytes()
    return sorted(set(m.decode('latin-1') for m in re.findall(rb'/URI\s*\(([^)]*)\)', data)))


def pdftotext(pdf: Path, *flags) -> str:
    try:
        return subprocess.run(['pdftotext', *flags, str(pdf), '-'], capture_output=True, text=True, timeout=60).stdout
    except OSError:
        return ''


def prepare_review(job: Job, kind: str, rnd: int) -> Path:
    """A folder holding only what this reviewer may see. The reviewer runs inside it."""
    r = job.d / 'reviews' / f'{kind}_{rnd}'
    if r.exists():
        shutil.rmtree(r)
    r.mkdir(parents=True)
    shutil.copy(job.d / 'jd.md', r / 'jd.md')
    shutil.copy(job.d / 'resume.pdf', r / 'resume.pdf')
    if kind == 'hm':
        (r / 'resume.txt').write_text(pdftotext(r / 'resume.pdf', '-layout'))
    else:
        src = job.d / 'resume_source.md'
        (r / 'resume_source.md').write_text(src.read_text() if src.exists() else '(the writer did not write resume_source.md)')
        (r / 'extract_pdftotext.txt').write_text(pdftotext(r / 'resume.pdf', '-layout'))
        (r / 'extract_raw.txt').write_text(pdftotext(r / 'resume.pdf', '-raw'))
        (r / 'links.txt').write_text('\n'.join(pdf_links(r / 'resume.pdf')) or '(no links found)')
    return r


def review(job: Job, cfg: dict, kinds, rnd: int) -> dict:
    """Run the reviewers for this round at the same time. Returns {kind: verdict}."""
    st = job.state
    labels = {'hm': 'Hiring manager review', 'ats': 'ATS review'}
    for k in kinds:
        job.stage(f'{k}{rnd}', f'{labels[k]} {rnd}', 'running', st['reviewer'])

    def one(kind):
        r = prepare_review(job, kind, rnd)
        prompt = fmt(f'{kind}.md', role=st.get('title') or 'this role', company=st.get('company') or 'the company')
        res = run_agent(st['reviewer'], prompt, r, False, cfg, job.d / 'agent.log')
        (job.d / f'review_{kind}_{rnd}.md').write_text(res['text'] or res['error'])
        v = verdict(res['text'], ['yes', 'no', 'unsure'] if kind == 'hm' else ['pass', 'fail'])
        return kind, v, res

    out = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for kind, v, res in pool.map(one, kinds):
            out[kind] = v
            job.state['cost'] = (job.state.get('cost') or 0) + (res['cost'] or 0)
            job.stage(f'{kind}{rnd}', f'{labels[kind]} {rnd}', 'done' if res['ok'] else 'failed',
                      v if res['ok'] else res['error'][:200])
    return out


def write_run(job: Job, cfg: dict, prompt: str, key: str, label: str) -> dict:
    st = job.state
    job.stage(key, label, 'running', st['writer'])
    # Claude Code and Grok continue the same session, so the writer remembers why it chose what it chose.
    session = st.get('session') if key != 'write' and st['writer'] in ('claude', 'deepseek', 'grok') else None
    res = run_agent(st['writer'], prompt, job.d, True, cfg, job.d / 'agent.log', session)
    if res['session']:
        st['session'] = res['session']
    st['cost'] = (st.get('cost') or 0) + (res['cost'] or 0)
    w = read_json(job.d / 'writer.json', {}) or {}
    ok = res['ok'] and (job.d / 'resume.pdf').exists()
    job.stage(key, label, 'done' if ok or w.get('status') in ('needs_user', 'skip') else 'failed',
              w.get('summary', '')[:300] if ok else (res['error'] or 'no resume.pdf was written')[:300])
    return {'ok': ok, 'writer': w, 'error': res['error']}


def run_checks(job: Job, key='check', label='Script checks') -> dict:
    job.stage(key, label)
    r = checks.check(str(job.d / 'resume.pdf'), str(job.d / 'analysis.md'))
    write_json(job.d / f'{key}.json', r)
    job.stage(key, label, 'done' if r['ok'] else 'failed', 'pass' if r['ok'] else '; '.join(r['failures'])[:300])
    return r


def revise(job: Job, cfg: dict, rnd: int, reviews: dict, check_result=None) -> dict:
    parts = []
    for kind, name in (('hm', 'HM review'), ('ats', 'ATS review')):
        if kind in reviews:
            parts.append(f'===== {name} (round {rnd}) =====\n' + (job.d / f'review_{kind}_{rnd}.md').read_text())
    checks_note = ''
    if check_result and not check_result['ok']:
        checks_note = 'The script check also failed:\n' + '\n'.join('- ' + f for f in check_result['failures'])
    st = job.state
    prompt = fmt('revise.md', round=rnd, jobdir=job.d, company=st.get('company', ''), title=st.get('title', ''),
                 checks=checks_note, check=f'python3 {CHECK}', reviews='\n\n'.join(parts) or '(no reviews this time)')
    return write_run(job, cfg, prompt, f'revise{rnd}', f'Revise after round {rnd}')


def work(d: Path):
    lock = d / 'worker.pid'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            if alive(int(lock.read_text().strip() or 0)):
                return  # another worker has this job
        except ValueError:
            pass
        lock.unlink(missing_ok=True)
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    job = Job(d)
    try:
        flow(job, load_config())
    except Exception as e:  # keep the panel honest about crashes
        job.finish('failed', error=f'{type(e).__name__}: {e}'[:400])
    finally:
        lock.unlink(missing_ok=True)


def flow(job: Job, cfg: dict):
    st = job.state
    st.update(status='running', started=now(), error='', stages=[], cost=0, pid=os.getpid())
    job.save()
    job.plan([('write', 'Analysis and first draft'), ('check', 'Script checks'), ('hm1', 'Hiring manager review 1'),
              ('ats1', 'ATS review 1'), ('revise1', 'Revise after round 1'), ('gate', 'Gate')])
    answers = (job.d / 'my_answers.md').read_text() if (job.d / 'my_answers.md').exists() else ''
    if answers:
        answers = '\nMy answers to your earlier questions (they decide what you asked):\n' + answers + '\n'
    w = write_run(job, cfg, fmt('writer.md', jobdir=job.d, company=st['company'], title=st['title'], url=st['url'],
                                answers=answers, check=f'python3 {CHECK}'), 'write', 'Analysis and first draft')
    info = w['writer']
    if info.get('status') in ('needs_user', 'skip'):
        return job.finish(info['status'], result=result(job, info, {}, 'n/a'))
    if not w['ok']:
        return job.finish('failed', error=w['error'] or 'the writer did not produce resume.pdf', result=result(job, info, {}, 'n/a'))

    c = run_checks(job)
    if not c['ok']:  # one repair pass before the reviewers see it
        info = revise(job, cfg, 0, {}, c)['writer'] or info
        c = run_checks(job, 'check0', 'Script checks (after repair)')

    last = review(job, cfg, ['hm', 'ats'], 1)
    info = revise(job, cfg, 1, last)['writer'] or info
    run_checks(job, 'check1', 'Script checks')

    # Round 2: HM if round 1 wasn't a yes, or the revision touched a hard-requirement bullet or 3+ bullets.
    # ATS only if round 1 failed. Round 3: HM only, only if round 2 said no; its notes are applied, not re-reviewed.
    kinds = []
    if last['hm'] != 'yes' or info.get('touched_hard_requirement') or int(info.get('bullets_changed') or 0) >= 3:
        kinds.append('hm')
    if last['ats'] != 'pass':
        kinds.append('ats')
    if kinds:
        job.plan([(f'{k}2', f'{"Hiring manager" if k == "hm" else "ATS"} review 2') for k in kinds] + [('revise2', 'Revise after round 2')])
        r2 = review(job, cfg, kinds, 2)
        last.update(r2)
        info = revise(job, cfg, 2, r2)['writer'] or info
        run_checks(job, 'check2', 'Script checks')
        if r2.get('hm') == 'no':
            r3 = review(job, cfg, ['hm'], 3)
            last.update(r3)
            info = revise(job, cfg, 3, r3)['writer'] or info
            run_checks(job, 'check3', 'Script checks')

    final_check = checks.check(str(job.d / 'resume.pdf'), str(job.d / 'analysis.md'))
    passed = last.get('hm') not in ('no', 'unknown') and last.get('ats') == 'pass' and final_check['ok']
    job.stage('gate', 'Gate', 'done' if passed else 'failed',
              f"HM {last.get('hm')}, ATS {last.get('ats')}, checks {'pass' if final_check['ok'] else 'fail'}")
    gate = 'pass' if passed else 'needs_you'
    job.finish('ready' if passed else 'needs_you', result=result(job, info, last, gate, final_check['warnings']))


def result(job: Job, info: dict, verdicts: dict, gate: str, warnings=()) -> dict:
    r = {
        'gate': gate, 'hm': verdicts.get('hm'), 'ats': verdicts.get('ats'),
        'direction': info.get('direction', ''), 'lead': info.get('lead', ''), 'summary': info.get('summary', ''),
        'gaps': info.get('gaps', []), 'constraints': info.get('constraints', []), 'dropped': info.get('dropped', []),
        'unverified_numbers': info.get('unverified_numbers', []), 'questions': info.get('questions', []),
        'warnings': list(warnings), 'pdf': (job.d / 'resume.pdf').exists(),
    }
    write_json(job.d / 'result.json', r)
    return r


# ---------------------------------------------------------------- native messaging

def view(d: Path) -> dict:
    st = read_json(d / 'state.json', {}) or {}
    if st.get('status') in ('running', 'queued') and st.get('pid') and not alive(st['pid']) \
            and not (d / 'worker.pid').exists() and st.get('updated', '') < time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time() - 30)):
        st['status'], st['error'] = 'failed', 'the worker stopped unexpectedly (see worker.log)'
    out = {k: st.get(k) for k in ('id', 'url', 'company', 'title', 'writer', 'reviewer', 'status', 'stage', 'stages',
                                  'created', 'updated', 'started', 'finished', 'error', 'cost', 'result')}
    out['folder'] = str(d)
    return out


def handle(msg: dict) -> dict:
    cmd = msg.get('cmd')
    cfg = load_config()
    if cmd == 'hello':
        s = skill_dir()
        return {'ok': True, 'version': VERSION, 'home': str(home()), 'agents': agent_status(cfg),
                'writer': cfg['writer'], 'reviewer': cfg['reviewer'], 'skill': str(s) if s else '',
                'tailor_config': str(tailor_config_path(cfg)) if tailor_config_path(cfg).exists() else '',
                'poppler': bool(shutil.which('pdftotext'))}
    if cmd == 'settings':
        allowed = {'writer', 'reviewer', 'deepseek_key', 'deepseek_model'}
        patch = {k: v for k, v in (msg.get('set') or {}).items() if k in allowed and isinstance(v, str)}
        if patch.get('writer') and patch['writer'] not in AGENTS:
            return {'ok': False, 'error': 'unknown agent'}
        if patch.get('reviewer') and patch['reviewer'] not in list(AGENTS) + ['same']:
            return {'ok': False, 'error': 'unknown agent'}
        cfg = save_config(patch)
        return {'ok': True, 'writer': cfg['writer'], 'reviewer': cfg['reviewer'], 'agents': agent_status(cfg)}
    if cmd == 'tailor':
        job = msg.get('job') or {}
        for a in ('writer', 'reviewer'):
            if job.get(a) and job[a] not in list(AGENTS) + ['same']:
                return {'ok': False, 'error': 'unknown agent'}
        ready = {a['id']: a['ready'] for a in agent_status(cfg)}
        writer = job.get('writer') or cfg['writer']
        reviewer = job.get('reviewer') or cfg['reviewer']
        for a in {writer, writer if reviewer == 'same' else reviewer}:
            if not ready.get(a):
                return {'ok': False, 'error': f'{AGENTS[a]["name"]} is not ready: ' + next(x['note'] for x in agent_status(cfg) if x['id'] == a)}
        try:
            jid = create_job(job, cfg)
        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        st = read_json(job_path(jid) / 'state.json', {})
        old_pid = int((job_path(jid) / 'worker.pid').read_text() or 0) if (job_path(jid) / 'worker.pid').exists() else 0
        if alive(old_pid):
            return {'ok': False, 'error': 'this job is already being tailored'}
        spawn_worker(jid)
        return {'ok': True, 'id': jid, 'job': view(job_path(jid))}
    if cmd == 'status':
        d = job_path(msg.get('id', ''))
        if not (d / 'state.json').exists():
            return {'ok': False, 'error': 'no such job'}
        return {'ok': True, 'job': view(d)}
    if cmd == 'find':  # the job for a posting URL, if any
        for d in jobs_dir().iterdir():
            st = read_json(d / 'state.json', {}) or {}
            if st.get('url') and st['url'] == msg.get('url'):
                return {'ok': True, 'job': view(d)}
        return {'ok': True, 'job': None}
    if cmd == 'list':
        items = [view(d) for d in jobs_dir().iterdir() if (d / 'state.json').exists()]
        items.sort(key=lambda j: j.get('updated') or '', reverse=True)
        return {'ok': True, 'jobs': [{k: j[k] for k in ('id', 'company', 'title', 'status', 'updated', 'url')} for j in items[:20]]}
    if cmd == 'answer':
        d = job_path(msg.get('id', ''))
        text = (msg.get('text') or '').strip()
        if not text or not (d / 'state.json').exists():
            return {'ok': False, 'error': 'nothing to send'}
        with open(d / 'my_answers.md', 'a') as f:
            f.write(f'\n## {now()}\n{text}\n')
        st = read_json(d / 'state.json', {})
        st.update(status='queued', session=None)
        write_json(d / 'state.json', st)
        spawn_worker(d.name)
        return {'ok': True, 'job': view(d)}
    if cmd == 'cancel':
        d = job_path(msg.get('id', ''))
        st = read_json(d / 'state.json', {}) or {}
        if alive(st.get('pid')):
            try:
                os.killpg(st['pid'], signal.SIGTERM)
            except OSError:
                pass
        (d / 'worker.pid').unlink(missing_ok=True)
        Job(d).finish('cancelled')
        return {'ok': True, 'job': view(d)}
    if cmd == 'pdf':
        p = job_path(msg.get('id', '')) / 'resume.pdf'
        if not p.exists():
            return {'ok': False, 'error': 'no PDF yet'}
        return {'ok': True, 'b64': base64.b64encode(p.read_bytes()).decode()}
    if cmd == 'reveal':
        d = job_path(msg.get('id', ''))
        target = d / 'resume.pdf' if (d / 'resume.pdf').exists() else d
        opener = ['open', '-R', str(target)] if sys.platform == 'darwin' else ['xdg-open', str(d)]
        subprocess.Popen(opener, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {'ok': True}
    if cmd == 'review':  # read one review or the analysis, for the panel
        d = job_path(msg.get('id', ''))
        name = msg.get('name', '')
        if not re.fullmatch(r'(review_(hm|ats)_\d|analysis|notes)', name):
            return {'ok': False, 'error': 'bad name'}
        p = d / f'{name}.md'
        return {'ok': True, 'text': p.read_text()[:60000] if p.exists() else ''}
    return {'ok': False, 'error': f'unknown command {cmd!r}'}


def host():
    raw = sys.stdin.buffer.read(4)
    if len(raw) < 4:
        return
    n = struct.unpack('<I', raw)[0]
    try:
        msg = json.loads(sys.stdin.buffer.read(n))
        out = handle(msg if isinstance(msg, dict) else {})
    except Exception as e:
        out = {'ok': False, 'error': f'{type(e).__name__}: {e}'}
    data = json.dumps(out).encode()
    if len(data) > 1024 * 1024 - 64:
        data = json.dumps({'ok': False, 'error': 'answer too large for the browser'}).encode()
    sys.stdout.buffer.write(struct.pack('<I', len(data)) + data)
    sys.stdout.buffer.flush()


# ---------------------------------------------------------------- install

def manifest_dirs() -> list:
    if sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
        names = ['Google/Chrome', 'Google/Chrome Beta', 'Google/Chrome Canary', 'Google/Chrome for Testing',
                 'Chromium', 'Microsoft Edge', 'Microsoft Edge Beta', 'BraveSoftware/Brave-Browser', 'Arc/User Data']
    else:
        base = Path.home() / '.config'
        names = ['google-chrome', 'google-chrome-beta', 'chromium', 'microsoft-edge', 'BraveSoftware/Brave-Browser']
    return [base / n / 'NativeMessagingHosts' for n in names if (base / n).exists()]


def install(ext_ids=None):
    ext_ids = ext_ids or [EXT_ID]
    h = home()
    h.mkdir(parents=True, exist_ok=True)
    launcher = h / 'jdt-host'
    # Browsers start the host with a bare PATH: keep the one from install time, so claude/codex/grok are found.
    launcher.write_text('#!/bin/sh\n'
                        f'export PATH={json.dumps(os.environ.get("PATH", "/usr/bin:/bin"))}\n'
                        + (f'export JD_TAILOR_HOME={json.dumps(str(h))}\n' if os.environ.get('JD_TAILOR_HOME') else '')
                        + f'exec {json.dumps(sys.executable)} {json.dumps(str(Path(__file__).resolve()))} host "$@"\n')
    launcher.chmod(0o755)
    manifest = {'name': HOST_NAME, 'description': 'JD Tailor local agent runner', 'path': str(launcher),
                'type': 'stdio', 'allowed_origins': [f'chrome-extension://{i}/' for i in ext_ids]}
    done = []
    for d in manifest_dirs():
        d.mkdir(parents=True, exist_ok=True)
        (d / f'{HOST_NAME}.json').write_text(json.dumps(manifest, indent=2))
        done.append(str(d))
    return launcher, done


def uninstall():
    removed = []
    for d in manifest_dirs():
        p = d / f'{HOST_NAME}.json'
        if p.exists():
            p.unlink()
            removed.append(str(p))
    return removed


def doctor():
    cfg = load_config()
    print(f'JD Tailor {VERSION}  data: {home()}')
    for a in agent_status(cfg):
        print(f"  {'✓' if a['ready'] else '✗'} {a['name']:<28} {a['note']}")
    s = skill_dir()
    print(f"  {'✓' if s else '✗'} jd-resume-tailor skill        {s or 'not found: install it from github.com/xungirl/jd-resume-tailor'}")
    tc = tailor_config_path(cfg)
    print(f"  {'✓' if tc.exists() else '✗'} jd-resume-tailor config       {tc if tc.exists() else str(tc) + ' (missing: run the skill once in Claude Code to set it up)'}")
    print(f"  {'✓' if shutil.which('pdftotext') else '✗'} poppler (pdftotext)           {'' if shutil.which('pdftotext') else 'brew install poppler'}")
    print(f'  writer: {cfg["writer"]}   reviewer: {cfg["reviewer"]}')
    print('  the writer may read:', ', '.join(str(d) for d in reading_dirs(cfg)) or '(nothing extra)')
    for d in manifest_dirs():
        p = d / f'{HOST_NAME}.json'
        print(f"  {'✓' if p.exists() else '·'} {p}")


def main():
    a = sys.argv[1:]
    if not a or a[0] in ('-h', '--help'):
        print(__doc__.strip())
        return
    if a[0] == 'host' or a[0].startswith('chrome-extension://'):
        return host()
    if a[0] == 'work':
        return work(Path(a[1]))
    if a[0] == 'install':
        launcher, done = install(a[1:] or None)
        print(f'Host: {launcher}')
        for d in done:
            print(f'  registered in {d}')
        if not done:
            print('  no Chrome/Edge profile folders found; open the browser once and run install again')
        print('Reload the extension, then open its side panel.')
        return
    if a[0] == 'uninstall':
        for p in uninstall():
            print('removed', p)
        return
    if a[0] == 'doctor':
        return doctor()
    print(__doc__.strip())
    sys.exit(2)


if __name__ == '__main__':
    main()
