import { summarize, BloodborneError } from './reader.js'
import { render, validate } from './render.js'
import { history, renderHistory, isSlotFile } from './combine.js'
import { mdToHtml } from './mdview.js'

const $ = (id) => document.getElementById(id)
let db = {}, last = { md: '', json: '' }

// the game tables are generated from the owner's install (tools/gamefiles.py); without them the page shows ids
async function loadDb() {
  const get = async (f) => { try { const r = await fetch(`db_bb/${f}`); return r.ok ? await r.json() : undefined } catch { return undefined } }
  db = { names: await get('names.json'), gemEffects: await get('gem_effects.json'), lanterns: await get('lanterns.json') }
  $('dbnote').textContent = db.names ? '' : 'Item names are not installed here (db_bb/names.json), so items show as ids.'
}

// SubtleCrypto exists on https and localhost only; a page opened from disk falls back to a cheap hash, enough to fold identical copies
async function sha1(bytes) {
  if (crypto.subtle) return [...new Uint8Array(await crypto.subtle.digest('SHA-1', bytes))].map((b) => b.toString(16).padStart(2, '0')).join('')
  let h = 2166136261
  for (let i = 0; i < bytes.length; i++) h = Math.imul(h ^ bytes[i], 16777619)
  return `${bytes.length}:${h >>> 0}`
}

function show(md, json, findings = []) {
  last = { md, json }
  $('out').innerHTML = (findings.length ? `<div class="warn"><strong>Does not add up</strong><ul>${findings.map((f) => `<li>${f.replace(/&/g, '&amp;').replace(/</g, '&lt;')}</li>`).join('')}</ul></div>` : '') + mdToHtml(md)
  $('actions').hidden = false
}

async function handle(fileList) {
  const files = [...fileList].filter((f) => isSlotFile(f.name))
  if (!files.length) { $('out').innerHTML = '<p class="warn">No userdata0000 to userdata0009 file in that selection.</p>'; $('actions').hidden = true; return }
  const loaded = await Promise.all(files.map(async (f) => ({ path: f.webkitRelativePath || f.name, bytes: new Uint8Array(await f.arrayBuffer()), mtimeMs: f.lastModified })))
  if (loaded.length === 1) {
    try {
      const s = summarize(loaded[0].bytes, loaded[0].path.split('/').pop(), db)
      show(render(s), JSON.stringify(s, null, 1), validate(s))
    } catch (e) {
      if (!(e instanceof BloodborneError)) throw e
      $('out').innerHTML = `<p class="warn">${e.message.replace(/&/g, '&amp;').replace(/</g, '&lt;')}</p>`
      $('actions').hidden = true
    }
    return
  }
  const h = await history(loaded, db, sha1)
  const findings = []
  show(renderHistory(h), JSON.stringify(h, null, 1), findings)
}

const drop = $('drop')
drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('over') })
drop.addEventListener('dragleave', () => drop.classList.remove('over'))
drop.addEventListener('drop', async (e) => {
  e.preventDefault(); drop.classList.remove('over')
  const files = []
  const walk = async (entry) => {   // a dropped folder (a BB-Save snapshot folder) is walked
    if (entry.isFile) files.push(await new Promise((res) => entry.file(res)))
    else { const r = entry.createReader(); let batch; do { batch = await new Promise((res) => r.readEntries(res)); for (const c of batch) await walk(c) } while (batch.length) }
  }
  for (const it of e.dataTransfer.items) { const en = it.webkitGetAsEntry && it.webkitGetAsEntry(); if (en) await walk(en) }
  handle(files.length ? files : e.dataTransfer.files)
})
$('pick').addEventListener('change', (e) => handle(e.target.files))
$('pickdir').addEventListener('change', (e) => handle(e.target.files))
const save = (name, text, type) => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], { type })); a.download = name; a.click(); URL.revokeObjectURL(a.href) }
$('dlmd').addEventListener('click', () => save('bloodborne.md', last.md, 'text/markdown'))
$('dljson').addEventListener('click', () => save('bloodborne.json', last.json, 'application/json'))
loadDb()
