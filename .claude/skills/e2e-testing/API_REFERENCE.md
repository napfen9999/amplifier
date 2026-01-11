# API Reference

## Authentication

### Get Token
```bash
ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"

TOKEN=$(curl -s -X POST "http://127.0.0.1:54321/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "dev@brandcomposer.test", "password": "DevTest2026"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### Test User
- Email: `dev@brandcomposer.test`
- Password: `DevTest2026`
- User-ID: `2a0ec5e9-e98a-4551-9d47-1ba46e838ca3`

## Interview Flow (Correct Order)

### 1. Create Project
```bash
curl -X POST "http://localhost:8001/api/v1/projects" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Project", "brand_name": "MyBrand", "industry": "Technology"}'
```

### 2. Start Session in Project
```bash
curl -X POST "http://localhost:8001/api/v1/projects/{project_id}/sessions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 3. Send Message
```bash
# IMPORTANT: Field is "message", NOT "content"!
curl -X POST "http://localhost:8001/api/v1/interview/{session_id}/message" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "User input here..."}'
```

### 4. Get State
```bash
curl "http://localhost:8001/api/v1/interview/{session_id}/state" \
  -H "Authorization: Bearer $TOKEN"
```

## Response Format

### ChatResponse
```json
{
  "assistant_message": "...",
  "progress": {
    "layer": "foundation",
    "progress_percent": 55.5,
    "is_frozen": false,
    "confidence_level": "very confident"
  },
  "turn_number": 2,
  "conflict": null,
  "freetext_prompt": null,
  "layer_transition": null
}
```

## Timing Expectations

| Operation | Expected | Notes |
|-----------|----------|-------|
| Auth | <500ms | Token valid for 1h |
| Create Project | <100ms | |
| Start Session | <200ms | Includes Turn 0 |
| Send Message | 12-25s | LLM processing |
| Get State | <100ms | |

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Signature verification failed` | Wrong JWT secret | Check `SUPABASE_JWT_SECRET` in .env |
| `Field required: message` | Wrong field name | Use `"message"` not `"content"` |
| `project_id NOT NULL` | Old API usage | Use projects flow, not `/interview/start` |
| `INTERNAL_ERROR` | Check API logs | `docker compose logs api --tail 50` |
