#!/usr/bin/env node
// THE gate for the web port: the Python reader and app/*.js run on the same saves and must agree on the summary (value AND key
// order), the Markdown (byte for byte) and the combined history.
//   node tools/parity.mjs <folder|save>...
import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { summarize } from '../app/reader.js'
import { render, validate } from '../app/render.js'
import { history, renderHistory, isSlotFile } from '../app/combine.js'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = (f) => (existsSync(join(root, 'db_bb', f)) ? JSON.parse(readFileSync(join(root, 'db_bb', f), 'utf8')) : undefined)
const db = { names: read('names.json'), gemEffects: read('gem_effects.json'), lamps: read('lamps.json') }
const py = (...args) => execFileSync('python3', ['bb_to_md.py', ...args], { cwd: root, encoding: 'utf8', maxBuffer: 1 << 28 })
const walk = (p) => (statSync(p).isDirectory() ? readdirSync(p).flatMap((n) => walk(join(p, n))) : isSlotFile(p) ? [p] : [])
const files = process.argv.slice(2).flatMap(walk)
if (!files.length) { console.error('no userdata000N files found'); process.exit(2) }
const sha1 = async (b) => createHash('sha1').update(b).digest('hex')
let bad = 0
const fail = (m) => { bad++; console.log('FAIL', m) }

for (const f of files) {
  const bytes = new Uint8Array(readFileSync(f))
  let jsS
  try { jsS = summarize(bytes, f.split('/').pop(), db) } catch (e) { jsS = { error: e.message } }
  let pyS
  // JSON through python's own writer, to a temp path, so the markdown stays out of the way
  const tmp = join(root, '.parity.json')
  try { py(f, '-o', tmp); pyS = JSON.parse(readFileSync(tmp, 'utf8')) } catch (e) { pyS = { error: String(e.stderr || e.message).trim().split('\n').pop() } }
  if (pyS.error || jsS.error) { if (!(pyS.error && jsS.error)) fail(`${f}: only one side failed (py ${pyS.error}, js ${jsS.error})`); continue }
  if (JSON.stringify(pyS) !== JSON.stringify(jsS)) fail(`${f}: summary differs`)
  const tmpMd = join(root, '.parity.md')
  py(f, '-o', tmpMd)
  if (readFileSync(tmpMd, 'utf8') !== render(jsS) + '\n' && readFileSync(tmpMd, 'utf8') !== render(jsS)) fail(`${f}: markdown differs`)
  const pv = py('--validate', f).split('\n').filter((l) => l.startsWith(f)).map((l) => l.slice(f.length + 2))
  if (JSON.stringify(pv) !== JSON.stringify(validate(jsS))) fail(`${f}: validate differs`)
}
const tmpH = join(root, '.parity-history.md')
py(...files, '--combined', '-o', tmpH)
const h = await history(files.map((f) => ({ path: f, bytes: new Uint8Array(readFileSync(f)), mtimeMs: statSync(f).mtimeMs })), db, sha1)
const jsH = renderHistory(h)
if (readFileSync(tmpH, 'utf8') !== jsH) {
  fail('history differs')
  const a = readFileSync(tmpH, 'utf8').split('\n'), b = jsH.split('\n')
  for (let i = 0; i < Math.max(a.length, b.length); i++) if (a[i] !== b[i]) { console.log(`  line ${i + 1}\n  py: ${a[i]}\n  js: ${b[i]}`); break }
}
console.log(bad ? `${bad} parity failure(s) over ${files.length} files` : `parity OK: ${files.length} files, summary + markdown + validate + history`)
process.exit(bad ? 1 : 0)
