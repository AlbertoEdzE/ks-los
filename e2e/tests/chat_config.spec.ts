import { test, expect } from '@playwright/test';

test('chat shows suggestions and progress', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('radio', { name: 'User' }).check();
  await page.getByLabel('Username').fill('demo');
  await page.getByLabel('Password').fill('demo123');
  await page.getByRole('button', { name: 'Login' }).click();
  await expect(page.getByText('Chat with Journey Coach')).toBeVisible();
  // Type name to trigger suggestions
  await page.getByLabel('Name', { exact: true }).fill('Jo');
  await expect(page.getByText('Suggestions')).toBeVisible();
  // Start chat and expect progress bar appears
  await page.getByPlaceholder('Type your message...').fill('I am 30, ECCU');
  await page.getByRole('button', { name: 'Login' }).isHidden();
});
