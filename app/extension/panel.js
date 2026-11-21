// JD Resume Tailor panel: capture the JD here, run the agents on your computer through native messaging.
// The agents card, job card and recent list are shared with the web UI (lib/ui.js).
import { captureJob } from './lib/capture.js';
import { $, createUI } from './lib/ui.js';

const HOST = 'io.github.xungirl.jd_resume_tailor';

let tab = null;      // the job tab
let job = null;      // what Capture found
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

async function pdfBlob(j) {
  const r = await native({ cmd: 'pdf', id: j.id });
  if (!r.ok) { ui.note(r.error, 'red'); return null; }
  const bin = atob(r.b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new Blob([bytes], { type: 'application/pdf' });
}

const ui = createUI({
  call: native,
  onHello(r) {
    $('install').hidden = r.ok;
    if (!r.ok) $('installErr').textContent = r.noHost ? '' : r.error;
  },
  async openPdf(j) {
    const b = await pdfBlob(j);
    if (b) chrome.tabs.create({ url: URL.createObjectURL(b) });
  },
  async downloadPdf(j) {
    const b = await pdfBlob(j);
    if (!b) return;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(b);
    a.download = 'Resume.pdf';
    a.click();
  },
  async afterReset() {
    job = null;
    await loadPage();
  },
});
const note = ui.note;

$('retry').onclick = async () => { if (await ui.hello()) loadPage(); };
$('copyCmd').onclick = async () => {
  await navigator.clipboard.writeText($('installCmd').textContent);
  $('copyCmd').textContent = 'Copied';
  setTimeout(() => ($('copyCmd').textContent = 'Copy'), 1500);
};

// ---------- the job page ----------

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
  if (ui.H && isWeb(tab)) {
    const r = await native({ cmd: 'find', url: tab.url });
    if (r.ok && r.job) ui.showJob(r.job);
  }
  ui.loadRecent();
}

function showJobInfo() {
  $('pageTitle').textContent = [job.company, job.title].filter(Boolean).join(' · ') || job.url;
  const words = (job.text.match(/\S+/g) || []).length;
  $('pageMeta').textContent = [job.location, `${words} words`, job.how && `read from ${job.how}`].filter(Boolean).join(' · ');
  $('jdLen').textContent = `(${words} words)`;
}

function refreshButtons() {
  $('capture').disabled = busy || !isWeb(tab);
  $('tailor').disabled = busy || !ui.H || $('jd').value.trim().length < 200;
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
  note(`JD Resume Tailor needs your OK to read ${label}.`, 'blue');
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
  ui.showJob(r.job);
};

// ---------- start ----------

chrome.tabs.onActivated.addListener(() => loadPage());
chrome.tabs.onUpdated.addListener((id, info) => { if (tab && id === tab.id && (info.url || info.status === 'complete')) loadPage(); });

(async () => {
  await ui.hello();
  await loadPage();
})();
