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
  $('dsBox').hidden = !H.agents.find((a) => a.id === 'deepseek' && a.found);
  const warn = [];
  if (!H.skill) warn.push('The jd-resume-tailor skill is not installed. Get it at github.com/xungirl/jd-resume-tailor.');
  if (!H.tailor_config) warn.push('jd-resume-tailor has no config yet. Run it once in Claude Code ("tailor my resume") so it learns where your bullet bank is.');
  if (!H.poppler) warn.push('poppler is missing, so the script checks can\'t read the PDF. Install it: brew install poppler');
  $('envWarn').hidden = !warn.length;
  $('envWarn').textContent = warn.join(' ');
  const rv = $('reviewer').value === 'same' ? H.writer : $('reviewer').value;
  const name = (id) => (H.agents.find((a) => a.id === id) || {}).name || id;
  $('who').textContent = `Writer: ${name(H.writer)} · Reviewers: ${name(rv)}`;
}

async function saveSettings(patch) {
  const r = await native({ cmd: 'settings', set: patch });
  if (r.ok) { H.writer = r.writer; H.reviewer = r.reviewer; H.agents = r.agents; renderAgents(); await hello(); }
  return r;
}

$('writer').onchange = () => saveSettings({ writer: $('writer').value });
$('reviewer').onchange = () => saveSettings({ reviewer: $('reviewer').value });
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

$('capture').onclick = async () => {
  tab = await activeTab();
  if (!isWeb(tab)) return;
  note('');
  let got;
  try {
    got = (await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: captureJob }))[0].result;
  } catch (e) {
    // No access to this site yet. Ask with a button of its own, so the request comes from a direct click.
    const origin = new URL(tab.url).origin + '/*';
    note(`JD Tailor needs your OK to read ${new URL(tab.url).hostname}.`, 'blue');
    const b = document.createElement('button');
    b.textContent = 'Allow on this site'; b.className = 'primary small'; b.style.marginLeft = '8px';
    b.onclick = () => chrome.permissions.request({ origins: [origin] }).then((ok) => {
      if (!ok) return note('Not allowed. You can still paste the job description below.', 'red');
      note('');
      $('capture').click();
    });
    $('pageMsg').appendChild(b);
    return;
  }
  if (!got || got.text.length < 200) {
    $('jdBox').open = true;
    return note('Could not find a job description on this page. Select the posting text and press Capture again, or paste it below.');
  }
  job = { ...got, tabUrl: tab.url };
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
  for (const s of j.stages || []) {
    const li = el('li', s.label, s.status);
    if (s.detail) li.appendChild(el('span', s.detail, 'd'));
    tl.appendChild(li);
  }
  const meta = [`writer ${name(j.writer)}`, `reviewers ${name(j.reviewer)}`];
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
    for (const part of [list('Script check warnings', r.warnings), list('Check these numbers: you reported them, the bank shows no re-measurement', r.unverified_numbers),
      list('Eligibility notes (for the form)', r.constraints), list('Gaps: the JD wants it, your bank has no evidence', r.gaps),
      list('Left out', r.dropped)]) if (part) box.appendChild(part);
    const rv = $('reviews');
    rv.innerHTML = '';
    const files = [['analysis', 'Analysis']];
    for (const s of j.stages || []) {
      const m = s.key.match(/^(hm|ats)(\d)$/);
      if (m && s.status !== 'todo') files.push([`review_${m[1]}_${m[2]}`, `${m[1].toUpperCase()} ${m[2]}: ${s.detail || '…'}`]);
    }
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
  }
  const qs = r?.questions || [];
  $('ask').hidden = !(j.status === 'needs_user' || (qs.length && j.status !== 'ready' && !ACTIVE.has(j.status)));
  const ql = $('questions');
  ql.innerHTML = '';
  for (const q of qs) ql.appendChild(el('li', q));

  const hasPdf = !!(r && r.pdf);
  $('openPdf').hidden = !hasPdf;
  $('downloadPdf').hidden = !hasPdf;
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
