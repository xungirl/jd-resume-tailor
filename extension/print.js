import { render } from './lib/md.js';

const { printDoc } = await chrome.storage.local.get('printDoc');
if (printDoc) {
  document.getElementById('doc').innerHTML = render(printDoc.md);
  document.title = printDoc.title || 'Resume'; // the PDF's default file name
}
document.getElementById('print').onclick = () => print();
// Tell the reader if it no longer fits on one page (11in minus the margins).
const sheet = document.getElementById('doc');
const pageIn = 11 - 1.0;
const tall = sheet.scrollHeight - 2 * 0.5 * 96;
if (tall > pageIn * 96) document.querySelector('.bar span').textContent = 'This runs past one page. Trim a bullet, or print anyway.';
if (!new URLSearchParams(location.search).has('noprint')) setTimeout(() => print(), 300);
