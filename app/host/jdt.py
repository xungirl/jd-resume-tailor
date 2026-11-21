#!/usr/bin/env python3
"""JD Resume Tailor's local side: the browser's native messaging host, and the worker that runs the agents.

    jdt.py install      register with Chrome / Edge (once); prints what it did
    jdt.py uninstall    remove that registration
    jdt.py doctor       which agents are installed and ready, and where things are
    jdt.py host         (started by the browser) answer one message on stdin/stdout
    jdt.py work <dir>   (started by the host) run the tailoring flow for one job
    jdt.py web [--port N] [--no-open]
                        the same app as a local web page, for any browser (Safari too); see web_main()

With the extension there's no server, no port, no token: the browser starts `host` itself, and only for
this extension's ID. `web` is the alternative: a server on 127.0.0.1 only, behind a random per-start key.
The agents are the CLIs you already logged in to (Claude Code, Codex, Grok Build), or Claude Code
pointed at DeepSeek with your DeepSeek key. Data lives in ~/.config/jd-resume-tailor/app ($JD_RESUME_TAILOR_APP_HOME).
Python 3.9+, standard library only.
"""
import base64
import concurrent.futures
import difflib
import fcntl
import hashlib
import hmac
import http.server
import json
import os
import re
import secrets
import shutil
import signal
import struct
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

VERSION = '0.2.0'
HERE = Path(__file__).resolve().parent
FLOW = HERE / 'flow'
CHECK = HERE / 'check.py'
HOST_NAME = 'io.github.xungirl.jd_resume_tailor'
EXT_ID = 'hmjpobnjbippkgjgnmopcbnbhipcadfj'  # fixed by the "key" in extension/manifest.json

sys.path.insert(0, str(HERE))
import check as checks  # noqa: E402

DEFAULTS = {
    'writer': 'claude',
    'reviewer': 'same',
    'mode': 'quick',           # quick: one review round; thorough: up to three, as the flow describes
    'writer_model': '',        # '' = the agent's best (Claude: opus)
    'reviewer_model': '',
    'max_budget_usd': 4,       # per agent run (Claude Code only)
    'timeout_minutes': 25,     # per agent run
    'extra_dirs': [],          # more folders the writer may read (your bank and build script are found from the skill config)
    'tailor_config': '',       # use this jd-resume-tailor config instead of the default (tests use a made-up person)
    'deepseek_key': '',
    'projects': [],            # your project folders, GitHub repo URLs, or github:<user>; the writer may mine them
    'agents': {},              # per-agent overrides, e.g. {"grok": {"model": "grok-4.6"}} or a full {"command": [...]}
}

AGENTS = {
    'claude': {'name': 'Claude Code', 'bin': 'claude', 'login': 'Uses your Claude Code login.',
               'models': [['opus', 'Opus (best)'], ['sonnet', 'Sonnet (faster)'], ['haiku', 'Haiku (fastest)']]},
    'codex': {'name': 'Codex', 'bin': 'codex', 'login': 'Uses your Codex login.',
              'models': [['', "Codex's default"]]},
    'grok': {'name': 'Grok Build', 'bin': 'grok', 'login': 'Uses your Grok Build login (run "grok login" once).',
             'models': [['', "Grok's default"]]},
    'deepseek': {'name': 'DeepSeek (in Claude Code)', 'bin': 'claude', 'login': 'Needs your DeepSeek API key, once.',
                 'models': [['deepseek-v4-pro', 'V4 Pro (best)'], ['deepseek-flash', 'Flash (faster)']]},
}


def model_for(agent: str, writing: bool, cfg: dict) -> str:
    """The model this role runs on: your choice, else the agent's best (the first in its list)."""
    chosen = cfg.get('writer_model' if writing else 'reviewer_model') or ''
    return chosen or cfg.get('agents', {}).get(agent, {}).get('model') or AGENTS[agent]['models'][0][0]


# ---------------------------------------------------------------- config and paths

def home() -> Path:
    return Path(os.environ.get('JD_RESUME_TAILOR_APP_HOME') or '~/.config/jd-resume-tailor/app').expanduser()


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
    here = HERE.parent.parent / 'skills' / 'jd-resume-tailor'  # this repo's own skill comes first
    if (here / 'SKILL.md').exists():
        return here.resolve()
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
        for p in _config_paths(cfg):
            d = p if p.is_dir() else p.parent
            if d.exists() and d != Path.home():
                dirs.append(d)
    out = []
    for d in dirs:
        if d.exists() and d not in out:
            out.append(d)
    return out


def _config_paths(cfg) -> list:
    tc = tailor_config_path(cfg)
    if not tc.exists():
        return []
    text = '\n'.join(l for l in tc.read_text().splitlines() if not re.search(r'track|notion|obsidian|spreadsheet|投递', l, re.I))
    out = []
    for m in re.findall(r'(~/[^\s`\'")\]]+|(?<![\w:/.])/[\w.~-][^\s`\'")\]]*)', text):  # not URLs
        p = Path(m.rstrip('.,;:')).expanduser()
        try:
            rel = p.relative_to(Path.home())
            if any(part.startswith('.') and part != '.config' for part in rel.parts):
                continue  # never agent settings or memory
        except ValueError:
            pass
        out.append(p)
    return out


def bank_files(cfg) -> list:
    """The files your jd-resume-tailor config names (bullet bank, build script): backed up before every writer run."""
    out = []
    for p in _config_paths(cfg):
        if p.is_file() and p.suffix in ('.py', '.toml', '.md', '.json', '.yaml', '.yml', '.tex') and p.stat().st_size < 4_000_000 and p not in out:
            out.append(p)
    return out


def snapshot_bank(job, cfg):
    """Copy the bank files into the job folder once per run, before the writer touches them."""
    d = job.d / 'bank_backup'
    if d.exists():
        shutil.rmtree(d)
    d.mkdir()
    index = []
    for i, f in enumerate(bank_files(cfg)):
        dst = d / f'{i}_{f.name}'
        shutil.copy2(f, dst)
        index.append({'src': str(f), 'copy': dst.name})
    write_json(d / 'index.json', index)
    return index


def bank_diff(job) -> str:
    """What the writer changed in your bank files during this run, as a unified diff."""
    d = job.d / 'bank_backup'
    out = []
    for e in read_json(d / 'index.json', []) or []:
        src, old = Path(e['src']), d / e['copy']
        new = src.read_text(errors='replace').splitlines(keepends=True) if src.exists() else []
        out += difflib.unified_diff(old.read_text(errors='replace').splitlines(keepends=True), new,
                                    fromfile=f'{src} (before this run)', tofile=str(src))
    return ''.join(out)


def restore_bank(job) -> list:
    """Put the bank files back as they were before this run (the current versions are kept next to the backup)."""
    d = job.d / 'bank_backup'
    done = []
    for e in read_json(d / 'index.json', []) or []:
        src = Path(e['src'])
        if src.exists():
            shutil.copy2(src, d / f'replaced_{time.strftime("%H%M%S")}_{e["copy"]}')
        shutil.copy2(d / e['copy'], src)
        done.append(str(src))
    return done


# ---------------------------------------------------------------- your projects

GH_REPO = re.compile(r'^(?:https?://)?github\.com/([A-Za-z0-9-]{1,39})/([A-Za-z0-9._-]{1,100}?)(?:\.git)?/?$')
GH_USER = re.compile(r'^(?:github:|(?:https?://)?github\.com/)([A-Za-z0-9-]{1,39})/?$')


def parse_source(src: str):
    """('dir', Path) | ('repo', owner, name) | ('user', login), or None."""
    src = (src or '').strip()
    if not src:
        return None
    m = GH_REPO.match(src)
    if m:
        return ('repo', m.group(1), m.group(2))
    m = GH_USER.match(src)
    if m:
        return ('user', m.group(1))
    p = Path(src).expanduser()
    if p.is_absolute() and p.is_dir():
        return ('dir', p.resolve())
    return None


def _git(*args, cwd=None, timeout=180):
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)


def fetch_repo(owner: str, name: str, log=None) -> Path:
    """A shallow, read-only copy of a GitHub repo under ~/.config/jd-resume-tailor/app/repos (pulled if it exists).
    Uses gh's login when gh is installed, so your private repos work too."""
    d = home() / 'repos' / f'{owner}__{name}'
    try:
        if (d / '.git').exists():
            _git('pull', '--ff-only', '--depth', '1', cwd=d)
        else:
            d.parent.mkdir(parents=True, exist_ok=True)
            if shutil.which('gh'):
                p = subprocess.run(['gh', 'repo', 'clone', f'{owner}/{name}', str(d), '--', '--depth', '1'],
                                   capture_output=True, text=True, timeout=180)
            else:
                p = _git('clone', '--depth', '1', f'https://github.com/{owner}/{name}.git', str(d))
            if p.returncode and log:
                log(f'could not clone {owner}/{name}: {p.stderr.strip()[-200:]}')
    except (OSError, subprocess.TimeoutExpired) as e:
        if log:
            log(f'could not fetch {owner}/{name}: {e}')
    return d


def user_repos(login: str, limit=20) -> list:
    """Public, non-fork, non-archived repos of a GitHub user, most recently pushed first."""
    url = f'https://api.github.com/users/{login}/repos?per_page=100&sort=pushed'
    req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'jd-resume-tailor'})
    with urllib.request.urlopen(req, timeout=30) as r:
        items = json.loads(r.read())
    return [x['name'] for x in items if not x.get('fork') and not x.get('archived')][:limit]


def project_dirs(cfg, log=None) -> list:
    out = []
    for src in cfg.get('projects', []):
        s = parse_source(src)
        if not s:
            continue
        if s[0] == 'dir':
            out.append(s[1])
        elif s[0] == 'repo':
            out.append(fetch_repo(s[1], s[2], log))
        else:
            try:
                for name in user_repos(s[1]):
                    out.append(fetch_repo(s[1], name, log))
            except OSError as e:
                if log:
                    log(f'could not list github:{s[1]}: {e}')
    seen, res = set(), []
    for d in out:
        if d.exists() and d not in seen:
            seen.add(d)
            res.append(d)
    return res


CODE_EXT = {'.py': 'Python', '.go': 'Go', '.ts': 'TypeScript', '.tsx': 'TypeScript', '.js': 'JavaScript', '.jsx': 'JavaScript',
            '.java': 'Java', '.kt': 'Kotlin', '.swift': 'Swift', '.rs': 'Rust', '.cpp': 'C++', '.cc': 'C++', '.c': 'C',
            '.rb': 'Ruby', '.cs': 'C#', '.scala': 'Scala', '.sql': 'SQL', '.ipynb': 'Jupyter'}
SKIP_DIRS = {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'dist', 'build', '.next', 'target', 'vendor'}


def describe_project(d: Path, bank_text: str) -> str:
    langs = {}
    n = 0
    for root, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith('.')]
        for f in files:
            lang = CODE_EXT.get(Path(f).suffix.lower())
            if lang:
                langs[lang] = langs.get(lang, 0) + 1
            n += 1
            if n > 5000:
                break
    readme = next((d / f for f in ('README.md', 'README.rst', 'README.txt', 'README', 'readme.md') if (d / f).exists()), None)
    summary = ''
    if readme:
        lines = [l.strip() for l in readme.read_text(errors='replace').splitlines()]
        lines = [l for l in lines if l and not l.startswith(('![', '<', '[!', '```', '|', '---'))]
        summary = ' '.join(lines[:4])[:300]
    p = _git('log', '-1', '--format=%cs', cwd=d, timeout=20) if (d / '.git').exists() else None
    last = p.stdout.strip() if p and p.returncode == 0 else ''
    evidence = [f for f in ('BENCHMARK.md', 'RESULTS.md', 'results', 'benchmarks', 'bench', 'eval', 'docs') if (d / f).exists()]
    name = d.name.split('__')[-1]
    on_resume = 'yes' if re.search(r'(?<![A-Za-z0-9])' + re.escape(name) + r'(?![A-Za-z0-9])', bank_text, re.I) else 'no'
    top = ', '.join(f'{k} ({v})' for k, v in sorted(langs.items(), key=lambda x: -x[1])[:4]) or 'no code files found'
    return (f'### {name}\n- path: {d}\n- in my bank already: {on_resume}\n- languages: {top}\n'
            f'- last commit: {last or "unknown"}\n- evidence files: {", ".join(evidence) or "none"}\n- README: {summary or "(none)"}\n')


def project_index(dirs, cfg) -> str:
    bank = ''
    tc = tailor_config_path(cfg)
    for d in reading_dirs(cfg):
        if d in (skill_dir().parent.parent if skill_dir() else None,):
            continue
        for f in list(d.glob('*.toml'))[:5] + list(d.glob('*.py'))[:5] + list(d.glob('*.md'))[:5]:
            try:
                bank += f.read_text(errors='replace')[:200000]
            except OSError:
                pass
    if tc.exists():
        bank += tc.read_text()
    return '\n'.join(describe_project(d, bank) for d in dirs)


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
        out.append({'id': aid, 'name': a['name'], 'found': found, 'ready': ready, 'note': note, 'models': a['models']})
    return out


def build_command(agent: str, prompt: str, cwd: Path, writing: bool, cfg: dict, session=None, stream=False):
    """The command line and environment for one unattended run."""
    env = dict(os.environ)
    if cfg.get('tailor_config'):
        env['JD_RESUME_TAILOR_CONFIG'] = str(Path(cfg['tailor_config']).expanduser())
    over = cfg.get('agents', {}).get(agent, {})
    if over.get('command'):  # tests, or your own wrapper
        fill = lambda s: s.replace('{prompt}', prompt).replace('{cwd}', str(cwd)).replace('{mode}', 'write' if writing else 'review')
        return [fill(x) for x in over['command']], env
    repos = [str(d) for d in cfg.get('_project_dirs', [])] if writing else []
    dirs = ([str(d) for d in reading_dirs(cfg)] + repos) if writing else []
    if agent in ('claude', 'deepseek'):
        tools = 'Bash Read Write Edit Glob Grep Skill' if writing else 'Read Glob Bash(pdftotext:*)'
        cmd = ['claude', '-p', prompt, '--allowedTools', tools,
               '--max-budget-usd', str(cfg.get('max_budget_usd', 4))]
        cmd += ['--output-format', 'stream-json', '--verbose'] if stream else ['--output-format', 'json']
        if writing:
            cmd += ['--permission-mode', 'acceptEdits']
        for d in dirs:
            cmd += ['--add-dir', d]
        deny = []
        if writing:
            # The JD comes from a web page. Even if one hides instructions, the writer can't reach the network
            # through the usual tools or read keys and credentials.
            deny += ['WebFetch', 'WebSearch', *[f'Bash({c}:*)' for c in
                    ('curl', 'wget', 'nc', 'ncat', 'ssh', 'scp', 'sftp', 'rsync', 'ftp', 'telnet', 'open', 'osascript', 'security')],
                    *[f'Read({p})' for p in ('~/.ssh/**', '~/.aws/**', '~/.gnupg/**', '~/.config/gcloud/**', '~/.netrc',
                                              '~/.claude.json', '~/.codex/**', '~/.grok/**', '**/.env', '**/.env.*')],
                     f'Read(/{home() / "config.json"})', f'Edit(/{home() / "config.json"})']  # may hold your DeepSeek key
        if repos:  # your project repos are evidence to read, never to change
            deny += [f'{t}(/{r}/**)' for r in repos for t in ('Edit', 'Write')]
        if deny:
            cmd += ['--disallowedTools', *deny]
        if session:
            cmd += ['--resume', session]
        model = model_for(agent, writing, cfg)
        if agent == 'claude' and model:
            cmd += ['--model', model]
        if agent == 'deepseek':
            # DeepSeek's documented setup for Claude Code (api-docs.deepseek.com, "Integrate with Claude Code").
            for k in ('ANTHROPIC_API_KEY', 'CLAUDE_CODE_OAUTH_TOKEN'):
                env.pop(k, None)
            m = model or 'deepseek-v4-pro'
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
        if model_for(agent, writing, cfg):
            cmd += ['-m', model_for(agent, writing, cfg)]
        return cmd + [prompt], env
    if agent == 'grok':
        cmd = ['grok', '--no-auto-update', '-p', prompt, '--cwd', str(cwd), '--output-format', 'json', '--always-approve']
        if session:
            cmd += ['--resume', session]
        if model_for(agent, writing, cfg):
            cmd += ['-m', model_for(agent, writing, cfg)]
        return cmd, env
    raise ValueError(f'unknown agent "{agent}"')


def activity(event: dict):
    """A few words on what a Claude Code stream-json event is doing, or None."""
    if event.get('type') != 'assistant':
        return None
    for b in (event.get('message') or {}).get('content') or []:
        if b.get('type') != 'tool_use':
            continue
        name, inp = b.get('name', ''), b.get('input') or {}
        if name == 'Bash':
            c = inp.get('description') or inp.get('command', '')
            return 'Running: ' + c.strip().splitlines()[0][:90] if c else 'Running a command'
        if name in ('Read', 'Write', 'Edit'):
            f = Path(inp.get('file_path', '')).name
            return {'Read': 'Reading', 'Write': 'Writing', 'Edit': 'Editing'}[name] + (f' {f}' if f else '')
        if name == 'Skill':
            return 'Loading the jd-resume-tailor skill'
        if name in ('Glob', 'Grep'):
            return 'Looking through files'
        return name
    return None


def run_agent(agent: str, prompt: str, cwd: Path, writing: bool, cfg: dict, log: Path, session=None, on_activity=None) -> dict:
    over = cfg.get('agents', {}).get(agent, {})
    stream = agent in ('claude', 'deepseek') and not over.get('command') or bool(over.get('stream'))
    cmd, env = build_command(agent, prompt, cwd, writing, cfg, session, stream)
    t0 = time.time()
    timeout = int(cfg.get('timeout_minutes', 25)) * 60
    final = None
    try:
        p = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, start_new_session=False)
        killer = threading.Timer(timeout, p.kill)
        killer.start()
        err_chunks = []
        t_err = threading.Thread(target=lambda: err_chunks.append(p.stderr.read()), daemon=True)
        t_err.start()
        lines, last_note = [], 0.0
        for line in p.stdout:
            lines.append(line)
            if stream and line.startswith('{'):
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                if ev.get('type') == 'result':
                    final = ev
                note = activity(ev)
                if note and on_activity and time.time() - last_note > 1.5:
                    on_activity(note)
                    last_note = time.time()
        code = p.wait()
        killer.cancel()
        t_err.join(5)
        out, err = ''.join(lines), ''.join(err_chunks)
        if code < 0 and time.time() - t0 >= timeout - 1:
            err = f'timed out after {timeout // 60} minutes\n' + err
    except OSError as e:
        out, err, code = '', str(e), -1
    with open(log, 'a') as f:
        f.write(f'\n===== {now()} {agent} {"write" if writing else "review"} in {cwd.name} (exit {code}, {time.time() - t0:.0f}s)\n')
        f.write(out[-40000:])
        if err.strip():
            f.write('\n--- stderr\n' + err[-5000:])
    res = {'ok': code == 0, 'text': out, 'session': None, 'cost': None, 'error': '' if code == 0 else (err.strip() or out.strip())[-400:]}
    j = final
    if j is None:
        try:
            j = json.loads(out)
        except ValueError:
            j = None
    if isinstance(j, dict):
        res['text'] = j.get('result') or j.get('text') or ''
        res['session'] = j.get('session_id') or j.get('sessionId')
        res['cost'] = j.get('total_cost_usd')
        if j.get('is_error'):
            res['ok'], res['error'] = False, str(j.get('result') or j.get('subtype') or 'agent error')[-400:]
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
        self.lock = threading.RLock()  # the two reviewers report at the same time

    def save(self):
        with self.lock:
            self.state['updated'] = now()
            write_json(self.d / 'state.json', self.state)

    def stage(self, key, label, status='running', detail=''):
        with self.lock:
            st = self.state.setdefault('stages', [])
            for s in st:
                if s['key'] == key:
                    break
            else:  # a new stage goes before the ones still to do
                at = next((i for i, x in enumerate(st) if x['status'] == 'todo'), len(st))
                s = {'key': key}
                st.insert(at, s)
            if status == 'running' and s.get('status') != 'running':
                s['started'] = time.time()
            if status in ('done', 'failed') and s.get('started'):
                s['seconds'] = round(time.time() - s['started'])
            s.update({'label': label, 'status': status, 'detail': detail})
            if status == 'running':
                self.state['stage'] = key
            self.save()

    def activity(self, key):
        """A callback that shows what the agent is doing under this stage."""
        def note(text):
            with self.lock:
                for s in self.state.get('stages', []):
                    if s['key'] == key and s['status'] == 'running':
                        s['detail'] = text
                        self.save()
        return note

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
        'writer_model': model_for(writer, True, cfg), 'reviewer_model': model_for(writer if reviewer == 'same' else reviewer, False, cfg),
        'mode': cfg.get('mode', 'quick'),
        'status': 'queued', 'stage': '', 'stages': [], 'created': old.get('created') or now(), 'updated': now(),
        'started': '', 'finished': '', 'error': '', 'session': None, 'cost': 0, 'pid': None,
    })
    for f in ('result.json', 'writer.json'):
        (d / f).unlink(missing_ok=True)
    return jid


_CHILDREN = []  # processes a long-running `web` server started: reaped, so finished ones don't linger as zombies
_CHILDREN_LOCK = threading.Lock()


def _track(p):
    with _CHILDREN_LOCK:
        _CHILDREN[:] = [c for c in _CHILDREN if c.poll() is None] + [p]


def reap_children():
    with _CHILDREN_LOCK:
        _CHILDREN[:] = [c for c in _CHILDREN if c.poll() is None]


def spawn_worker(jid: str):
    d = job_path(jid)
    log = open(d / 'worker.log', 'a')
    p = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'work', str(d)],
                         stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True, cwd=str(d))
    log.close()
    _track(p)
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
        res = run_agent(st['reviewer'], prompt, r, False, cfg, job.d / 'agent.log', on_activity=job.activity(f'{kind}{rnd}'))
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
    before = read_json(job.d / 'writer.json', {}) or {}
    # One writer at a time: two jobs editing the same bank file would overwrite each other.
    lockf = open(home() / 'writer.lock', 'w')
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        job.stage(key, label, 'running', 'waiting for another job to finish writing')
        fcntl.flock(lockf, fcntl.LOCK_EX)
        job.stage(key, label, 'running', st['writer'])
    try:
        res = run_agent(st['writer'], prompt, job.d, True, cfg, job.d / 'agent.log', session, on_activity=job.activity(key))
    finally:
        fcntl.flock(lockf, fcntl.LOCK_UN)
        lockf.close()
    diff = bank_diff(job)
    (job.d / 'bank_changes.diff').write_text(diff)
    st['bank_changed'] = bool(diff)
    if (job.d / 'resume.pdf').exists():  # keep every draft, so you (and the demo) can compare them
        v = job.d / 'versions'
        v.mkdir(exist_ok=True)
        n = len(list(v.glob('*.pdf'))) + 1
        shutil.copy2(job.d / 'resume.pdf', v / f'{n}_{key}.pdf')
        if (job.d / 'resume_source.md').exists():
            shutil.copy2(job.d / 'resume_source.md', v / f'{n}_{key}.md')
    if res['session']:
        st['session'] = res['session']
    st['cost'] = (st.get('cost') or 0) + (res['cost'] or 0)
    w = read_json(job.d / 'writer.json', {}) or {}
    if 'new_from_projects' not in w and before.get('new_from_projects'):  # a revision that didn't restate them
        w['new_from_projects'] = before['new_from_projects']
        write_json(job.d / 'writer.json', w)
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


PROJECTS_NOTE = """
## My projects, including ones not on my resume

./projects.md lists my project folders: languages, README summary, last commit, whether my bank already has it. If a project there proves this JD's hard requirements or "what the team builds" better than what my bank has, you may add it:
- Read its README, any results/benchmark files and the code itself. These folders are read-only: never change anything in them.
- Write bullets only from facts you verified in those files. Every number must appear in a file there (a README, a results file, a test, a config), never estimated. If a result was never measured, describe what was built, without a number.
- Add the project and its bullets to my bank as the skill says (back the bank up first; targeted edits), with a comment naming the source file for each fact, and use them in this variant.
- List every bullet you added under "new_from_projects" in writer.json, so I can check each one.
"""


def flow(job: Job, cfg: dict):
    st = job.state
    st.update(status='running', started=now(), error='', stages=[], cost=0, pid=os.getpid())
    if (job.d / 'versions').exists():
        shutil.rmtree(job.d / 'versions')
    job.save()
    job.plan([('write', 'Analysis and first draft'), ('check', 'Script checks'), ('hm1', 'Hiring manager review 1'),
              ('ats1', 'ATS review 1'), ('revise1', 'Revise after round 1'), ('gate', 'Gate')])
    snapshot_bank(job, cfg)
    answers = (job.d / 'my_answers.md').read_text() if (job.d / 'my_answers.md').exists() else ''
    if answers:
        answers = '\nMy answers to your earlier questions (they decide what you asked):\n' + answers + '\n'
    projects = ''
    if cfg.get('projects'):
        job.stage('projects', 'Reading your project repos', 'running', ', '.join(cfg['projects'])[:200])
        notes = []
        dirs = project_dirs(cfg, notes.append)
        cfg['_project_dirs'] = dirs
        (job.d / 'projects.md').write_text(project_index(dirs, cfg))
        job.stage('projects', 'Reading your project repos', 'done',
                  f'{len(dirs)} projects' + (f'; {"; ".join(notes)}' if notes else ''))
        projects = PROJECTS_NOTE
    w = write_run(job, cfg, fmt('writer.md', jobdir=job.d, company=st['company'], title=st['title'], url=st['url'],
                                answers=answers, check=f'python3 {CHECK}', projects=projects), 'write', 'Analysis and first draft')
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

    # Quick mode stops after round 1. Thorough mode, per the flow:
    # round 2 HM if round 1 wasn't a yes, or the revision touched a hard-requirement bullet or 3+ bullets;
    # round 2 ATS only if round 1 failed; round 3 HM only if round 2 said no (applied, not re-reviewed).
    kinds = []
    if cfg.get('mode', 'quick') != 'quick':
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
        'new_from_projects': info.get('new_from_projects', []),
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
    out = {k: st.get(k) for k in ('id', 'url', 'company', 'title', 'writer', 'reviewer', 'writer_model', 'reviewer_model', 'mode', 'status', 'stage', 'stages',
                                  'created', 'updated', 'started', 'finished', 'error', 'cost', 'result')}
    out['folder'] = str(d)
    out['has_pdf'] = (d / 'resume.pdf').exists()
    out['bank_changed'] = bool(st.get('bank_changed'))  # the first draft can be opened before the reviews finish
    out['now'] = time.time()
    return out


def handle(msg: dict) -> dict:
    cmd = msg.get('cmd')
    cfg = load_config()
    if cmd == 'hello':
        s = skill_dir()
        return {'ok': True, 'version': VERSION, 'home': str(home()), 'agents': agent_status(cfg),
                'writer': cfg['writer'], 'reviewer': cfg['reviewer'], 'mode': cfg['mode'],
                'writer_model': cfg['writer_model'], 'reviewer_model': cfg['reviewer_model'], 'projects': cfg['projects'],
                'skill': str(s) if s else '',
                'tailor_config': str(tailor_config_path(cfg)) if tailor_config_path(cfg).exists() else '',
                'poppler': bool(shutil.which('pdftotext'))}
    if cmd == 'settings':
        allowed = {'writer', 'reviewer', 'mode', 'writer_model', 'reviewer_model', 'deepseek_key'}
        patch = {k: v for k, v in (msg.get('set') or {}).items() if k in allowed and isinstance(v, str)}
        for k in ('writer_model', 'reviewer_model'):
            if k in patch and not re.fullmatch(r'[A-Za-z0-9._:\[\]/-]{0,80}', patch[k]):
                return {'ok': False, 'error': 'that does not look like a model name'}
        # a new agent starts on its own best model
        if 'writer' in patch and patch['writer'] != cfg['writer'] and 'writer_model' not in patch:
            patch['writer_model'] = ''
        if 'reviewer' in patch and patch['reviewer'] != cfg['reviewer'] and 'reviewer_model' not in patch:
            patch['reviewer_model'] = ''
        if patch.get('mode') and patch['mode'] not in ('quick', 'thorough'):
            return {'ok': False, 'error': 'mode is quick or thorough'}
        if patch.get('writer') and patch['writer'] not in AGENTS:
            return {'ok': False, 'error': 'unknown agent'}
        if patch.get('reviewer') and patch['reviewer'] not in list(AGENTS) + ['same']:
            return {'ok': False, 'error': 'unknown agent'}
        if isinstance((msg.get('set') or {}).get('projects'), list):
            items = [str(x).strip() for x in msg['set']['projects'] if str(x).strip()][:30]
            bad = [x for x in items if not parse_source(x)]
            if bad:
                return {'ok': False, 'error': 'not a folder, GitHub repo URL or github:<user>: ' + ', '.join(bad)}
            patch['projects'] = items
        cfg = save_config(patch)
        return {'ok': True, 'projects': cfg['projects'], 'writer': cfg['writer'], 'reviewer': cfg['reviewer'], 'mode': cfg['mode'],
                'writer_model': cfg['writer_model'], 'reviewer_model': cfg['reviewer_model'], 'agents': agent_status(cfg)}
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
    if cmd == 'restore_bank':  # undo what this job's writer changed in your bank
        d = job_path(msg.get('id', ''))
        st = read_json(d / 'state.json', {}) or {}
        if st.get('status') in ('running', 'queued') and alive(st.get('pid')):
            return {'ok': False, 'error': 'stop the run first'}
        files = restore_bank(Job(d))
        st['bank_changed'] = False
        write_json(d / 'state.json', st)
        (d / 'bank_changes.diff').write_text('')
        return {'ok': True, 'restored': files}
    if cmd == 'reset':  # stop it and move the job aside, so this posting can start fresh
        d = job_path(msg.get('id', ''))
        st = read_json(d / 'state.json', {}) or {}
        if alive(st.get('pid')):
            try:
                os.killpg(st['pid'], signal.SIGTERM)
            except OSError:
                pass
        if d.exists():
            trash = jobs_dir().parent / 'trash'
            trash.mkdir(exist_ok=True)
            shutil.move(str(d), str(trash / f'{d.name}_{time.strftime("%Y%m%d-%H%M%S")}'))
        return {'ok': True}
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
        _track(subprocess.Popen(opener, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        return {'ok': True}
    if cmd == 'review':  # read one review or the analysis, for the panel
        d = job_path(msg.get('id', ''))
        name = msg.get('name', '')
        if not re.fullmatch(r'(review_(hm|ats)_\d|analysis|notes|bank_changes)', name):
            return {'ok': False, 'error': 'bad name'}
        p = d / (f'{name}.diff' if name == 'bank_changes' else f'{name}.md')
        return {'ok': True, 'text': p.read_text()[:60000] if p.exists() else ''}
    if cmd == 'fetch_url':  # the web UI's "Fetch": read the JD from a posting link
        return fetch_url(msg.get('url', ''))
    return {'ok': False, 'error': f'unknown command {cmd!r}'}


# ---------------------------------------------------------------- a posting link -> its JD (for the web UI)

NOT_COMPANY = {'www', 'careers', 'career', 'jobs', 'job', 'apply', 'boards', 'job-boards', 'about', 'work', 'join', 'hire',
               'com', 'io', 'co', 'net', 'org', 'ai', 'app', 'dev', 'us', 'uk', 'greenhouse', 'lever', 'ashbyhq',
               'myworkdayjobs', 'smartrecruiters', 'oraclecloud', 'workable', 'jobvite', 'icims', 'recruitee'}


def company_from_url(url: str) -> str:
    """A best guess at the company from a posting link (the board's name, or the site's domain). You can edit it."""
    u = urllib.parse.urlsplit(url)
    host = (u.hostname or '').lower()
    parts = [x for x in u.path.split('/') if x]
    guess = ''
    q = urllib.parse.parse_qs(u.query)
    if host.endswith('greenhouse.io'):
        guess = (q.get('for') or [''])[0] or (parts[0] if parts and parts[0] not in ('embed',) else '')
    elif host.endswith(('ashbyhq.com', 'lever.co', 'smartrecruiters.com')) and parts:
        guess = parts[0]
    elif host.endswith('myworkdayjobs.com'):
        guess = host.split('.')[0]
    else:
        guess = next((x for x in reversed(host.split('.')[:-1]) if x not in NOT_COMPANY), '')
    guess = re.sub(r'[^A-Za-z0-9 &.-]', '', urllib.parse.unquote(guess)).strip()[:60]
    if not guess or guess.isdigit():
        return ''
    return guess.replace('-', ' ').title() if guess.islower() else guess


def fetch_url(url: str) -> dict:
    """Run the skill's fetch_jd.py on a posting link: {ok, job: {url, title, company, location, text}} or {ok: False, error}."""
    url = (url or '').strip()
    u = urllib.parse.urlsplit(url)
    if u.scheme not in ('http', 'https') or not u.hostname or len(url) > 2000:
        return {'ok': False, 'error': 'Paste the posting\'s link, starting with https://'}
    s = skill_dir()
    script = s / 'fetch_jd.py' if s else None
    if not script or not script.exists():
        return {'ok': False, 'error': 'fetch_jd.py was not found (it comes with the jd-resume-tailor skill). Paste the job description instead.'}
    try:
        p = subprocess.run([sys.executable, str(script), url, '--json'], capture_output=True, text=True, timeout=60,
                           stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': 'The posting took too long to load. Paste the job description instead.'}
    except OSError as e:
        return {'ok': False, 'error': f'Could not run fetch_jd.py: {e}'}
    if p.returncode == 2:
        return {'ok': False, 'closed': True, 'error': 'That posting is closed or no longer exists.'}
    if p.returncode != 0:
        why = re.sub(r'^error:\s*', '', (p.stderr.strip().splitlines() or ['unknown error'])[-1])[:200]
        return {'ok': False, 'error': f'Could not read that page ({why}). Paste the job description instead.'}
    try:
        data = json.loads(p.stdout)
    except ValueError:
        return {'ok': False, 'error': 'fetch_jd.py gave an answer that is not JSON. Paste the job description instead.'}
    text = (data.get('text') or '').strip()
    if len(text) < 200:
        return {'ok': False, 'error': 'That page has no job description we can read (it may need JavaScript). Paste the job description instead.'}
    final = data.get('url') or url
    return {'ok': True, 'job': {'url': final, 'title': (data.get('title') or '').strip()[:200],
                                'company': company_from_url(final) or company_from_url(url),
                                'location': (data.get('location') or '').strip()[:200], 'text': text[:100000],
                                'ats': data.get('ats') or ''}}


# ---------------------------------------------------------------- the local web UI

WEB = HERE.parent / 'web'
EXT = HERE.parent / 'extension'
JS, CSS = 'text/javascript; charset=utf-8', 'text/css; charset=utf-8'
STATIC = {  # a fixed list: nothing else on disk can be served
    '/': (WEB / 'index.html', 'text/html; charset=utf-8'),
    '/index.html': (WEB / 'index.html', 'text/html; charset=utf-8'),
    '/web.js': (WEB / 'web.js', JS),
    '/web.css': (WEB / 'web.css', CSS),
    '/panel.css': (EXT / 'panel.css', CSS),
    '/lib/ui.js': (EXT / 'lib' / 'ui.js', JS),
    '/icons/32.png': (EXT / 'icons' / '32.png', 'image/png'),
    '/favicon.ico': (EXT / 'icons' / '32.png', 'image/png'),
}
CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; "
       "object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
MAX_BODY = 1_000_000
WEB_PORTS = range(8790, 8800)


class WebHandler(http.server.BaseHTTPRequestHandler):
    """POST /api: one handle() message as JSON. GET /pdf?id=&t=: a job's PDF. GET /: the UI.
    Every request: Host must be 127.0.0.1:PORT or localhost:PORT, and an Origin, if sent, must be this server.
    /api and /pdf also need the key (X-JDRT-Token header, or t= for /pdf), compared in constant time."""
    server_version = 'jd-resume-tailor'
    sys_version = ''

    def log_message(self, fmt_, *args):
        if os.environ.get('JDRT_WEB_LOG'):
            sys.stderr.write('%s %s\n' % (self.address_string(), fmt_ % args))

    def _send(self, code, body: bytes, ctype: str, extra=None):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj).encode(), 'application/json')

    def _refuse(self, code, why, auth=False):
        self.close_connection = True
        self._json(code, {'ok': False, 'error': why, **({'auth': True} if auth else {})})

    def _guard(self) -> bool:
        """DNS rebinding and cross-site requests stop here, before anything else is looked at."""
        port = self.server.server_address[1]
        host = (self.headers.get('Host') or '').strip().lower()
        if host not in (f'127.0.0.1:{port}', f'localhost:{port}'):
            self._refuse(403, 'wrong Host header')
            return False
        origin = self.headers.get('Origin')
        if origin is not None and origin not in (f'http://127.0.0.1:{port}', f'http://localhost:{port}'):
            self._refuse(403, 'requests from other sites are refused')
            return False
        return True

    def _key(self, given: str) -> bool:
        if not given:
            self._refuse(401, 'missing key: open the link that "jdrt web" printed', auth=True)
            return False
        if not hmac.compare_digest(given.encode('utf-8', 'replace'), self.server.token.encode()):
            self._refuse(403, 'wrong key: open the link that "jdrt web" printed (it changes each time it starts)', auth=True)
            return False
        if self.headers.get('Sec-Fetch-Site', 'same-origin') not in ('same-origin', 'none'):
            self._refuse(403, 'requests from other sites are refused')
            return False
        return True

    def do_GET(self):
        if not self._guard():
            return
        u = urllib.parse.urlsplit(self.path)
        if u.path == '/pdf':
            return self._pdf(urllib.parse.parse_qs(u.query))
        f = STATIC.get(u.path)
        if not f or not f[0].exists():
            return self._json(404, {'ok': False, 'error': 'not found'})
        self._send(200, f[0].read_bytes(), f[1], {'Content-Security-Policy': CSP} if f[1].startswith('text/html') else None)

    def _pdf(self, q):
        if not self._key((q.get('t') or [''])[0]):
            return
        try:
            p = job_path((q.get('id') or [''])[0]) / 'resume.pdf'
        except ValueError:
            return self._json(400, {'ok': False, 'error': 'bad job id'})
        if not p.exists():
            return self._json(404, {'ok': False, 'error': 'no PDF yet'})
        how = 'attachment' if q.get('download') else 'inline'
        self._send(200, p.read_bytes(), 'application/pdf', {'Content-Disposition': f'{how}; filename="Resume.pdf"'})

    def do_POST(self):
        if not self._guard():
            return
        if urllib.parse.urlsplit(self.path).path != '/api':
            return self._refuse(404, 'not found')
        if not self._key(self.headers.get('X-JDRT-Token', '')):
            return
        if (self.headers.get('Content-Type') or '').split(';')[0].strip().lower() != 'application/json':
            return self._refuse(415, 'send JSON')
        try:
            n = int(self.headers.get('Content-Length') or '')
        except ValueError:
            return self._refuse(411, 'Content-Length is required')
        if n > MAX_BODY:
            return self._refuse(413, 'too large')
        try:
            msg = json.loads(self.rfile.read(n) or b'null')
        except ValueError:
            return self._refuse(400, 'not JSON')
        if not isinstance(msg, dict):
            return self._refuse(400, 'send one JSON object')
        try:
            out = handle(msg)
        except Exception as e:  # the page shows it; the server keeps running
            out = {'ok': False, 'error': f'{type(e).__name__}: {e}'}
        self._json(200, out)

    def do_PUT(self):
        self._refuse(405, 'method not allowed')

    do_DELETE = do_PATCH = do_OPTIONS = do_PUT


class WebServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False  # a busy port means busy: no sharing it with another process
    allow_reuse_port = False


def make_web_server(port=None, token=None) -> WebServer:
    """Bind 127.0.0.1 only. port=None tries 8790-8799, then any free port; port=0 is any free port."""
    last = None
    for p in ([port] if port is not None else [*WEB_PORTS, 0]):
        try:
            srv = WebServer(('127.0.0.1', p), WebHandler)
            break
        except OSError as e:
            last = e
    else:
        raise last
    srv.token = token or secrets.token_urlsafe(24)
    return srv


def web_main(args):
    port, no_open = None, False
    it = iter(args)
    for a in it:
        if a == '--no-open':
            no_open = True
        elif a == '--port' or a.startswith('--port='):
            v = a.split('=', 1)[1] if '=' in a else next(it, '')
            if not v.isdigit() or int(v) > 65535:
                sys.exit('--port needs a number (0 = any free port)')
            port = int(v)
        else:
            sys.exit(f'unknown option {a}; use: jdt.py web [--port N] [--no-open]')
    try:
        srv = make_web_server(port)
    except OSError as e:
        sys.exit(f'could not listen on 127.0.0.1:{port}: {e.strerror or e}')
    url = f'http://127.0.0.1:{srv.server_address[1]}/#t={srv.token}'
    print(f'JD Resume Tailor is running at {url}', flush=True)
    print('Open that link in any browser on this computer. It holds a key that changes every start: don\'t share it.\n'
          'Keep this window open while you use it; Ctrl-C stops it (runs already started keep going).', flush=True)

    def reaper():
        while True:
            time.sleep(5)
            reap_children()
    threading.Thread(target=reaper, daemon=True).start()
    if not no_open:
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001  no browser: the printed link is enough
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\nstopped')
    finally:
        srv.server_close()


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


OLD_HOST_NAME = 'io.github.xungirl.jd_tailor'   # before the app moved into jd-resume-tailor
OLD_HOME = Path('~/.config/jd-tailor').expanduser()


def install(ext_ids=None):
    ext_ids = ext_ids or [EXT_ID]
    h = home()
    if OLD_HOME.exists() and not h.exists() and not os.environ.get('JD_RESUME_TAILOR_APP_HOME'):
        h.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(OLD_HOME), str(h))  # keep your earlier jobs and settings
        print(f'moved {OLD_HOME} to {h}')
    h.mkdir(parents=True, exist_ok=True)
    for d in manifest_dirs():
        (d / f'{OLD_HOST_NAME}.json').unlink(missing_ok=True)
    launcher = h / 'jdt-host'
    # Browsers start the host with a bare PATH: keep the one from install time, so claude/codex/grok are found.
    launcher.write_text('#!/bin/sh\n'
                        f'export PATH={json.dumps(os.environ.get("PATH", "/usr/bin:/bin"))}\n'
                        + (f'export JD_RESUME_TAILOR_APP_HOME={json.dumps(str(h))}\n' if os.environ.get('JD_RESUME_TAILOR_APP_HOME') else '')
                        + f'exec {json.dumps(sys.executable)} {json.dumps(str(Path(__file__).resolve()))} host "$@"\n')
    launcher.chmod(0o755)
    manifest = {'name': HOST_NAME, 'description': 'JD Resume Tailor local agent runner', 'path': str(launcher),
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
    print(f'JD Resume Tailor {VERSION}  data: {home()}')
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
    if a[0] == 'web':
        return web_main(a[1:])
    print(__doc__.strip())
    sys.exit(2)


if __name__ == '__main__':
    main()
