import { expect, test, type Page } from '@playwright/test';

const canonicalPlaywrightArtifact = {
  schema_version: 1,
  artifact_type: 'stock_analysis_report',
  symbol: 'NVDA',
  stock_name: 'NVIDIA Corporation',
  query: 'NVDA accelerated computing research',
  generated_at: '2026-07-11T00:00:00+00:00',
  research_only: true,
  readiness: {
    status: 'ready',
    reason: 'readiness_ready',
    flags: [],
  },
  report_gate: {
    status: 'available',
    reason: 'readiness_ready',
    research_only: true,
  },
  source_coverage: {
    status: 'ready',
    focus_ticker: 'NVDA',
    evidence_count: 6,
    focus_evidence_count: 5,
    primary_count: 3,
    risk_count: 2,
    methodology_share: 0,
    placeholder_share: 0,
    external_non_serenity_count: 1,
    flags: [
      {
        code: 'external_source_reviewed',
        severity: 'info',
        message: 'One external source passed provenance review.',
        recommendation: 'Retain source-level traceability.',
      },
    ],
  },
  skeptical_review: {
    summary: 'Risk coverage uses 2 risk or invalidation evidence items.',
    counter_thesis: ['Demand concentration remains an explicit invalidation risk.'],
  },
  reports: {
    stock_analysis: '/api/artifacts/stock-analysis/latest/report',
    manifest: '/api/artifacts/stock-analysis/latest/manifest',
  },
  safety: {
    passed: true,
    boundary: 'research only; not investment advice',
    findings: [],
  },
  key_claims: [
    {
      claim_id: 'claim:NVDA:readiness',
      claim: 'NVDA research readiness is ready.',
      provenance_refs: [
        {
          evidence_id: 'serenity:market-data:NVDA:quote:2026-07-11',
          source_url: 'serenity://market-data/NVDA/quote/2026-07-11',
          source_title: 'NVDA normalized quote',
          excerpt: 'Normalized quote evidence supports the current research state.',
        },
      ],
      diagnostics: [],
    },
  ],
};

test('canonical non-AAPL artifact drives the complete research flow', async ({
  page,
}) => {
  await page.route(
    '**/api/artifacts/stock-analysis/latest',
    async (route) => {
      expect(route.request().method()).toBe('GET');
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(canonicalPlaywrightArtifact),
      });
    },
  );

  await page.goto('/');

  await expect(
    page.getByRole('heading', { name: 'Serenity Alpha Lab' }),
  ).toBeVisible();
  await expect(page.getByText('NVDA', { exact: true })).toBeVisible();
  await expect(
    page.getByText('NVDA accelerated computing research'),
  ).toBeVisible();
  await expectNoAapl(page);

  await page.getByRole('link', { name: 'Analysis' }).click();
  await expect(
    page.getByRole('heading', { name: 'Analysis Workbench' }),
  ).toBeVisible();
  const semantics = page.getByRole('region', { name: 'Report Semantics' });
  await expect(semantics.getByText('Readiness gate')).toBeVisible();
  await expect(semantics.getByText('readiness_ready')).toBeVisible();
  await expect(semantics.getByText('Evidence 6', { exact: true })).toBeVisible();
  await expect(semantics.getByText('Focus 5', { exact: true })).toBeVisible();
  await expect(semantics.getByText('Primary 3', { exact: true })).toBeVisible();
  await expect(semantics.getByText('Risk 2', { exact: true })).toBeVisible();
  await expect(semantics.getByText('External 1', { exact: true })).toBeVisible();
  await expect(semantics.getByText('external_source_reviewed')).toBeVisible();
  await expect(
    semantics.getByText(
      'Risk coverage uses 2 risk or invalidation evidence items.',
    ),
  ).toBeVisible();
  await expect(semantics.getByText('Passed', { exact: true })).toBeVisible();
  await expect(
    semantics.getByText('research only; not investment advice'),
  ).toBeVisible();
  const provenance = semantics.getByRole('region', { name: 'Provenance' });
  await expect(
    provenance.getByText('serenity:market-data:NVDA:quote:2026-07-11'),
  ).toBeVisible();
  await expectNoAapl(page);

  await page.getByRole('button', { name: 'Open report reader' }).click();
  const reader = page.getByRole('dialog', { name: 'NVDA Report Reader' });
  await expect(reader).toBeVisible();
  await expect(
    reader.getByRole('link', { name: 'Open Markdown report' }),
  ).toHaveAttribute(
    'href',
    '/api/artifacts/stock-analysis/latest/report',
  );
  await expect(
    reader.getByRole('link', { name: 'Open manifest' }),
  ).toHaveAttribute(
    'href',
    '/api/artifacts/stock-analysis/latest/manifest',
  );
  await expectNoAapl(page);

  await reader.getByRole('button', { name: 'Close report reader' }).click();
  await expect(reader).toBeHidden();

  await page.getByRole('link', { name: 'History' }).click();
  await expect(page.getByRole('heading', { name: 'History' })).toBeVisible();
  await expect(page.getByText('Latest available artifact')).toBeVisible();
  await expect(
    page.getByText('NVDA accelerated computing research'),
  ).toBeVisible();
  await expect(
    page.getByText(
      'This page shows the latest validated stock-analysis artifact. Complete run history is deferred to a separate source.',
    ),
  ).toBeVisible();
  await expectNoAapl(page);

  await page.getByRole('link', { name: 'Settings' }).click();
  await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
  await expect(
    page.getByText('No live providers are enabled by default.'),
  ).toBeVisible();
  await expectNoAapl(page);
});

test('blocked canonical artifact exposes no report links', async ({ page }) => {
  await page.route(
    '**/api/artifacts/stock-analysis/latest',
    async (route) => {
      expect(route.request().method()).toBe('GET');
      await route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({
          error: {
            code: 'artifact_blocked',
            reason: 'report_safety_failed',
          },
        }),
      });
    },
  );

  await page.goto('/analysis');

  const alert = page.getByRole('alert');
  await expect(
    alert.getByRole('heading', { name: 'Research artifact blocked' }),
  ).toBeVisible();
  await expect(alert.getByText('report_safety_failed')).toBeVisible();
  await expect(alert.getByRole('button', { name: 'Retry' })).toBeVisible();
  await expect(
    page.getByRole('link', { name: 'Open Markdown report' }),
  ).toHaveCount(0);
  await expect(
    page.getByRole('link', { name: 'Open manifest' }),
  ).toHaveCount(0);
  await expect(
    page.locator('a[href*="/api/artifacts/stock-analysis/latest/"]'),
  ).toHaveCount(0);
  await expectNoAapl(page);
});

async function expectNoAapl(page: Page): Promise<void> {
  await expect(page.locator('body')).not.toContainText(/\bAAPL\b/i);
}
