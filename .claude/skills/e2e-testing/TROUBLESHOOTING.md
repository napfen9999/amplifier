# Troubleshooting Guide

## Authentication Errors

### "Token validation failed: Signature verification failed"

**Cause**: JWT Secret mismatch between Supabase and API container

**Fix**:
1. Check Supabase secret:
   ```bash
   docker exec supabase_auth_brand_composer_amplifyier env | grep GOTRUE_JWT_SECRET
   ```
2. Ensure `.env` matches:
   ```
   SUPABASE_JWT_SECRET=super-secret-jwt-token-with-at-least-32-characters-long
   ```
3. Restart API:
   ```bash
   docker compose up -d api
   ```

## API Errors

### "Field required: message"

**Cause**: Using wrong field name in request

**Fix**: Use `"message"` not `"content"`:
```json
{"message": "User input"}  // Correct
{"content": "User input"}  // Wrong!
```

### "project_id NOT NULL violation"

**Cause**: Using old `/interview/start` endpoint

**Fix**: Use new flow:
1. Create project: `POST /api/v1/projects`
2. Start session: `POST /api/v1/projects/{id}/sessions`

### "INTERNAL_ERROR"

**Debug**:
```bash
docker compose logs api --tail 100 | grep -E "(ERROR|Exception)"
```

Common causes:
- Database connection issue
- Missing environment variable
- Neo4j not reachable

## Frontend Issues

### "net::ERR_CONNECTION_REFUSED" at localhost:80

**Cause**: Frontend container not running

**Fix**:
```bash
docker compose up -d frontend
sleep 10
curl http://localhost:80
```

### "Lädt..." forever

**Causes**:
- API not healthy
- CORS issues
- Auth token expired

**Debug**:
1. Check API: `curl http://localhost:8001/health`
2. Check browser console (F12)
3. Re-login if token expired

## Database Issues

### Traceability tables empty

**RESOLVED (2026-01-10)**: Traceability is now fully working via `/message/stream` endpoint.

ProcessedSignals, SolverSeeds, SolverDeltas are generated AND persisted.

**Verification**:
```bash
docker exec -i supabase_db_brand_composer_amplifyier psql -U postgres -d postgres -c \
  "SELECT COUNT(*) as signals FROM processed_signals; SELECT COUNT(*) as seeds FROM solver_seeds; SELECT COUNT(*) as deltas FROM solver_deltas;"
```

### Session/Turns not persisting

**Check**:
```bash
docker exec -i supabase_db_brand_composer_amplifyier psql -U postgres -d postgres -c \
  "SELECT COUNT(*) FROM sessions;"
```

## Performance Issues

### Turn taking >5s

**Current**: ~3.5s per turn (optimized from 31s)
**Achieved**: -89% latency reduction

Optimizations applied:
- Haiku migration: 31s → 6.5s (-79%)
- Prompt caching: 6.5s → 3.5s (-46%)
- Solver vectorization: -54% solver latency

If turns take >10s, check:
- Neo4j connection (GraphCache loaded?)
- LLM API latency
- Network issues

## Container Issues

### API "unhealthy" status

**Cause**: GraphCache loading (~2.5 min, loads 344k edges from Neo4j)

**Wait**: Check logs for progress:
```bash
docker compose logs api -f | grep -E "(Loaded|ready|GraphCache)"
```

**With file caching**: Subsequent starts take <10s (uses `/tmp/graph_cache.pkl`)

### Container has old code

**Fix**:
```bash
docker compose build api --no-cache
docker compose up -d api
```

## Quick Health Check Script

```bash
echo "=== Infrastructure Check ==="
echo "API: $(curl -s http://localhost:8001/health | python3 -c 'import sys,json; print(json.load(sys.stdin).get(\"status\",\"ERROR\"))')"
echo "Frontend: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:80)"
echo "Supabase: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:54321/rest/v1/)"
echo "Neo4j: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:7474)"
docker compose ps --format "{{.Name}}: {{.Status}}"
```
