import { test, expect } from '@playwright/test';

test('chat shows suggestions and progress', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('User').check();
  await page.getByLabel('Username').fill('demo');
  await page.getByLabel('Password').fill('demo123');
  await page.getByRole('button', { name: 'Login' }).click();
  await expect(page.getByText('Chat with Journey Coach')).toBeVisible();
  // Type name to trigger suggestions
  await page.getByLabel('Name').fill('Jo');
  await page.getByLabel('Surname').fill('Do');
  await expect(page.getByText('Suggestions')).toBeVisible();
  // Start chat and expect progress bar appears
  await page.getByRole('textbox').fill('I am 30, ECCU');
  await page.getByRole('button', { name: 'Login' }).isHidden();
});
