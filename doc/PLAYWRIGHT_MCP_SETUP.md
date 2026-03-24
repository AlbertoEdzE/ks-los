# Playwright MCP Agent Configuration

## ✅ Installation Complete

The Playwright MCP (Model Context Protocol) server has been configured for Qwen Code.

## Configuration

**Location:** `~/.qwen/settings.json`

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"],
      "env": {
        "PLAYWRIGHT_BROWSERS_PROFILE": "1",
        "PLAYWRIGHT_HEADLESS": "false"
      }
    }
  }
}
```

## What is Playwright MCP?

Playwright MCP is a Model Context Protocol server that provides browser automation capabilities to AI assistants. It allows Qwen Code to:

- **Navigate** to URLs
- **Click** elements
- **Type** text
- **Take screenshots**
- **Extract** content from pages
- **Test** user interactions
- **Verify** UI behavior

## Available Tools

Once configured, the following tools become available:

| Tool | Description |
|------|-------------|
| `playwright_navigate` | Go to a URL |
| `playwright_click` | Click an element |
| `playwright_type` | Type text into an input |
| `playwright_select` | Select from dropdown |
| `playwright_checkbox` | Check/uncheck boxes |
| `playwright_evaluate` | Run JavaScript in browser |
| `playwright_screenshot` | Take screenshots |
| `playwright_hover` | Hover over elements |
| `playwright_drag` | Drag and drop |
| `playwright_wait_for` | Wait for conditions |

## Usage Example

When asking Qwen Code to test the application, you can say:

```
Use Playwright to test the borrower login flow:
1. Navigate to http://localhost:5175
2. Click "Loan Applicant"
3. Login with demo/demo123
4. Verify the welcome screen appears
5. Take screenshots at each step
```

Or:

```
Run a Playwright test to verify:
- Role selection screen shows both options
- Journey tracker appears after starting conversation
- Quick prompts are clickable
- Chat messages are sent correctly
```

## Testing the Current Application

### Quick Test

```bash
cd /Users/alberto/Documents/projects/ks-los/frontend
npx playwright test quick-login-test
```

### Full Workflow Test

```bash
npx playwright test complete-borrower-workflow
```

### Interactive UI Mode

```bash
npx playwright test --ui
```

### Generate Report

```bash
npx playwright show-report
```

## Headless vs Headed Mode

**Current Configuration:** Headed (browser visible)
- Good for: Debugging, visual verification, screenshots
- Set in config: `"PLAYWRIGHT_HEADLESS": "false"`

**Headless Mode:** (no browser window)
- Good for: CI/CD, fast automated tests
- Change config to: `"PLAYWRIGHT_HEADLESS": "true"`

## Troubleshooting

### MCP Server Not Starting

1. Check installation:
   ```bash
   npm list -g @playwright/mcp
   ```

2. Reinstall if needed:
   ```bash
   npm install -g @playwright/mcp
   ```

3. Verify Playwright browsers:
   ```bash
   npx playwright install chromium
   ```

### Permission Errors

On macOS, you might need to allow terminal automation:
- System Preferences → Security & Privacy → Privacy → Automation
- Enable your terminal app

### Browser Issues

If browsers aren't found:
```bash
npx playwright install
```

## Files Created

| File | Purpose |
|------|---------|
| `~/.qwen/settings.json` | MCP configuration |
| `frontend/playwright/e2e/quick-login-test.spec.ts` | Quick login test |
| `frontend/playwright/e2e/complete-borrower-workflow.spec.ts` | Full workflow tests |
| `frontend/playwright.config.ts` | Playwright configuration |

## Next Steps

1. **Restart Qwen Code** to load the new MCP configuration
2. **Ask Qwen to test** the application using Playwright tools
3. **Review screenshots** in `frontend/playwright-screenshots/`
4. **Check test reports** with `npx playwright show-report`

## Resources

- [Playwright MCP on npm](https://www.npmjs.com/package/@playwright/mcp)
- [Playwright Documentation](https://playwright.dev/)
- [Model Context Protocol](https://modelcontextprotocol.io/)

---

**Status:** ✅ Configured and ready to use!

Restart Qwen Code to activate the Playwright MCP agent.
