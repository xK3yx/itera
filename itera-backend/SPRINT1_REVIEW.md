# Sprint 1 Review — Itera Backend

**Date:** March 2026  
**Sprint Duration:** 2 weeks  
**Status:** ✅ COMPLETE

---

## What Was Built

### Authentication System
- User registration with email + username uniqueness validation
- JWT login with bcrypt password hashing
- Protected endpoints via Bearer token middleware

### Database Layer
- PostgreSQL with async SQLAlchemy
- 4 models: User, Session, Message, Roadmap
- Alembic migrations applied successfully
- Redis caching for conversation history (1hr TTL)

### AI Integration (Groq + Llama 3.3 70B)
- Two-phase conversation: Discovery → Roadmap Generation
- Structured JSON output with skill areas, topics, time estimates
- Experience-adjusted time estimates
- Fallback handling for malformed AI responses

### API Endpoints (all P0 complete)
| Endpoint | Method | Status |
|---|---|---|
| /api/v1/auth/register | POST | ✅ |
| /api/v1/auth/login | POST | ✅ |
| /api/v1/auth/me | GET | ✅ |
| /api/v1/chat/start | POST | ✅ |
| /api/v1/chat/{id}/message | POST | ✅ |
| /api/v1/chat/{id}/history | GET | ✅ |
| /api/v1/roadmap/{id} | GET | ✅ |
| /api/v1/roadmap/ | GET | ✅ |
| /api/v1/courses/search | GET | ✅ |
| /health | GET | ✅ |

### Course Data Layer
- AI-powered course search (no hardcoded data)
- Returns real courses from Coursera, Udemy, freeCodeCamp, YouTube
- Filters by topic, level, and max results

### Testing
- 30 tests total — all passing
- Unit tests: AI service, auth, course service
- Integration tests: full chat-to-roadmap flow, auth flows, security tests

---

## Backend Gate Checklist

- [x] All P0 API endpoints return correct responses
- [x] Claude/Groq integration returns valid structured roadmap JSON
- [x] Pytest suite passes — 30/30 tests green
- [x] Docker Compose starts cleanly (FastAPI + Postgres + Redis healthy)
- [x] OpenAPI docs at /docs fully populated

---

## Sprint Retro

### What Went Well
- Groq API (free tier) worked excellently as Claude API replacement
- AI-powered course search avoids need for maintaining static course database
- Test infrastructure solid despite SQLite/PostgreSQL type differences

### Challenges
- Switched from Gemini → Groq due to regional quota limitations
- SQLite UUID/JSONB incompatibility required custom type patching in tests
- httpx/groq version conflict required pinning specific versions

### Decisions Made
- Used Groq (Llama 3.3 70B) instead of Claude API for cost/availability
- AI-powered course search instead of static JSON dataset
- bcrypt pinned to 4.0.1 for passlib compatibility

---

## Ready for Sprint 2

Backend is fully complete and signed off.  
Sprint 2 begins: React frontend development.

**Tech stack for Sprint 2:** React 18 + Vite + Tailwind CSS + Zustand