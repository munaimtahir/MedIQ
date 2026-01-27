import { test, expect } from '@playwright/test';

test.describe('Logout Flow', () => {
  test('should logout successfully', async ({ page }) => {
    const studentEmail = process.env.STUDENT_USER || 'student-1@example.com';
    const studentPassword = process.env.STUDENT_PASS || 'StudentPass123!';
    
    // Login first
    await page.goto('/login');
    await page.getByTestId('login-email-input').fill(studentEmail);
    await page.getByTestId('login-password-input').fill(studentPassword);
    await page.getByTestId('login-submit-button').click();
    
    // Wait for dashboard
    await page.waitForURL(/\/student\/dashboard/, { timeout: 10000 });
    
    // Click logout button (in sidebar or header)
    const logoutButton = page.getByTestId('logout-button');
    await expect(logoutButton).toBeVisible({ timeout: 5000 });
    await logoutButton.click();
    
    // Wait for redirect to login
    await page.waitForURL(/\/login/, { timeout: 10000 });
    
    // Verify we're on login page
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByTestId('login-form')).toBeVisible();
  });
});
