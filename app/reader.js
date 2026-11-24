// Line-for-line port of bloodborne/{container,layout,records,gear,lanterns,bb}.py. The Python reader is the reference:
// tools/parity.mjs runs both on the same saves and compares the summary, key order included.
import { BOSSES } from './bosses.js'

export const SIZE = 0x140000
const MAGIC = [0x41, 0, 0, 0]
export class BloodborneError extends Error {}

const FACE_AFTER = 0xf000, INV_TO_USER = 469, INV_TO_STORAGE = 34268, USER_TO_KEY = 32201, USER_TO_AOB = 68545
export const INV_SLOTS = 1983, STORAGE_SLOTS = 1984, KEY_SLOTS = 128
const SLOT = 16, NONE = 0xffffffff
const AOB = [3, 0, 0, 0, 5, 0, 1, 0]
const GEM_START = 84, GEM = 40, BLOCK = 60, CLOSED = 0x80000000
const SHAPES = { 1: 'Radial', 2: 'Triangle', 4: 'Waning', 8: 'Circle', 0x3f: 'Droplet' }
const WEAPON_SLOTS = [389, 393, 397, 401], ARMOR_SLOTS = [421, 425, 429, 433]
const STATS = { vigor: -103, endurance: -95, strength: -79, skill: -71, bloodtinge: -63, arcane: -55 }
const BASE_LEVEL_SUM = 50, HEADER = 12

export const u32 = (d, o) => (d[o] | (d[o + 1] << 8) | (d[o + 2] << 16) | (d[o + 3] << 24)) >>> 0

export function check(d) {
  if (d.length === 0x40000) throw new BloodborneError('this is the settings file (userdata0010), not a character')
  if (d.length === SIZE && !d.some((b) => b)) return d
  if (d.length !== SIZE || MAGIC.some((b, i) => d[i] !== b)) {
    throw new BloodborneError(`not a decrypted Bloodborne character file (${d.length} bytes); a PS4 save must be decrypted first`)
  }
  return d
}

function indexOfFace(d, from) {
  for (let i = from; i + 4 <= d.length; i++) if (d[i] === 0x46 && d[i + 1] === 0x41 && d[i + 2] === 0x43 && d[i + 3] === 0x45) return i
  return -1
}

export function findLayout(d) {
  const face = indexOfFace(d, FACE_AFTER)
  if (face < 0) return null
  const inv = face - 34028, user = inv - INV_TO_USER, aob = user + USER_TO_AOB
  if (user < 0 || AOB.some((b, i) => d[aob + i] !== b)) return null
  return { face, inventory: inv, username: user, storage: inv + INV_TO_STORAGE, key: user + USER_TO_KEY, aob }
}

const IMPRINTS = { 10000: 'Uncanny', 20000: 'Lost' }
function decode(d, at) {
  const first = u32(d, at + 4), second = u32(d, at + 8), amount = u32(d, at + 12)
  if (second === NONE || !(first || second)) return null
  const b7 = d[at + 7], b11 = d[at + 11]
  const out = { handle: d[at], first, amount }
  if (b7 === 0xb0 && b11 === 0x40) return { ...out, kind: 'goods', id: second & 0xffffff }
  if (b11 === 0x10) return { ...out, kind: 'armor', id: second & 0xffffff }
  if (b7 === 0xc0) return { ...out, kind: 'gem', id: second & 0xffffff, raw: second }
  if (b7 === 0x80) {
    const level = Math.floor((second % 10000) / 100)
    const imprint = IMPRINTS[(second % 100000) - (second % 10000)] ?? null
    const base = second - level * 100 - (imprint === 'Uncanny' ? 10000 : imprint === 'Lost' ? 20000 : 0)
    return { ...out, kind: 'weapon', id: base, level, imprint }
  }
  return { ...out, kind: 'unknown', id: second, raw: second }
}

function readSlots(d, start, count) {
  const out = []
  for (let i = 0; i < count; i++) {
    const s = decode(d, start + i * SLOT)
    if (s) out.push({ slot: i, ...s })
  }
  return out
}

function gems(d, lay) {
  const out = []
  let pos = GEM_START
  while (pos + GEM <= lay.username) {
    const [first, , kind, shape] = [0, 4, 8, 12].map((i) => u32(d, pos + i))
    if (first >>> 24 !== 0xc0 || (kind !== 1 && kind !== 2)) break
    const eff = [0, 1, 2, 3, 4, 5].map((i) => u32(d, pos + 16 + 4 * i))
    out.push({ handle: first, type: kind === 1 ? 'gem' : 'rune', shape: kind === 1 ? SHAPES[shape] ?? null : null, category: kind === 2 ? shape : null, effects: eff.filter((e) => e !== NONE) })
    pos += GEM
  }
  return [out, pos]
}

function blocks(d, lay, start) {
  const out = new Map()
  let pos = start
  while (pos + BLOCK <= lay.username) {
    const w = [0, 1, 2, 3, 4].map((i) => u32(d, pos + 4 * i))
    if ([0x80, 0x90].includes(w[0] >>> 24) && w[0] !== CLOSED && w[4] === 1) {
      const slots = []
      for (let i = 0; i < 5; i++) {
        const shape = u32(d, pos + 20 + 8 * i), gem = u32(d, pos + 24 + 8 * i)
        slots.push({ shape: shape === CLOSED ? 'Closed' : SHAPES[shape] ?? `0x${shape.toString(16)}`, gem: shape !== CLOSED && gem !== 0 && gem !== NONE ? gem : null })
      }
      out.set(w[0], { id: w[1], slots })
      pos += BLOCK
    } else pos += w[0] === 0 && w[1] === NONE ? 8 : 4
  }
  return out
}

const label = (it) => {
  let n = it.name || `unnamed ${it.kind} ${it.id}`
  if (it.kind === 'weapon') n += (it.level ? ` +${it.level}` : '') + (it.imprint ? ` (${it.imprint})` : '')
  return n
}
export const itemLabel = label

function named(slots, db) {
  const t = db.names || {}
  for (const s of slots) s.name = (t[{ goods: 'goods', weapon: 'weapons', armor: 'armor' }[s.kind]] || {})[String(s.id)] ?? ''
  return slots
}
function grouped(slots, db) {
  slots = named(slots, db)
  const out = { goods: [], armor: [], weapons: [], gems: [], other: [] }
  for (const s of slots) out[{ goods: 'goods', armor: 'armor', weapon: 'weapons', gem: 'gems' }[s.kind] || 'other'].push(s)
  return out
}

function gear(d, lay, inv, db) {
  const [gl, end] = gems(d, lay)
  const table = db.gemEffects || {}
  const byHandle = new Map()
  for (const g of gl) {
    g.effects = g.effects.map((e) => ({ id: e, text: table[String(e)] ?? '' }))
    g.fittedTo = null
    byHandle.set(g.handle, g)
  }
  const bl = blocks(d, lay, end), items = new Map()
  for (const grp of ['weapons', 'armor']) {
    for (const it of inv[grp]) {
      items.set(it.first, it)
      const b = bl.get(it.first)
      it.gemSlots = b ? b.slots.map((sl) => ({ shape: sl.shape, gem: sl.gem })) : []
      for (const sl of it.gemSlots) if (byHandle.has(sl.gem)) byHandle.get(sl.gem).fittedTo = label(it)
    }
  }
  const u = lay.username
  const w = { weapons: WEAPON_SLOTS.map((o) => u32(d, u + o)), armor: ARMOR_SLOTS.map((o) => u32(d, u + o)) }
  const worn = {}
  for (const k of Object.keys(w)) worn[k] = w[k].map((h) => (items.has(h) ? label(items.get(h)) : null))
  return [gl, worn]
}

const nameAt = (d, u) => new TextDecoder('utf-16le').decode(d.subarray(u + 1, u + 33)).split('\0')[0]

// db = { names, gemEffects, lanterns } as loaded from db_bb/*.json; any may be missing
export function summarize(bytes, name = '', db = {}) {
  const d = check(bytes)
  const lay = findLayout(d)
  const out = { file: name, size: d.length, empty: lay === null }
  if (!lay) {
    out.integrity = { fileBytes: d.length, decodedBytes: 0, note: 'no character in this slot' }
    return out
  }
  const u = lay.username, g = (off) => u32(d, u + off)
  const stats = {}
  for (const [k, o] of Object.entries(STATS)) stats[k] = g(o)
  const playMs = u32(d, 8)
  const pad = (n) => String(n).padStart(2, '0')
  out.header = { loadedMap: '0x' + u32(d, 4).toString(16).padStart(8, '0'), playtimeMs: playMs, playtime: `${Math.floor(playMs / 3600000)}:${pad(Math.floor(playMs / 60000) % 60)}:${pad(Math.floor(playMs / 1000) % 60)}` }
  out.character = {
    name: nameAt(d, u), level: g(-23), levelFromStats: Object.values(stats).reduce((a, b) => a + b, 0) - BASE_LEVEL_SUM, stats,
    health: { current: g(-147), withBuffs: g(-143), base: g(-139) }, stamina: { current: g(-119), withBuffs: g(-115), base: g(-111) },
    bloodEchoes: g(-19), insight: g(-35), gender: d[u + 35], voice: d[u + 36], origin: d[u + 39], newGameCycle: d[u + 68831], deaths: u32(d, lay.aob + 360),
  }
  out.inventory = grouped(readSlots(d, lay.inventory, INV_SLOTS), db)
  ;[out.gems, out.equipped] = gear(d, lay, out.inventory, db)
  out.storage = grouped(readSlots(d, lay.storage, STORAGE_SLOTS), db)
  out.keyItems = grouped(readSlots(d, lay.key, KEY_SLOTS), db)
  const entries = db.lanterns || []
  out.lanterns = { calibrated: entries.length, lit: entries.filter((e) => (d[lay.aob + e.offset] & e.mask) === e.mask).map((e) => e.name) }
  const flags = BOSSES.map(([n, fl]) => [n, fl.every(([off, mask]) => (d[lay.aob + off] & mask) === mask)])
  out.bosses = { tracked: BOSSES.length, defeated: flags.filter(([, dead]) => dead).map(([n]) => n) }
  out.integrity = {
    fileBytes: d.length, username: u, inventory: lay.inventory, storage: lay.storage, keyItems: lay.key, flags: lay.aob,
    decodedBytes: HEADER + 185 + (INV_SLOTS + STORAGE_SLOTS + KEY_SLOTS) * SLOT + BOSSES.length,
    note: 'map position, appearance, lantern bits until calibrated and most event flags are not read yet (notes/format.md)',
  }
  return out
}
