// Shared by the extension's side panel (panel.js) and the local web UI (web/web.js):
// the agents card, the job card (timeline, result, reviews, bank undo, questions), and recent jobs.
// Each page passes its own way to reach the host (`call`) and its own PDF handling.

export const $ = (id) => document.getElementById(id);
export const ACTIVE = new Set(['queued', 'running']);
export const STATUS = { queued: 'queued', running: 'running', ready: 'ready', needs_you: 'needs your call', needs_user: 'question for you',
  skip: 'not a fit', failed: 'failed', cancelled: 'stopped' };

export function el(tag, text, cls) {
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

/**
 * o.call(msg) -> Promise<answer>      talk to the host (native messaging, or the local web server)
 * o.onHello(r)                        after each hello, ok or not
 * o.openPdf(job), o.downloadPdf(job)  called synchronously from the click (so pop-up blockers allow it)
 * o.afterReset()                      the job card was reset
 */
export function createUI(o) {
  const ui = { H: null, shown: null };
  let poll = null;
  const call = o.call;

  function note(text, kind = '') {
    const m = $('pageMsg');
    m.hidden = !text;
    m.className = 'alert' + (kind ? ' ' + kind : '');
    m.textContent = text;
  }

  async function hello() {
    const r = await call({ cmd: 'hello' });
    const c = $('gear');
    if (!r.ok) {
      ui.H = null;
      c.className = 'conn bad';
      $('connText').textContent = 'not connected';
      if (o.onHello) o.onHello(r);
      return false;
    }
    ui.H = r;
    const w = r.agents.find((a) => a.id === r.writer);
    c.className = 'conn ' + (w && w.ready ? 'ok' : 'bad');
    $('connText').textContent = w ? w.name : 'no agent';
    renderAgents();
    if (o.onHello) o.onHello(r);
    return true;
  }

  function renderAgents() {
    const H = ui.H;
    const agentList = $('agentList');
    agentList.innerHTML = '';
    for (const a of H.agents) {
      const li = document.createElement('li');
      li.className = a.ready ? 'ok' : 'no';
      const b = document.createElement('b'); b.textContent = a.name;
      const n = document.createElement('span'); n.className = 'muted small'; n.textContent = a.note;
      li.append(b, n);
      agentList.appendChild(li);
    }
    const fill = (sel, value, same) => {
      sel.innerHTML = '';
      if (same) sel.add(new Option('Same as writer', 'same'));
      for (const a of H.agents) {
        const opt = new Option(a.name + (a.ready ? '' : ' (not ready)'), a.id);
        opt.disabled = !a.ready;
        sel.add(opt);
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
    const mlabel = (agentId, v) => { const a = H.agents.find((x) => x.id === agentId); const m = a && a.models.find(([id]) => id === (v || a.models[0][0])); return m ? m[1].replace(/ \(.*\)/, '') : v; };
    $('who').textContent = `Writer: ${name(H.writer)} ${mlabel(H.writer, H.writer_model) || ''} · Reviewers: ${name(rv)} ${mlabel(rv, H.reviewer_model) || ''} · ${H.mode === 'thorough' ? 'thorough' : 'quick'}`.replace(/ +·/g, ' ·');
  }

  async function saveSettings(patch) {
    const r = await call({ cmd: 'settings', set: patch });
    if (r.ok) await hello();
    else note(r.error, 'red');
    return r;
  }

  $('writer').onchange = () => saveSettings({ writer: $('writer').value });
  $('reviewer').onchange = () => saveSettings({ reviewer: $('reviewer').value });
  $('mode').onchange = () => saveSettings({ mode: $('mode').value });
  $('saveProjects').onclick = async () => {
    const items = $('projects').value.split('\n').map((x) => x.trim()).filter(Boolean);
    const r = await call({ cmd: 'settings', set: { projects: items } });
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
  $('gear').onclick = () => { if (ui.H) $('agents').hidden = !$('agents').hidden; };
  $('closeAgents').onclick = () => ($('agents').hidden = true);

  // ---------- the job card ----------

  const name = (id) => (ui.H?.agents.find((a) => a.id === id) || {}).name || id || '';

  function showJob(j) {
    ui.shown = j;
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
          const res = await call({ cmd: 'review', id: j.id, name: file });
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
          const res = await call({ cmd: 'restore_bank', id: j.id });
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
    if (!ui.shown) return;
    const r = await call({ cmd: 'status', id: ui.shown.id });
    if (r.ok) showJob(r.job);
    else poll = setTimeout(refreshJob, 5000);
  }

  function hideJob() {
    clearTimeout(poll);
    ui.shown = null;
    $('job').hidden = true;
  }

  $('openPdf').onclick = () => { if (ui.shown) o.openPdf(ui.shown); };
  $('downloadPdf').onclick = () => { if (ui.shown) o.downloadPdf(ui.shown); };
  $('reveal').onclick = () => call({ cmd: 'reveal', id: ui.shown.id });
  $('reset').onclick = async () => {
    if (!ui.shown) return;
    if (!confirm('Start this posting over? The current run stops and its files move to the trash folder.')) return;
    const r = await call({ cmd: 'reset', id: ui.shown.id });
    if (!r.ok) return note(r.error, 'red');
    hideJob();
    await o.afterReset();
  };
  $('cancel').onclick = async () => { const r = await call({ cmd: 'cancel', id: ui.shown.id }); if (r.ok) showJob(r.job); };
  $('sendAnswer').onclick = async () => {
    const text = $('answer').value.trim();
    if (!text) return;
    const r = await call({ cmd: 'answer', id: ui.shown.id, text });
    if (!r.ok) return note(r.error, 'red');
    $('answer').value = '';
    showJob(r.job);
  };

  async function loadRecent() {
    if (!ui.H) return;
    const r = await call({ cmd: 'list' });
    const ul = $('recent');
    ul.innerHTML = '';
    const items = (r.ok ? r.jobs : []).filter((x) => !ui.shown || x.id !== ui.shown.id).slice(0, 8);
    $('recentBox').hidden = !items.length;
    for (const x of items) {
      const li = el('li');
      li.append(el('span', [x.company, x.title].filter(Boolean).join(' · ') || x.id), el('span', STATUS[x.status] || x.status, 'badge ' + x.status));
      li.onclick = async () => { const s = await call({ cmd: 'status', id: x.id }); if (s.ok) showJob(s.job); };
      ul.appendChild(li);
    }
  }

  return Object.assign(ui, { hello, note, showJob, refreshJob, hideJob, loadRecent, saveSettings });
}
