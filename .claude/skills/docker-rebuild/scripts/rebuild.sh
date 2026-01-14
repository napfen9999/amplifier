#!/bin/bash
# Docker Rebuild Script for Brand Composer
# Usage: ./scripts/rebuild.sh [service]
# Default service: api

set -e

SERVICE="${1:-api}"
CONTAINER="brand_composer_amplifyier-${SERVICE}-1"
TIMEOUT=300  # 5 minutes

echo "=== Docker Rebuild: $SERVICE ==="
echo ""

# Step 1: Build
echo "Building $SERVICE container (--no-cache)..."
docker compose build "$SERVICE" --no-cache
echo "Build complete."
echo ""

# Step 2: Start
echo "Starting $SERVICE container..."
docker compose up -d "$SERVICE"
echo "Container started."
echo ""

# Step 3: Wait for healthy
echo "Waiting for healthy status (timeout: ${TIMEOUT}s)..."
START=$SECONDS

while true; do
    STATUS=$(docker inspect "$CONTAINER" --format '{{.State.Health.Status}}' 2>/dev/null || echo "not_found")
    ELAPSED=$((SECONDS - START))

    if [ "$STATUS" = "healthy" ]; then
        echo ""
        echo "✓ $SERVICE healthy after ${ELAPSED}s"
        break
    elif [ "$STATUS" = "unhealthy" ]; then
        echo ""
        echo "✗ ERROR: $SERVICE unhealthy after ${ELAPSED}s"
        echo "Check logs: docker compose logs $SERVICE --tail 50"
        exit 1
    elif [ "$STATUS" = "not_found" ]; then
        echo ""
        echo "✗ ERROR: Container $CONTAINER not found"
        exit 1
    elif [ $ELAPSED -gt $TIMEOUT ]; then
        echo ""
        echo "✗ ERROR: Timeout after ${TIMEOUT}s (status: $STATUS)"
        exit 1
    fi

    echo -n "."
    sleep 5
done

echo ""

# Step 4: Verify (API only)
if [ "$SERVICE" = "api" ]; then
    echo "=== Verification ==="
    curl -s http://localhost:8001/health | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f'Status: {d[\"status\"]}')
print(f'Graph: {d[\"graph_loaded\"]} (MA:{d[\"meta_attributes_count\"]}, Enum:{d[\"enumerations_count\"]})')
print(f'Auth: {d[\"auth_enabled\"]}, LLM: {d[\"llm_enabled\"]}')"
    echo ""
fi

echo "=== Rebuild Complete ==="
