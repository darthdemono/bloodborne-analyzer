"""Does this save add up? Every rule here is an invariant that holds on real saves; a failure means a damaged or hand-edited file."""
from .bb import BASE_LEVEL_SUM, STATS

STAT_MAX = 99


def validate(s: dict) -> list[str]:
    """Findings as plain sentences. An empty list means the rules found nothing wrong."""
    if s.get("empty"):
        return []
    c, out = s["character"], []
    total = sum(c["stats"].values())
    if c["level"] != total - BASE_LEVEL_SUM:
        out.append(f"level {c['level']} but the six stats add up to level {total - BASE_LEVEL_SUM}")
    for k, v in c["stats"].items():
        if not 1 <= v <= STAT_MAX:
            out.append(f"{k} is {v}, outside 1 to {STAT_MAX}")
    if not c["name"] or not c["name"].isprintable():
        out.append("the character name is empty or has unprintable characters")
    if c["health"] <= 0 or c["stamina"] <= 0:
        out.append("health or stamina is zero")
    return out
