from __future__ import annotations

import json
import os
from typing import Any

import httpx

SYSTEM_PROMPT = (
    "You are a slide generator. Return valid JSON only."
    "Create concise, logical presentation slides."
)


def _build_user_prompt(topic: str, description: str | None, slide_count: int, language: str) -> str:
    return (
        "Generate a presentation plan in JSON array format. "
        "Each slide item must include: title, subtitle(optional), bullets(array of short strings), "
        "image(keyword), layout(title|content|image_text). "
        f"Language: {language}. Topic: {topic}. Description: {description or 'N/A'}. "
        f"Slide count: {slide_count}."
    )


async def generate_slides(topic: str, description: str | None, slide_count: int, language: str) -> list[dict[str, Any]]:
    """Generate slides with OpenAI-compatible API; fallback to deterministic mock data."""
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        return _fallback_slides(topic, description, slide_count, language)

    payload = {
        "model": model,
        "temperature": 0.5,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(topic, description, slide_count, language)},
        ],
    }

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=25.0) as client:
        response = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(raw)

    slides = parsed.get("slides") if isinstance(parsed, dict) else parsed
    if not isinstance(slides, list):
        raise ValueError("Model output is not a slide list")

    return slides


def _fallback_slides(topic: str, description: str | None, slide_count: int, language: str) -> list[dict[str, Any]]:
    intro = "Giới thiệu" if language == "vi" else "Introduction"
    slides: list[dict[str, Any]] = [
        {
            "title": f"{topic}",
            "subtitle": description or intro,
            "bullets": ["Mục tiêu bài trình bày" if language == "vi" else "Presentation goal"],
            "image": topic,
            "layout": "title",
        }
    ]

    for i in range(1, max(slide_count - 1, 1)):
        slides.append(
            {
                "title": f"{topic} - {i}",
                "subtitle": "",
                "bullets": [
                    (f"Ý chính {i}.1" if language == "vi" else f"Key point {i}.1"),
                    (f"Ý chính {i}.2" if language == "vi" else f"Key point {i}.2"),
                    (f"Ví dụ thực tế {i}" if language == "vi" else f"Real-world example {i}"),
                ],
                "image": f"{topic} illustration",
                "layout": "content" if i % 2 else "image_text",
            }
        )

    slides.append(
        {
            "title": "Kết luận" if language == "vi" else "Conclusion",
            "subtitle": "",
            "bullets": [
                "Tóm tắt nội dung chính" if language == "vi" else "Summary of key ideas",
                "Định hướng tiếp theo" if language == "vi" else "Next steps",
            ],
            "image": "summary",
            "layout": "content",
        }
    )

    return slides[:slide_count]
