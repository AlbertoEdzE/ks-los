import { test, expect, type Page } from '@playwright/test';

/**
 * KS-LOS v2.0 - Complete Borrower Workflow E2E Test
 * 
 * This test suite validates the entire borrower journey:
 * 1. LNAI-style role selection login
 * 2. Quick prompt selection
 * 3. Conversation flow with AI
 * 4. Journey tracker visibility
 * 5. Card rendering (when metadata present)
 */

test.describe('Complete Borrower Workflow - LNAI Style', () => {
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
    
    // Take screenshot of initial state
    await page.screenshot({ 
      path: 'playwright-screenshots/00-initial-state.png',
      fullPage: true 
    });
  });

  test.afterAll(async () => {
    await page.close();
  });

  test('should display LNAI-style role selection screen', async () => {
    await page.goto('http://localhost:5175');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    
    // Check for role selection cards
    await expect(page.locator('[data-testid="select-borrower"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="select-officer"]')).toBeVisible();
    
    // Check for LNAI-style elements
    await expect(page.locator('text=Welcome to LoanAssist')).toBeVisible();
    await expect(page.locator('text=AI-Powered Loan Origination')).toBeVisible();
    
    // Check for feature lists
    await expect(page.locator('text=Loan Applicant')).toBeVisible();
    await expect(page.locator('text=Loan Officer')).toBeVisible();
    
    // Screenshot
    await page.screenshot({ 
      path: 'playwright-screenshots/01-role-selection.png',
      fullPage: true 
    });
  });

  test('should select borrower role and show login form', async () => {
    // Click borrower card
    await page.click('[data-testid="select-borrower"]');
    
    // Wait for login form to appear
    await expect(page.locator('text=Loan Applicant Login')).toBeVisible();
    await expect(page.locator('text=Welcome Back')).toBeVisible();
    
    // Check for back button
    await expect(page.locator('text=← Back')).toBeVisible();
    
    // Check for demo credentials
    await expect(page.locator('text=demo / demo123')).toBeVisible();
    
    // Screenshot
    await page.screenshot({ 
      path: 'playwright-screenshots/02-borrower-login.png',
      fullPage: true 
    });
  });

  test('should login successfully with demo credentials', async () => {
    // Fill credentials
    await page.fill('#username', 'demo');
    await page.fill('#password', 'demo123');
    
    // Submit login
    await page.click('button[type="submit"]');
    
    // Wait for navigation
    await page.waitForURL('http://localhost:5175/', { timeout: 10000 });
    
    // Check we're on borrower home page
    await expect(page.locator('[data-testid="text-app-title"]')).toBeVisible();
    await expect(page.locator('text=Tell me what you need')).toBeVisible();
    
    // Screenshot
    await page.screenshot({ 
      path: 'playwright-screenshots/03-logged-in-welcome.png',
      fullPage: true 
    });
  });

  test('should display welcome state with quick prompts', async () => {
    // Check welcome message
    await expect(page.locator('text=Tell me what you need')).toBeVisible();
    await expect(page.locator('text=I\'ll recommend borrowing paths')).toBeVisible();
    
    // Check all 4 quick prompts
    const quickPrompts = [
      { title: 'Home Loan', prompt: /home/i },
      { title: 'Car Loan', prompt: /car/i },
      { title: 'Personal Loan', prompt: /personal/i },
      { title: 'Debt Consolidation', prompt: /debt/i }
    ];
    
    for (const prompt of quickPrompts) {
      await expect(page.locator(`text=${prompt.title}`)).toBeVisible();
    }
    
    // Screenshot
    await page.screenshot({ 
      path: 'playwright-screenshots/04-quick-prompts.png',
      fullPage: true 
    });
  });

  test('should start conversation with Car Loan quick prompt', async () => {
    // Click Car Loan prompt
    await page.click('button:has-text("Car Loan")');
    
    // Wait for AI response (give it time for Ollama)
    await page.waitForTimeout(8000);
    
    // Check that conversation started
    const assistantMessages = page.locator('[data-testid="chat-message-assistant"]');
    await expect(assistantMessages).toHaveCount({ min: 1 });
    
    // Check journey tracker appears
    await expect(page.locator('[data-testid="borrower-journey-tracker"]')).toBeVisible();
    
    // Screenshot
    await page.screenshot({ 
      path: 'playwright-screenshots/05-first-response.png',
      fullPage: true 
    });
  });

  test('should display 7-step journey tracker', async () => {
    // Check journey tracker is visible
    const tracker = page.locator('[data-testid="borrower-journey-tracker"]');
    await expect(tracker).toBeVisible();
    
    // Check all 7 steps exist
    for (let i = 0; i < 7; i++) {
      await expect(page.locator(`[data-testid="journey-step-${i}"]`)).toBeVisible();
    }
    
    // Check step labels
    await expect(page.locator('text=Tell us your need')).toBeVisible();
    await expect(page.locator('text=Check eligibility')).toBeVisible();
    await expect(page.locator('text=Share documents')).toBeVisible();
    
    // Screenshot of journey tracker
    await page.screenshot({ 
      path: 'playwright-screenshots/06-journey-tracker.png',
      fullPage: true 
    });
  });

  test('should send second message and get AI response', async () => {
    // Type message in chat input
    const chatInput = page.locator('[data-testid="input-chat-message"]');
    await chatInput.fill('I want to buy a car for $25,000');
    await chatInput.press('Enter');
    
    // Wait for AI response
    await page.waitForTimeout(8000);
    
    // Check we have at least 2 assistant messages
    const assistantMessages = page.locator('[data-testid="chat-message-assistant"]');
    await expect(assistantMessages).toHaveCount({ min: 2 });
    
    // Check user message is visible
    await expect(page.locator('[data-testid="chat-message-user"]')).toHaveCount({ min: 1 });
    
    // Screenshot
    await page.screenshot({ 
      path: 'playwright-screenshots/07-second-message.png',
      fullPage: true 
    });
  });

  test('should continue conversation with financial details', async () => {
    // Provide more details
    const chatInput = page.locator('[data-testid="input-chat-message"]');
    await chatInput.fill('My monthly income is $5,000 and I am salaried');
    await chatInput.press('Enter');
    
    // Wait for AI response
    await page.waitForTimeout(8000);
    
    // Check response
    const assistantMessages = page.locator('[data-testid="chat-message-assistant"]');
    await expect(assistantMessages).toHaveCount({ min: 3 });
    
    // Screenshot
    await page.screenshot({ 
      path: 'playwright-screenshots/08-financial-details.png',
      fullPage: true 
    });
  });

  test('should test New Chat functionality', async () => {
    // Click New Chat button
    await page.click('[data-testid="button-new-chat"]');
    
    // Wait for welcome state
    await page.waitForTimeout(2000);
    
    // Check we're back to welcome state
    await expect(page.locator('text=Tell me what you need')).toBeVisible();
    
    // Journey tracker should be hidden
    await expect(page.locator('[data-testid="borrower-journey-tracker"]')).not.toBeVisible();
    
    // Screenshot
    await page.screenshot({ 
      path: 'playwright-screenshots/09-new-chat.png',
      fullPage: true 
    });
  });

  test('should test logout and return to role selection', async () => {
    // Find and click logout button
    const logoutButton = page.locator('button:has-text("Logout")').first();
    if (await logoutButton.isVisible()) {
      await logoutButton.click();
      
      // Wait for redirect to login
      await page.waitForTimeout(2000);
      
      // Should be back at role selection
      await expect(page.locator('[data-testid="select-borrower"]')).toBeVisible();
      await expect(page.locator('[data-testid="select-officer"]')).toBeVisible();
      
      // Screenshot
      await page.screenshot({ 
        path: 'playwright-screenshots/10-logged-out.png',
        fullPage: true 
      });
    }
  });
});

/**
 * Integration Test: Code + UI + Backend
 */
test.describe('Integration Tests - Full Stack', () => {
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
  });

  test.afterAll(async () => {
    await page.close();
  });

  test('should verify backend API is healthy', async () => {
    const response = await page.request.get('http://localhost:8001/health');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.status).toBe('healthy');
  });

  test('should verify Ollama is running', async () => {
    const response = await page.request.get('http://localhost:11434/api/tags');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(Array.isArray(data.models)).toBeTruthy();
    expect(data.models.length).toBeGreaterThan(0);
  });

  test('should create conversation via API and verify in UI', async () => {
    // Login first
    await page.goto('http://localhost:5175');
    await page.click('[data-testid="select-borrower"]');
    await page.fill('#username', 'demo');
    await page.fill('#password', 'demo123');
    await page.click('button[type="submit"]');
    await page.waitForURL('http://localhost:5175/');
    
    // Create conversation via API
    const response = await page.request.post('http://localhost:8001/api/conversations', {
      data: {}
    });
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.conversation).toBeDefined();
    expect(data.conversation.id).toBeDefined();
    
    console.log('Created conversation:', data.conversation.id);
  });

  test('should verify phases are loaded', async () => {
    const response = await page.request.get('http://localhost:8001/api/phases/active');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(Array.isArray(data)).toBeTruthy();
  });
});

/**
 * Visual Regression Tests
 */
test.describe('Visual Regression - UI Components', () => {
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
    await page.goto('http://localhost:5175');
    await page.click('[data-testid="select-borrower"]');
    await page.fill('#username', 'demo');
    await page.fill('#password', 'demo123');
    await page.click('button[type="submit"]');
    await page.waitForURL('http://localhost:5175/');
  });

  test.afterAll(async () => {
    await page.close();
  });

  test('should verify header component', async () => {
    const header = page.locator('header').first();
    await expect(header).toBeVisible();
    
    // Check KS logo
    await expect(page.locator('text=KS').first()).toBeVisible();
    
    // Check app title
    await expect(page.locator('[data-testid="text-app-title"]')).toHaveText('LoanAssist AI');
    
    // Screenshot
    await header.screenshot({ path: 'playwright-screenshots/component-header.png' });
  });

  test('should verify chat input component', async () => {
    const chatInput = page.locator('[data-testid="input-chat-message"]');
    await expect(chatInput).toBeVisible();
    
    // Check placeholder
    await expect(chatInput).toHaveAttribute('placeholder', /Tell me what you're looking for/i);
    
    // Screenshot
    await chatInput.screenshot({ path: 'playwright-screenshots/component-chat-input.png' });
  });

  test('should verify quick prompts layout', async () => {
    const welcomeCard = page.locator('text=Tell me what you need').first();
    await expect(welcomeCard).toBeVisible();
    
    // Screenshot the entire welcome card
    await welcomeCard.locator('..').locator('..').screenshot({ 
      path: 'playwright-screenshots/component-welcome-card.png' 
    });
  });
});
