import type { CanonicalReportArtifact } from '../../artifacts/canonicalReportArtifact';
import type { ReportArtifact } from '../../types';

export const canonicalReportArtifactWireFixture = {
  schema_version: 1,
  artifact_type: 'stock_analysis_report',
  symbol: 'MSFT',
  stock_name: 'Microsoft Corporation',
  query: 'MSFT market data research',
  generated_at: '2026-07-10T00:00:00+00:00',
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
    focus_ticker: 'MSFT',
    evidence_count: 4,
    focus_evidence_count: 4,
    primary_count: 3,
    risk_count: 1,
    methodology_share: 0,
    placeholder_share: 0,
    external_non_serenity_count: 0,
    flags: [],
  },
  skeptical_review: {
    summary: 'Risk coverage uses 1 risk or invalidation evidence item.',
    counter_thesis: ['MSFT closed lower on 2026-07-08.'],
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
      claim_id: 'claim:MSFT:readiness',
      claim: 'Readiness is ready.',
      provenance_refs: [
        {
          evidence_id: 'serenity:market-data:MSFT:quote:2026-07-10',
          source_url: 'serenity://market-data/MSFT/quote/2026-07-10',
          source_title: 'MSFT quote',
          excerpt: 'Normalized quote evidence.',
        },
      ],
      diagnostics: [],
    },
  ],
} as const satisfies CanonicalReportArtifact;

export const reportArtifactFixture = {
  schemaVersion: 1,
  artifactType: 'stock_analysis_report',
  symbol: 'MSFT',
  company: 'Microsoft Corporation',
  query: 'MSFT market data research',
  generatedAt: '2026-07-10T00:00:00+00:00',
  researchOnly: true,
  markdownHref: '/api/artifacts/stock-analysis/latest/report',
  manifestHref: '/api/artifacts/stock-analysis/latest/manifest',
  readiness: {
    status: 'ready',
    reason: 'readiness_ready',
    flags: [],
  },
  reportGate: {
    status: 'available',
    reason: 'readiness_ready',
    researchOnly: true,
  },
  sourceCoverage: {
    status: 'ready',
    focusTicker: 'MSFT',
    evidenceCount: 4,
    focusEvidenceCount: 4,
    primaryCount: 3,
    riskCount: 1,
    methodologyShare: 0,
    placeholderShare: 0,
    externalNonSerenityCount: 0,
    flags: [],
  },
  safety: {
    passed: true,
    boundary: 'research only; not investment advice',
    findings: [],
  },
  skepticalReview: {
    summary: 'Risk coverage uses 1 risk or invalidation evidence item.',
    counterThesis: ['MSFT closed lower on 2026-07-08.'],
  },
  keyClaims: [
    {
      claimId: 'claim:MSFT:readiness',
      claim: 'Readiness is ready.',
      provenanceRefs: [
        {
          evidenceId: 'serenity:market-data:MSFT:quote:2026-07-10',
          sourceUrl: 'serenity://market-data/MSFT/quote/2026-07-10',
          sourceTitle: 'MSFT quote',
          excerpt: 'Normalized quote evidence.',
        },
      ],
      diagnostics: [],
    },
  ],
} satisfies ReportArtifact;
