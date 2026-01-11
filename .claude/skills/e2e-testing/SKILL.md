---
name: e2e-testing
description: End-to-end testing for Brand Composer. Tests API endpoints, database traceability, and frontend UI via Dev-Browser. Use when testing interview flow, verifying DB persistence, or debugging frontend issues. Triggers on "e2e test", "test interview", "check frontend", "verify DB".
---

# E2E Testing Skill

Quick validation of Brand Composer infrastructure, API, and frontend.

## Quick Start

### 1. Infrastructure Check
```bash
# All services healthy?
curl -s http://localhost:8001/health
curl -s http://localhost:80 | head -5
docker compose ps
```

### 2. Get Auth Token
```bash
ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"
TOKEN=$(curl -s -X POST "http://127.0.0.1:54321/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "dev@brandcomposer.test", "password": "DevTest2026"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### 3. Test Interview Flow
```bash
# Create project
PROJECT=$(curl -s -X POST "http://localhost:8001/api/v1/projects" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Test", "brand_name": "TestBrand"}')
PROJECT_ID=$(echo "$PROJECT" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Start session
SESSION=$(curl -s -X POST "http://localhost:8001/api/v1/projects/$PROJECT_ID/sessions" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{}')
SESSION_ID=$(echo "$SESSION" | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

# Send message (NOTE: field is "message", NOT "content")
curl -s -X POST "http://localhost:8001/api/v1/interview/$SESSION_ID/message" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"message": "Wir helfen kleinen Unternehmen mit professionellem Branding."}'
```

## Critical Knowledge

| Topic | Key Info |
|-------|----------|
| **JWT Secret** | Must be `super-secret-jwt-token-with-at-least-32-characters-long` |
| **API Prefix** | All endpoints under `/api/v1/` |
| **Message Field** | Use `"message"` not `"content"` |
| **Turn Timing** | ~12-25s per turn (target: <5s) |
| **Traceability** | Signals/Seeds/Deltas NOT persisted yet! |

## Reference Files

- [INFRASTRUCTURE.md](INFRASTRUCTURE.md) - Docker, DB access, ports
- [API_REFERENCE.md](API_REFERENCE.md) - Endpoints, auth flow
- [BROWSER_TESTING.md](BROWSER_TESTING.md) - Dev-Browser patterns
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common errors & fixes

## DB Verification

```bash
# Check turns persisted
docker exec -i supabase_db_brand_composer_amplifyier psql -U postgres -d postgres -c \
  "SELECT turn_number, created_at FROM turns WHERE session_id = '$SESSION_ID' ORDER BY turn_number;"

# Check messages persisted
docker exec -i supabase_db_brand_composer_amplifyier psql -U postgres -d postgres -c \
  "SELECT m.role, LEFT(m.content, 50) FROM messages m JOIN turns t ON m.turn_id = t.id WHERE t.session_id = '$SESSION_ID';"
```
