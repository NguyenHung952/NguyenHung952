from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from time import monotonic

import jwt
from fastapi import Depends, FastAPI, HTTPException, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.models import (
    GenerateSlidesRequest,
    GenerateSlidesResponse,
    LoginRequest,
    LoginResponse,
    RewriteRequest,
    SaveProjectRequest,
    SaveProjectResponse,
    Slide,
)
from export.pptx_service import build_pptx
from services.ai_pipeline import AIPipeline
from services.analytics_service import log_event, usage_summary
from services.billing_service import check_credits, consume_credits, reset_daily_free_quota
from services.image_service import fetch_image

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("slides-saas")

app = FastAPI(title="Auto Slide Generator API", version="0.5.0")
pipeline = AIPipeline()
security = HTTPBearer(auto_error=False)
SECRET = os.getenv("JWT_SECRET", "dev-secret")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_CACHE: dict[str, dict] = {}
_CACHE_TTL_SECONDS = 600
DB_PATH = Path(__file__).parent / "slides.db"
ROOMS: dict[int, dict] = {}


def _init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT UNIQUE NOT NULL,
              password TEXT NOT NULL,
              credits INTEGER NOT NULL DEFAULT 10,
              plan TEXT NOT NULL DEFAULT 'free',
              last_reset TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
              user_id INTEGER PRIMARY KEY,
              style TEXT DEFAULT 'professional',
              tone TEXT DEFAULT 'formal',
              avg_slide_length INTEGER DEFAULT 5
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER,
              topic TEXT NOT NULL,
              payload TEXT NOT NULL,
              created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER,
              event TEXT NOT NULL,
              metadata TEXT,
              created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            "INSERT OR IGNORE INTO users(username, password, credits, plan, last_reset) VALUES('demo', 'demo123', 10, 'free', ?)",
            (datetime.utcnow().strftime("%Y-%m-%d"),),
        )
        conn.execute("INSERT OR IGNORE INTO user_preferences(user_id) VALUES(1)")
        conn.commit()


_init_db()


def _semantic_cache_key(payload: GenerateSlidesRequest, pref_style: str | None) -> str:
    seed = f"{payload.topic}|{payload.style}|{pref_style or ''}|{payload.slide_count}|{payload.language}"
    return hashlib.sha256(seed.encode()).hexdigest()


def _get_user_id(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> int | None:
    if not credentials:
        return None
    try:
        data = jwt.decode(credentials.credentials, SECRET, algorithms=["HS256"])
        return int(data["sub"])
    except Exception:
        return None


def _require_user(user_id: int | None) -> int:
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user_id


def _load_preferences(user_id: int | None) -> dict:
    if not user_id:
        return {"style": None, "tone": None, "avg_slide_length": None}
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT style, tone, avg_slide_length FROM user_preferences WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return {"style": None, "tone": None, "avg_slide_length": None}
    return {"style": row[0], "tone": row[1], "avg_slide_length": row[2]}


async def _build_with_retry(payload: GenerateSlidesRequest, user_id: int | None) -> list[dict]:
    prefs = _load_preferences(user_id)
    effective_style = prefs["style"] or payload.style
    key = _semantic_cache_key(payload, effective_style)

    now = monotonic()
    if key in _CACHE and now - _CACHE[key]["ts"] < _CACHE_TTL_SECONDS:
        return _CACHE[key]["value"]

    for attempt in range(2):
        slides = await pipeline.build_presentation(payload.topic, payload.slide_count, payload.language, effective_style)
        if all(len(s.get("bullets", [])) <= 5 and all(len(str(b).split()) <= 10 for b in s.get("bullets", [])) for s in slides):
            _CACHE[key] = {"ts": now, "value": slides}
            return slides
        if attempt == 1:
            clean = [pipeline._validate_slide(s) for s in slides]
            _CACHE[key] = {"ts": now, "value": clean}
            return clean
    return []


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    reset_daily_free_quota()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT id FROM users WHERE username = ? AND password = ?", (payload.username, payload.password)).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = jwt.encode({"sub": str(row[0]), "username": payload.username}, SECRET, algorithm="HS256")
    return LoginResponse(access_token=token)


@app.post("/api/generate", response_model=GenerateSlidesResponse)
async def generate(payload: GenerateSlidesRequest, user_id: int | None = Depends(_get_user_id)) -> GenerateSlidesResponse:
    if user_id:
        try:
            check_credits(user_id, cost=max(1, payload.slide_count // 5))
        except ValueError as exc:
            raise HTTPException(status_code=402, detail=str(exc)) from exc

    slides = await _build_with_retry(payload, user_id)
    normalized = [Slide(**{**s, "image": s.get("image_keyword")}) for s in slides]

    if user_id:
        consume_credits(user_id, cost=max(1, payload.slide_count // 5))
        log_event(user_id, "generate_slide", metadata=str(payload.slide_count))

    return GenerateSlidesResponse(slides=normalized)


@app.post("/api/generate/stream")
async def generate_stream(payload: GenerateSlidesRequest, user_id: int | None = Depends(_get_user_id)) -> StreamingResponse:
    if user_id:
        try:
            check_credits(user_id, cost=max(1, payload.slide_count // 5))
        except ValueError as exc:
            raise HTTPException(status_code=402, detail=str(exc)) from exc

    async def event_stream() -> AsyncIterator[str]:
        prefs = _load_preferences(user_id)
        style = prefs["style"] or payload.style
        outline = await pipeline.generate_outline(payload.topic, payload.slide_count, payload.language, style)
        built: list[dict] = []
        context: list[str] = []
        for item in outline[: payload.slide_count]:
            expanded = await pipeline.expand_slide(item, context, payload.language, style)
            refined = await pipeline.refine_slide(expanded, context, payload.language, style)
            built.append(refined)
            context.append(refined.get("summary") or refined.get("title", ""))
        built = pipeline._assign_roles(built)
        for slide in built:
            slide["image"] = slide.get("image_keyword")
            yield f"data: {json.dumps(slide, ensure_ascii=False)}\n\n"

    if user_id:
        consume_credits(user_id, cost=max(1, payload.slide_count // 5))
        log_event(user_id, "generate_slide", metadata=f"stream:{payload.slide_count}")

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/image")
async def image(keyword: str) -> dict[str, str]:
    return {"image_url": fetch_image(keyword)}


@app.post("/api/save", response_model=SaveProjectResponse)
async def save_project(payload: SaveProjectRequest, user_id: int | None = Depends(_get_user_id)) -> SaveProjectResponse:
    raw = payload.payload.model_dump_json()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("INSERT INTO projects(user_id, topic, payload) VALUES (?, ?, ?)", (user_id, payload.topic, raw))
        conn.commit()
        project_id = int(cur.lastrowid)
    if user_id:
        log_event(user_id, "save_project", metadata=str(project_id))
    return SaveProjectResponse(project_id=project_id)


@app.get("/api/projects")
async def list_projects(user_id: int | None = Depends(_get_user_id)) -> dict:
    uid = _require_user(user_id)
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT id, topic, created_at FROM projects WHERE user_id = ? ORDER BY id DESC", (uid,)).fetchall()
    return {"projects": [{"id": r[0], "topic": r[1], "created_at": r[2]} for r in rows]}


@app.get("/api/project/{project_id}", response_model=GenerateSlidesResponse)
async def get_project(project_id: int) -> GenerateSlidesResponse:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT payload FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return GenerateSlidesResponse(**json.loads(row[0]))


@app.get("/api/share/{project_id}", response_model=GenerateSlidesResponse)
async def share_project(project_id: int) -> GenerateSlidesResponse:
    return await get_project(project_id)


@app.post("/api/rewrite")
async def rewrite(payload: RewriteRequest, user_id: int | None = Depends(_get_user_id)) -> dict[str, str]:
    if user_id:
        try:
            check_credits(user_id, 1)
        except ValueError as exc:
            raise HTTPException(status_code=402, detail=str(exc)) from exc

    text = payload.text.strip()
    if payload.mode == "shorten":
        result = " ".join(text.split()[: max(3, len(text.split()) // 2)])
    elif payload.mode == "expand":
        result = f"{text}. Additional context: impact, examples, and next step."
    else:
        tone_map = {"professional": "In a formal tone:", "casual": "In a friendly tone:", "storytelling": "In a narrative tone:"}
        result = f"{tone_map[payload.tone]} {text}"

    if user_id:
        consume_credits(user_id, 1)
        log_event(user_id, "rewrite", metadata=payload.mode)

    return {"result": result}


@app.get("/api/analytics")
async def analytics(user_id: int | None = Depends(_get_user_id)) -> dict:
    uid = _require_user(user_id)
    return {"usage": usage_summary(uid)}


@app.websocket("/ws/projects/{project_id}")
async def ws_project(websocket: WebSocket, project_id: int) -> None:
    await websocket.accept()
    room = ROOMS.setdefault(project_id, {"connections": [], "doc": {}, "cursors": {}})
    room["connections"].append(websocket)
    await websocket.send_json({"type": "connected", "project_id": project_id, "doc": room["doc"]})
    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            if message_type == "cursor":
                room["cursors"][data.get("user", "anon")] = data.get("position")
            elif message_type == "edit":
                # last-write-wins conflict resolution
                room["doc"] = data.get("doc", room["doc"])
            for conn in list(room["connections"]):
                await conn.send_json({"type": "sync", "doc": room["doc"], "cursors": room["cursors"]})
    except Exception as exc:
        logger.warning("ws disconnected: %s", exc)
    finally:
        if websocket in room["connections"]:
            room["connections"].remove(websocket)
        await websocket.close()


@app.post("/api/export")
async def export_pptx(payload: GenerateSlidesResponse, user_id: int | None = Depends(_get_user_id)) -> Response:
    if user_id:
        log_event(user_id, "export", metadata=str(len(payload.slides)))
    pptx_bytes = build_pptx([slide.model_dump() for slide in payload.slides])
    return Response(
        content=pptx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": 'attachment; filename="generated-slides.pptx"'},
    )


@app.get("/api/cache")
async def cache_debug() -> dict:
    return {"entries": len(_CACHE), "keys": list(_CACHE.keys())[:25]}
