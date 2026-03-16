# Itera

Itera is an AI-powered personalized learning roadmap generator. Tell it your background and goal, and it builds you a custom curriculum with curated course recommendations — then helps you stay on track with progress tracking, daily planning, and adaptive updates.

## Features

- **AI conversation** - multi-turn chat to understand your background, skills, and goals
- **File upload** - attach a CV, PDF, Word doc, Excel sheet, or text file so the AI can read your background without you having to type it out
- **Voice input** - click the microphone to dictate your message using the Web Speech API built into modern browsers
- **Personalized roadmap** - skill areas, topics, time estimates, and course recommendations
- **Explain any topic** - click "Explain this" on any topic for a beginner-friendly AI breakdown
- **Progress tracking** - check off completed topics with per-area progress bars and an overall completion percentage
- **Daily Study Coach** - set your study hours and days, get a day-by-day AI-generated schedule with today's plan
- **Adaptive roadmap** - regenerate your roadmap to skip completed topics and recalculate remaining time
- **Post-roadmap Q&A** - ask the AI anything about your roadmap after it's generated
- **Session history** - save and reload past roadmaps
- **Dark / Light / Auto theme**
- **JWT authentication**

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 + FastAPI |
| AI | Groq API (LLaMA 3.3 70B) |
| Database | PostgreSQL + Redis |
| ORM | SQLAlchemy (async) + Alembic |
| Frontend | React 19 + Vite + Tailwind CSS |
| State | Zustand (with localStorage persistence) |
| Deployment | Docker + Nginx |

## Getting Started

### Prerequisites
- Docker Desktop
- A [Groq API key](https://console.groq.com) (free)

### Run with Docker

```bash
git clone https://github.com/xK3yx/itera.git
cd itera/itera-backend

# Copy the example env file and fill in your Groq API key
cp .env.example .env

docker compose up --build -d
```

Then open **http://localhost** in your browser.

Migrations run automatically on startup — no manual step needed.

### Run locally (without Docker)

You'll need PostgreSQL running separately. Update `DATABASE_URL` in `.env` to point to `localhost`.

**Backend**
```bash
cd itera-backend
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Frontend**
```bash
cd itera-frontend
npm install
npm run dev
```

Then open **http://localhost:5173**.

### Tests

```bash
# Backend (30 tests)
cd itera-backend
python -m pytest tests/ -v

# Frontend (10 tests)
cd itera-frontend
npm test
```

## Project Structure

```
itera/
├── itera-backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── auth.py         # Register / login
│   │   │   ├── chat.py         # Session messaging + file upload
│   │   │   ├── roadmap.py      # Roadmap, progress, adapt
│   │   │   ├── explain.py      # Topic explanation
│   │   │   └── schedule.py     # Study schedule
│   │   ├── models/
│   │   │   ├── roadmap.py
│   │   │   └── study_schedule.py
│   │   ├── services/
│   │   │   └── ai_service.py   # All Groq AI methods
│   │   └── schemas/            # Pydantic request/response models
│   ├── alembic/versions/       # Database migrations
│   ├── tests/
│   └── docker-compose.yml
└── itera-frontend/
    ├── src/
    │   ├── pages/              # Login, Register, Chat
    │   ├── components/
    │   │   ├── MessageBubble.jsx
    │   │   ├── RoadmapView.jsx
    │   │   └── StudyCoach.jsx
    │   ├── store/
    │   │   ├── chatStore.js
    │   │   ├── progressStore.js
    │   │   └── scheduleStore.js
    │   ├── services/           # Axios API client
    │   └── tests/
    └── Dockerfile
```

## API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login, returns JWT |
| GET | `/api/v1/auth/me` | Get current user |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat/start` | Start new session |
| POST | `/api/v1/chat/{id}/message` | Send message |
| GET | `/api/v1/chat/{id}/history` | Get message history |
| DELETE | `/api/v1/chat/{id}` | Delete session |
| POST | `/api/v1/chat/upload-file` | Extract text from an uploaded file (PDF, Word, Excel, txt) |

### Roadmap
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/roadmap/` | List all roadmaps |
| GET | `/api/v1/roadmap/{id}` | Get roadmap by session |
| PATCH | `/api/v1/roadmap/{id}/progress` | Save completed topic keys |
| POST | `/api/v1/roadmap/{id}/adapt` | Regenerate skipping completed topics |

### Explain
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/explain/topic` | AI explanation for a roadmap topic |

### Study Schedule
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/schedule/generate` | Generate day-by-day study schedule |
| GET | `/api/v1/schedule/{id}` | Get existing schedule |
| GET | `/api/v1/schedule/{id}/today` | Get today's study plan |

## Environment Variables

```env
# App
APP_NAME=Itera
SECRET_KEY=your-secret-key

# Database
POSTGRES_USER=itera_user
POSTGRES_PASSWORD=itera_password
POSTGRES_DB=itera_db
DATABASE_URL=postgresql+asyncpg://itera_user:itera_password@localhost:5432/itera_db

# Redis (optional — falls back to DB if unavailable)
REDIS_URL=redis://localhost:6379/0

# Groq AI
GROQ_API_KEY=your-groq-api-key

# JWT
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
```

Note: when running with Docker, `DATABASE_URL` and `REDIS_URL` are overridden automatically by `docker-compose.yml` to use the correct internal service hostnames.

## Docker Commands

```bash
# Start everything (builds images, runs migrations automatically)
docker compose up --build -d

# View logs
docker compose logs -f api

# Stop
docker compose down

# Full reset (wipes the database volume)
docker compose down -v
```
