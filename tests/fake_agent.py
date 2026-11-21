#!/usr/bin/env python3
"""Stands in for claude/codex/grok in tests. Usage: fake_agent.py <mode> <prompt>.

Writer: writes analysis.md, resume.pdf, resume_source.md, notes.md, writer.json in its cwd.
HM review: "unsure" in round 1, "yes" later. ATS review: "pass". Reviews list the files they can see,
so the test can check that reviewers only get the JD and the resume.
If the JD contains SECURITY CLEARANCE, the writer stops with a question (needs_user), unless
my_answers.md exists.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_pdf import ANALYSIS, RESUME_LINES, make_pdf  # noqa: E402

mode, prompt = sys.argv[1], sys.argv[2]
cwd = Path.cwd()
role = prompt.split('\n', 1)[0].strip()
seen = sorted(p.name for p in cwd.iterdir() if not p.name.startswith('.'))

if role.startswith('ROLE: writer'):
    assert mode == 'write', mode
    jd = (cwd / 'jd.md').read_text()
    if 'SECURITY CLEARANCE' in jd and not (cwd / 'my_answers.md').exists() and 'revision' not in role:
        (cwd / 'writer.json').write_text(json.dumps({'status': 'needs_user', 'questions': ['The JD needs a security clearance. Do you hold one?'],
                                                     'summary': 'Stopped: clearance required.'}))
        print(json.dumps({'result': 'stopped', 'session_id': 'sess-1', 'total_cost_usd': 0.01}))
        sys.exit(0)
    (cwd / 'analysis.md').write_text(ANALYSIS)
    make_pdf(cwd / 'resume.pdf', RESUME_LINES)
    (cwd / 'resume_source.md').write_text('\n'.join(RESUME_LINES))
    (cwd / 'notes.md').write_text('Led with Trailmap.\n')
    revisions = len([l for l in (cwd / 'notes.md').read_text().splitlines()])
    (cwd / 'writer.json').write_text(json.dumps({
        'status': 'built', 'direction': 'backend', 'lead': 'Trailmap answers "route-planning API"',
        'dropped': ['Pixel Pets: off-topic'], 'gaps': ['Kubernetes'], 'constraints': ['No visa sponsorship'],
        'unverified_numbers': ['14 minutes to 2 minutes (self-reported)'], 'questions': [],
        'bullets_changed': 1 if 'revision' in role else 0, 'touched_hard_requirement': False,
        'summary': ('Revised: ' if 'revision' in role else '') + 'Backend resume led by Trailmap.'}))
    with open(cwd / 'calls.log', 'a') as f:
        f.write(role + ' | session=' + os.environ.get('FAKE_SESSION', '') + '\n')
    print(json.dumps({'result': 'built', 'session_id': 'sess-1', 'total_cost_usd': 0.05}))
elif role == 'ROLE: hm':
    assert mode == 'review', mode
    rnd = cwd.name.split('_')[-1]
    v = 'unsure' if rnd == '1' else 'yes'
    print(json.dumps({'result': f'files: {" ".join(seen)}\n1. Backend student.\n2. {v}\nVERDICT: {v}', 'session_id': 'r', 'total_cost_usd': 0.02}))
elif role == 'ROLE: ats':
    assert mode == 'review', mode
    print(json.dumps({'result': f'files: {" ".join(seen)}\n1. pass\nVERDICT: pass', 'session_id': 'r', 'total_cost_usd': 0.02}))
else:
    print('unknown role: ' + role, file=sys.stderr)
    sys.exit(3)
