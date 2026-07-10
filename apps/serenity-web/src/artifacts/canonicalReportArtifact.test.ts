import { describe, expect, it } from 'vitest';

import { canonicalReportArtifactWireFixture } from '../test/fixtures/reportArtifacts';
import { decodeCanonicalReportArtifact } from './canonicalReportArtifact';

type JsonRecord = Record<string, unknown>;

function validPayload(): JsonRecord {
  return structuredClone(canonicalReportArtifactWireFixture) as JsonRecord;
}

function nestedRecord(
  payload: JsonRecord,
  key: string,
): JsonRecord {
  return payload[key] as JsonRecord;
}

function firstClaim(payload: JsonRecord): JsonRecord {
  return (payload.key_claims as JsonRecord[])[0];
}

function firstProvenanceRef(payload: JsonRecord): JsonRecord {
  return (firstClaim(payload).provenance_refs as JsonRecord[])[0];
}

interface InvalidCase {
  name: string;
  message: string;
  mutate: (payload: JsonRecord) => void;
}

const invalidCases: InvalidCase[] = [
  {
    name: 'missing schema version',
    message: 'schema_version_unsupported',
    mutate: (payload) => {
      delete payload.schema_version;
    },
  },
  {
    name: 'unsupported schema version',
    message: 'schema_version_unsupported',
    mutate: (payload) => {
      payload.schema_version = 2;
    },
  },
  {
    name: 'boolean schema version',
    message: 'schema_version_unsupported',
    mutate: (payload) => {
      payload.schema_version = true;
    },
  },
  {
    name: 'wrong artifact type',
    message: 'artifact_type_unsupported',
    mutate: (payload) => {
      payload.artifact_type = 'trade_order';
    },
  },
  {
    name: 'blank symbol',
    message: 'symbol_invalid',
    mutate: (payload) => {
      payload.symbol = '   ';
    },
  },
  {
    name: 'invalid generated timestamp',
    message: 'generated_at_invalid',
    mutate: (payload) => {
      payload.generated_at = 'not-a-timestamp';
    },
  },
  {
    name: 'naive generated timestamp',
    message: 'generated_at_invalid',
    mutate: (payload) => {
      payload.generated_at = '2026-07-10T00:00:00';
    },
  },
  {
    name: 'impossible generated calendar date',
    message: 'generated_at_invalid',
    mutate: (payload) => {
      payload.generated_at = '2026-02-30T00:00:00+00:00';
    },
  },
  {
    name: 'missing research-only flag',
    message: 'research_only_required',
    mutate: (payload) => {
      delete payload.research_only;
    },
  },
  {
    name: 'false research-only flag',
    message: 'research_only_required',
    mutate: (payload) => {
      payload.research_only = false;
    },
  },
  {
    name: 'missing readiness',
    message: 'readiness_missing',
    mutate: (payload) => {
      delete payload.readiness;
    },
  },
  {
    name: 'unknown readiness status',
    message: 'readiness_invalid',
    mutate: (payload) => {
      nestedRecord(payload, 'readiness').status = 'published';
    },
  },
  {
    name: 'missing report gate',
    message: 'report_gate_missing',
    mutate: (payload) => {
      delete payload.report_gate;
    },
  },
  {
    name: 'unknown report gate status',
    message: 'report_gate_invalid',
    mutate: (payload) => {
      nestedRecord(payload, 'report_gate').status = 'ready';
    },
  },
  {
    name: 'false report gate research-only flag',
    message: 'report_gate_research_only_required',
    mutate: (payload) => {
      nestedRecord(payload, 'report_gate').research_only = false;
    },
  },
  {
    name: 'missing source coverage',
    message: 'source_coverage_missing',
    mutate: (payload) => {
      delete payload.source_coverage;
    },
  },
  {
    name: 'unknown source coverage status',
    message: 'source_coverage_invalid',
    mutate: (payload) => {
      nestedRecord(payload, 'source_coverage').status = 'available';
    },
  },
  {
    name: 'non-finite coverage count',
    message: 'source_coverage_invalid',
    mutate: (payload) => {
      nestedRecord(payload, 'source_coverage').evidence_count = Number.NaN;
    },
  },
  {
    name: 'negative coverage count',
    message: 'source_coverage_invalid',
    mutate: (payload) => {
      nestedRecord(payload, 'source_coverage').risk_count = -1;
    },
  },
  {
    name: 'fractional coverage count',
    message: 'source_coverage_invalid',
    mutate: (payload) => {
      nestedRecord(payload, 'source_coverage').primary_count = 1.5;
    },
  },
  {
    name: 'boolean coverage count',
    message: 'source_coverage_invalid',
    mutate: (payload) => {
      nestedRecord(payload, 'source_coverage').focus_evidence_count = true;
    },
  },
  {
    name: 'non-finite methodology share',
    message: 'source_coverage_invalid',
    mutate: (payload) => {
      nestedRecord(payload, 'source_coverage').methodology_share =
        Number.POSITIVE_INFINITY;
    },
  },
  {
    name: 'negative placeholder share',
    message: 'source_coverage_invalid',
    mutate: (payload) => {
      nestedRecord(payload, 'source_coverage').placeholder_share = -0.1;
    },
  },
  {
    name: 'invalid structured coverage flag',
    message: 'source_coverage_invalid',
    mutate: (payload) => {
      nestedRecord(payload, 'source_coverage').flags = [
        {
          code: 'missing_primary_source_depth',
          severity: 'warning',
          message: 'Primary-source depth is incomplete.',
        },
      ];
    },
  },
  {
    name: 'missing skeptical review',
    message: 'skeptical_review_missing',
    mutate: (payload) => {
      delete payload.skeptical_review;
    },
  },
  {
    name: 'empty skeptical counter-thesis',
    message: 'skeptical_review_invalid',
    mutate: (payload) => {
      nestedRecord(payload, 'skeptical_review').counter_thesis = [];
    },
  },
  {
    name: 'missing safety',
    message: 'report_safety_failed',
    mutate: (payload) => {
      delete payload.safety;
    },
  },
  {
    name: 'failed safety result',
    message: 'report_safety_failed',
    mutate: (payload) => {
      nestedRecord(payload, 'safety').passed = false;
    },
  },
  {
    name: 'missing research-only boundary',
    message: 'research_boundary_required',
    mutate: (payload) => {
      nestedRecord(payload, 'safety').boundary = '';
    },
  },
  {
    name: 'boundary without research-only language',
    message: 'research_boundary_required',
    mutate: (payload) => {
      nestedRecord(payload, 'safety').boundary = 'For internal use only.';
    },
  },
  {
    name: 'invalid structured safety finding',
    message: 'report_safety_invalid',
    mutate: (payload) => {
      nestedRecord(payload, 'safety').findings = [
        {
          line_number: 3.5,
          phrase: 'target price',
          line: 'Unsafe line.',
        },
      ];
    },
  },
  {
    name: 'missing reports',
    message: 'reports_missing',
    mutate: (payload) => {
      delete payload.reports;
    },
  },
  {
    name: 'external report href',
    message: 'artifact_href_invalid',
    mutate: (payload) => {
      nestedRecord(payload, 'reports').stock_analysis =
        'https://example.com/report';
    },
  },
  {
    name: 'file report href',
    message: 'artifact_href_invalid',
    mutate: (payload) => {
      nestedRecord(payload, 'reports').stock_analysis =
        'file:///tmp/report';
    },
  },
  {
    name: 'parent traversal report href',
    message: 'artifact_href_invalid',
    mutate: (payload) => {
      nestedRecord(payload, 'reports').stock_analysis = '../report';
    },
  },
  {
    name: 'protocol-relative manifest href',
    message: 'artifact_href_invalid',
    mutate: (payload) => {
      nestedRecord(payload, 'reports').manifest = '//example.com/manifest';
    },
  },
  {
    name: 'report href with query',
    message: 'artifact_href_invalid',
    mutate: (payload) => {
      nestedRecord(payload, 'reports').stock_analysis =
        '/api/artifacts/stock-analysis/latest/report?raw=1';
    },
  },
  {
    name: 'manifest href with fragment',
    message: 'artifact_href_invalid',
    mutate: (payload) => {
      nestedRecord(payload, 'reports').manifest =
        '/api/artifacts/stock-analysis/latest/manifest#raw';
    },
  },
  {
    name: 'report href with backslash',
    message: 'artifact_href_invalid',
    mutate: (payload) => {
      nestedRecord(payload, 'reports').stock_analysis =
        '/api/artifacts/stock-analysis/latest\\report';
    },
  },
  {
    name: 'encoded parent traversal href',
    message: 'artifact_href_invalid',
    mutate: (payload) => {
      nestedRecord(payload, 'reports').manifest =
        '/api/artifacts/stock-analysis/latest/%2e%2e/manifest';
    },
  },
  {
    name: 'swapped report and manifest hrefs',
    message: 'artifact_href_invalid',
    mutate: (payload) => {
      const reports = nestedRecord(payload, 'reports');
      reports.stock_analysis =
        '/api/artifacts/stock-analysis/latest/manifest';
      reports.manifest = '/api/artifacts/stock-analysis/latest/report';
    },
  },
  {
    name: 'unknown API artifact suffix',
    message: 'artifact_href_invalid',
    mutate: (payload) => {
      nestedRecord(payload, 'reports').stock_analysis =
        '/api/artifacts/stock-analysis/latest/raw';
    },
  },
  {
    name: 'empty key claims',
    message: 'key_claims_missing',
    mutate: (payload) => {
      payload.key_claims = [];
    },
  },
  {
    name: 'empty key-claim provenance',
    message: 'key_claim_provenance_missing',
    mutate: (payload) => {
      firstClaim(payload).provenance_refs = [];
    },
  },
  {
    name: 'incomplete provenance fields',
    message: 'key_claim_provenance_missing',
    mutate: (payload) => {
      delete firstProvenanceRef(payload).excerpt;
    },
  },
  {
    name: 'unsafe provenance URL',
    message: 'key_claim_provenance_missing',
    mutate: (payload) => {
      firstProvenanceRef(payload).source_url = 'javascript:alert(1)';
    },
  },
  {
    name: 'relative provenance URL',
    message: 'key_claim_provenance_missing',
    mutate: (payload) => {
      firstProvenanceRef(payload).source_url = '/private/evidence.json';
    },
  },
  {
    name: 'provenance URL with credentials',
    message: 'key_claim_provenance_missing',
    mutate: (payload) => {
      firstProvenanceRef(payload).source_url =
        'https://user:secret@example.com/evidence';
    },
  },
  {
    name: 'non-string claim diagnostics',
    message: 'key_claim_invalid',
    mutate: (payload) => {
      firstClaim(payload).diagnostics = [42];
    },
  },
  {
    name: 'recursive operation advice field',
    message: 'forbidden_field',
    mutate: (payload) => {
      payload.nested = { operation_advice: 'buy' };
    },
  },
  {
    name: 'recursive target price field',
    message: 'forbidden_field',
    mutate: (payload) => {
      firstClaim(payload).metadata = { targetPrice: 500 };
    },
  },
  {
    name: 'recursive position sizing field',
    message: 'forbidden_field',
    mutate: (payload) => {
      nestedRecord(payload, 'source_coverage').metadata = {
        'position-sizing': 'all-in',
      };
    },
  },
  {
    name: 'recursive broker field',
    message: 'forbidden_field',
    mutate: (payload) => {
      nestedRecord(payload, 'readiness').brokerage_account = 'hidden';
    },
  },
  {
    name: 'recursive order field',
    message: 'forbidden_field',
    mutate: (payload) => {
      nestedRecord(payload, 'skeptical_review').order_details = {
        side: 'buy',
      };
    },
  },
  {
    name: 'recursive forbidden field inside an array',
    message: 'forbidden_field',
    mutate: (payload) => {
      payload.nested = [{ metadata: { tradeAction: 'buy' } }];
    },
  },
];

describe('decodeCanonicalReportArtifact', () => {
  it.each([null, [], 'artifact', 1, true])(
    'rejects non-object root input %j',
    (input) => {
      expect(() => decodeCanonicalReportArtifact(input)).toThrow(
        'artifact_object_required',
      );
    },
  );

  it('decodes and maps a valid canonical artifact without semantic loss', () => {
    const payload = validPayload();
    payload.internal_debug = { local_path: '/tmp/private.json' };
    nestedRecord(payload, 'readiness').internal_state = 'hidden';
    firstProvenanceRef(payload).local_path = '/tmp/private-source.txt';

    const artifact = decodeCanonicalReportArtifact(payload);

    expect(artifact).toMatchObject({
      schemaVersion: 1,
      artifactType: 'stock_analysis_report',
      symbol: 'MSFT',
      company: 'Microsoft Corporation',
      generatedAt: '2026-07-10T00:00:00+00:00',
      researchOnly: true,
      markdownHref: '/api/artifacts/stock-analysis/latest/report',
      manifestHref: '/api/artifacts/stock-analysis/latest/manifest',
      reportGate: {
        status: 'available',
        reason: 'readiness_ready',
        researchOnly: true,
      },
      sourceCoverage: {
        evidenceCount: 4,
        focusEvidenceCount: 4,
        primaryCount: 3,
        riskCount: 1,
        externalNonSerenityCount: 0,
      },
    });
    expect(artifact.keyClaims[0].provenanceRefs[0].evidenceId).toBe(
      'serenity:market-data:MSFT:quote:2026-07-10',
    );
    expect(artifact).not.toHaveProperty('internal_debug');
    expect(JSON.stringify(artifact)).not.toContain('internal_state');
    expect(JSON.stringify(artifact)).not.toContain('local_path');
  });

  it('returns a detached projection and accepts trusted provenance schemes', () => {
    const payload = validPayload();
    firstProvenanceRef(payload).source_url =
      'https://example.com/research/evidence';

    const artifact = decodeCanonicalReportArtifact(payload);

    nestedRecord(payload, 'readiness').flags = ['changed_after_decode'];
    firstProvenanceRef(payload).source_title = 'Changed after decode';

    expect(artifact.readiness.flags).toEqual([]);
    expect(artifact.keyClaims[0].provenanceRefs[0]).toMatchObject({
      sourceUrl: 'https://example.com/research/evidence',
      sourceTitle: 'MSFT quote',
    });
  });

  it('does not reject safe research text when forbidden words appear only in values', () => {
    const payload = validPayload();
    payload.query = 'MSFT order-flow research';
    firstClaim(payload).claim = 'Broker research coverage is available.';

    const artifact = decodeCanonicalReportArtifact(payload);

    expect(artifact.query).toBe('MSFT order-flow research');
    expect(artifact.keyClaims[0].claim).toBe(
      'Broker research coverage is available.',
    );
  });

  it.each(invalidCases)('rejects $name', ({ mutate, message }) => {
    const payload = validPayload();
    mutate(payload);

    expect(() => decodeCanonicalReportArtifact(payload)).toThrow(message);
  });
});
