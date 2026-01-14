---
name: docker-rebuild
description: This skill should be used when the user asks to "rebuild docker", "docker neu bauen", "deploy changes", "container rebuild", "api rebuild", "redeploy api", "restart containers", or needs to rebuild Docker containers after code changes. Provides timing expectations, troubleshooting, and verification for Brand Composer services.
---

# Docker Rebuild Skill

Rebuild Docker containers after code changes in Brand Composer with proper verification.

## Quick Reference

```bash
# Standard rebuild (most common)
docker compose build api --no-cache && docker compose up -d api

# Wait for healthy (~2.5 min for API)
./scripts/docker_health_wait.sh

# Verify
curl -s http://localhost:8001/health
```

## Architecture

| Service | Port | Container | Startup |
|---------|------|-----------|---------|
| API | 8001 | `brand_composer_amplifyier-api-1` | ~2.5 min |
| Frontend | 80 | `brand_composer_amplifyier-frontend-1` | ~10s |
| Neo4j | 7687 | `bc-neo4j` | ~30s |
| Redis | 6379 | `brand_composer_amplifyier-redis-1` | ~5s |

**Dependency Chain**: Supabase (host) → neo4j → redis → api → frontend

## Timing Expectations

| Operation | Duration |
|-----------|----------|
| Build (`--no-cache`) | 60-90s |
| API healthy | **~2.5 min** (GraphCache: 344k edges) |
| **Total rebuild** | **~4-5 min** |

**CRITICAL**: API takes ~2.5 min because GraphCache loads 344,335 edges from Neo4j. This is normal.

## Standard Rebuild Procedure

### 1. Build

```bash
docker compose build api --no-cache
```

Always use `--no-cache` after code changes.

### 2. Start

```bash
docker compose up -d api
```

### 3. Wait for Healthy

```bash
# Recommended: Use script
./scripts/docker_health_wait.sh

# Or manual check
docker inspect brand_composer_amplifyier-api-1 --format '{{.State.Health.Status}}'
```

### 4. Verify

```bash
curl -s http://localhost:8001/health | python3 -c "
import sys,json; d=json.load(sys.stdin)
print(f'Status: {d[\"status\"]}')
print(f'Graph: MA:{d[\"meta_attributes_count\"]}, Enum:{d[\"enumerations_count\"]}')"
```

**Expected**: `Status: ok`, `Graph: MA:43, Enum:847`

## Makefile Commands

| Command | Effect |
|---------|--------|
| `make docker-build` | Build all images |
| `make docker-up` | Start full stack |
| `make docker-health` | Check health |
| `make docker-verify` | Run verification |

## Common Issues (Quick Fixes)

| Problem | Quick Fix |
|---------|-----------|
| API stays "starting" >5min | `docker compose restart neo4j api` |
| ImportError after rebuild | `docker compose build api --no-cache --pull` |
| Old code still running | `docker builder prune -f && docker compose build api --no-cache` |

For detailed troubleshooting, see `references/troubleshooting.md`.

## Verification Checklist

- [ ] `docker compose ps` shows `healthy`
- [ ] `curl http://localhost:8001/health` returns `status: ok`
- [ ] Graph shows `meta_attributes_count: 43`, `enumerations_count: 847`

## Test Credentials (LOCAL DEV)

| Field | Value |
|-------|-------|
| Email | `dev@brandcomposer.test` |
| Password | `DevTest2026` |

## Additional Resources

- `references/troubleshooting.md` - Detailed error diagnosis and solutions
- `references/environment.md` - Environment variables, volumes, networking
- `scripts/rebuild.sh` - Automated rebuild script
- `scripts/e2e-test.sh` - Complete E2E verification

## Project Documentation

- `docs/operations/RESTART_PROCEDURE.md` - Full restart procedure
- `docs/operations/RESTART_VERIFICATION_FLOW.md` - Verification flow diagram
- `scripts/docker_health_wait.sh` - Health wait utility
- `scripts/restart_verify.sh` - Complete restart workflow
