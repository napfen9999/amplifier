# Infrastructure Reference

## Services & Ports

| Service | Port | Health Check |
|---------|------|--------------|
| API | 8001 | `curl http://localhost:8001/health` |
| Frontend | 80 | `curl http://localhost:80` |
| Supabase | 54321 | `curl http://localhost:54321/rest/v1/` |
| PostgreSQL | 54322 | Via Supabase |
| Neo4j | 7474/7687 | `curl http://localhost:7474` |
| Redis | 6379 | `redis-cli ping` |

## Docker Commands

```bash
# Start all services
docker compose up -d

# Start specific service (often needed!)
docker compose up -d frontend

# Rebuild after code changes
docker compose build api --no-cache && docker compose up -d api

# Check status
docker compose ps

# View logs
docker compose logs api --tail 50
```

## Database Access

### PostgreSQL (Supabase)

```bash
# Direct SQL
docker exec -i supabase_db_brand_composer_amplifyier psql -U postgres -d postgres -c "SELECT ..."

# Table overview
docker exec -i supabase_db_brand_composer_amplifyier psql -U postgres -d postgres -c "\dt"
```

### Key Tables

| Table | Purpose |
|-------|---------|
| `sessions` | Interview sessions |
| `turns` | Turn metadata |
| `messages` | User/assistant messages |
| `processed_signals` | Signal → Enum matching (EMPTY!) |
| `solver_seeds` | Solver input (EMPTY!) |
| `solver_deltas` | Solver effects (EMPTY!) |
| `projects` | User projects |

### Neo4j (Graph DB)

```bash
# Browser UI
open http://localhost:7474

# Via cypher-shell
docker exec -it bc-neo4j cypher-shell -u neo4j -p localdev \
  "MATCH (ma:MetaAttribute) RETURN count(ma);"
```

## Environment Variables

Critical for JWT validation:
```bash
# .env must have EXACTLY this value
SUPABASE_JWT_SECRET=super-secret-jwt-token-with-at-least-32-characters-long
```

After changing .env:
```bash
docker compose up -d api  # Restart to pick up changes
```

## Data Persistence

| Service | Volume | Survives rebuild? |
|---------|--------|-------------------|
| PostgreSQL | Supabase managed | Yes |
| Redis | `redis_data` | Yes |
| Neo4j | External container | Yes |
| Graph Cache | `graph-cache` | Yes |

Volumes are only deleted with `docker compose down -v`.
