from __future__ import annotations

from typing import Literal

Layout = Literal["title", "content", "image_left", "image_right", "section"]


VISUAL_KEYWORDS = {"architecture", "timeline", "ui", "diagram", "iot", "network", "flow"}


def choose_layout(bullets: list[str], title: str, role: str) -> Layout:
    text = f"{title} {' '.join(bullets)}".lower()
    if role == "title":
        return "title"
    if role == "section":
        return "section"
    if role == "key_point":
        return "content"
    if len(bullets) >= 4:
        return "content"
    if any(token in text for token in VISUAL_KEYWORDS):
        return "image_right"
    return "content"


def slide_theme(role: str) -> dict:
    return {
        "margin_left": 0.6,
        "title_size": 42 if role == "title" else (30 if role == "key_point" else 28),
        "bullet_spacing": 10,
    }
