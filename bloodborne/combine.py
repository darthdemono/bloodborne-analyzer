"""Many summaries -> one history. A straight playthrough only ever adds: a stat that drops, or play time that goes back, is reported."""
import hashlib
import re
from datetime import datetime
from pathlib import Path

from .bb import STATS, summarize
from .container import BloodborneError
from .render import render

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


def _label(x: dict) -> str:
    return f"{x['name'] or x['id']}" + (f" +{x['level']}" if x["kind"] == "weapon" and x["level"] else "")


def _gear(s: dict) -> set[str]:
    return {_label(x) for grp in ("inventory", "storage") for k in ("weapons", "armor") for x in s[grp][k]}


def _amounts(s: dict) -> dict[str, int]:
    """Every goods item by name with its total amount over inventory, storage and key items."""
    out: dict[str, int] = {}
    for g in ("inventory", "storage", "keyItems"):
        for x in s[g]["goods"]:
            k = x["name"] or str(x["id"])
            out[k] = out.get(k, 0) + x["amount"]
    return out


def _gem_text(g: dict) -> str:
    return f"{g['shape'] or 'category ' + str(g['category'])} {g['type']}: " + "; ".join(e["text"] or str(e["id"]) for e in g["effects"])


def hms(ms: int) -> str:
    return f"{ms // 3600000}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}"


def _gained(now: list[str], before: list[str]) -> list[str]:
    """now minus before as a multiset, order kept: two identical gems are two gems."""
    left = list(before)
    out = []
    for x in now:
        if x in left:
            left.remove(x)
        else:
            out.append(x)
    return out


def _step(a: dict, b: dict) -> dict:
    """What changed from snapshot a to snapshot b (both rows carrying their private _s summary)."""
    sa, sb = a["_s"], b["_s"]
    ga, gb = _gear(sa), _gear(sb)
    ma, mb = _amounts(sa), _amounts(sb)
    names = sorted(set(ma) | set(mb))
    stats = {k: b["stats"][k] - a["stats"][k] for k in STATS if b["stats"][k] != a["stats"][k]}
    gems_a = [_gem_text(g) for g in sa["gems"]]
    return {
        "time": b["time"],
        "playMs": b["playtimeMs"] - a["playtimeMs"],
        "level": [a["level"], b["level"]],
        "echoes": [a["bloodEchoes"], b["bloodEchoes"]],
        "insight": [a["insight"], b["insight"]],
        "deaths": b["deaths"] - a["deaths"],
        "stats": stats,
        "bossesDefeated": [x for x in b["bosses"] if x not in a["bosses"]],
        "gear": {"gained": sorted(gb - ga), "lost": sorted(ga - gb)},
        "goods": {"new": [f"{n} x{mb[n]}" for n in names if n not in ma], "gone": [n for n in names if n not in mb],
                  "changed": [f"{n} {ma[n]} to {mb[n]}" for n in names if n in ma and n in mb and ma[n] != mb[n]]},
        "gems": _gained([_gem_text(g) for g in sb["gems"]], gems_a),      # by content: a gem's handle changes between saves
        "lampsLit": [x for x in sb["lanterns"]["lit"] if x not in sa["lanterns"]["lit"]],
        "restored": b["playtimeMs"] < a["playtimeMs"],
    }


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
                        "playtime": s["header"]["playtime"], **s["character"], "bosses": s["bosses"]["defeated"], "_s": s}
        rows.append(seen[digest])
    rows.sort(key=lambda r: (r["time"], r["playtimeMs"]))
    notes, steps = [], []
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
        steps.append(_step(a, b))
    first_seen: dict[str, str] = {}
    for r in rows:
        for x in r["bosses"]:
            first_seen.setdefault(x, r["time"])
    latest = rows[-1]["_s"] if rows else None
    for r in rows:
        r.pop("_s")
    return {"snapshots": rows, "emptySlots": empty, "skipped": skipped, "notes": notes, "changes": steps,
            "bossTimeline": [{"boss": b, "firstSeenDefeated": t} for b, t in first_seen.items()], "latest": latest}


def _signed(n: int) -> str:
    return f"+{n:,}" if n >= 0 else f"-{-n:,}"


def _step_lines(c: dict) -> list[str]:
    out, play = [], c["playMs"]
    if c["restored"]:
        out.append("- **An older save was restored here**: play time went back, so the numbers below are against the snapshot before it.")
    if c["level"][0] != c["level"][1]:
        out.append(f"- Level {c['level'][0]} to {c['level'][1]} ({_signed(c['level'][1] - c['level'][0])})")
    if c["stats"]:
        out.append("- Stats: " + ", ".join(f"{k} {_signed(v)}" for k, v in c["stats"].items()))
    if c["echoes"][0] != c["echoes"][1]:
        out.append(f"- Blood Echoes {c['echoes'][0]:,} to {c['echoes'][1]:,}")
    if c["insight"][0] != c["insight"][1]:
        out.append(f"- Insight {c['insight'][0]} to {c['insight'][1]}")
    if c["deaths"]:
        out.append(f"- Deaths {_signed(c['deaths'])}")
    if c["bossesDefeated"]:
        out.append("- Defeated: " + ", ".join(c["bossesDefeated"]))
    g = c["gear"]
    if g["gained"]:
        out.append("- New gear: " + ", ".join(g["gained"]))
    if g["lost"]:
        out.append("- Gear gone: " + ", ".join(g["lost"]))
    gd = c["goods"]
    if gd["new"]:
        out.append("- New items: " + ", ".join(gd["new"]))
    if gd["gone"]:
        out.append("- Used up or gone: " + ", ".join(gd["gone"]))
    if gd["changed"]:
        out.append("- Amounts: " + ", ".join(gd["changed"]))
    if c["gems"]:
        out.append("- New blood gems and runes: " + "; ".join(c["gems"]))
    if c["lampsLit"]:
        out.append("- Lamps lit: " + ", ".join(c["lampsLit"]))
    return out or ["- No change in the tracked values."]


def render_history(h: dict) -> str:
    rows = h["snapshots"]
    out = ["# Bloodborne playthrough history", ""]
    if not rows:
        return "\n".join(out + ["No saves with a character were found.", ""])
    first, last = rows[0], rows[-1]
    s = h["latest"]
    eq = s["equipped"]
    out += ["## Overview", "",
            f"**Character:** {last['name']}  ", f"**Snapshots:** {len(rows)} distinct saves ({sum(r['copies'] - 1 for r in rows)} identical copies folded in)  ",
            f"**First:** {first['time']}  ", f"**Latest:** {last['time']}  ",
            f"**Level:** {first['level']} to {last['level']}  ", f"**Play time:** {first['playtime']} to {last['playtime']}  ", f"**Deaths:** {first['deaths']} to {last['deaths']}  ",
            f"**Blood Echoes (latest):** {last['bloodEchoes']:,}  ", f"**Insight (latest):** {last['insight']}  ",
            f"**Bosses defeated:** {len(last['bosses'])} of {s['bosses']['tracked']}  ",
            f"**Lamps lit:** {len(s['lanterns']['lit'])} of {s['lanterns']['known']}: " + (", ".join(s["lanterns"]["lit"]) or "none") + "  ",
            "**Worn now:** " + ", ".join(x or "empty" for x in eq["weapons"] + eq["armor"]), "",
            "## Timeline", "",
            "| Time | Level | Play time | Deaths | Echoes | Insight | Vig | End | Str | Skl | Blt | Arc | Bosses |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        st = r["stats"]
        out.append(f"| {r['time']} | {r['level']} | {r['playtime']} | {r['deaths']} | {r['bloodEchoes']:,} | {r['insight']} | " + " | ".join(str(st[k]) for k in STATS) + f" | {len(r['bosses'])} |")
    out += ["", "## Checks", ""]
    out += [f"- {n}" for n in h["notes"]] or ["- Stats and play time only grow across the snapshots: a straight line."]
    out += ["", "## Boss timeline", ""]
    out += [f"- {b['boss']}: first seen defeated in the snapshot of {b['firstSeenDefeated']}" for b in h["bossTimeline"]] or ["No boss defeated in any snapshot."]
    if h["changes"]:
        out += ["", "## Between snapshots", ""]
        for c in h["changes"]:
            out += [f"### {c['time']} ({'+' if c['playMs'] >= 0 else '-'}{hms(abs(c['playMs']))} played since the previous snapshot)", ""] + _step_lines(c) + [""]
    full = render(s).split("\n")
    out += ["## Latest save in full", "", *[("#" + ln if ln.startswith("#") else ln) for ln in full[2:]]]
    out += [f"**Empty slots passed over:** {h['emptySlots']}  "]
    if h["skipped"]:
        out += ["", f"## Unreadable ({len(h['skipped'])})", ""] + [f"- {Path(p).parent.parent.name}/{Path(p).name}: {why}" for p, why in h["skipped"]]
    return "\n".join(out) + "\n"
