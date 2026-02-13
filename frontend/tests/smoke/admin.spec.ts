import { test, expect } from '@playwright/test';

test.describe('Admin Flow', () => {
  test('should login as admin and verify admin landing loads', async ({ page }) => {
    const adminEmail = process.env.ADMIN_USER || 'admin@example.com';
    const adminPassword = process.env.ADMIN_PASS || 'Admin123!';
    
    // Navigate to login
    await page.goto('/login');
    
    // Fill login form
    await page.getByTestId('login-email-input').fill(adminEmail);
    await page.getByTestId('login-password-input').fill(adminPassword);
    await page.getByTestId('login-submit-button').click();
    
    // Wait for navigation to admin dashboard
    await page.waitForURL(/\/admin/, { timeout: 10000 });
    
    // Verify admin dashboard loads
    await expect(page).toHaveURL(/\/admin/);
    
    // Check admin sidebar is visible
    await expect(page.getByTestId('admin-sidebar')).toBeVisible();
    
    // Check dashboard content is visible (at least the header)
    const dashboardHeader = page.getByRole('heading', { name: /dashboard/i }).first();
    await expect(dashboardHeader).toBeVisible({ timeout: 5000 });
  });
});
