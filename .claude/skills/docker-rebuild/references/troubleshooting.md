# Docker Rebuild Troubleshooting

Detailed troubleshooting for Docker rebuild issues in Brand Composer.

## Problem: API stays "starting" for too long (>5 min)

**Cause**: Neo4j not reachable or unhealthy

**Diagnosis**:
```bash
docker compose ps neo4j
docker compose logs neo4j --tail 20
```

**Solution**:
```bash
# Restart Neo4j first
docker compose restart neo4j
sleep 30  # Wait for Neo4j healthcheck

# Then restart API
docker compose restart api
```

## Problem: API becomes "unhealthy"

**Cause**: Neo4j connection failed or GraphCache error

**Diagnosis**:
```bash
docker compose logs api --tail 50 | grep -E "(Error|error|Exception|exception)"
```

**Common errors and solutions**:

| Error | Cause | Solution |
|-------|-------|----------|
| `DNS resolve address bc-neo4j` | Neo4j not in network | `docker compose restart neo4j api` |
| `Connection refused` | Neo4j not ready | Wait 30s, then `docker compose restart api` |
| `timeout` | Neo4j overloaded | `docker compose restart neo4j`, wait 30s |

## Problem: ImportError after rebuild

**Cause**: Container wasn't actually rebuilt (Docker cache issue)

**Solution**:
```bash
# Force fresh build with pull
docker compose build api --no-cache --pull

# Remove old container completely
docker compose rm -f api

# Start fresh
docker compose up -d api
```

## Problem: Old code still running

**Cause**: Docker layer cache used old code

**Solution**:
```bash
# Nuclear option - remove all build cache
docker builder prune -f

# Rebuild from scratch
docker compose build api --no-cache
docker compose up -d api
```

## Problem: GraphCache stale or corrupted

**Cause**: Cache file outdated (>1 hour TTL) or corrupted

**Solution**:
```bash
# Option 1: Restart (cache expires based on TTL)
docker compose restart api

# Option 2: Force fresh load by removing volume
docker compose down api
docker volume rm brand_composer_amplifyier_graph-cache
docker compose up -d api
```

## Problem: Frontend shows old content

**Cause**: Browser cache or nginx cache

**Solution**:
```bash
# Rebuild frontend
docker compose build frontend --no-cache
docker compose up -d frontend

# Clear browser cache (Ctrl+Shift+R)
```

## Problem: Redis connection errors

**Cause**: Redis container not running or unhealthy

**Diagnosis**:
```bash
docker compose ps redis
docker exec brand_composer_amplifyier-redis-1 redis-cli ping
```

**Solution**:
```bash
docker compose restart redis api
```

## Problem: Supabase connection errors

**Cause**: Supabase not running on host (runs outside Docker)

**Diagnosis**:
```bash
curl -s http://localhost:54321/health
```

**Solution**:
```bash
# Start Supabase on host
cd /home/ufeld/dev/brand_composer_amplifyier
npx supabase start
```

## Log Analysis Commands

```bash
# API logs (last 50 lines)
docker compose logs api --tail 50

# Follow logs in real-time
docker compose logs -f api

# Search for errors
docker compose logs api 2>&1 | grep -i error

# Check all services
docker compose logs --tail 20
```

## Health Check Commands

```bash
# All services status
docker compose ps

# Specific container health
docker inspect brand_composer_amplifyier-api-1 --format '{{.State.Health.Status}}'

# API health endpoint
curl -s http://localhost:8001/health | python3 -m json.tool

# Neo4j health
docker compose exec neo4j cypher-shell -u neo4j -p localdev "RETURN 1"

# Redis health
docker exec brand_composer_amplifyier-redis-1 redis-cli ping
```

## Nuclear Reset

If nothing else works, complete reset:

```bash
# Stop everything
docker compose down

# Remove all volumes (DATA LOSS!)
docker compose down -v

# Remove build cache
docker builder prune -af

# Rebuild everything
docker compose build --no-cache

# Start fresh
docker compose up -d
```

**WARNING**: `docker compose down -v` removes all data including Neo4j database and Redis cache.
