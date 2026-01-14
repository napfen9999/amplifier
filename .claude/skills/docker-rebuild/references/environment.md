# Docker Environment Configuration

Environment variables, volumes, and networking for Brand Composer Docker setup.

## Critical API Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `SIGNAL_EXTRACTION_MODEL` | `haiku` | LLM model (haiku: 52% faster, sonnet: higher quality) |
| `GRAPH_CACHE_FILE_ENABLED` | `true` | File caching for fast restarts (<10s vs 2.5min) |
| `GRAPH_CACHE_TTL_HOURS` | `1` | Cache TTL before reload from Neo4j |
| `REDIS_ENABLED` | `false` | Redis state cache (recommended for production) |
| `NEO4J_URI_LEAN` | `bolt://bc-neo4j:7687` | Neo4j connection (container DNS) |
| `DATABASE_URL` | `postgresql://...@host.docker.internal:54322/postgres` | PostgreSQL via Supabase |
| `SUPABASE_URL` | `http://host.docker.internal:54321` | Supabase API on host |

## Frontend Build Variables

| Variable | Value | Notes |
|----------|-------|-------|
| `VITE_API_URL` | `http://localhost:8001/api/v1` | Must use `localhost` (browser access) |
| `VITE_SUPABASE_URL` | `http://localhost:54321` | Must use `localhost` (browser access) |
| `VITE_SUPABASE_ANON_KEY` | from `.env` | Supabase anonymous key |

## Network Configuration

### DNS Names

| Context | Neo4j | Redis | Supabase |
|---------|-------|-------|----------|
| Inside containers | `bc-neo4j:7687` | `redis:6379` | `host.docker.internal:54321` |
| From host | `localhost:7687` | `localhost:6379` | `localhost:54321` |

### Network Name

```
brand_composer_amplifyier_brand-composer
```

### Host Gateway

Containers access host services via `host.docker.internal` (configured via `extra_hosts`).

## Volumes

| Volume | Mount | Purpose | Persistence |
|--------|-------|---------|-------------|
| `graph-cache` | `/tmp` | GraphCache pickle (speeds restarts) | Survives restart |
| `redis_data` | `/data` | Redis AOF persistence | Survives restart |
| `neo4j-data` | `/data` | Neo4j database | Survives restart |
| `neo4j-logs` | `/logs` | Neo4j logs | Survives restart |

### Graph Cache Behavior

- **Cold start**: ~2.5 min (loads 344,335 edges from Neo4j)
- **With file cache**: <10s (loads from `/tmp/graph_cache.pkl`)
- **TTL**: 1 hour (then reloads from Neo4j)
- **Volume**: Persists across container restarts

## Service Dependencies

```
Supabase (manual, on host)
    ↓
neo4j ──────────────────────┐
    ↓                       │
redis (optional) ───────────┤
                            ↓
            api (depends_on: neo4j, redis)
                            ↓
            frontend (depends_on: api healthy)
```

## Healthchecks

| Service | Check | Interval | Retries |
|---------|-------|----------|---------|
| API | `curl -f http://localhost:8001/health` | 10s | 5 |
| Frontend | `wget --spider http://127.0.0.1/` | 30s | 3 |
| Neo4j | `wget --spider http://localhost:7474` | 10s | 10 |
| Redis | `redis-cli ping` | 10s | 5 |

## Development Overrides

`docker-compose.override.yml` provides development settings:

```yaml
# Volume mounts for hot-reload
volumes:
  - ./solver_api/src:/app/src:ro
  - ./frontend/src:/app/src:ro

# Debug logging
environment:
  - LOG_LEVEL=DEBUG
```

**Note**: Hot-reload removed to reduce CPU. Use `docker compose build` for code changes.

## Port Mapping

| Service | Container Port | Host Port |
|---------|---------------|-----------|
| API | 8001 | 8001 |
| Frontend | 80 | 80 |
| Neo4j Browser | 7474 | 7474 |
| Neo4j Bolt | 7687 | 7687 |
| Redis | 6379 | 6379 |
| Supabase Kong | 54321 | 54321 |
| Supabase PostgreSQL | 5432 | 54322 |
| Supabase Studio | 3000 | 54323 |
