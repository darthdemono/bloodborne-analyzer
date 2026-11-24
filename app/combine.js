// Port of bloodborne/combine.py: many summaries -> one history. sha1 is injected (node crypto or SubtleCrypto).
import { summarize, BloodborneError } from './reader.js'

const STATS = ['vigor', 'endurance', 'strength', 'skill', 'bloodtinge', 'arcane']
const SNAP = /BB_(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})/
const BBPORT = /savedata-backups\/(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})/
const SLOT = /^userdata000\d$/
export const isSlotFile = (name) => SLOT.test(name.split('/').pop())

// "BB_2026-11-24_12-45-04" or bbport's "20261122-114824" give the time; anything else uses the file's own mtime (ms)
export function stamp(path, mtimeMs = 0) {
  let m = SNAP.exec(path)
  if (m) return `${m[1]}T${m[2]}:${m[3]}:${m[4]}`
  m = BBPORT.exec(path)
  if (m) return `${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:${m[6]}`
  const d = new Date(mtimeMs), p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

const gearOf = (s) => {
  const out = new Set()
  for (const grp of ['inventory', 'storage']) for (const k of ['weapons', 'armor']) for (const x of s[grp][k]) out.add(`${x.name || x.id}` + (x.kind === 'weapon' && x.level ? ` +${x.level}` : ''))
  return out
}
const goodsOf = (s) => new Set(['inventory', 'storage', 'keyItems'].flatMap((g) => s[g].goods.map((x) => x.name || String(x.id))))

// files: [{ path, bytes, mtimeMs }]
export async function history(files, db, sha1) {
  const rows = [], skipped = []
  let empty = 0
  const seen = new Map()
  const ordered = files.map((f) => ({ ...f, t: stamp(f.path, f.mtimeMs) })).sort((a, b) => (a.t < b.t ? -1 : a.t > b.t ? 1 : 0))
  for (const f of ordered) {
    let s
    try { s = summarize(f.bytes, '', db) } catch (e) {
      if (e instanceof BloodborneError) { skipped.push([f.path, e.message]); continue }
      throw e
    }
    if (s.empty) { empty++; continue }
    const digest = await sha1(f.bytes)
    if (seen.has(digest)) { seen.get(digest).copies++; continue }
    const row = { time: f.t, path: f.path, copies: 1, playtimeMs: s.header.playtimeMs, playtime: s.header.playtime, ...s.character, bosses: s.bosses.defeated, _gear: gearOf(s), _goods: goodsOf(s) }
    seen.set(digest, row)
    rows.push(row)
  }
  rows.sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : a.playtimeMs - b.playtimeMs))
  const notes = [], changes = []
  for (let i = 1; i < rows.length; i++) {
    const a = rows[i - 1], b = rows[i]
    for (const k of STATS) if (b.stats[k] < a.stats[k]) notes.push(`${b.time}: ${k} dropped from ${a.stats[k]} to ${b.stats[k]} (a respec, or a different character)`)
    if (b.name !== a.name) notes.push(`${b.time}: the name changed from ${a.name} to ${b.name}`)
    if (b.playtimeMs < a.playtimeMs) notes.push(`${b.time}: play time went back from ${a.playtime} to ${b.playtime}, so an older save was restored`)
    if (b.deaths < a.deaths) notes.push(`${b.time}: deaths went back from ${a.deaths} to ${b.deaths} (an older save was restored)`)
    const gone = a.bosses.filter((x) => !b.bosses.includes(x))
    if (gone.length) notes.push(`${b.time}: ${gone.join(', ')} no longer defeated (an older save was restored)`)
    const newItems = [...[...b._gear].filter((x) => !a._gear.has(x)), ...[...b._goods].filter((x) => !a._goods.has(x)).map((x) => `${x} (item)`)]
    // Python sorts the combined set of strings; sort by code point the same way
    const nw = [...new Set(newItems)].sort((x, y) => (x < y ? -1 : x > y ? 1 : 0))
    const killed = b.bosses.filter((x) => !a.bosses.includes(x))
    if (nw.length || killed.length) changes.push([b.time, killed, nw])
  }
  for (const r of rows) { delete r._gear; delete r._goods }
  return { snapshots: rows, emptySlots: empty, skipped, notes, changes: changes.map(([time, k, n]) => ({ time, bossesDefeated: k, new: n })) }
}

const fmt = (n) => Number(n).toLocaleString('en-US')
export function renderHistory(h) {
  const rows = h.snapshots
  const out = ['# Bloodborne playthrough history', '']
  if (!rows.length) return [...out, 'No saves with a character were found.', ''].join('\n')
  const last = rows[rows.length - 1]
  out.push(`**Snapshots:** ${rows.length}  `, `**First:** ${rows[0].time}  `, `**Latest:** ${last.time} (${last.name}, level ${last.level}, ${last.playtime} played, ${last.deaths} deaths)`, '',
    '| Time | Level | Play time | Deaths | Echoes | Insight | Vig | End | Str | Skl | Blt | Arc | Bosses |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|')
  for (const r of rows) out.push(`| ${r.time} | ${r.level} | ${r.playtime} | ${r.deaths} | ${fmt(r.bloodEchoes)} | ${r.insight} | ` + STATS.map((k) => r.stats[k]).join(' | ') + ` | ${r.bosses.length} |`)
  out.push('', '## Checks', '')
  if (h.notes.length) out.push(...h.notes.map((n) => `- ${n}`))
  else out.push('- Stats and play time only grow across the snapshots: a straight line.')
  if (h.changes.length) {
    out.push('', '## What changed between snapshots', '')
    for (const c of h.changes) out.push(`- **${c.time}**` + (c.bossesDefeated.length ? ` defeated ${c.bossesDefeated.join(', ')};` : '') + (c.new.length ? ` new: ${c.new.join(', ')}` : ''))
  }
  out.push('', `**Empty slots passed over:** ${h.emptySlots}  `, `**Identical copies folded in:** ${rows.reduce((a, r) => a + r.copies - 1, 0)}`)
  if (h.skipped.length) {
    out.push('', `## Unreadable (${h.skipped.length})`, '')
    for (const [p, why] of h.skipped) { const parts = p.split('/'); out.push(`- ${parts.slice(-3, -1).length === 2 ? parts[parts.length - 3] : ''}/${parts[parts.length - 1]}: ${why}`) }
  }
  return out.join('\n') + '\n'
}
