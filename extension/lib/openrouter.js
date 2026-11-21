// OpenRouter: one-click login (OAuth PKCE, no server, no client secret), key check, model list, chat.
// The key lives only in chrome.storage.local on this computer.

const SITE = 'https://openrouter.ai';
const APP = 'JD Tailor';

// Tests point API calls at a local mock with storage key "apiBase". Login always uses OpenRouter itself.
async function api() {
  const { apiBase } = await chrome.storage.local.get('apiBase');
  return (apiBase || SITE) + '/api/v1';
}

const b64url = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

// Safari has no chrome.identity.launchWebAuthFlow: there, people paste a key instead.
export const canLogin = () => !!(chrome.identity && chrome.identity.launchWebAuthFlow);

export async function login() {
  const verifier = b64url(crypto.getRandomValues(new Uint8Array(32)));
  const challenge = b64url(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier)));
  const state = b64url(crypto.getRandomValues(new Uint8Array(16)));
  const url = `${SITE}/auth?` + new URLSearchParams({
    callback_url: chrome.identity.getRedirectURL(), code_challenge: challenge, code_challenge_method: 'S256', state,
  });
  const back = new URL(await chrome.identity.launchWebAuthFlow({ url, interactive: true }));
  if (back.searchParams.get('state') !== state) throw new Error('login came back from the wrong place; try again');
  const code = back.searchParams.get('code');
  if (!code) throw new Error('login was cancelled');
  const r = await fetch(`${SITE}/api/v1/auth/keys`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, code_verifier: verifier, code_challenge_method: 'S256' }),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok || !j.key) throw new Error(`OpenRouter refused the login (HTTP ${r.status})`);
  return j.key;
}

// { ok, limit_remaining, usage, is_free_tier } or { ok: false, status }
export async function keyInfo(key) {
  try {
    const r = await fetch(`${await api()}/key`, { headers: { Authorization: `Bearer ${key}` } });
    if (!r.ok) return { ok: false, status: r.status };
    const d = (await r.json()).data || {};
    return { ok: true, ...d };
  } catch (e) {
    return { ok: false, status: 0 };
  }
}

// The models people are most likely to want come first, then the free ones.
const PICKS = [
  ['anthropic/claude-opus-5.5', 'best results'],
  ['anthropic/claude-sonnet-5.5', 'good, about half the price'],
  ['openai/gpt-5.6-sol', ''],
  ['deepseek/deepseek-v4-pro', 'cheap'],
];
const IN_TOKENS = 12000, OUT_TOKENS = 4000; // a typical posting + resume, and the answer

export async function models() {
  const { modelCache } = await chrome.storage.local.get('modelCache');
  if (modelCache && Date.now() - modelCache.at < 864e5) return modelCache.list;
  const r = await fetch(`${await api()}/models`);
  if (!r.ok) throw new Error(`could not load the model list (HTTP ${r.status})`);
  const all = (await r.json()).data || [];
  const json = (m) => (m.supported_parameters || []).some((p) => p === 'response_format' || p === 'structured_outputs');
  const cost = (m) => (+m.pricing?.prompt || 0) * IN_TOKENS + (+m.pricing?.completion || 0) * OUT_TOKENS;
  const list = [];
  for (const [id, note] of PICKS) {
    const m = all.find((x) => x.id === id);
    if (m) list.push({ id, name: m.name || id, note, cost: cost(m), free: false });
  }
  for (const m of all) {
    if (m.id.endsWith(':free') && json(m)) list.push({ id: m.id, name: m.name || m.id, note: 'free, weaker; the provider may keep your text', cost: 0, free: true });
  }
  await chrome.storage.local.set({ modelCache: { at: Date.now(), list } });
  return list;
}

export class ApiError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

function explain(status, body) {
  const msg = body?.error?.message || '';
  if (status === 401) return 'OpenRouter did not accept the key. Connect again.';
  if (status === 402) return 'Your OpenRouter balance is empty. Add credits, or pick a free model.';
  if (status === 429) return 'Rate limited. Wait a minute, or pick another model.';
  return `OpenRouter error ${status}${msg ? `: ${msg}` : ''}`;
}

// Returns { text, usage }. Asks for JSON matching the schema; models that can't do that get plain JSON mode.
export async function chat({ key, model, system, user, schema }) {
  const url = `${await api()}/chat/completions`;
  const send = async (format) => {
    const r = await fetch(url, {
      method: 'POST',
      headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json', 'X-Title': APP },
      body: JSON.stringify({
        model, max_tokens: 16000, usage: { include: true },
        messages: [{ role: 'system', content: system }, { role: 'user', content: user }],
        ...(format ? { response_format: format } : {}),
      }),
    });
    const body = await r.json().catch(() => ({}));
    return { r, body };
  };
  let { r, body } = await send({ type: 'json_schema', json_schema: { name: 'tailored_resume', strict: true, schema } });
  if (r.status === 400 && /response_format|json_schema|structured/i.test(body?.error?.message || '')) {
    ({ r, body } = await send({ type: 'json_object' }));
  }
  if (!r.ok) throw new ApiError(r.status, explain(r.status, body));
  const choice = body.choices?.[0];
  if (!choice) throw new ApiError(0, 'OpenRouter returned no answer');
  if (choice.finish_reason === 'length') throw new ApiError(0, 'The answer was cut off. Try again, or shorten your material.');
  return { text: choice.message?.content || '', usage: body.usage || {} };
}
