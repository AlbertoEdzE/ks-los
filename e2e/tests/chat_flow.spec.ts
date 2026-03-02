import { test, expect } from '@playwright/test';

test.describe('Chat Flow', () => {
  test('Complete chat flow with suggestions and progress bar', async ({ page }) => {
    // Increase test timeout to handle slow LLM responses
    test.setTimeout(120000);

    // a. Log in
    await page.goto('/');
    await page.getByPlaceholder('Enter username').fill('demo');
    await page.getByPlaceholder('Enter password').fill('demo123');
    await page.getByRole('button', { name: 'Login' }).click();

    // Verify chat interface loaded
    await expect(page.locator('h2', { hasText: 'Chat with Journey Coach' })).toBeVisible();

    // b. Verify suggestion strip appears
    await expect(page.getByText(/Quick Start|Suggested inputs/)).toBeVisible();
    
    // Get a suggestion button and click it
    // Use a more robust selector that doesn't depend on specific text "Start as"
    // but rather finds the button within the suggestion strip area
    const suggestionStripLabel = page.getByText(/Quick Start|Suggested inputs/).first();
    // The buttons are in a sibling div or nearby. 
    // Let's just find the first button that looks like a suggestion (contains text)
    const suggestionBtn = page.locator('button').filter({ hasText: /\w+/ }).filter({ hasNotText: 'Send' }).first();
    
    await expect(suggestionBtn).toBeVisible();
    await suggestionBtn.click();

    // Wait for the assistant's response (second message)
    // The first message is the welcome message. We expect a second one.
    const assistantMessages = page.getByTestId('chat-message-assistant');
    await expect(assistantMessages).toHaveCount(2, { timeout: 60000 });

    // Check if we need to provide documents
    const lastMsg = assistantMessages.last();
    const content = await lastMsg.textContent();
    
    // If the agent asks for documents or further info
    if (content?.toLowerCase().includes('upload') || 
        content?.toLowerCase().includes('statement') || 
        content?.toLowerCase().includes('provide') ||
        content?.toLowerCase().includes('share')) {
        
        await page.getByPlaceholder('Type your message...').fill('Here is my bank statement text: DEPOSIT 5000, SALARY 3000. ID: 12345.');
        await page.getByRole('button', { name: 'Send' }).click();
        
        // Wait for next response (third message)
        await expect(assistantMessages).toHaveCount(3, { timeout: 60000 });
    }

    // c. Check that the progress bar appears (role="status")
    // It appears when profile is generated. This might happen after the 2nd or 3rd message depending on the flow.
    const progressBar = page.getByRole('status');
    await expect(progressBar).toBeVisible({ timeout: 60000 });
    
    // Check for step labels (any of the steps) inside the progress bar
    await expect(progressBar.getByText('Intake')).toBeVisible();
    
    // c. Wait for credit profile to appear (ChatInterface calls onProfileReceived)
    // The profile appears when the progress bar is complete or near complete.
    // We look for "Credit Summary" which is in CreditProfileView
    await expect(page.getByText('Credit Summary')).toBeVisible({ timeout: 60000 });
  });
});
