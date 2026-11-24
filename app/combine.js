// Port of bloodborne/combine.py: many summaries -> one history. sha1 is injected (node crypto or SubtleCrypto).
import { summarize, BloodborneError } from './reader.js'
import { render } from './render.js'

const STATS = ['vigor', 'endurance', 'strength', 'skill', 'bloodtinge', 'arcane']
const SNAP = /BB_(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})/
const BBPORT = /savedata-backups\/(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})/
const SLOT = /^userdata000\d$/
export const isSlotFile = (name) => SLOT.test(name.split('/').pop())
const cmp = (x, y) => (x < y ? -1 : x > y ? 1 : 0)   // code point order, the same as Python's sorted() on these strings
const fmt = (n) => Number(n).toLocaleString('en-US')
const signed = (n) => (n >= 0 ? `+${fmt(n)}` : `-${fmt(-n)}`)
const hms = (ms) => `${Math.floor(ms / 3600000)}:${String(Math.floor(ms / 60000) % 60).padStart(2, '0')}:${String(Math.floor(ms / 1000) % 60).padStart(2, '0')}`

// "BB_2026-11-24_12-45-04" or bbport's "20261122-114824" give the time; anything else uses the file's own mtime (ms)
export function stamp(path, mtimeMs = 0) {
  let m = SNAP.exec(path)
  if (m) return `${m[1]}T${m[2]}:${m[3]}:${m[4]}`
  m = BBPORT.exec(path)
  if (m) return `${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:${m[6]}`
  const d = new Date(mtimeMs), p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

const labelOf = (x) => `${x.name || x.id}` + (x.kind === 'weapon' && x.level ? ` +${x.level}` : '')
const gearOf = (s) => new Set(['inventory', 'storage'].flatMap((g) => ['weapons', 'armor'].flatMap((k) => s[g][k].map(labelOf))))
function amountsOf(s) {
  const out = new Map()
  for (const g of ['inventory', 'storage', 'keyItems']) for (const x of s[g].goods) { const k = x.name || String(x.id); out.set(k, (out.get(k) || 0) + x.amount) }
  return out
}
const gemText = (g) => `${g.shape || 'category ' + g.category} ${g.type}: ` + g.effects.map((e) => e.text || String(e.id)).join('; ')
function gained(now, before) {   // multiset difference, order kept
  const left = [...before], out = []
  for (const x of now) { const i = left.indexOf(x); if (i >= 0) left.splice(i, 1); else out.push(x) }
  return out
}

function step(a, b) {
  const sa = a._s, sb = b._s
  const ga = gearOf(sa), gb = gearOf(sb), ma = amountsOf(sa), mb = amountsOf(sb)
  const names = [...new Set([...ma.keys(), ...mb.keys()])].sort(cmp)
  const stats = {}
  for (const k of STATS) if (b.stats[k] !== a.stats[k]) stats[k] = b.stats[k] - a.stats[k]
  return {
    time: b.time, playMs: b.playtimeMs - a.playtimeMs, level: [a.level, b.level], echoes: [a.bloodEchoes, b.bloodEchoes], insight: [a.insight, b.insight], deaths: b.deaths - a.deaths, stats,
    bossesDefeated: b.bosses.filter((x) => !a.bosses.includes(x)),
    gear: { gained: [...gb].filter((x) => !ga.has(x)).sort(cmp), lost: [...ga].filter((x) => !gb.has(x)).sort(cmp) },
    goods: {
      new: names.filter((n) => !ma.has(n)).map((n) => `${n} x${mb.get(n)}`), gone: names.filter((n) => !mb.has(n)),
      changed: names.filter((n) => ma.has(n) && mb.has(n) && ma.get(n) !== mb.get(n)).map((n) => `${n} ${ma.get(n)} to ${mb.get(n)}`),
    },
    gems: gained(sb.gems.map(gemText), sa.gems.map(gemText)),
    lampsLit: sb.lanterns.lit.filter((x) => !sa.lanterns.lit.includes(x)),
    restored: b.playtimeMs < a.playtimeMs,
  }
}

// files: [{ path, bytes, mtimeMs }]
export async function history(files, db, sha1) {
  const rows = [], skipped = []
  let empty = 0
  const seen = new Map()
  const ordered = files.map((f) => ({ ...f, t: stamp(f.path, f.mtimeMs) })).sort((a, b) => cmp(a.t, b.t))
  for (const f of ordered) {
    let s
    try { s = summarize(f.bytes, '', db) } catch (e) {
      if (e instanceof BloodborneError) { skipped.push([f.path, e.message]); continue }
      throw e
    }
    if (s.empty) { empty++; continue }
    const digest = await sha1(f.bytes)
    if (seen.has(digest)) { seen.get(digest).copies++; continue }
    const row = { time: f.t, path: f.path, copies: 1, playtimeMs: s.header.playtimeMs, playtime: s.header.playtime, ...s.character, bosses: s.bosses.defeated, _s: s }
    seen.set(digest, row)
    rows.push(row)
  }
  rows.sort((a, b) => cmp(a.time, b.time) || a.playtimeMs - b.playtimeMs)
  const notes = [], steps = []
  for (let i = 1; i < rows.length; i++) {
    const a = rows[i - 1], b = rows[i]
    for (const k of STATS) if (b.stats[k] < a.stats[k]) notes.push(`${b.time}: ${k} dropped from ${a.stats[k]} to ${b.stats[k]} (a respec, or a different character)`)
    if (b.name !== a.name) notes.push(`${b.time}: the name changed from ${a.name} to ${b.name}`)
    if (b.playtimeMs < a.playtimeMs) notes.push(`${b.time}: play time went back from ${a.playtime} to ${b.playtime}, so an older save was restored`)
    if (b.deaths < a.deaths) notes.push(`${b.time}: deaths went back from ${a.deaths} to ${b.deaths} (an older save was restored)`)
    const gone = a.bosses.filter((x) => !b.bosses.includes(x))
    if (gone.length) notes.push(`${b.time}: ${gone.join(', ')} no longer defeated (an older save was restored)`)
    steps.push(step(a, b))
  }
  const firstSeen = new Map()
  for (const r of rows) for (const x of r.bosses) if (!firstSeen.has(x)) firstSeen.set(x, r.time)
  const latest = rows.length ? rows[rows.length - 1]._s : null
  for (const r of rows) delete r._s
  return { snapshots: rows, emptySlots: empty, skipped, notes, changes: steps, bossTimeline: [...firstSeen].map(([boss, t]) => ({ boss, firstSeenDefeated: t })), latest }
}

function stepLines(c) {
  const out = []
  if (c.restored) out.push('- **An older save was restored here**: play time went back, so the numbers below are against the snapshot before it.')
  if (c.level[0] !== c.level[1]) out.push(`- Level ${c.level[0]} to ${c.level[1]} (${signed(c.level[1] - c.level[0])})`)
  if (Object.keys(c.stats).length) out.push('- Stats: ' + Object.entries(c.stats).map(([k, v]) => `${k} ${signed(v)}`).join(', '))
  if (c.echoes[0] !== c.echoes[1]) out.push(`- Blood Echoes ${fmt(c.echoes[0])} to ${fmt(c.echoes[1])}`)
  if (c.insight[0] !== c.insight[1]) out.push(`- Insight ${c.insight[0]} to ${c.insight[1]}`)
  if (c.deaths) out.push(`- Deaths ${signed(c.deaths)}`)
  if (c.bossesDefeated.length) out.push('- Defeated: ' + c.bossesDefeated.join(', '))
  if (c.gear.gained.length) out.push('- New gear: ' + c.gear.gained.join(', '))
  if (c.gear.lost.length) out.push('- Gear gone: ' + c.gear.lost.join(', '))
  if (c.goods.new.length) out.push('- New items: ' + c.goods.new.join(', '))
  if (c.goods.gone.length) out.push('- Used up or gone: ' + c.goods.gone.join(', '))
  if (c.goods.changed.length) out.push('- Amounts: ' + c.goods.changed.join(', '))
  if (c.gems.length) out.push('- New blood gems and runes: ' + c.gems.join('; '))
  if (c.lampsLit.length) out.push('- Lamps lit: ' + c.lampsLit.join(', '))
  return out.length ? out : ['- No change in the tracked values.']
}

export function renderHistory(h) {
  const rows = h.snapshots
  let out = ['# Bloodborne playthrough history', '']
  if (!rows.length) return [...out, 'No saves with a character were found.', ''].join('\n')
  const first = rows[0], last = rows[rows.length - 1], s = h.latest, eq = s.equipped
  out.push('## Overview', '',
    `**Character:** ${last.name}  `, `**Snapshots:** ${rows.length} distinct saves (${rows.reduce((a, r) => a + r.copies - 1, 0)} identical copies folded in)  `,
    `**First:** ${first.time}  `, `**Latest:** ${last.time}  `,
    `**Level:** ${first.level} to ${last.level}  `, `**Play time:** ${first.playtime} to ${last.playtime}  `, `**Deaths:** ${first.deaths} to ${last.deaths}  `,
    `**Blood Echoes (latest):** ${fmt(last.bloodEchoes)}  `, `**Insight (latest):** ${last.insight}  `,
    `**Bosses defeated:** ${last.bosses.length} of ${s.bosses.tracked}  `,
    `**Lamps lit:** ${s.lanterns.lit.length} of ${s.lanterns.known}: ` + (s.lanterns.lit.join(', ') || 'none') + '  ',
    '**Worn now:** ' + [...eq.weapons, ...eq.armor].map((x) => x || 'empty').join(', '), '',
    '## Timeline', '',
    '| Time | Level | Play time | Deaths | Echoes | Insight | Vig | End | Str | Skl | Blt | Arc | Bosses |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|')
  for (const r of rows) out.push(`| ${r.time} | ${r.level} | ${r.playtime} | ${r.deaths} | ${fmt(r.bloodEchoes)} | ${r.insight} | ` + STATS.map((k) => r.stats[k]).join(' | ') + ` | ${r.bosses.length} |`)
  out.push('', '## Checks', '')
  if (h.notes.length) out.push(...h.notes.map((n) => `- ${n}`))
  else out.push('- Stats and play time only grow across the snapshots: a straight line.')
  out.push('', '## Boss timeline', '')
  if (h.bossTimeline.length) out.push(...h.bossTimeline.map((b) => `- ${b.boss}: first seen defeated in the snapshot of ${b.firstSeenDefeated}`))
  else out.push('No boss defeated in any snapshot.')
  if (h.changes.length) {
    out.push('', '## Between snapshots', '')
    for (const c of h.changes) out.push(`### ${c.time} (${c.playMs >= 0 ? '+' : '-'}${hms(Math.abs(c.playMs))} played since the previous snapshot)`, '', ...stepLines(c), '')
  }
  out.push('## Latest save in full', '', ...render(s).split('\n').slice(2).map((ln) => (ln.startsWith('#') ? '#' + ln : ln)))
  out.push(`**Empty slots passed over:** ${h.emptySlots}  `)
  if (h.skipped.length) {
    out.push('', `## Unreadable (${h.skipped.length})`, '')
    for (const [p, why] of h.skipped) { const parts = p.split('/'); out.push(`- ${parts[parts.length - 3] ?? ''}/${parts[parts.length - 1]}: ${why}`) }
  }
  return out.join('\n') + '\n'
}
