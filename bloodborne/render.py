"""summary -> Markdown. Bold-label bullets and tables, no emoji, no em dashes."""



def _label(s: dict) -> str:
    n = s.get("name") or f"unnamed {s['kind']} {s['id']}"
    if s["kind"] == "weapon":
        n += (f" +{s['level']}" if s["level"] else "") + (f" ({s['imprint']})" if s["imprint"] else "")
    return n


def _slots(s: dict) -> str:
    """Open gem slots of a weapon or armor piece, as 'Radial (empty), Circle (Physical ATK UP +1.1%)'."""
    gem = {g["handle"]: g for g in _GEMS}
    out = []
    for sl in s.get("gemSlots", []):
        if sl["shape"] == "Closed":
            continue
        g = gem.get(sl["gem"])
        out.append(f"{sl['shape']} ({', '.join(e['text'] or str(e['id']) for e in g['effects']) if g else 'empty'})")
    return ", ".join(out)


_GEMS: list = []


def _section(title: str, grp: dict) -> list[str]:
    total = sum(len(v) for k, v in grp.items() if k != "gems")
    gems = len(grp["gems"])
    out = [f"### {title} ({total} entries" + (f", {gems} gems and runes" if gems else "") + ")", ""]
    if not total:
        return out + ["Empty.", ""]
    out += ["| Kind | Name | Amount | Gem slots |", "|---|---|---|---|"]
    for kind in ("weapons", "armor", "goods", "other"):
        out += [f"| {kind[:-1] if kind.endswith('s') else kind} | {_label(s)} | {s['amount']} | {_slots(s)} |" for s in grp[kind]]
    return out + [""]


def render(s: dict) -> str:
    out = [f"# Bloodborne save: {s['file']}", ""]
    if s["empty"]:
        return "\n".join(out + ["No character in this slot.", ""])
    c, h = s["character"], s["header"]
    out += [
        f"**Character:** {c['name']}",
        f"**Origin (id):** {c['origin']}",
        f"**Level:** {c['level']}" + ("" if c["level"] == c["levelFromStats"] else f" (the stats add up to level {c['levelFromStats']}: check this save)"),
        f"**Play time:** {h['playtime']}",
        f"**Deaths:** {c['deaths']}",
        f"**New Game cycle:** " + (f"NG+{c['newGameCycle']}" if c["newGameCycle"] else "NG (first playthrough)"),
        f"**Blood Echoes:** {c['bloodEchoes']:,}",
        f"**Insight:** {c['insight']}",
        f"**Health:** {c['health']['current']} of {c['health']['base']}",
        f"**Stamina:** {c['stamina']['current']} of {c['stamina']['base']}",
        "",
        "| Stat | Value |",
        "|---|---|",
    ]
    out += [f"| {k.title()} | {v} |" for k, v in c["stats"].items()]
    _GEMS[:] = s["gems"]
    eq = s["equipped"]
    out += ["", "### Worn", "", "**Weapon slots (stored order):** " + ", ".join(x or "empty" for x in eq["weapons"]), "**Armor (head, chest, arms, legs):** " + ", ".join(x or "empty" for x in eq["armor"]), ""]
    out += [f"### Blood gems and runes ({len(s['gems'])})", ""]
    if s["gems"]:
        out += ["| Type | Shape | Effects | Fitted to |", "|---|---|---|---|"]
        out += [f"| {g['type']} | {g['shape'] or 'category ' + str(g['category'])} | {'; '.join(e['text'] or str(e['id']) for e in g['effects'])} | {g['fittedTo'] or 'not fitted'} |" for g in s["gems"]]
    else:
        out += ["None."]
    ln = s["lanterns"]
    out += ["", f"### Lanterns lit ({len(ln['lit'])} of {ln['known']} known)", ""]
    out += [f"- {n}" for n in ln["lit"]] or ["None lit." if ln["known"] else "The lamp table is not installed here (db_bb/lamps.json)."]
    b = s["bosses"]
    out += ["", f"### Bosses defeated ({len(b['defeated'])} of {b['tracked']} tracked)", ""]
    out += [f"- {n}" for n in b["defeated"]] or ["None yet."]
    out += [""] + _section("Inventory", s["inventory"]) + _section("Storage", s["storage"]) + _section("Key items", s["keyItems"])
    i = s["integrity"]
    out += [f"**Decoded:** {i['decodedBytes']:,} of {i['fileBytes']:,} bytes. {i['note']}.", ""]
    return "\n".join(out)
