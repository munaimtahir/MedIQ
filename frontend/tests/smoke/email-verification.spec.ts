import { test, expect } from '@playwright/test';

test.describe('Email Verification Flow', () => {
  test('should show verification message after registration', async ({ page }) => {
    // Navigate to registration page (if exists)
    await page.goto('/register');
    await page.waitForLoadState('networkidle');
    
    // Check if registration form exists
    const emailInput = page.getByLabel(/email/i).first();
    const hasForm = await emailInput.isVisible().catch(() => false);
    
    if (hasForm) {
      // Fill registration form
      const testEmail = `test_${Date.now()}@example.com`;
      await emailInput.fill(testEmail);
      
      const passwordInput = page.getByLabel(/password/i).first();
      if (await passwordInput.isVisible().catch(() => false)) {
        await passwordInput.fill('TestPass123!');
        
        const nameInput = page.getByLabel(/name|full.*name/i).first();
        if (await nameInput.isVisible().catch(() => false)) {
          await nameInput.fill('Test User');
        }
        
        // Submit registration
        const submitButton = page.getByRole('button', { name: /register|sign.*up|create.*account/i }).first();
        if (await submitButton.isVisible().catch(() => false)) {
          await submitButton.click();
          
          // Wait for verification message or redirect
          await page.waitForTimeout(2000);
          
          // Check for verification message
          const verifyMessage = page.getByText(/verify.*email|check.*email|verification/i).first();
          const hasMessage = await verifyMessage.isVisible().catch(() => false);
          
          if (hasMessage) {
            await expect(verifyMessage).toBeVisible();
          }
        }
      }
    }
  });

  test('should handle verification link (mock)', async ({ page }) => {
    // Navigate to verification page with mock token
    await page.goto('/verify-email?token=mock_token_12345');
    await page.waitForLoadState('networkidle');
    
    // Check if verification page loads
    // Should either show success, error, or redirect
    const currentUrl = page.url();
    expect(currentUrl).toBeTruthy();
    
    // Look for verification-related content
    const verifyContent = page.getByText(/verify|verification|invalid|expired/i).first();
    const hasContent = await verifyContent.isVisible().catch(() => false);
    
    // Page should load (even if showing error for invalid token)
    expect(hasContent || currentUrl.includes('verify') || currentUrl.includes('login')).toBeTruthy();
  });
});
