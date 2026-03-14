import { test, expect } from '@playwright/test';

test('chat shows suggestions and progress', async ({ page }) => {
  await page.route('http://localhost:8000/chat/suggestions', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: ['Katie Brady, Antigua and Barbuda, 34 years old'] }),
    });
  });

  await page.route('http://localhost:8000/agent/chat', async (route) => {
    if (route.request().method() !== 'POST') {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ response: 'Thanks — I can help with that.' }),
    });
  });

  await page.goto('/login');
  await page.getByLabel('Username').fill('demo');
  await page.getByLabel('Password').fill('demo123');
  await page.getByRole('button', { name: 'Login' }).click();
  await expect(page.getByText('Chat with Journey Coach')).toBeVisible();

  await expect(page.getByText(/Quick Start|Suggested inputs/i)).toBeVisible({ timeout: 10000 });
  await expect(page.getByRole('button', { name: /Katie Brady/i })).toBeVisible({ timeout: 10000 });

  await page.getByRole('button', { name: /Katie Brady/i }).click();
  await expect(page.getByTestId('chat-message-assistant')).toHaveCount(2, { timeout: 10000 });
  await expect(page.getByRole('status')).toBeVisible();
});
