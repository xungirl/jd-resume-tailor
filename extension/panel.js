// JD Tailor panel (Chrome/Edge side panel, Safari popup).
import { captureJob } from './lib/capture.js';
import * as OR from './lib/openrouter.js';
import { SCHEMA, SYSTEM, userMessage, parseAnswer, newNumbers, rewordedBullets } from './lib/tailor.js';
import { render } from './lib/md.js';

const $ = (id) => document.getElementById(id);
const DEFAULT_MODEL = 'anthropic/claude-opus-5.5';
const KEEP_RESULTS = 15;

let S = { orKey: '', model: DEFAULT_MODEL, resume: '' };
let tab = null;        // the job tab we are looking at
let job = null;        // what Capture found on it
let current = null;    // the result shown
let busy = false;

// ---------- settings ----------

async function loadSettings() {
  S = { ...S, ...(await chrome.storage.local.get(['orKey', 'model', 'resume'])) };
  $('resume').value = S.resume || '';
  countResume();
}
const save = (patch) => { Object.assign(S, patch); return chrome.storage.local.set(patch); };

function countResume() {
  const n = ($('resume').value.trim().match(/\S+/g) || []).length;
  $('resumeCount').textContent = n ? `${n} words` : '';
}

async function showKey() {
  const c = $('gear');
  if (!S.orKey) { c.className = 'conn'; $('connText').textContent = 'not connected'; $('keyStatus').textContent = ''; return; }
  const info = await OR.keyInfo(S.orKey);
  if (info.ok) {
    c.className = 'conn ok';
    const left = info.limit_remaining != null ? ` · $${(+info.limit_remaining).toFixed(2)} left on this key` : '';
    $('connText').textContent = 'OpenRouter';
    $('keyStatus').textContent = `✓ Connected${left}`;
  } else {
    c.className = 'conn bad';
    $('connText').textContent = info.status === 401 ? 'key not accepted' : 'offline?';
    $('keyStatus').textContent = info.status === 401 ? 'OpenRouter did not accept this key. Connect again.' : 'Could not reach OpenRouter.';
  }
}

async function loadModels() {
  const sel = $('model');
  let list = [];
  try { list = await OR.models(); } catch (e) { $('modelNote').textContent = e.message; }
  if (!list.some((m) => m.id === S.model)) list.unshift({ id: S.model, name: S.model, note: '', cost: null });
  sel.innerHTML = '';
  let freeHeader = false;
  for (const m of list) {
    if (m.free && !freeHeader) { const o = new Option('── free models ──', ''); o.disabled = true; sel.add(o); freeHeader = true; }
    const price = m.free ? 'free' : m.cost != null ? `≈ $${m.cost.toFixed(2)} each` : '';
    sel.add(new Option(`${m.name}${price ? ` (${price})` : ''}`, m.id));
  }
  sel.value = S.model;
  const note = () => { const m = list.find((x) => x.id === sel.value); $('modelNote').textContent = m?.note || ''; };
  note();
  sel.onchange = () => { save({ model: sel.value }); note(); };
}

function setupNeeded() { return !S.orKey || !S.resume.trim(); }
function showSetup(on) { $('setup').hidden = !on; }

$('gear').onclick = () => showSetup($('setup').hidden);

$('login').onclick = async () => {
  const b = $('login');
  b.disabled = true; b.textContent = 'Waiting for OpenRouter…';
  try {
    const key = await OR.login();
    await save({ orKey: key });
    await showKey();
  } catch (e) {
    $('keyStatus').textContent = '✗ ' + (e.message || e);
  } finally {
    b.disabled = false; b.textContent = 'Connect OpenRouter';
  }
};

$('saveKey').onclick = async () => {
  const k = $('keyInput').value.trim();
  if (!k) return;
  await save({ orKey: k });
  $('keyInput').value = '';
  await showKey();
};

$('resume').addEventListener('input', countResume);
$('resume').addEventListener('change', () => save({ resume: $('resume').value }));
$('resumeFile').onchange = async (e) => {
  const f = e.target.files[0];
  if (!f) return;
  $('resume').value = await f.text();
  countResume();
  await save({ resume: $('resume').value });
};

$('doneSetup').onclick = async () => {
  await save({ resume: $('resume').value });
  if (!S.orKey) return note('Connect OpenRouter or paste a key first.', 'red');
  if (!S.resume.trim()) return note('Paste your resume first.', 'red');
  showSetup(false);
  note('');
  refreshButtons();
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

async function results() { return (await chrome.storage.local.get('results')).results || {}; }

async function loadPage() {
  if (busy) return;
  tab = await activeTab();
  const r = isWeb(tab) ? (await results())[tab.url] : null;
  if (r) {
    job = r.job;
    $('jd').value = job.text;
    showJob();
    showResult(r);
  } else if (!job || !tab || job.tabUrl !== tab.url) {
    job = null;
    $('jd').value = '';
    $('pageTitle').textContent = isWeb(tab) ? (tab.title || tab.url) : 'Open a job posting';
    $('pageMeta').textContent = isWeb(tab) ? 'Press Capture JD to read the job description.' : '';
    $('jdLen').textContent = '';
    $('result').hidden = true;
    note('');
  }
  refreshButtons();
}

function showJob() {
  $('pageTitle').textContent = [job.company, job.title].filter(Boolean).join(' · ') || job.url;
  const words = (job.text.match(/\S+/g) || []).length;
  $('pageMeta').textContent = [job.location, `${words} words`, job.how && `read from ${job.how}`].filter(Boolean).join(' · ');
  $('jdLen').textContent = `(${words} words)`;
}

function refreshButtons() {
  $('capture').disabled = busy || !isWeb(tab);
  $('tailor').disabled = busy || $('jd').value.trim().length < 200;
}

async function runCapture() {
  return (await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: captureJob }))[0].result;
}

$('capture').onclick = async () => {
  tab = await activeTab();
  if (!isWeb(tab)) return;
  note('');
  let got;
  try {
    got = await runCapture();
  } catch (e) {
    // No access to this site yet. Ask for it with a button of its own, so the request is a direct click.
    const origin = new URL(tab.url).origin + '/*';
    note(`JD Tailor needs your OK to read ${new URL(tab.url).hostname}.`, 'blue');
    const b = document.createElement('button');
    b.textContent = 'Allow on this site'; b.className = 'primary'; b.style.marginLeft = '8px';
    b.onclick = () => chrome.permissions.request({ origins: [origin] }).then(async (ok) => {
      if (!ok) return note('Not allowed. You can still paste the job description below.', 'red');
      note('');
      $('capture').click();
    });
    $('pageMsg').appendChild(b);
    return;
  }
  if (!got || got.text.length < 200) {
    $('jdBox').open = true;
    return note('Could not find a job description on this page. Select the text of the posting and press Capture again, or paste it below.');
  }
  job = { ...got, tabUrl: tab.url };
  $('jd').value = job.text;
  showJob();
  refreshButtons();
};

$('jd').addEventListener('input', () => {
  if (!job) job = { url: tab?.url || '', tabUrl: tab?.url || '', title: '', company: '', location: '', how: 'pasted' };
  job.text = $('jd').value;
  $('jdLen').textContent = `(${(job.text.match(/\S+/g) || []).length} words)`;
  refreshButtons();
});

// ---------- tailoring ----------

$('tailor').onclick = async () => {
  if (setupNeeded()) { showSetup(true); return note('Finish setup first.', 'red'); }
  job.text = $('jd').value.trim();
  busy = true; refreshButtons();
  const t0 = Date.now();
  const tick = () => note(`Tailoring with ${S.model.split('/').pop()}… ${Math.round((Date.now() - t0) / 1000)}s`, 'blue');
  tick();
  const timer = setInterval(tick, 1000);
  try {
    const { text, usage } = await OR.chat({ key: S.orKey, model: S.model, system: SYSTEM, user: userMessage(job, S.resume), schema: SCHEMA });
    const answer = parseAnswer(text);
    const r = { job, answer, model: S.model, usage, seconds: Math.round((Date.now() - t0) / 1000), at: Date.now(),
      newNumbers: newNumbers(S.resume, answer.resume_markdown),
      reworded: [...rewordedBullets(S.resume, answer.resume_markdown)] };
    const all = await results();
    all[job.tabUrl || job.url] = r;
    const keys = Object.keys(all).sort((a, b) => all[b].at - all[a].at);
    for (const k of keys.slice(KEEP_RESULTS)) delete all[k];
    await chrome.storage.local.set({ results: all });
    note('');
    showResult(r);
  } catch (e) {
    note(e.message || String(e), 'red');
    if (e.status === 401) showSetup(true);
  } finally {
    clearInterval(timer);
    busy = false; refreshButtons();
  }
};

function li(parent, text, cls) {
  const el = document.createElement('li');
  if (cls) el.className = cls;
  el.textContent = text;
  parent.appendChild(el);
  return el;
}

function showResult(r) {
  current = r;
  const a = r.answer;
  $('result').hidden = false;
  $('rRole').textContent = a.role || [r.job.company, r.job.title].filter(Boolean).join(' · ');
  $('rFit').textContent = a.fit || '';
  const el = $('rElig'); el.innerHTML = '';
  for (const c of a.eligibility) li(el, `${c.constraint}${c.note ? ': ' + c.note : ''}`, c.status);
  const w = $('rWarn');
  w.hidden = !r.newNumbers.length;
  w.textContent = r.newNumbers.length ? `These numbers are not in your resume: ${r.newNumbers.join(', ')}. Delete them unless you know they're true.` : '';
  $('rResume').innerHTML = render(a.resume_markdown, new Set(r.reworded));
  const ch = $('rChanges'); ch.innerHTML = '';
  for (const c of a.changes) li(ch, c);
  const g = $('rGaps'); g.innerHTML = '';
  for (const x of a.gaps) {
    const item = li(g, '');
    const b = document.createElement('b'); b.textContent = x.requirement;
    item.append(b, document.createTextNode(x.advice ? ` · ${x.advice}` : ''));
  }
  if (!a.gaps.length) li(g, 'No gaps found.');
  $('rKeys').textContent = [a.keywords_covered.length && `Covered: ${a.keywords_covered.join(', ')}`,
    a.keywords_missing.length && `Missing: ${a.keywords_missing.join(', ')}`].filter(Boolean).join('  ·  ');
  const u = r.usage || {};
  $('rCost').textContent = [r.model, r.seconds != null && `${r.seconds}s`, u.total_tokens && `${u.total_tokens.toLocaleString()} tokens`,
    u.cost != null && `$${(+u.cost).toFixed(3)}`].filter(Boolean).join(' · ');
}

document.querySelectorAll('.tabs button').forEach((b) => (b.onclick = () => {
  document.querySelectorAll('.tabs button').forEach((x) => x.classList.toggle('on', x === b));
  document.querySelectorAll('[data-pane]').forEach((p) => (p.hidden = p.dataset.pane !== b.dataset.tab));
}));

function fileName(ext) {
  const name = (current.answer.resume_markdown.match(/^#\s+(.+)$/m) || [, 'Resume'])[1];
  const co = current.job.company || '';
  return [name, co, 'Resume'].filter(Boolean).join('_').replace(/[^\w\-]+/g, '_').replace(/_+/g, '_') + ext;
}

$('copy').onclick = async () => {
  await navigator.clipboard.writeText(current.answer.resume_markdown);
  $('copy').textContent = 'Copied ✓';
  setTimeout(() => ($('copy').textContent = 'Copy text'), 1500);
};

$('download').onclick = () => {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([current.answer.resume_markdown], { type: 'text/markdown' }));
  a.download = fileName('.md');
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
};

$('pdf').onclick = async () => {
  await chrome.storage.local.set({ printDoc: { md: current.answer.resume_markdown, title: fileName('') } });
  chrome.tabs.create({ url: chrome.runtime.getURL('print.html') });
};

// ---------- start ----------

if (!OR.canLogin()) { $('loginRow').hidden = true; $('loginHint').hidden = true; $('pasteBox').open = true; }

chrome.tabs.onActivated.addListener(() => loadPage());
chrome.tabs.onUpdated.addListener((id, info) => { if (tab && id === tab.id && (info.url || info.status === 'complete')) loadPage(); });

(async () => {
  await loadSettings();
  showSetup(setupNeeded());
  await loadPage();
  showKey();
  loadModels();
})();
