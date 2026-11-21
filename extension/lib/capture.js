// Runs inside the job page (chrome.scripting.executeScript), so it must be self-contained.
// Reads the posting: JSON-LD JobPosting first, then known ATS containers, then your selection, then the page.
export function captureJob() {
  const clean = (s) => (s || '').replace(/ /g, ' ').replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
  // DOMParser builds an inert document: nothing in the posting's HTML loads or runs.
  // Some sites escape the HTML once more (&lt;p&gt;), so parse twice when tags are still showing.
  const parse = (h) => new DOMParser().parseFromString(
    String(h || '').replace(/<(br|\/p|\/li|\/h\d|\/div|\/ul|\/ol)\b[^>]*>/gi, '$&\n'), 'text/html').body.textContent;
  const htmlText = (h) => { const t = parse(h); return clean(/<\/?(p|li|ul|br|div|strong|b)\b/i.test(t) ? parse(t) : t); };
  let url = location.href;
  const u = new URL(url);
  if (/linkedin\.com$/.test(u.hostname) && u.searchParams.get('currentJobId')) {
    url = `https://www.linkedin.com/jobs/view/${u.searchParams.get('currentJobId')}/`;
  }
  const out = { url, title: '', company: '', location: '', text: '', how: '' };

  for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
    let data; try { data = JSON.parse(s.textContent); } catch (e) { continue; }
    const items = [].concat(data, data && data['@graph'] || []);
    const jp = items.find((x) => x && [].concat(x['@type']).includes('JobPosting'));
    if (jp) {
      out.title = jp.title || '';
      out.company = (jp.hiringOrganization && (jp.hiringOrganization.name || jp.hiringOrganization)) || '';
      const loc = [].concat(jp.jobLocation || [])[0];
      const a = loc && loc.address;
      out.location = a ? [a.addressLocality, a.addressRegion, a.addressCountry && (a.addressCountry.name || a.addressCountry)].filter(Boolean).join(', ') : '';
      out.text = htmlText(jp.description);
      out.how = 'json-ld';
      break;
    }
  }
  const pick = (sels) => { for (const q of sels) { const el = document.querySelector(q); if (el && el.innerText.trim()) return el; } return null; };
  if (out.text.length < 200) {
    const body = pick(['.jobs-description__content', '.jobs-box__html-content', '#job-details',        // LinkedIn
      '[data-hook="job-description"]', '.style__description___', '[class*="jobDescription"]',            // Handshake & co.
      '#content .job__description', '.job__description', '#content', '.posting-page .section-wrapper',   // Greenhouse, Lever
      '[data-automation-id="jobPostingDescription"]',                                                      // Workday
      '.ashby-job-posting-right-pane', 'main article', 'article', 'main', '[role="main"]', 'body']);
    const sel = String(getSelection() || '').trim();
    if (sel.length >= 200) { out.text = clean(sel); out.how = 'selection'; }
    else if (body) { out.text = clean(body.innerText); out.how = 'page'; }
  }
  const h1 = document.querySelector('.job-details-jobs-unified-top-card__job-title, .top-card-layout__title, h1');
  out.title = out.title || (h1 ? h1.innerText.trim() : document.title);
  const co = document.querySelector('.job-details-jobs-unified-top-card__company-name, .topcard__org-name-link, [data-automation-id="company"]');
  out.company = out.company || (co ? co.innerText.trim() : '') ||
    (document.querySelector('meta[property="og:site_name"]') || {}).content || '';
  out.text = out.text.slice(0, 60000);
  return out;
}
