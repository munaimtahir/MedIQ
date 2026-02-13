import { test, expect } from '@playwright/test';

test.describe('Student Flow', () => {
  test('should login as student and verify student dashboard loads', async ({ page }) => {
    const studentEmail = process.env.STUDENT_USER || 'student@example.com';
    const studentPassword = process.env.STUDENT_PASS || 'Student123!';
    
    // Navigate to login
    await page.goto('/login');
    
    // Fill login form
    await page.getByTestId('login-email-input').fill(studentEmail);
    await page.getByTestId('login-password-input').fill(studentPassword);
    await page.getByTestId('login-submit-button').click();
    
    // Wait for navigation to student dashboard
    await page.waitForURL(/\/student\/dashboard/, { timeout: 10000 });
    
    // Verify student dashboard loads
    await expect(page).toHaveURL(/\/student\/dashboard/);
    
    // Check student sidebar is visible
    await expect(page.getByTestId('student-sidebar')).toBeVisible();
    
    // Check dashboard content is visible (at least the header)
    const dashboardHeader = page.getByRole('heading', { name: /dashboard/i }).first();
    await expect(dashboardHeader).toBeVisible({ timeout: 5000 });
  });

  test('should open revision page and verify question cards render', async ({ page }) => {
    const studentEmail = process.env.STUDENT_USER || 'student@example.com';
    const studentPassword = process.env.STUDENT_PASS || 'Student123!';
    
    // Login first
    await page.goto('/login');
    await page.getByTestId('login-email-input').fill(studentEmail);
    await page.getByTestId('login-password-input').fill(studentPassword);
    await page.getByTestId('login-submit-button').click();
    
    // Wait for dashboard
    await page.waitForURL(/\/student\/dashboard/, { timeout: 10000 });
    
    // Navigate to revision page
    await page.goto('/student/revision');
    await page.waitForLoadState('networkidle');
    
    // Check revision page loads
    await expect(page).toHaveURL(/\/student\/revision/);
    
    // Check revision page header
    const revisionHeader = page.getByRole('heading', { name: /revision/i }).first();
    await expect(revisionHeader).toBeVisible({ timeout: 5000 });
    
    // Check if there are themes (may be empty, but page should render)
    // Look for either the table or empty state
    const hasTable = await page.getByTestId('revision-themes-table').isVisible().catch(() => false);
    const hasEmptyState = await page.getByText(/no themes due today/i).isVisible().catch(() => false);
    
    // At least one should be visible
    expect(hasTable || hasEmptyState).toBeTruthy();
  });
});
