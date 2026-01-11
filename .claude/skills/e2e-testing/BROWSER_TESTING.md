# Browser Testing with Dev-Browser

## Setup

### Start Server
```bash
cd /home/ufeld/.claude/plugins/cache/dev-browser-marketplace/dev-browser/66682fb0513a/skills/dev-browser
./server.sh &
# Wait for "Ready" message
```

### Run Scripts
```bash
cd /home/ufeld/.claude/plugins/cache/dev-browser-marketplace/dev-browser/66682fb0513a/skills/dev-browser
npx tsx <<'EOF'
import { connect, waitForPageLoad } from "@/client.js";
// ... script code
EOF
```

## Page Patterns

### Navigate & Screenshot
```typescript
const client = await connect();
const page = await client.page("brand-composer", { viewport: { width: 1920, height: 1080 } });

await page.goto("http://localhost:80");
await waitForPageLoad(page);
await page.screenshot({ path: "tmp/screenshot.png" });

await client.disconnect();
```

### Find Elements (ARIA Snapshot)
```typescript
const snapshot = await client.getAISnapshot("brand-composer");
console.log(snapshot);
// Look for [ref=eXX] to get element references
```

### Interact with Elements
```typescript
const element = await client.selectSnapshotRef("brand-composer", "e15");
await element.click();
await element.fill("text");
await element.press("Enter");
```

## Login Flow

```typescript
// Fill email
const emailField = await client.selectSnapshotRef("brand-composer", "e11");
await emailField.fill("dev@brandcomposer.test");

// Fill password
const passwordField = await client.selectSnapshotRef("brand-composer", "e14");
await passwordField.fill("DevTest2026");

// Click login
const loginButton = await client.selectSnapshotRef("brand-composer", "e15");
await loginButton.click();

await page.waitForTimeout(3000);  // Wait for navigation
```

## Interview Flow

### Send Message via UI
```typescript
// Find input (use getAISnapshot to find current ref)
const input = await client.selectSnapshotRef("brand-composer", "e180");
await input.fill("My message here...");
await input.press("Enter");

// Wait for LLM response (12-25s!)
await page.waitForTimeout(30000);
await page.screenshot({ path: "tmp/after-response.png" });
```

## Timing Considerations

| Operation | Wait Time |
|-----------|-----------|
| Page load | `waitForPageLoad(page)` |
| After login | 3s |
| After sending message | 30s (LLM processing) |
| After navigation | 2-3s |

## Troubleshooting

### "net::ERR_CONNECTION_REFUSED"
Frontend container not running:
```bash
docker compose up -d frontend
```

### Element ref not found
Refs change on page updates. Get fresh snapshot:
```typescript
const snapshot = await client.getAISnapshot("brand-composer");
```

### Screenshots location
```
/home/ufeld/.claude/plugins/cache/dev-browser-marketplace/dev-browser/66682fb0513a/skills/dev-browser/tmp/
```
