# Itera 🗺

Itera is an AI-powered personalized learning roadmap generator. Tell it your background and goal, and it builds you a custom curriculum with curated course recommendations.

## Features

- 🤖 AI-powered multi-turn conversation to understand your background
- 🗺 Personalized learning roadmap with skill areas, topics, and time estimates
- 📚 Course recommendations from Coursera, Udemy, YouTube, and more
- 💾 Session history — save and reload past roadmaps
- 🌙 Dark / Light / Auto theme
- 🔐 JWT authentication

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 + FastAPI |
| AI | Groq API (Llama 3.3 70B) |
| Database | PostgreSQL + Redis |
| Frontend | React 18 + Vite + Tailwind CSS |
| State | Zustand |
| Deployment | Docker + Nginx |

## Getting Started

### Prerequisites
- Docker Desktop
- Git

### Run the app
```bash
git clone https://github.com/xK3yx/itera.git
cd itera/itera-backend

# Add your environment variables
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

docker-compose up --build
```

Then open **http://localhost** in your browser.

### Run migrations (first time only)
```bash
docker-compose exec api alembic upgrade head
```

### Run backend tests
```bash
cd itera-backend
docker-compose exec api pytest
```

### Run frontend tests
```bash
cd itera-frontend
npm test
```

## Project Structure
```
itera/
├── itera-backend/          # FastAPI backend
│   ├── app/
│   │   ├── routers/        # API endpoints
│   │   ├── models/         # SQLAlchemy models
│   │   ├── services/       # AI, chat, course logic
│   │   ├── middleware/     # Auth middleware
│   │   └── schemas/        # Pydantic schemas
│   ├── tests/              # Pytest test suite
│   └── docker-compose.yml
└── itera-frontend/         # React frontend
    ├── src/
    │   ├── pages/          # Login, Register, Chat
    │   ├── components/     # UI components
    │   ├── store/          # Zustand stores
    │   ├── services/       # Axios API client
    │   └── tests/          # Vitest test suite
    └── Dockerfile
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/auth/register | Register new user |
| POST | /api/v1/auth/login | Login, returns JWT |
| POST | /api/v1/chat/start | Start new session |
| POST | /api/v1/chat/{id}/message | Send message |
| GET | /api/v1/chat/{id}/history | Get chat history |
| GET | /api/v1/roadmap/ | Get all roadmaps |
| GET | /api/v1/roadmap/{id} | Get roadmap by session |
| DELETE | /api/v1/chat/{id} | Delete session |

## Environment Variables
```env
DATABASE_URL=postgresql+asyncpg://user:password@db:5432/itera
REDIS_URL=redis://redis:6379
SECRET_KEY=your-secret-key
GROQ_API_KEY=your-groq-api-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=itera
```