from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SlideRole = Literal["title", "introduction", "section", "content", "key_point", "summary"]


class GenerateSlidesRequest(BaseModel):
    topic: str = Field(min_length=2)
    description: str | None = None
    slide_count: int = Field(default=6, ge=3, le=30)
    language: Literal["vi", "en"] = "vi"
    theme: Literal["minimal", "business", "colorful"] = "minimal"
    style: Literal["professional", "casual", "storytelling"] = "professional"


class Slide(BaseModel):
    title: str
    subtitle: str | None = None
    bullets: list[str] = Field(default_factory=list)
    role: SlideRole = "content"
    summary: str | None = None
    image: str | None = None  # backwards compatibility
    image_keyword: str | None = None
    image_url: str | None = None
    layout: Literal["title", "content", "image_left", "image_right", "section"] = "content"


class GenerateSlidesResponse(BaseModel):
    slides: list[Slide]


class SaveProjectRequest(BaseModel):
    topic: str
    payload: GenerateSlidesResponse


class SaveProjectResponse(BaseModel):
    project_id: int


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RewriteRequest(BaseModel):
    text: str
    mode: Literal["shorten", "expand", "rewrite_tone"]
    tone: Literal["professional", "casual", "storytelling"] = "professional"
