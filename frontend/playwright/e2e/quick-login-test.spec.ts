import { test, expect } from '@playwright/test';

test.describe('LNAI Login Flow - Quick Test', () => {
  test('should show role selection and login', async ({ page }) => {
    // Go to app
    await page.goto('http://localhost:5175', { waitUntil: 'networkidle' });
    
    // Take screenshot
    await page.screenshot({ path: 'playwright-screenshots/01-role-selection.png', fullPage: true });
    
    // Check role selection is visible
    await expect(page.locator('[data-testid="select-borrower"]')).toBeVisible({ timeout: 10000 });
    console.log('✅ Role selection screen visible');
    
    // Click borrower
    await page.click('[data-testid="select-borrower"]');
    await page.waitForTimeout(2000);
    
    // Take screenshot
    await page.screenshot({ path: 'playwright-screenshots/02-borrower-login.png', fullPage: true });
    
    // Check login form
    await expect(page.locator('text=Loan Applicant Login')).toBeVisible();
    console.log('✅ Borrower login form visible');
    
    // Fill credentials
    await page.fill('#username', 'demo');
    await page.fill('#password', 'demo123');
    
    // Login
    await page.click('button[type="submit"]');
    await page.waitForTimeout(5000);
    
    // Take screenshot
    await page.screenshot({ path: 'playwright-screenshots/03-welcome-screen.png', fullPage: true });
    
    // Check we're logged in
    await expect(page.locator('[data-testid="text-app-title"]')).toBeVisible();
    await expect(page.locator('text=Tell me what you need')).toBeVisible();
    console.log('✅ Successfully logged in - welcome screen visible');
    
    // Check quick prompts
    await expect(page.locator('text=Home Loan')).toBeVisible();
    await expect(page.locator('text=Car Loan')).toBeVisible();
    console.log('✅ Quick prompts visible');
    
    console.log('\n✅ ALL CHECKS PASSED! Login flow working correctly.');
  });
});
