"""summary -> Markdown. Bold-label bullets and tables, no emoji, no em dashes."""


def render(s: dict) -> str:
    out = [f"# Bloodborne save: {s['file']}", ""]
    if s["empty"]:
        return "\n".join(out + ["No character in this slot.", ""])
    c = s["character"]
    out += [
        f"**Character:** {c['name']}",
        f"**Level:** {c['level']}" + ("" if c["level"] == c["levelFromStats"] else f" (the stats add up to level {c['levelFromStats']}: check this save)"),
        f"**Blood Echoes:** {c['bloodEchoes']:,}",
        f"**Insight:** {c['insight']}",
        f"**Health / Stamina:** {c['health']} / {c['stamina']}",
        "",
        "| Stat | Value |",
        "|---|---|",
    ]
    out += [f"| {k.title()} | {v} |" for k, v in c["stats"].items()]
    i = s["integrity"]
    out += ["", f"**Decoded:** {i['decodedBytes']} of {i['fileBytes']:,} bytes. {i['note']}.", ""]
    return "\n".join(out)
