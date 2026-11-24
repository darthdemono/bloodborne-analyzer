// The tiny Markdown subset render.js and combine.js emit (headings, bold, tables, bullets, paragraphs) -> safe HTML.
const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
const inline = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')

export function mdToHtml(md) {
  const lines = md.split('\n'), out = []
  for (let i = 0; i < lines.length; i++) {
    const l = lines[i]
    let m
    if ((m = /^(#{1,6}) (.*)$/.exec(l))) out.push(`<h${m[1].length}>${inline(m[2])}</h${m[1].length}>`)
    else if (l.startsWith('|') && /^\|[-| ]+\|$/.test(lines[i + 1] || '')) {
      const row = (r, tag) => '<tr>' + r.slice(1, -1).split('|').map((c) => `<${tag}>${inline(c.trim())}</${tag}>`).join('') + '</tr>'
      const head = row(l, 'th'), body = []
      i += 2
      while (i < lines.length && lines[i].startsWith('|')) body.push(row(lines[i++], 'td'))
      i--
      out.push(`<div class="scroll"><table><thead>${head}</thead><tbody>${body.join('')}</tbody></table></div>`)
    } else if (l.startsWith('- ')) {
      const items = []
      while (i < lines.length && lines[i].startsWith('- ')) items.push(`<li>${inline(lines[i++].slice(2))}</li>`)
      i--
      out.push(`<ul>${items.join('')}</ul>`)
    } else if (l.trim()) {
      const para = [l]
      while (i + 1 < lines.length && lines[i + 1].trim() && !/^(#|\||- )/.test(lines[i + 1])) para.push(lines[++i])
      out.push(`<p>${para.map((p) => inline(p.replace(/ +$/, ''))).join('<br>')}</p>`)
    }
  }
  return out.join('\n')
}
