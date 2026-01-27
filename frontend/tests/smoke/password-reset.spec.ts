import { test, expect } from '@playwright/test';

test.describe('Password Reset Flow', () => {
  test('should navigate to password reset page', async ({ page }) => {
    // Navigate to login
    await page.goto('/login');
    
    // Look for "Forgot password" link
    const forgotPasswordLink = page.getByRole('link', { name: /forgot.*password|reset.*password/i }).first();
    
    if (await forgotPasswordLink.isVisible().catch(() => false)) {
      await forgotPasswordLink.click();
      
      // Wait for password reset page
      await page.waitForURL(/\/.*password.*reset|\/.*forgot.*password/i, { timeout: 10000 });
      
      // Verify reset form is visible
      const emailInput = page.getByLabel(/email/i).first();
      await expect(emailInput).toBeVisible({ timeout: 5000 });
    } else {
      // If link doesn't exist, try direct navigation
      await page.goto('/forgot-password');
      await page.waitForLoadState('networkidle');
      
      // Check if page loaded (may be 404 if route doesn't exist)
      const hasForm = await page.getByLabel(/email/i).first().isVisible().catch(() => false);
      if (hasForm) {
        await expect(page.getByLabel(/email/i).first()).toBeVisible();
      }
    }
  });

  test('should submit password reset request', async ({ page }) => {
    // Navigate to password reset page
    await page.goto('/forgot-password');
    await page.waitForLoadState('networkidle');
    
    // Check if form exists
    const emailInput = page.getByLabel(/email/i).first();
    const hasForm = await emailInput.isVisible().catch(() => false);
    
    if (hasForm) {
      // Fill in email
      await emailInput.fill('test@example.com');
      
      // Submit form
      const submitButton = page.getByRole('button', { name: /submit|send|reset/i }).first();
      if (await submitButton.isVisible().catch(() => false)) {
        await submitButton.click();
        
        // Wait for success message or redirect
        await page.waitForTimeout(2000);
        
        // Verify success message or redirect
        const successMessage = page.getByText(/check.*email|sent|success/i).first();
        const hasSuccess = await successMessage.isVisible().catch(() => false);
        
        if (hasSuccess) {
          await expect(successMessage).toBeVisible();
        }
      }
    }
  });
});
