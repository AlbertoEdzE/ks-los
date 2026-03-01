import { test, expect } from '@playwright/test';

test.describe('Agentic Loan Prequalification Journey', () => {
  
  test.beforeEach(async ({ page }) => {
    // Start by navigating to the home page
    await page.goto('/');
  });

  test('User can complete a basic chat flow', async ({ page }) => {
    // Wait for the chat interface to be visible
    await expect(page.locator('text=Chat with Journey Coach')).toBeVisible();

    // Wait for the initial message from the assistant
    await expect(page.locator('text=Hello! I am your Journey Coach')).toBeVisible();

    // Type a message into the chat input
    const chatInput = page.locator('input[placeholder="Type your message..."]');
    await chatInput.fill('Generate a credit profile for a 30 year old in Antigua');
    await page.keyboard.press('Enter');

    // Wait for the agent response
    // Use a unique selector for the profile view header to avoid ambiguity with chat text
    await expect(page.locator('h2:has-text("Applicant Profile")')).toBeVisible({ timeout: 90000 });
    
    // Verify specific elements of the profile view are rendered
    // Scope to .profile-container to avoid matching chat text
    const profileView = page.locator('.profile-container');
    
    await expect(profileView.locator('.score-box:has-text("Credit Score")')).toBeVisible();
    await expect(profileView.locator('.score-box .value')).not.toBeEmpty();
    
    // Use exact text match or scoped locator
    await expect(profileView.getByText('Utilization', { exact: true })).toBeVisible();
    await expect(profileView.getByText('Total Debt', { exact: true })).toBeVisible();

    // Verify the metadata footer shows the source
    await expect(profileView.locator('text=Source: SYNTHETIC')).toBeVisible();
  });

  test('User can trigger a Thin File scenario', async ({ page }) => {
    // Navigate to fresh page
    await page.goto('/');
    
    // Input for a young applicant which triggers thin file logic
    const chatInput = page.locator('input[placeholder="Type your message..."]');
    await chatInput.fill('Generate a profile for a 19 year old student in Grenada');
    await page.keyboard.press('Enter');

    // Wait for response (long timeout for LLM)
    await expect(page.locator('h2:has-text("Applicant Profile")')).toBeVisible({ timeout: 90000 });
    
    // Check if archetype is mentioned in metadata
    // We expect THIN_FILE_YOUNG or similar
    await expect(page.locator('.metadata-footer')).toContainText('THIN_FILE', { timeout: 10000 });
  });

  test('System handles error gracefully', async ({ page }) => {
    // Simulate a network failure for the API call
    await page.route('**/agent/chat', route => route.abort());

    const chatInput = page.locator('input[placeholder="Type your message..."]');
    await chatInput.fill('Hello');
    await page.keyboard.press('Enter');

    // Expect an error message in the chat
    await expect(page.locator('text=Sorry, I encountered an error')).toBeVisible({ timeout: 10000 });
  });

});
