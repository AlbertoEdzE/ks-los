import { test, expect, type Page } from '@playwright/test';

// KS-LOS v2.0 - Borrower Workflow E2E Tests
// Tests the complete borrower journey from login to loan application

test.describe('Borrower Workflow', () => {
  let page: Page;

  test.beforeEach(async ({ page: _args }, testInfo) => {
    page = _args;
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    if (testInfo.title === 'should login successfully') return;

    await page.click('[data-testid="select-borrower"]');
    await page.fill('#username', 'demo');
    await page.fill('#password', 'demo123');
    await page.click('button[type="submit"]');
    await expect(page.locator('[data-testid="text-app-title"]')).toBeVisible({ timeout: 20000 });
    await expect(page.locator('text=Tell me what you need')).toBeVisible({ timeout: 20000 });
  });
  test('should login successfully', async () => {
    await page.goto('/');
    await expect(page.locator('[data-testid="select-borrower"]')).toBeVisible({ timeout: 10000 });
    await page.click('[data-testid="select-borrower"]');
    await expect(page.locator('text=Loan Applicant Login')).toBeVisible();
    await expect(page.locator('text=Username')).toBeVisible();
    
    // Login as demo user
    await page.fill('input[type="text"]', 'demo');
    await page.fill('input[type="password"]', 'demo123');
    await page.click('button[type="submit"]');
    
    // Wait for navigation and check we're on the borrower page
    await expect(page.locator('[data-testid="text-app-title"]')).toBeVisible();
    await expect(page.locator('[data-testid="text-app-title"]')).toHaveText('LoanAssist AI');
    
    // Take screenshot
    await page.screenshot({ path: 'playwright-screenshots/01-login-success.png' });
  });

  test('should display welcome state with quick prompts', async () => {
    // Check welcome message is visible
    await expect(page.locator('text=Tell me what you need')).toBeVisible();
    await expect(page.getByText(/recommend borrowing paths/i)).toBeVisible();
    
    // Check all 4 quick prompts are visible
    const quickPrompts = [
      'Home Loan',
      'Car Loan', 
      'Personal Loan',
      'Debt Consolidation'
    ];
    
    for (const prompt of quickPrompts) {
      await expect(page.getByRole('button', { name: new RegExp(prompt, 'i') })).toBeVisible();
    }
    
    // Take screenshot
    await page.screenshot({ path: 'playwright-screenshots/02-welcome-state.png' });
  });

  test('should start conversation when clicking Home Loan quick prompt', async () => {
    // Click Home Loan quick prompt
    await page.click('button:has-text("Home Loan")');

    // Check that we're now in chat view
    const chatMessages = page.locator('[data-testid="chat-message-assistant"]');
    await expect(chatMessages.first()).toBeVisible({ timeout: 20000 });

    // Check Borrower Journey Tracker appears once
    await expect(page.locator('[data-testid="borrower-journey-tracker"]')).toHaveCount(1);
    
    // Take screenshot
    await page.screenshot({ path: 'playwright-screenshots/03-first-response.png' });
  });

  test('should display 7-step journey tracker', async () => {
    // Ensure a conversation has started so tracker is visible
    await page.click('button:has-text("Home Loan")');
    // Check all 7 journey steps are visible
    for (let i = 0; i < 7; i++) {
      const step = page.locator(`[data-testid="journey-step-${i}"]`);
      await step.scrollIntoViewIfNeeded();
      await expect(step).toBeVisible();
    }
    
    // Check first step is active
    const firstStep = page.locator('[data-testid="journey-step-0"]');
    await expect(firstStep).toBeVisible();
    
    // Take screenshot
    await page.screenshot({ path: 'playwright-screenshots/04-journey-tracker.png' });
  });

  test('should send second message and get AI response', async () => {
    await page.click('button:has-text("Home Loan")');
    await expect(page.locator('[data-testid="chat-message-assistant"]').first()).toBeVisible({ timeout: 20000 });

    // Type and send message about budget
    const chatInput = page.locator('[data-testid="input-chat-message"]');
    await chatInput.fill('My budget is XCD 500,000 and I make XCD 8,000 per month');
    await chatInput.press('Enter');
    
    // Wait for AI response
    await page.waitForTimeout(10000);
    
    // Check we have at least 2 assistant messages
    const chatMessages = page.locator('[data-testid="chat-message-assistant"]');
    await expect(chatMessages.nth(1)).toBeVisible({ timeout: 20000 });
    
    // Check user message is visible
    await expect(page.locator('[data-testid="chat-message-user"]').first()).toBeVisible();
    
    // Take screenshot
    await page.screenshot({ path: 'playwright-screenshots/05-second-response.png' });
  });

  test('should hide think tags and gate loan snapshot until option selected', async () => {
    test.setTimeout(120000);
    await page.click('button:has-text("Home Loan")');
    await expect(page.locator('[data-testid="chat-message-assistant"]').first()).toBeVisible({ timeout: 20000 });

    const chatInput = page.locator('[data-testid="input-chat-message"]');
    await expect(chatInput).toBeEnabled({ timeout: 60000 });
    await chatInput.fill('I want to borrow 280000 USD. Property value is 350000 USD.');
    await chatInput.press('Enter');
    await expect(page.locator('[data-testid="loan-card-balanced"]').first()).toBeVisible({ timeout: 60000 });

    await expect(page.locator('text=</think>')).toHaveCount(0);
    await expect(page.locator('text=<think>')).toHaveCount(0);

    await expect(page.locator('[data-testid="loan-snapshot-card"]')).toHaveCount(0);

    const balanced = page.locator('[data-testid="loan-card-balanced"]').first();
    await expect(balanced).toBeVisible({ timeout: 20000 });
    await balanced.click();
    await expect(page.locator('[data-testid="chat-message-assistant"]').last()).toBeVisible({ timeout: 60000 });

    await expect(page.locator('[data-testid="loan-snapshot-card"]')).toHaveCount(0);

    await expect(chatInput).toBeEnabled({ timeout: 60000 });
    await chatInput.fill('My down payment will be 70000 USD.');
    await chatInput.press('Enter');

    await expect(page.locator('text=</think>')).toHaveCount(0);
    await expect(page.locator('text=<think>')).toHaveCount(0);
    await expect(page.locator('[data-testid="loan-snapshot-card"]')).toBeVisible({ timeout: 60000 });
    await expect(page.locator('[data-testid="loan-snapshot-card"]')).toHaveCount(1);
  });

  test('should allow uploading a document via clip button', async () => {
    test.setTimeout(120000);
    await page.click('button:has-text("Home Loan")');
    await expect(page.locator('[data-testid="chat-message-assistant"]').first()).toBeVisible({ timeout: 20000 });

    const passportPath = '/Users/alberto/Documents/projects/ks-los/data/passport-example.png';

    const [chooser] = await Promise.all([
      page.waitForEvent('filechooser'),
      page.click('button[aria-label="Attach"]'),
    ]);
    await chooser.setFiles(passportPath);

    await expect(page.locator('[data-testid="chat-message-user"]').last()).toContainText('Uploaded "passport-example.png"', { timeout: 60000 });
  });

  test('should display approval probability in insights', async () => {
    // Check approval probability is displayed
    await expect(page.locator('[data-testid="approval-probability"]')).toBeVisible();
    
    // Check insights card is visible
    await expect(page.locator('[data-testid="card-insights"]')).toBeVisible();
    
    // Take screenshot
    await page.screenshot({ path: 'playwright-screenshots/06-insights-panel.png' });
  });

  test('should start new chat successfully', async () => {
    // Click New Chat button
    await page.click('[data-testid="button-new-chat"]');
    
    // Wait for welcome state to appear
    await page.waitForTimeout(1000);
    
    // Check we're back to welcome state
    await expect(page.locator('text=Tell me what you need')).toBeVisible();
    
    // Check journey tracker is hidden
    await expect(page.locator('[data-testid="borrower-journey-tracker"]')).not.toBeVisible();
    
    // Take screenshot
    await page.screenshot({ path: 'playwright-screenshots/07-new-chat.png' });
  });
});

test.describe('UI Components Verification', () => {
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
    await page.goto('http://localhost:5175');
    
    await expect(page.locator('[data-testid="select-borrower"]')).toBeVisible({ timeout: 10000 });
    await page.click('[data-testid="select-borrower"]');
    
    // Login
    await page.fill('input[type="text"]', 'demo');
    await page.fill('input[type="password"]', 'demo123');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(2000);
  });

  test.afterAll(async () => {
    await page.close();
  });

  test('should have proper header with logo and title', async () => {
    // Check header is visible
    const header = page.locator('header');
    await expect(header).toBeVisible();
    
    // Check KS logo initials
    await expect(page.locator('text=KS')).toBeVisible();
    
    // Check app title
    await expect(page.locator('[data-testid="text-app-title"]')).toHaveText('LoanAssist AI');
    
    // Check subtitle
    await expect(page.locator('text=Smart loan guidance')).toBeVisible();
  });

  test('should have theme toggle visible', async () => {
    await expect(page.locator('[data-testid="theme-toggle"]')).toBeVisible();
    await expect(page.locator('[data-testid="theme-light"]')).toBeVisible();
    await expect(page.locator('[data-testid="theme-dark"]')).toBeVisible();
  });

  test('should have New Chat button in header', async () => {
    await expect(page.locator('[data-testid="button-new-chat"]')).toBeVisible();
    await expect(page.locator('[data-testid="button-new-chat"]')).toHaveText('New Chat');
  });

  test('should have proper chat input field', async () => {
    const chatInput = page.locator('[data-testid="input-chat-message"]');
    await expect(chatInput).toBeVisible();
    await expect(chatInput).toHaveAttribute('placeholder', /Tell me what you're looking for.../);
  });
});
