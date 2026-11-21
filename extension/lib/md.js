// A small Markdown renderer for the resume: headings, bullets, paragraphs, bold, italic, links, code.
// Everything is escaped first, so model output can never inject HTML.

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

function inline(s) {
  return esc(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, '$1<em>$2</em>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+|mailto:[^\s)]+)\)/g, '<a href="$2">$1</a>');
}

// marked: a Set of line numbers to tag with class "reworded".
export function render(md, marked = new Set()) {
  const out = [];
  let list = false;
  const close = () => { if (list) { out.push('</ul>'); list = false; } };
  String(md || '').split('\n').forEach((line, i) => {
    const h = line.match(/^(#{1,4})\s+(.*)$/);
    const b = line.match(/^\s*[-*•]\s+(.*)$/);
    if (h) { close(); const n = h[1].length; out.push(`<h${n}>${inline(h[2])}</h${n}>`); }
    else if (b) { if (!list) { out.push('<ul>'); list = true; } out.push(`<li${marked.has(i) ? ' class="reworded"' : ''}>${inline(b[1])}</li>`); }
    else if (line.trim()) { close(); out.push(`<p>${inline(line)}</p>`); }
    else close();
  });
  close();
  return out.join('\n');
}
