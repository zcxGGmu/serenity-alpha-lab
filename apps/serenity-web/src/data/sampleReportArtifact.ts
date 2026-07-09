import type { ReportArtifact } from '../types';

export const sampleReportArtifact: ReportArtifact = {
  symbol: 'AAPL',
  company: 'Apple Inc.',
  query: 'AAPL market data research',
  generatedAt: '2026-07-09 09:30 UTC',
  researchOnly: true,
  markdownHref: 'reports/stock-analysis-report.md',
  manifestHref: 'analysis-report-manifest.json',
  readiness: {
    status: 'needs_work',
    reason: 'readiness_not_ready',
    flags: ['missing_primary_source_depth', 'needs_recent_risk_evidence'],
  },
  sourceCoverage: {
    status: 'needs_work',
    primarySources: {
      collected: 3,
      required: 5,
    },
    flags: ['primary-source-depth:needs-work', 'risk-coverage:watch'],
  },
  safety: {
    passed: true,
    boundary: 'research only; not investment advice',
    findings: [],
  },
  skepticalReview: {
    summary: 'Risk coverage uses 1 risk or invalidation evidence item.',
    counterThesis: [
      'Primary-source coverage is below the publish-quality threshold.',
      'Recent downside evidence should be collected before stronger conclusions.',
    ],
  },
  keyClaims: [
    {
      claimId: 'claim:AAPL:latest-normalized-quote',
      claim: 'Latest normalized quote is available for AAPL.',
      provenanceRefs: [
        {
          evidenceId: 'serenity:market-data:AAPL:quote:2026-07-09',
          sourceUrl: 'serenity://market-data/AAPL/quote/2026-07-09',
          sourceTitle: 'Serenity normalized quote snapshot',
          excerpt: 'AAPL quote normalized from the stub market data provider.',
        },
      ],
      diagnostics: [],
    },
    {
      claimId: 'claim:AAPL:readiness',
      claim: 'Readiness is needs_work with missing primary-source depth.',
      provenanceRefs: [
        {
          evidenceId: 'serenity:market-data:AAPL:bars:2026-07-09',
          sourceUrl: 'serenity://market-data/AAPL/daily-bars/2026-07-09',
          sourceTitle: 'Serenity daily bar snapshot',
          excerpt: 'Daily bars provide recent market context but need more primary-source support.',
        },
      ],
      diagnostics: [],
    },
    {
      claimId: 'claim:AAPL:risk-coverage',
      claim: 'Risk coverage uses 1 risk or invalidation evidence item.',
      provenanceRefs: [
        {
          evidenceId: 'serenity:market-data:AAPL:risk-bar:2026-07-06',
          sourceUrl: 'serenity://market-data/AAPL/risk/2026-07-06',
          sourceTitle: 'Serenity downside movement snapshot',
          excerpt: 'One negative daily movement is available for skeptical review.',
        },
      ],
      diagnostics: [],
    },
  ],
};
