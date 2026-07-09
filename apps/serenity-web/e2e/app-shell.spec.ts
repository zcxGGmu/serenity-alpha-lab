import { expect, test } from '@playwright/test';

test('Serenity-owned app shell exposes core pages and report-reading flow', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'Serenity Alpha Lab' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Primary' })).toBeVisible();

  await page.getByRole('link', { name: 'Analysis' }).click();
  await expect(page.getByRole('heading', { name: 'Analysis Workbench' })).toBeVisible();
  await expect(page.getByText('Research-only stock analysis')).toBeVisible();

  await page.getByRole('button', { name: 'Open report reader' }).click();
  const reader = page.getByRole('dialog', { name: 'AAPL Report Reader' });
  await expect(reader).toBeVisible();
  await expect(reader.getByText('Readiness gate')).toBeVisible();
  await expect(reader.getByText('Provenance', { exact: true })).toBeVisible();
  await expect(reader.getByText('Source coverage', { exact: true })).toBeVisible();
  await expect(reader.getByText('Skeptical review', { exact: true })).toBeVisible();
  await expect(reader.getByText('Report safety')).toBeVisible();
  await expect(reader.getByText('research only; not investment advice')).toBeVisible();
  await expect(reader.getByRole('link', { name: 'Open Markdown report' })).toHaveAttribute(
    'data-report-href',
    'reports/stock-analysis-report.md',
  );

  await reader.getByRole('button', { name: 'Close report reader' }).click();
  await expect(reader).toBeHidden();

  await page.getByRole('link', { name: 'History' }).click();
  await expect(page.getByRole('heading', { name: 'History' })).toBeVisible();
  await expect(page.getByText('AAPL market data research')).toBeVisible();

  await page.getByRole('link', { name: 'Settings' }).click();
  await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
  await expect(page.getByText('No live providers are enabled by default.')).toBeVisible();
});
