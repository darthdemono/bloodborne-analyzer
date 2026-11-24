// Port of bloodborne/render.py and validate.py. Byte-for-byte the same Markdown: tools/parity.mjs checks it.
import { itemLabel } from './reader.js'

const fmt = (n) => Number(n).toLocaleString('en-US')
const title = (k) => k.charAt(0).toUpperCase() + k.slice(1).toLowerCase()

function slotsText(s, gems) {
  const byHandle = new Map(gems.map((g) => [g.handle, g]))
  const out = []
  for (const sl of s.gemSlots || []) {
    if (sl.shape === 'Closed') continue
    const g = byHandle.get(sl.gem)
    out.push(`${sl.shape} (${g ? g.effects.map((e) => e.text || String(e.id)).join(', ') : 'empty'})`)
  }
  return out.join(', ')
}

function section(name, grp, gems) {
  const total = Object.entries(grp).filter(([k]) => k !== 'gems').reduce((a, [, v]) => a + v.length, 0)
  const ng = grp.gems.length
  const out = [`### ${name} (${total} entries` + (ng ? `, ${ng} gems and runes` : '') + ')', '']
  if (!total) return [...out, 'Empty.', '']
  out.push('| Kind | Name | Amount | Gem slots |', '|---|---|---|---|')
  for (const kind of ['weapons', 'armor', 'goods', 'other']) {
    for (const s of grp[kind]) out.push(`| ${kind.endsWith('s') ? kind.slice(0, -1) : kind} | ${itemLabel(s)} | ${s.amount} | ${slotsText(s, gems)} |`)
  }
  return [...out, '']
}

export function render(s) {
  let out = [`# Bloodborne save: ${s.file}`, '']
  if (s.empty) return [...out, 'No character in this slot.', ''].join('\n')
  const c = s.character, h = s.header
  out.push(
    `**Character:** ${c.name}`,
    `**Origin (id):** ${c.origin}`,
    `**Level:** ${c.level}` + (c.level === c.levelFromStats ? '' : ` (the stats add up to level ${c.levelFromStats}: check this save)`),
    `**Play time:** ${h.playtime}`,
    `**Deaths:** ${c.deaths}`,
    '**New Game cycle:** ' + (c.newGameCycle ? `NG+${c.newGameCycle}` : 'NG (first playthrough)'),
    `**Blood Echoes:** ${fmt(c.bloodEchoes)}`,
    `**Insight:** ${c.insight}`,
    `**Health:** ${c.health.current} of ${c.health.base}`,
    `**Stamina:** ${c.stamina.current} of ${c.stamina.base}`,
    '', '| Stat | Value |', '|---|---|',
  )
  for (const [k, v] of Object.entries(c.stats)) out.push(`| ${title(k)} | ${v} |`)
  const eq = s.equipped
  out.push('', '### Worn', '', '**Weapon slots (stored order):** ' + eq.weapons.map((x) => x || 'empty').join(', '), '**Armor (head, chest, arms, legs):** ' + eq.armor.map((x) => x || 'empty').join(', '), '')
  out.push(`### Blood gems and runes (${s.gems.length})`, '')
  if (s.gems.length) {
    out.push('| Type | Shape | Effects | Fitted to |', '|---|---|---|---|')
    for (const g of s.gems) out.push(`| ${g.type} | ${g.shape || 'category ' + g.category} | ${g.effects.map((e) => e.text || String(e.id)).join('; ')} | ${g.fittedTo || 'not fitted'} |`)
  } else out.push('None.')
  const ln = s.lanterns
  out.push('', `### Lanterns lit (${ln.lit.length} of ${ln.calibrated} calibrated)`, '')
  if (ln.lit.length) out.push(...ln.lit.map((n) => `- ${n}`))
  else out.push(ln.calibrated ? 'Calibrated lanterns: none lit.' : 'No lanterns calibrated yet: see tools/flagdiff.py --add.')
  const b = s.bosses
  out.push('', `### Bosses defeated (${b.defeated.length} of ${b.tracked} tracked)`, '')
  if (b.defeated.length) out.push(...b.defeated.map((n) => `- ${n}`))
  else out.push('None yet.')
  out = [...out, '', ...section('Inventory', s.inventory, s.gems), ...section('Storage', s.storage, s.gems), ...section('Key items', s.keyItems, s.gems)]
  const i = s.integrity
  out.push(`**Decoded:** ${fmt(i.decodedBytes)} of ${fmt(i.fileBytes)} bytes. ${i.note}.`, '')
  return out.join('\n')
}

const STAT_MAX = 99
const printable = (s) => !/[\x00-\x1f\x7f-\x9f]/.test(s)
export function validate(s) {
  if (s.empty) return []
  const c = s.character, out = []
  const total = Object.values(c.stats).reduce((a, b) => a + b, 0)
  if (c.level !== total - 50) out.push(`level ${c.level} but the six stats add up to level ${total - 50}`)
  for (const [k, v] of Object.entries(c.stats)) if (!(v >= 1 && v <= STAT_MAX)) out.push(`${k} is ${v}, outside 1 to ${STAT_MAX}`)
  if (!c.name || !printable(c.name)) out.push('the character name is empty or has unprintable characters')
  if (c.health.base <= 0 || c.stamina.base <= 0) out.push('health or stamina is zero')
  if (s.header.playtimeMs <= 0) out.push('play time is zero')
  if (c.health.current > c.health.withBuffs) out.push('current health is above the buffed maximum')
  return out
}
