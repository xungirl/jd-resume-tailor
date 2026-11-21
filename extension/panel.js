// JD Tailor panel: capture the JD here, run the agents on your computer through native messaging.
import { captureJob } from './lib/capture.js';

const HOST = 'io.github.xungirl.jd_tailor';
const $ = (id) => document.getElementById(id);
const ACTIVE = new Set(['queued', 'running']);
const STATUS = { queued: 'queued', running: 'running', ready: 'ready', needs_you: 'needs your call', needs_user: 'question for you',
  skip: 'not a fit', failed: 'failed', cancelled: 'stopped' };

let H = null;        // hello from the host: agents, settings
let tab = null;      // the job tab
let job = null;      // what Capture found
let shown = null;    // the job shown in the job card
let poll = null;
let busy = false;

// ---------- talking to the host ----------

function native(msg) {
  return new Promise((resolve) => {
    try {
      chrome.runtime.sendNativeMessage(HOST, msg, (res) => {
        const err = chrome.runtime.lastError;
        resolve(err ? { ok: false, error: err.message, noHost: /not found|forbidden|native/i.test(err.message) } : res || { ok: false, error: 'no answer' });
      });
    } catch (e) {
      resolve({ ok: false, error: String(e), noHost: true });
    }
  });
}

async function hello() {
  const r = await native({ cmd: 'hello' });
  const c = $('gear');
  if (!r.ok) {
    H = null;
    c.className = 'conn bad';
    $('connText').textContent = 'not connected';
    $('install').hidden = false;
    $('installErr').textContent = r.noHost ? '' : r.error;
    return false;
  }
  H = r;
  $('install').hidden = true;
  const w = r.agents.find((a) => a.id === r.writer);
  c.className = 'conn ' + (w && w.ready ? 'ok' : 'bad');
  $('connText').textContent = w ? w.name : 'no agent';
  renderAgents();
  return true;
}

function renderAgents() {
  const list = $('agentList');
  list.innerHTML = '';
  for (const a of H.agents) {
    const li = document.createElement('li');
    li.className = a.ready ? 'ok' : 'no';
    const b = document.createElement('b'); b.textContent = a.name;
    const n = document.createElement('span'); n.className = 'muted small'; n.textContent = a.note;
    li.append(b, n);
    list.appendChild(li);
  }
  const fill = (sel, value, same) => {
    sel.innerHTML = '';
    if (same) sel.add(new Option('Same as writer', 'same'));
    for (const a of H.agents) {
      const o = new Option(a.name + (a.ready ? '' : ' (not ready)'), a.id);
      o.disabled = !a.ready;
      sel.add(o);
    }
    sel.value = value;
  };
  fill($('writer'), H.writer, false);
  fill($('reviewer'), H.reviewer, true);
  const models = (sel, custom, agentId, value) => {
    const a = H.agents.find((x) => x.id === agentId) || { models: [] };
    sel.innerHTML = '';
    for (const [id, label] of a.models) sel.add(new Option(label, id));
    sel.add(new Option('Other model…', '__custom'));
    const known = a.models.some(([id]) => id === value);
    sel.value = known ? value : value ? '__custom' : a.models[0][0];
    custom.hidden = sel.value !== '__custom';
    if (!known && value) custom.value = value;
  };
  models($('writerModel'), $('writerCustom'), H.writer, H.writer_model);
  models($('reviewerModel'), $('reviewerCustom'), H.reviewer === 'same' ? H.writer : H.reviewer, H.reviewer_model);
  $('mode').value = H.mode || 'quick';
  if (document.activeElement !== $('projects')) $('projects').value = (H.projects || []).join('\n');
  $('dsBox').hidden = !H.agents.find((a) => a.id === 'deepseek' && a.found);
  const warn = [];
  if (!H.skill) warn.push('The jd-resume-tailor skill is not installed. Get it at github.com/xungirl/jd-resume-tailor.');
  if (!H.tailor_config) warn.push('jd-resume-tailor has no config yet. Run it once in Claude Code ("tailor my resume") so it learns where your bullet bank is.');
  if (!H.poppler) warn.push('poppler is missing, so the script checks can\'t read the PDF. Install it: brew install poppler');
  $('envWarn').hidden = !warn.length;
  $('envWarn').textContent = warn.join(' ');
  const rv = $('reviewer').value === 'same' ? H.writer : $('reviewer').value;
  const name = (id) => (H.agents.find((a) => a.id === id) || {}).name || id;
  const mlabel = (agentId, v) => { const a = H.agents.find((x) => x.id === agentId); const m = a && a.models.find(([id]) => id === (v || a.models[0][0])); return m ? m[1].replace(/ \(.*\)/, '') : v; };
  $('who').textContent = `Writer: ${name(H.writer)} ${mlabel(H.writer, H.writer_model) || ''} · Reviewers: ${name(rv)} ${mlabel(rv, H.reviewer_model) || ''} · ${H.mode === 'thorough' ? 'thorough' : 'quick'}`.replace(/ +·/g, ' ·');
}

async function saveSettings(patch) {
  const r = await native({ cmd: 'settings', set: patch });
  if (r.ok) await hello();
  else note(r.error, 'red');
  return r;
}

$('writer').onchange = () => saveSettings({ writer: $('writer').value });
$('reviewer').onchange = () => saveSettings({ reviewer: $('reviewer').value });
$('mode').onchange = () => saveSettings({ mode: $('mode').value });
$('saveProjects').onclick = async () => {
  const items = $('projects').value.split('\n').map((x) => x.trim()).filter(Boolean);
  const r = await native({ cmd: 'settings', set: { projects: items } });
  $('projMsg').textContent = r.ok ? `Saved ${r.projects.length}` : r.error;
  if (r.ok) await hello();
};
for (const role of ['writer', 'reviewer']) {
  const sel = $(role + 'Model'), custom = $(role + 'Custom');
  sel.onchange = () => {
    custom.hidden = sel.value !== '__custom';
    if (sel.value !== '__custom') saveSettings({ [role + '_model']: sel.value });
    else custom.focus();
  };
  custom.onchange = () => saveSettings({ [role + '_model']: custom.value.trim() });
}
$('saveDs').onclick = async () => {
  const k = $('dsKey').value.trim();
  if (!k) return;
  await saveSettings({ deepseek_key: k });
  $('dsKey').value = '';
};
$('gear').onclick = () => { if (H) $('agents').hidden = !$('agents').hidden; };
$('closeAgents').onclick = () => ($('agents').hidden = true);
$('retry').onclick = async () => { if (await hello()) loadPage(); };
$('copyCmd').onclick = async () => {
  await navigator.clipboard.writeText($('installCmd').textContent);
  $('copyCmd').textContent = 'Copied';
  setTimeout(() => ($('copyCmd').textContent = 'Copy'), 1500);
};

// ---------- the job page ----------

function note(text, kind = '') {
  const m = $('pageMsg');
  m.hidden = !text;
  m.className = 'alert' + (kind ? ' ' + kind : '');
  m.textContent = text;
}

async function activeTab() {
  const pinned = new URLSearchParams(location.search).get('tab'); // tests and pop-out windows
  if (pinned) return chrome.tabs.get(+pinned).catch(() => null);
  const [t] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  return t || null;
}
const isWeb = (t) => t && /^https?:/.test(t.url || '');

async function loadPage() {
  tab = await activeTab();
  if (!job || !tab || job.tabUrl !== tab.url) {
    job = null;
    $('jd').value = '';
    $('jdLen').textContent = '';
    $('pageTitle').textContent = isWeb(tab) ? (tab.title || tab.url) : 'Open a job posting';
    $('pageMeta').textContent = isWeb(tab) ? 'Press Capture JD to read the job description.' : '';
    note('');
  }
  refreshButtons();
  if (H && isWeb(tab)) {
    const r = await native({ cmd: 'find', url: tab.url });
    if (r.ok && r.job) showJob(r.job);
  }
  loadRecent();
}

function showJobInfo() {
  $('pageTitle').textContent = [job.company, job.title].filter(Boolean).join(' · ') || job.url;
  const words = (job.text.match(/\S+/g) || []).length;
  $('pageMeta').textContent = [job.location, `${words} words`, job.how && `read from ${job.how}`].filter(Boolean).join(' · ');
  $('jdLen').textContent = `(${words} words)`;
}

function refreshButtons() {
  $('capture').disabled = busy || !isWeb(tab);
  $('tailor').disabled = busy || !H || $('jd').value.trim().length < 200;
}

// How much a capture looks like a job description.
const JD_WORDS = /responsibilit|qualification|requirement|what you('|’)ll|you will|about the (role|team|program|job)|minimum|preferred|experience with|we('|’)re looking for/gi;
function score(r) {
  if (!r || !r.text) return 0;
  return (r.how === 'json-ld' ? 1e6 : 0) + ((r.text.match(JD_WORDS) || []).length * 1000) + Math.min(r.text.length, 20000);
}
const looksLikeJD = (r) => r && (r.how === 'json-ld' || (r.text.length >= 600 && (r.text.match(JD_WORDS) || []).length >= 2));

async function capture(target) {
  return (await chrome.scripting.executeScript({ target, func: captureJob })).map((x) => x.result).filter(Boolean);
}

function askAccess(origins, label) {
  note(`JD Tailor needs your OK to read ${label}.`, 'blue');
  const b = document.createElement('button');
  b.textContent = 'Allow'; b.className = 'primary small'; b.style.marginLeft = '8px';
  b.onclick = () => chrome.permissions.request({ origins: origins.map((o) => o + '/*') }).then((ok) => {
    if (!ok) return note('Not allowed. You can still paste the job description below.', 'red');
    note('');
    $('capture').click();
  });
  $('pageMsg').appendChild(b);
}

$('capture').onclick = async () => {
  tab = await activeTab();
  if (!isWeb(tab)) return;
  note('');
  const top = new URL(tab.url).origin;
  let best;
  try {
    best = (await capture({ tabId: tab.id }))[0];
  } catch (e) {
    return askAccess([top], new URL(tab.url).hostname);
  }
  if (!looksLikeJD(best) && best && best.frames && best.frames.length) {
    // The posting is probably in an embedded frame: read every frame we may read and keep the best.
    try {
      for (const r of await capture({ tabId: tab.id, allFrames: true })) if (score(r) > score(best)) best = { ...r, url: best.url, frames: best.frames };
    } catch (e) { /* frames we can't read yet */ }
    if (!looksLikeJD(best)) {
      const missing = [];
      for (const o of best.frames) if (!(await chrome.permissions.contains({ origins: [o + '/*'] }))) missing.push(o);
      if (missing.length) return askAccess(missing, 'the job board embedded in this page (' + missing.map((o) => new URL(o).hostname).join(', ') + ')');
    }
  }
  if (!best || best.text.length < 200 || !looksLikeJD(best)) {
    $('jdBox').open = true;
    if (best && best.text.length >= 200) { job = { ...best, tabUrl: tab.url }; $('jd').value = best.text; showJobInfo(); refreshButtons(); }
    return note('This doesn\'t look like a job description. Select the posting text on the page and press Capture again, or paste it below.');
  }
  job = { ...best, tabUrl: tab.url };
  if (!job.title || job.title === document.title) job.title = tab.title || job.title;
  $('jd').value = job.text;
  showJobInfo();
  refreshButtons();
};

$('jd').addEventListener('input', () => {
  if (!job) job = { url: tab?.url || '', tabUrl: tab?.url || '', title: tab?.title || '', company: '', location: '', how: 'pasted' };
  job.text = $('jd').value;
  $('jdLen').textContent = `(${(job.text.match(/\S+/g) || []).length} words)`;
  refreshButtons();
});

$('tailor').onclick = async () => {
  job.text = $('jd').value.trim();
  busy = true; refreshButtons();
  const r = await native({ cmd: 'tailor', job: { url: job.url, title: job.title, company: job.company, location: job.location, text: job.text } });
  busy = false; refreshButtons();
  if (!r.ok) return note(r.error, 'red');
  note('');
  showJob(r.job);
};

// ---------- the job card ----------

const name = (id) => (H?.agents.find((a) => a.id === id) || {}).name || id || '';

function el(tag, text, cls) {
  const e = document.createElement(tag);
  if (text != null) e.textContent = text;
  if (cls) e.className = cls;
  return e;
}

function list(title, items) {
  if (!items || !items.length) return null;
  const box = document.createDocumentFragment();
  box.appendChild(el('h4', title));
  const ul = el('ul');
  for (const x of items) ul.appendChild(el('li', typeof x === 'string' ? x : JSON.stringify(x)));
  box.appendChild(ul);
  return box;
}

function showJob(j) {
  shown = j;
  $('job').hidden = false;
  $('jobTitle').textContent = [j.company, j.title].filter(Boolean).join(' · ');
  const b = $('jobBadge');
  b.className = 'badge ' + j.status;
  b.textContent = STATUS[j.status] || j.status;

  const tl = $('timeline');
  tl.innerHTML = '';
  const dur = (sec) => sec >= 60 ? `${Math.floor(sec / 60)}m ${String(Math.round(sec % 60)).padStart(2, '0')}s` : `${Math.round(sec)}s`;
  for (const s of j.stages || []) {
    const li = el('li', s.label, s.status);
    if (s.seconds != null) li.prepend(el('span', dur(s.seconds), 't'));
    else if (s.status === 'running' && s.started && j.now) li.prepend(el('span', dur(j.now - s.started), 't'));
    if (s.detail) li.appendChild(el('span', s.detail, 'd'));
    tl.appendChild(li);
  }
  const meta = [`writer ${name(j.writer)}${j.writer_model ? ' ' + j.writer_model : ''}`, `reviewers ${name(j.reviewer)}${j.reviewer_model ? ' ' + j.reviewer_model : ''}`];
  if (j.mode) meta.push(j.mode);
  if (j.cost) meta.push(`$${(+j.cost).toFixed(2)} in agent usage`);
  if (j.started && j.finished) meta.push(`${Math.round((new Date(j.finished) - new Date(j.started)) / 60000)} min`);
  $('jobMeta').textContent = meta.join(' · ');

  const r = j.result;
  const g = $('gate');
  g.hidden = !(r && r.gate && r.gate !== 'n/a') && j.status !== 'failed' && j.status !== 'skip';
  if (j.status === 'ready') { g.className = 'alert green'; g.textContent = `Passed the gate: HM said ${r.hm}, ATS ${r.ats}. Read it once more, then send it.`; }
  else if (j.status === 'needs_you') { g.className = 'alert'; g.textContent = `Didn't pass the gate (HM ${r?.hm}, ATS ${r?.ats}). The resume is finished anyway: read the reviews and decide whether to send it as is, revise, or skip.`; }
  else if (j.status === 'failed') { g.className = 'alert red'; g.textContent = j.error || 'Something went wrong; see agent.log in the job folder.'; }
  else if (j.status === 'skip') { g.className = 'alert red'; g.textContent = r?.summary || 'The writer thinks this job is not a fit.'; }

  $('result').hidden = !r;
  if (r) {
    $('rSummary').textContent = r.summary || '';
    $('rLead').textContent = r.lead ? `Leads with: ${r.lead}` : '';
    const box = $('rLists');
    box.innerHTML = '';
    const fresh = (r.new_from_projects || []).map((x) => `${x.project}: ${x.bullet} (from ${x.source})`);
    for (const part of [list('New from your projects: check each one against its source', fresh), list('Script check warnings', r.warnings), list('Check these numbers: you reported them, the bank shows no re-measurement', r.unverified_numbers),
      list('Eligibility notes (for the form)', r.constraints), list('Gaps: the JD wants it, your bank has no evidence', r.gaps),
      list('Left out', r.dropped)]) if (part) box.appendChild(part);
    const rv = $('reviews');
    rv.innerHTML = '';
    const files = [['analysis', 'Analysis']];
    for (const s of j.stages || []) {
      const m = s.key.match(/^(hm|ats)(\d)$/);
      if (m && s.status !== 'todo') files.push([`review_${m[1]}_${m[2]}`, `${m[1].toUpperCase()} ${m[2]}: ${s.detail || '…'}`]);
    }
    if (j.bank_changed) files.push(['bank_changes', 'Bank changes']);
    for (const [file, label] of files) {
      const btn = el('button', label, 'small');
      btn.onclick = async () => {
        const t = $('reviewText');
        if (!t.hidden && t.dataset.file === file) { t.hidden = true; return; }
        const res = await native({ cmd: 'review', id: j.id, name: file });
        t.textContent = res.ok ? (res.text || '(empty)') : res.error;
        t.dataset.file = file;
        t.hidden = false;
      };
      rv.appendChild(btn);
    }
    if (j.bank_changed && !ACTIVE.has(j.status)) {
      const undo = el('button', 'Undo bank changes', 'small');
      undo.title = 'Put your bullet bank back as it was before this run';
      undo.onclick = async () => {
        if (!confirm('Put your bullet bank back as it was before this run? The current version is kept as a backup.')) return;
        const res = await native({ cmd: 'restore_bank', id: j.id });
        if (!res.ok) return note(res.error, 'red');
        refreshJob();
      };
      rv.appendChild(undo);
    }
  }
  const qs = r?.questions || [];
  $('ask').hidden = !(j.status === 'needs_user' || (qs.length && j.status !== 'ready' && !ACTIVE.has(j.status)));
  const ql = $('questions');
  ql.innerHTML = '';
  for (const q of qs) ql.appendChild(el('li', q));

  const hasPdf = !!((r && r.pdf) || j.has_pdf);
  $('openPdf').hidden = !hasPdf;
  $('openPdf').textContent = ACTIVE.has(j.status) ? 'Open draft' : 'Open PDF';
  $('downloadPdf').hidden = !hasPdf || ACTIVE.has(j.status);
  $('reveal').hidden = !(r || j.status === 'failed');
  $('cancel').hidden = !ACTIVE.has(j.status);

  clearTimeout(poll);
  if (ACTIVE.has(j.status)) poll = setTimeout(refreshJob, 3000);
  else loadRecent();
}

async function refreshJob() {
  if (!shown) return;
  const r = await native({ cmd: 'status', id: shown.id });
  if (r.ok) showJob(r.job);
  else poll = setTimeout(refreshJob, 5000);
}

async function pdfBlob() {
  const r = await native({ cmd: 'pdf', id: shown.id });
  if (!r.ok) { note(r.error, 'red'); return null; }
  const bin = atob(r.b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new Blob([bytes], { type: 'application/pdf' });
}

$('openPdf').onclick = async () => {
  const b = await pdfBlob();
  if (b) chrome.tabs.create({ url: URL.createObjectURL(b) });
};
$('downloadPdf').onclick = async () => {
  const b = await pdfBlob();
  if (!b) return;
  const a = document.createElement('a');
  a.href = URL.createObjectURL(b);
  a.download = 'Resume.pdf';
  a.click();
};
$('reveal').onclick = () => native({ cmd: 'reveal', id: shown.id });
$('reset').onclick = async () => {
  if (!shown) return;
  if (!confirm('Start this posting over? The current run stops and its files move to the trash folder.')) return;
  const r = await native({ cmd: 'reset', id: shown.id });
  if (!r.ok) return note(r.error, 'red');
  clearTimeout(poll);
  shown = null;
  job = null;
  $('job').hidden = true;
  await loadPage();
};
$('cancel').onclick = async () => { const r = await native({ cmd: 'cancel', id: shown.id }); if (r.ok) showJob(r.job); };
$('sendAnswer').onclick = async () => {
  const text = $('answer').value.trim();
  if (!text) return;
  const r = await native({ cmd: 'answer', id: shown.id, text });
  if (!r.ok) return note(r.error, 'red');
  $('answer').value = '';
  showJob(r.job);
};

async function loadRecent() {
  if (!H) return;
  const r = await native({ cmd: 'list' });
  const ul = $('recent');
  ul.innerHTML = '';
  const items = (r.ok ? r.jobs : []).filter((x) => !shown || x.id !== shown.id).slice(0, 8);
  $('recentBox').hidden = !items.length;
  for (const x of items) {
    const li = el('li');
    li.append(el('span', [x.company, x.title].filter(Boolean).join(' · ') || x.id), el('span', STATUS[x.status] || x.status, 'badge ' + x.status));
    li.onclick = async () => { const s = await native({ cmd: 'status', id: x.id }); if (s.ok) showJob(s.job); };
    ul.appendChild(li);
  }
}

// ---------- start ----------

chrome.tabs.onActivated.addListener(() => loadPage());
chrome.tabs.onUpdated.addListener((id, info) => { if (tab && id === tab.id && (info.url || info.status === 'complete')) loadPage(); });

(async () => {
  await hello();
  await loadPage();
})();
