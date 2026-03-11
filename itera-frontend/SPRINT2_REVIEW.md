# Sprint 2 Review — Frontend + Polish + Deployment

**Sprint Duration:** Weeks 3–4  
**Status:** ✅ Complete

## Goals Achieved

All Sprint 2 milestones met:
- React frontend connected to live backend
- Full user journey working end-to-end
- Docker production build deployed via Nginx
- All P0 bugs resolved

## Tasks Completed

| Task | Description | Status |
|------|-------------|--------|
| 2.1 | React + Vite + Tailwind + Zustand setup | ✅ |
| 2.2 | Login / Register pages with JWT auth | ✅ |
| 2.3 | Chat interface with typing indicator | ✅ |
| 2.4 | Axios API service layer with interceptors | ✅ |
| 2.5 | Roadmap display with collapsible skill areas | ✅ |
| 2.6 | Course cards with platform search URLs | ✅ |
| 2.7 | Session history panel | ✅ |
| 2.8 | Responsive design + ARIA accessibility | ✅ |
| 2.9 | Frontend tests (Vitest) — 10 tests passing | ✅ |
| 2.10 | Docker production build with Nginx | ✅ |
| 2.11 | End-to-end testing — full user journey | ✅ |
| 2.12 | README, Sprint review, final polish | ✅ |

## Bug Fixes & Improvements

1. Fixed `/me` endpoint returning nothing
2. Added `weekly_hours` and `estimated_weeks` to Roadmap model + migration
3. Fixed session service not saving weekly/weeks fields from AI response
4. Replaced N+1 query in `get_all_roadmaps` with single JOIN
5. Switched sync Groq client to AsyncGroq in `ai_service.py` and `course_service.py`
6. Fixed error messages not showing in red in chat
7. Fixed dark mode not applying on Login/Register pages
8. Fixed invalid Tailwind class `gray-750`
9. Updated deprecated `datetime.utcnow()` to `datetime.now(timezone.utc)`
10. Fixed `is_active` nullable column → NOT NULL DEFAULT TRUE
11. Added Zustand persist middleware for auth token survival on refresh
12. Added `email-validator` to requirements.txt
13. Fixed AI-generated course URLs returning 404 → replaced with platform search URLs
14. Fixed session history showing empty → corrected response key parsing
15. Added sticky header so navigation always visible while scrolling
16. Added dark/light/auto theme toggle persisted to localStorage
17. Added delete button for sessions in history panel

## Frontend Test Results
```
Test Files  3 passed (3)
Tests       10 passed (10)
```

## Backend Test Results
```
30 tests passing
Coverage: >80% on core services
```

## Definition of Done — Frontend Gate ✅

- [x] User can register, log in, and receive a JWT
- [x] Chat interface sends messages and receives AI responses
- [x] Roadmap displayed with all skill areas, topics, and courses
- [x] Application runs in Docker production mode (Nginx + FastAPI)
- [x] No P0 bugs outstanding

## Retrospective

**What went well:**
- Backend-first approach paid off — frontend integration was smooth
- Zustand made state management simple and predictable
- Docker Compose made the full stack easy to run in one command

**What was challenging:**
- AI-generated course URLs were invalid — solved with platform search URL strategy
- Tailwind dark mode required touching every component
- Async/sync Groq client mismatch caused subtle performance issues

**What to improve next:**
- Add PDF export of roadmap (Post-MVP)
- Add email notifications (Post-MVP)
- Consider streaming AI responses for faster perceived performance
```

---