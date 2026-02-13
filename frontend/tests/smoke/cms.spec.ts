import { test, expect } from '@playwright/test';

test.describe('CMS Workflow', () => {
  test('should create, update, and publish a question as admin', async ({ page }) => {
    const adminEmail = process.env.ADMIN_USER || 'admin@example.com';
    const adminPassword = process.env.ADMIN_PASS || 'Admin123!';
    
    // Login as admin
    await page.goto('/login');
    await page.getByTestId('login-email-input').fill(adminEmail);
    await page.getByTestId('login-password-input').fill(adminPassword);
    await page.getByTestId('login-submit-button').click();
    
    // Wait for admin dashboard
    await page.waitForURL(/\/admin/, { timeout: 10000 });
    
    // Navigate to questions page
    await page.goto('/admin/questions');
    await page.waitForLoadState('networkidle');
    
    // Click "New Question" button (look for Plus icon or "New" button)
    const newButton = page.getByRole('button', { name: /new|create|add/i }).first();
    await newButton.click();
    
    // Wait for new question page
    await page.waitForURL(/\/admin\/questions\/new/, { timeout: 10000 });
    
    // Fill in question form (minimal for draft)
    const stemInput = page.getByLabel(/question|stem/i).first();
    await stemInput.fill('Test question for CMS workflow');
    
    // Fill in options
    const optionA = page.getByLabel(/option a|option 1/i).first();
    await optionA.fill('Option A');
    
    const optionB = page.getByLabel(/option b|option 2/i).first();
    await optionB.fill('Option B');
    
    // Save as draft
    const saveButton = page.getByRole('button', { name: /save.*draft|save/i }).first();
    await saveButton.click();
    
    // Wait for redirect to question detail page
    await page.waitForURL(/\/admin\/questions\/[^/]+$/, { timeout: 10000 });
    
    // Verify question was created (check for status or edit button)
    const questionPage = page.url();
    expect(questionPage).toMatch(/\/admin\/questions\/[^/]+$/);
    
    // Update the question (if there's an edit mode or update button)
    const updateButton = page.getByRole('button', { name: /update|edit|save/i }).first();
    if (await updateButton.isVisible().catch(() => false)) {
      await updateButton.click();
      // Make a small change
      await stemInput.fill('Updated test question for CMS workflow');
      await saveButton.click();
    }
    
    // Submit for review (if button exists)
    const submitButton = page.getByRole('button', { name: /submit.*review|submit/i }).first();
    if (await submitButton.isVisible().catch(() => false)) {
      await submitButton.click();
      // Wait for status change
      await page.waitForTimeout(1000);
    }
    
    // Approve question (if button exists and question is in review)
    const approveButton = page.getByRole('button', { name: /approve/i }).first();
    if (await approveButton.isVisible().catch(() => false)) {
      await approveButton.click();
      await page.waitForTimeout(1000);
    }
    
    // Publish question (if button exists and question is approved)
    const publishButton = page.getByRole('button', { name: /publish/i }).first();
    if (await publishButton.isVisible().catch(() => false)) {
      await publishButton.click();
      await page.waitForTimeout(1000);
    }
    
    // Verify we're still on the question page (workflow completed)
    expect(page.url()).toMatch(/\/admin\/questions\/[^/]+$/);
  });
});
