from __future__ import annotations

from difflib import SequenceMatcher


def _is_similar(a: str, b: str, threshold: float = 0.78) -> bool:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio() >= threshold


def deduplicate_outline(outline: list[dict]) -> list[dict]:
    unique: list[dict] = []
    for item in outline:
        title = item.get("title", "")
        if any(_is_similar(title, existing.get("title", "")) for existing in unique):
            continue
        unique.append(item)
    return unique


def build_story(outline: list[dict]) -> list[dict]:
    """Remove duplicates, reorder logically, and group by sections."""
    cleaned = deduplicate_outline(outline)
    if len(cleaned) <= 3:
        return cleaned

    title = cleaned[0]
    intro = cleaned[1]
    body = cleaned[2:-1]
    summary = cleaned[-1]

    grouped: list[dict] = []
    for idx, item in enumerate(body):
        if idx % 3 == 0:
            grouped.append({"title": f"Section {idx // 3 + 1}", "intent": "section"})
        grouped.append(item)

    return [title, intro, *grouped, summary]
