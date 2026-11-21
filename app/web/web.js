// JD Resume Tailor in any browser: the same app as the extension's side panel, served by `jdt.py web`
// on 127.0.0.1. Every call carries the key from the link the server printed (#t=… or ?t=…).
import { $, createUI } from './lib/ui.js';

const KEY = 'jdrt-key';
const TOKEN = (() => {
  const fromUrl = new URLSearchParams(location.hash.slice(1)).get('t') || new URLSearchParams(location.search).get('t') || '';
  let t = fromUrl;
  try {
    if (fromUrl) sessionStorage.setItem(KEY, fromUrl);
    else t = sessionStorage.getItem(KEY) || '';
    // The key is remembered for this tab, so take it out of the address bar (and out of anything you copy from it).
    if (fromUrl && sessionStorage.getItem(KEY) === fromUrl) history.replaceState(null, '', location.pathname);
  } catch (e) { /* no sessionStorage: the key stays in the URL, so a reload still works */ }
  return t;
})();

async function call(msg) {
  let res;
  try {
    res = await fetch('/api', {
      method: 'POST', cache: 'no-store', credentials: 'omit',
      headers: { 'Content-Type': 'application/json', 'X-JDRT-Token': TOKEN },
      body: JSON.stringify(msg),
    });
  } catch (e) {
    return { ok: false, down: true, error: 'Can\'t reach JD Resume Tailor on this computer. Is "jdrt web" still running?' };
  }
  let j;
  try { j = await res.json(); } catch (e) { j = { ok: false, error: `HTTP ${res.status}` }; }
  if (res.status === 401 || res.status === 403) j.auth = true;
  return j;
}

const pdfUrl = (j, download) => `/pdf?id=${encodeURIComponent(j.id)}&t=${encodeURIComponent(TOKEN)}${download ? '&download=1' : ''}`;

const ui = createUI({
  call,
  onHello(r) {
    $('connect').hidden = r.ok;
    $('page').hidden = !r.ok;
    if (r.ok) return;
    $('connectTitle').textContent = r.auth ? 'Open the link from Terminal' : 'JD Resume Tailor isn\'t running';
    $('connectText').textContent = r.auth
      ? 'This page needs the key in the link that "jdrt web" printed. The key changes each time it starts, so an old link stops working. Run it again if you closed it:'
      : 'Start it in Terminal. It runs the AI agent already on your computer and keeps everything on this machine:';
    refresh();
  },
  openPdf(j) { window.open(pdfUrl(j, false), '_blank', 'noopener'); },
  downloadPdf(j) {
    const a = document.createElement('a');
    a.href = pdfUrl(j, true);
    a.download = 'Resume.pdf';
    document.body.appendChild(a);
    a.click();
    a.remove();
  },
  afterReset() { ui.loadRecent(); },
});
const note = ui.note;

// ---------- the job form ----------

let job = { url: '', location: '', how: '' };   // what Fetch found (the text box and fields can be edited after)
let busy = false;

const words = (t) => (t.match(/\S+/g) || []).length;
const linkOk = (u) => /^https?:\/\/\S+$/i.test(u);

function refresh() {
  const text = $('jd').value.trim();
  $('jdLen').textContent = text ? `(${words(text)} words)` : '';
  $('tailor').disabled = busy || !ui.H || text.length < 200;
  $('fetch').disabled = busy || !ui.H;
  const head = [$('company').value.trim(), $('title').value.trim()].filter(Boolean).join(' · ');
  $('pageTitle').textContent = head || (text ? 'Pasted job description' : 'Paste a posting link, or the job description');
  if (text) $('pageMeta').textContent = [job.location, `${words(text)} words`, job.how && `read from ${job.how}`].filter(Boolean).join(' · ');
}

$('fetchForm').onsubmit = async (e) => {
  e.preventDefault();
  const url = $('url').value.trim();
  if (!linkOk(url)) return note('Paste the posting\'s link, starting with https://', 'red');
  note('');
  busy = true;
  $('fetch').textContent = 'Fetching…';
  refresh();
  const r = await call({ cmd: 'fetch_url', url });
  busy = false;
  $('fetch').textContent = 'Fetch';
  if (!r.ok) {
    refresh();
    $('jd').focus();
    return note(r.error, r.closed ? 'red' : '');
  }
  job = { url: r.job.url, location: r.job.location || '', how: r.job.ats && r.job.ats !== 'html' ? r.job.ats : 'the page' };
  $('url').value = r.job.url;
  $('company').value = r.job.company || '';
  $('title').value = r.job.title || '';
  $('jd').value = r.job.text;
  refresh();
  const f = await call({ cmd: 'find', url: r.job.url });
  if (f.ok && f.job) ui.showJob(f.job);
};

for (const id of ['jd', 'company', 'title']) $(id).addEventListener('input', refresh);
$('jd').addEventListener('input', () => { if (!$('jd').value.trim()) job = { url: '', location: '', how: '' }; });

$('tailor').onclick = async () => {
  const typed = $('url').value.trim();
  const msg = {
    url: linkOk(typed) ? typed : '', company: $('company').value.trim(), title: $('title').value.trim(),
    location: job.location, text: $('jd').value.trim(),
  };
  busy = true; refresh();
  const r = await call({ cmd: 'tailor', job: msg });
  busy = false; refresh();
  if (!r.ok) return note(r.error, 'red');
  note('');
  ui.showJob(r.job);
};

$('clear').onclick = () => {
  for (const id of ['url', 'company', 'title', 'jd']) $(id).value = '';
  job = { url: '', location: '', how: '' };
  $('pageMeta').textContent = '';
  note('');
  refresh();
};

$('retry').onclick = async () => { if (await ui.hello()) { refresh(); ui.loadRecent(); } };
$('copyCmd').onclick = async () => {
  try { await navigator.clipboard.writeText($('startCmd').textContent); } catch (e) { return; }
  $('copyCmd').textContent = 'Copied';
  setTimeout(() => ($('copyCmd').textContent = 'Copy'), 1500);
};

(async () => {
  if (await ui.hello()) ui.loadRecent();
  refresh();
})();
