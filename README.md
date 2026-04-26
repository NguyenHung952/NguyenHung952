# AI Presentation SaaS — Scale & Monetization Ready

Nâng cấp tập trung vào scale, tối ưu chi phí AI, và mô hình kiếm tiền.

## Monetization & Billing
- Credit system: user bị trừ credit khi generate/rewrite.
- Plan tiers:
  - Free: 10 credits/day (daily reset)
  - Pro: unlimited
- Endpoints dùng auth JWT để gắn usage theo user.

## Analytics
- Track usage events: generate, rewrite, save, export.
- API `GET /api/analytics` trả summary theo user.

## Cost Optimization
- Semantic cache key theo `topic + style + slide_count + language + preference`.
- Nếu trùng truy vấn sẽ trả cache.

## Preference Learning
- Bảng `user_preferences` lưu style/tone/avg slide length.
- Pipeline inject preference vào generation style.

## New APIs
- `POST /api/auth/login`
- `POST /api/generate`
- `POST /api/generate/stream`
- `POST /api/rewrite`
- `POST /api/save`
- `GET /api/projects`
- `GET /api/project/{id}`
- `GET /api/share/{id}`
- `GET /api/analytics`

## Realtime Collaboration
- WebSocket `/ws/projects/{project_id}`
- Live sync + shared cursors + basic conflict resolution (last-write-wins).

## Deployment
- `Dockerfile`
- `docker-compose.yml`
- `deploy/nginx.conf`
- GitHub Actions CI: compile backend + docker build

## Frontend Conversion
- Added landing page with CTA at `frontend/src/pages/landing/LandingPage.tsx`.

## Run locally
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

cd ../frontend
npm install
npm run dev
```
