"""Many summaries -> one history. A straight playthrough only ever adds: a stat that drops, or play time that goes back, is reported."""
import hashlib
import re
from datetime import datetime
from pathlib import Path

from .bb import STATS, summarize
from .container import BloodborneError

SLOT = re.compile(r"^userdata000\d$")
SNAP = re.compile(r"BB_(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})")
BBPORT = re.compile(r"savedata-backups/(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})")


def stamp(path: Path) -> datetime:
    """Snapshot folders carry their time (BB_2026-11-24_12-45-04, or bbport's 20261122-114824); anything else uses the mtime."""
    m = SNAP.search(str(path))
    if m:
        return datetime.fromisoformat(f"{m.group(1)}T{m.group(2)}:{m.group(3)}:{m.group(4)}")
    m = BBPORT.search(str(path))
    if m:
        return datetime(*map(int, m.groups()))
    return datetime.fromtimestamp(path.stat().st_mtime)


def collect(paths) -> list[Path]:
    found = []
    for p in map(Path, paths):
        found += sorted(f for f in p.rglob("userdata000*") if SLOT.match(f.name)) if p.is_dir() else [p]
    return found


def _gear(s: dict) -> set[str]:
    out = set()
    for grp in ("inventory", "storage"):
        out |= {f"{x['name'] or x['id']}" + (f" +{x['level']}" if x["kind"] == "weapon" and x["level"] else "") for k in ("weapons", "armor") for x in s[grp][k]}
    return out


def _goods(s: dict) -> set[str]:
    return {x["name"] or str(x["id"]) for g in ("inventory", "storage", "keyItems") for x in s[g]["goods"]}


def history(paths) -> dict:
    rows, skipped, empty, seen = [], [], 0, {}
    for f in sorted(collect(paths), key=stamp):
        try:
            s = summarize(f)
        except BloodborneError as e:
            skipped.append((str(f), str(e)))
            continue
        if s["empty"]:
            empty += 1
            continue
        digest = hashlib.sha1(f.read_bytes()).hexdigest()
        if digest in seen:   # the same save kept twice (BB-Save and bbport both back it up): shown once
            seen[digest]["copies"] += 1
            continue
        seen[digest] = {"time": stamp(f).isoformat(timespec="seconds"), "path": str(f), "copies": 1, "playtimeMs": s["header"]["playtimeMs"],
                        "playtime": s["header"]["playtime"], **s["character"], "bosses": s["bosses"]["defeated"], "_gear": _gear(s), "_goods": _goods(s)}
        rows.append(seen[digest])
    rows.sort(key=lambda r: (r["time"], r["playtimeMs"]))
    notes, changes = [], []
    for a, b in zip(rows, rows[1:]):
        for k in STATS:
            if b["stats"][k] < a["stats"][k]:
                notes.append(f"{b['time']}: {k} dropped from {a['stats'][k]} to {b['stats'][k]} (a respec, or a different character)")
        if b["name"] != a["name"]:
            notes.append(f"{b['time']}: the name changed from {a['name']} to {b['name']}")
        if b["playtimeMs"] < a["playtimeMs"]:
            notes.append(f"{b['time']}: play time went back from {a['playtime']} to {b['playtime']}, so an older save was restored")
        if b["deaths"] < a["deaths"]:
            notes.append(f"{b['time']}: deaths went back from {a['deaths']} to {b['deaths']} (an older save was restored)")
        gone = [x for x in a["bosses"] if x not in b["bosses"]]
        if gone:
            notes.append(f"{b['time']}: {', '.join(gone)} no longer defeated (an older save was restored)")
        new = sorted((b["_gear"] - a["_gear"]) | {f"{x} (item)" for x in b["_goods"] - a["_goods"]})
        killed = [x for x in b["bosses"] if x not in a["bosses"]]
        if new or killed:
            changes.append((b["time"], killed, new))
    for r in rows:
        r.pop("_gear"), r.pop("_goods")
    return {"snapshots": rows, "emptySlots": empty, "skipped": skipped, "notes": notes, "changes": [{"time": t, "bossesDefeated": k, "new": n} for t, k, n in changes]}


def render_history(h: dict) -> str:
    rows = h["snapshots"]
    out = ["# Bloodborne playthrough history", ""]
    if not rows:
        return "\n".join(out + ["No saves with a character were found.", ""])
    last = rows[-1]
    out += [f"**Snapshots:** {len(rows)}  ", f"**First:** {rows[0]['time']}  ", f"**Latest:** {last['time']} ({last['name']}, level {last['level']}, {last['playtime']} played, {last['deaths']} deaths)", "",
            "| Time | Level | Play time | Deaths | Echoes | Insight | Vig | End | Str | Skl | Blt | Arc | Bosses |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        s = r["stats"]
        out.append(f"| {r['time']} | {r['level']} | {r['playtime']} | {r['deaths']} | {r['bloodEchoes']:,} | {r['insight']} | " + " | ".join(str(s[k]) for k in STATS) + f" | {len(r['bosses'])} |")
    out += ["", "## Checks", ""]
    out += [f"- {n}" for n in h["notes"]] or ["- Stats and play time only grow across the snapshots: a straight line."]
    if h["changes"]:
        out += ["", "## What changed between snapshots", ""]
        for c in h["changes"]:
            out.append(f"- **{c['time']}**" + (f" defeated {', '.join(c['bossesDefeated'])};" if c["bossesDefeated"] else "") + (f" new: {', '.join(c['new'])}" if c["new"] else ""))
    out += ["", f"**Empty slots passed over:** {h['emptySlots']}  ", f"**Identical copies folded in:** {sum(r['copies'] - 1 for r in rows)}"]
    if h["skipped"]:
        out += ["", f"## Unreadable ({len(h['skipped'])})", ""] + [f"- {Path(p).parent.parent.name}/{Path(p).name}: {why}" for p, why in h["skipped"]]
    return "\n".join(out) + "\n"
