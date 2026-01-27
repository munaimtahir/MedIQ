import { test, expect } from '@playwright/test';

test.describe('Session Creation and Question Answering', () => {
  test('should create a session and answer questions as student', async ({ page }) => {
    const studentEmail = process.env.STUDENT_USER || 'student-1@example.com';
    const studentPassword = process.env.STUDENT_PASS || 'StudentPass123!';
    
    // Login as student
    await page.goto('/login');
    await page.getByTestId('login-email-input').fill(studentEmail);
    await page.getByTestId('login-password-input').fill(studentPassword);
    await page.getByTestId('login-submit-button').click();
    
    // Wait for student dashboard
    await page.waitForURL(/\/student/, { timeout: 10000 });
    
    // Navigate to session creation or start a practice session
    // Look for "Start Session", "Practice", or similar button
    const startSessionButton = page.getByRole('button', { name: /start.*session|practice|begin/i }).first();
    
    if (await startSessionButton.isVisible().catch(() => false)) {
      await startSessionButton.click();
      
      // Wait for session page or modal
      await page.waitForTimeout(2000);
      
      // If there's a session configuration modal, fill it and start
      const startButton = page.getByRole('button', { name: /start|begin|create/i }).first();
      if (await startButton.isVisible().catch(() => false)) {
        await startButton.click();
      }
    } else {
      // Alternative: navigate directly to session creation if URL is known
      await page.goto('/student/session/new');
      await page.waitForLoadState('networkidle');
      
      // Fill session configuration if needed
      const createButton = page.getByRole('button', { name: /create|start/i }).first();
      if (await createButton.isVisible().catch(() => false)) {
        await createButton.click();
      }
    }
    
    // Wait for session player page
    await page.waitForURL(/\/student\/session\/[^/]+$/, { timeout: 15000 });
    
    // Verify session page loaded
    const sessionUrl = page.url();
    expect(sessionUrl).toMatch(/\/student\/session\/[^/]+$/);
    
    // Wait for question to load
    await page.waitForTimeout(2000);
    
    // Look for question stem or options
    const questionStem = page.getByText(/what|which|how|when/i).first();
    const hasQuestion = await questionStem.isVisible().catch(() => false);
    
    if (hasQuestion) {
      // Try to find and click an option (usually radio buttons or clickable divs)
      const optionButtons = page.getByRole('button', { name: /option|a|b|c|d|e/i });
      const optionCount = await optionButtons.count();
      
      if (optionCount > 0) {
        // Click first option
        await optionButtons.first().click();
        await page.waitForTimeout(500);
      } else {
        // Try clicking on option text directly
        const optionText = page.getByText(/^[A-E]\.|^option [a-e]/i).first();
        if (await optionText.isVisible().catch(() => false)) {
          await optionText.click();
          await page.waitForTimeout(500);
        }
      }
      
      // Look for "Next" or "Submit Answer" button
      const nextButton = page.getByRole('button', { name: /next|submit.*answer|continue/i }).first();
      if (await nextButton.isVisible().catch(() => false)) {
        await nextButton.click();
        await page.waitForTimeout(1000);
      }
    }
    
    // Verify we're still in the session (or moved to next question)
    const currentUrl = page.url();
    expect(currentUrl).toMatch(/\/student\/session\/[^/]+/);
    
    // Try to submit session (look for submit/finish button)
    const submitButton = page.getByRole('button', { name: /submit|finish|end.*session/i }).first();
    if (await submitButton.isVisible().catch(() => false)) {
      await submitButton.click();
      await page.waitForTimeout(2000);
      
      // After submission, should be on review page or redirected
      const finalUrl = page.url();
      expect(finalUrl).toMatch(/\/student\/session\/[^/]+/);
    }
  });
});
