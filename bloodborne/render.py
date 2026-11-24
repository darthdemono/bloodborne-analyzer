"""summary -> Markdown. Bold-label bullets and tables, no emoji, no em dashes."""



def _label(s: dict) -> str:
    n = s.get("name") or f"unnamed {s['kind']} {s['id']}"
    if s["kind"] == "weapon":
        n += (f" +{s['level']}" if s["level"] else "") + (f" ({s['imprint']})" if s["imprint"] else "")
    return n


def _section(title: str, grp: dict) -> list[str]:
    total = sum(len(v) for k, v in grp.items() if k != "gems")
    gems = len(grp["gems"])
    out = [f"### {title} ({total} entries" + (f", {gems} gems and runes" if gems else "") + ")", ""]
    if not total:
        return out + ["Empty.", ""]
    out += ["| Kind | Name | Amount |", "|---|---|---|"]
    for kind in ("weapons", "armor", "goods", "other"):
        out += [f"| {kind[:-1] if kind.endswith('s') else kind} | {_label(s)} | {s['amount']} |" for s in grp[kind]]
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
    b = s["bosses"]
    out += ["", f"### Bosses defeated ({len(b['defeated'])} of {b['tracked']} tracked)", ""]
    out += [f"- {n}" for n in b["defeated"]] or ["None yet."]
    out += [""] + _section("Inventory", s["inventory"]) + _section("Storage", s["storage"]) + _section("Key items", s["keyItems"])
    i = s["integrity"]
    out += [f"**Decoded:** {i['decodedBytes']:,} of {i['fileBytes']:,} bytes. {i['note']}.", ""]
    return "\n".join(out)
