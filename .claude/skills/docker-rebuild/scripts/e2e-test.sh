#!/bin/bash
# E2E Test Script for Brand Composer
# Verifies full system functionality after rebuild

set -e

echo "=== E2E Verification Test ==="
echo ""

# Configuration
ANON_KEY="${SUPABASE_ANON_KEY:-eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0}"

# Step 1: Get auth token
echo "1. Getting auth token..."
TOKEN=$(curl -s -X POST "http://127.0.0.1:54321/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "dev@brandcomposer.test", "password": "DevTest2026"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

if [ -z "$TOKEN" ]; then
    echo "✗ ERROR: Failed to get auth token"
    echo "  Check if Supabase is running: curl http://localhost:54321/health"
    echo "  Check if test user exists"
    exit 1
fi
echo "✓ Token obtained: ${TOKEN:0:30}..."
echo ""

# Step 2: Create project
echo "2. Creating test project..."
PROJECT=$(curl -s -X POST "http://localhost:8001/api/v1/projects" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "E2E Test", "brand_name": "E2ETestBrand", "industry": "Technology"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")

if [ -z "$PROJECT" ]; then
    echo "✗ ERROR: Failed to create project"
    exit 1
fi
echo "✓ Project created: $PROJECT"
echo ""

# Step 3: Start session
echo "3. Starting interview session..."
SESSION=$(curl -s -X POST "http://localhost:8001/api/v1/projects/$PROJECT/sessions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))")

if [ -z "$SESSION" ]; then
    echo "✗ ERROR: Failed to start session"
    exit 1
fi
echo "✓ Session started: $SESSION"
echo ""

# Step 4: Send message and check SSE events
echo "4. Sending message (checking SSE streaming)..."
echo "   Watching for events..."

EVENTS=$(timeout 60 curl -s -N -X POST "http://localhost:8001/api/v1/interview/$SESSION/message/stream" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Wir sind ein innovatives Tech-Startup."}' 2>&1 | grep -E "^event:" | head -10)

echo "$EVENTS"
echo ""

# Check for expected events
if echo "$EVENTS" | grep -q "event: listening"; then
    echo "✓ listening event received"
else
    echo "✗ missing listening event"
fi

if echo "$EVENTS" | grep -q "event: understanding"; then
    echo "✓ understanding event received"
else
    echo "✗ missing understanding event"
fi

if echo "$EVENTS" | grep -q "event: thinking"; then
    echo "✓ thinking event received"
else
    echo "✗ missing thinking event"
fi

if echo "$EVENTS" | grep -q "event: token"; then
    echo "✓ token events received (streaming working!)"
else
    echo "⚠ no token events (streaming may not be working)"
fi

if echo "$EVENTS" | grep -q "event: complete"; then
    echo "✓ complete event received"
else
    echo "✗ missing complete event"
fi

echo ""
echo "=== E2E Test Complete ==="
