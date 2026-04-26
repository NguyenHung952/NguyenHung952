from __future__ import annotations

import json
import os
from typing import Any

import httpx

from services.design_engine import choose_layout
from services.image_service import fetch_image
from services.story_engine import build_story

DESIGNER_PROMPT = """You are a professional presentation designer.

Constraints:
- Max 5 bullets per slide
- Each bullet <= 10 words
- No full sentences
- Use concise, impactful phrasing
- Avoid repetition
- Each slide must have role in: title, introduction, section, content, key_point, summary
- Ensure each slide does NOT repeat previous slides
- Ensure each slide logically follows previous slides
- Add new information only

Return JSON only.
"""

STYLE_TONE = {
    "professional": "formal, concise",
    "casual": "friendly, easy-going",
    "storytelling": "engaging, narrative-driven",
}


class AIPipeline:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    async def generate_outline(self, topic: str, slide_count: int, language: str = "vi", style: str = "professional") -> list[dict[str, Any]]:
        if not self.api_key:
            outline = [
                {"title": f"{topic}", "intent": "title"},
                {"title": "Overview", "intent": "introduction"},
                *[{"title": f"{topic} - {idx}", "intent": "content"} for idx in range(1, max(slide_count - 2, 1))],
                {"title": "Key takeaways", "intent": "key_point"},
                {"title": "Kết luận" if language == "vi" else "Conclusion", "intent": "summary"},
            ]
            return build_story(outline[:slide_count])

        prompt = (
            f"Create outline with {slide_count} slides for topic: {topic}. Language: {language}. "
            f"Style: {style}. Tone: {STYLE_TONE.get(style, 'formal, concise')}. "
            "Return JSON array only with keys: title, intent."
        )
        outline = await self._chat_json_array(prompt)
        return build_story(outline)

    async def expand_slide(self, outline_item: dict[str, Any], context: list[str], language: str = "vi", style: str = "professional") -> dict[str, Any]:
        title = outline_item.get("title", "Untitled")
        intent = outline_item.get("intent", "content")

        if not self.api_key:
            role = intent if intent in {"title", "introduction", "section", "content", "key_point", "summary"} else "content"
            bullets = [
                "Định nghĩa ngắn" if language == "vi" else "Quick definition",
                f"Không trùng: {len(context)+1}" if language == "vi" else f"Non-redundant: {len(context)+1}",
                "Ứng dụng" if language == "vi" else "Use case",
            ]
            slide = {
                "title": title,
                "subtitle": "",
                "bullets": bullets,
                "role": role,
                "layout": choose_layout(bullets, title, role),
                "image_keyword": title,
            }
            slide["image_url"] = fetch_image(slide["image_keyword"])
            slide["summary"] = " | ".join(bullets[:2])
            return slide

        prompt = (
            f"Expand this outline item into one slide JSON. language={language}. "
            f"Style: {style}. Tone: {STYLE_TONE.get(style, 'formal, concise')}. "
            f"Previous context summaries: {json.dumps(context[-8:])}. "
            f"Input: {json.dumps(outline_item)}. "
            "Choose layout based on content: many bullets->content, visual topic->image_right, emphasis->key_point. "
            "Output keys exactly: title, subtitle, bullets, layout, image_keyword, role, summary"
        )
        slide = await self._chat_json_object(prompt)
        slide["image_url"] = fetch_image(slide.get("image_keyword", title))
        return slide

    async def refine_slide(self, slide: dict[str, Any], context: list[str], language: str = "vi", style: str = "professional") -> dict[str, Any]:
        if not self.api_key:
            return self._validate_slide(slide)

        prompt = (
            f"Refine this slide for clarity and consistency. language={language}. "
            f"Style: {style}. Tone: {STYLE_TONE.get(style, 'formal, concise')}. "
            f"Avoid overlap with previous summaries: {json.dumps(context[-8:])}. "
            f"Keep JSON schema unchanged. Input: {json.dumps(slide)}"
        )
        refined = await self._chat_json_object(prompt)
        refined.setdefault("image_keyword", slide.get("image_keyword", refined.get("title", "presentation")))
        refined.setdefault("image_url", slide.get("image_url") or fetch_image(refined["image_keyword"]))
        refined.setdefault("summary", slide.get("summary", refined.get("title", "")))
        return self._validate_slide(refined)

    async def build_presentation(self, topic: str, slide_count: int, language: str = "vi", style: str = "professional") -> list[dict[str, Any]]:
        outline = await self.generate_outline(topic, slide_count, language, style)
        slides: list[dict[str, Any]] = []
        context: list[str] = []

        for item in outline[:slide_count]:
            expanded = await self.expand_slide(item, context, language, style)
            refined = await self.refine_slide(expanded, context, language, style)
            slides.append(refined)
            context.append(refined.get("summary") or refined.get("title", ""))

        slides = self._assign_roles(slides)
        for s in slides:
            s["layout"] = choose_layout(s.get("bullets", []), s.get("title", ""), s.get("role", "content")) if s.get("layout") not in {"title", "section"} else s["layout"]
        return slides

    def _assign_roles(self, slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not slides:
            return slides
        for idx, slide in enumerate(slides):
            if idx == 0:
                slide["role"] = "title"
                slide["layout"] = "title"
            elif idx == 1:
                slide["role"] = "introduction"
            elif idx == len(slides) - 1:
                slide["role"] = "summary"
            elif slide.get("layout") == "section":
                slide["role"] = "section"
            elif idx % 4 == 0:
                slide["role"] = "key_point"
            else:
                slide["role"] = "content"
        return slides

    def _validate_slide(self, slide: dict[str, Any]) -> dict[str, Any]:
        bullets = slide.get("bullets") or []
        valid_bullets = []
        for bullet in bullets[:5]:
            words = str(bullet).strip().split()
            valid_bullets.append(" ".join(words[:10]))

        role = slide.get("role", "content")
        if role not in {"title", "introduction", "section", "content", "key_point", "summary"}:
            role = "content"

        layout = slide.get("layout") or choose_layout(valid_bullets, slide.get("title", ""), role)
        if layout not in {"title", "content", "image_left", "image_right", "section"}:
            layout = "content"

        return {
            "title": slide.get("title", "Untitled"),
            "subtitle": slide.get("subtitle", ""),
            "bullets": valid_bullets,
            "layout": layout,
            "role": role,
            "summary": slide.get("summary", slide.get("title", "")),
            "image_keyword": slide.get("image_keyword", slide.get("title", "presentation")),
            "image_url": slide.get("image_url", fetch_image(slide.get("image_keyword", "presentation"))),
        }

    async def _chat_json_array(self, user_prompt: str) -> list[dict[str, Any]]:
        result = await self._chat(user_prompt)
        payload = json.loads(result)
        if isinstance(payload, dict) and "items" in payload:
            payload = payload["items"]
        if not isinstance(payload, list):
            raise ValueError("Expected JSON array from model")
        return payload

    async def _chat_json_object(self, user_prompt: str) -> dict[str, Any]:
        result = await self._chat(user_prompt)
        payload = json.loads(result)
        if not isinstance(payload, dict):
            raise ValueError("Expected JSON object from model")
        return payload

    async def _chat(self, user_prompt: str) -> str:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY missing")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        body = {
            "model": self.model,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": DESIGNER_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=25.0) as client:
            res = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=body)
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"]
