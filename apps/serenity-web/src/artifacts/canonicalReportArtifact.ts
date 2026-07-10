import type {
  CoverageFlag,
  KeyClaim,
  ProvenanceRef,
  ReadinessStatus,
  ReportArtifact,
  ReportGateStatus,
  SafetyFinding,
  SourceCoverageStatus,
} from '../types';

const API_ARTIFACT_PREFIX = '/api/artifacts/stock-analysis/latest/';
const REPORT_HREF = `${API_ARTIFACT_PREFIX}report`;
const MANIFEST_HREF = `${API_ARTIFACT_PREFIX}manifest`;

const READINESS_STATUSES: readonly ReadinessStatus[] = [
  'ready',
  'needs_work',
  'blocked',
];
const REPORT_GATE_STATUSES: readonly ReportGateStatus[] = [
  'available',
  'blocked',
];
const SOURCE_COVERAGE_STATUSES: readonly SourceCoverageStatus[] = [
  'ready',
  'needs_work',
  'blocked',
];

const FORBIDDEN_FIELDS = [
  'operation_advice',
  'buy',
  'sell',
  'target_price',
  'price_target',
  'stop_loss',
  'take_profit',
  'position_size',
  'position_sizing',
  'broker',
  'order',
  'trade_action',
] as const;

export interface CanonicalProvenanceRef {
  evidence_id: string;
  source_url: string;
  source_title: string;
  excerpt: string;
}

export interface CanonicalKeyClaim {
  claim_id: string;
  claim: string;
  provenance_refs: CanonicalProvenanceRef[];
  diagnostics: string[];
}

export interface CanonicalReportArtifact {
  schema_version: 1;
  artifact_type: 'stock_analysis_report';
  symbol: string;
  stock_name: string;
  query: string;
  generated_at: string;
  research_only: true;
  readiness: {
    status: ReadinessStatus;
    reason: string;
    flags: string[];
  };
  report_gate: {
    status: ReportGateStatus;
    reason: string;
    research_only: true;
  };
  source_coverage: {
    status: SourceCoverageStatus;
    focus_ticker: string;
    evidence_count: number;
    focus_evidence_count: number;
    primary_count: number;
    risk_count: number;
    methodology_share: number;
    placeholder_share: number;
    external_non_serenity_count: number;
    flags: Array<{
      code: string;
      severity: string;
      message: string;
      recommendation: string;
    }>;
  };
  skeptical_review: {
    summary: string;
    counter_thesis: string[];
  };
  reports: {
    stock_analysis: string;
    manifest: string;
  };
  safety: {
    passed: true;
    boundary: string;
    findings: Array<{
      line_number: number;
      phrase: string;
      line: string;
    }>;
  };
  key_claims: CanonicalKeyClaim[];
}

export function decodeCanonicalReportArtifact(
  input: unknown,
): ReportArtifact {
  assertNoForbiddenFields(input);
  const artifact = requireRecord(input, 'artifact_object_required');

  if (artifact.schema_version !== 1) {
    fail('schema_version_unsupported');
  }
  if (artifact.artifact_type !== 'stock_analysis_report') {
    fail('artifact_type_unsupported');
  }
  if (artifact.research_only !== true) {
    fail('research_only_required');
  }

  const readiness = decodeReadiness(artifact.readiness);
  const reportGate = decodeReportGate(artifact.report_gate);
  const sourceCoverage = decodeSourceCoverage(artifact.source_coverage);
  const skepticalReview = decodeSkepticalReview(artifact.skeptical_review);
  const reports = decodeReports(artifact.reports);
  const safety = decodeSafety(artifact.safety);
  const keyClaims = decodeKeyClaims(artifact.key_claims);

  return {
    schemaVersion: 1,
    artifactType: 'stock_analysis_report',
    symbol: requireNonEmptyString(artifact.symbol, 'symbol_invalid'),
    company: requireNonEmptyString(artifact.stock_name, 'stock_name_invalid'),
    query: requireNonEmptyString(artifact.query, 'query_invalid'),
    generatedAt: requireTimestamp(artifact.generated_at),
    researchOnly: true,
    markdownHref: reports.markdownHref,
    manifestHref: reports.manifestHref,
    readiness,
    reportGate,
    sourceCoverage,
    safety,
    skepticalReview,
    keyClaims,
  };
}

function decodeReadiness(value: unknown): ReportArtifact['readiness'] {
  const readiness = requireRecord(value, 'readiness_missing');

  return {
    status: requireEnum(
      readiness.status,
      READINESS_STATUSES,
      'readiness_invalid',
    ),
    reason: requireNonEmptyString(readiness.reason, 'readiness_invalid'),
    flags: requireStringArray(readiness.flags, 'readiness_invalid'),
  };
}

function decodeReportGate(value: unknown): ReportArtifact['reportGate'] {
  const reportGate = requireRecord(value, 'report_gate_missing');
  if (reportGate.research_only !== true) {
    fail('report_gate_research_only_required');
  }

  return {
    status: requireEnum(
      reportGate.status,
      REPORT_GATE_STATUSES,
      'report_gate_invalid',
    ),
    reason: requireNonEmptyString(reportGate.reason, 'report_gate_invalid'),
    researchOnly: true,
  };
}

function decodeSourceCoverage(
  value: unknown,
): ReportArtifact['sourceCoverage'] {
  const coverage = requireRecord(value, 'source_coverage_missing');
  const rawFlags = requireArray(coverage.flags, 'source_coverage_invalid');
  const flags: CoverageFlag[] = rawFlags.map((rawFlag) => {
    const flag = requireRecord(rawFlag, 'source_coverage_invalid');
    return {
      code: requireString(flag.code, 'source_coverage_invalid'),
      severity: requireString(flag.severity, 'source_coverage_invalid'),
      message: requireString(flag.message, 'source_coverage_invalid'),
      recommendation: requireString(
        flag.recommendation,
        'source_coverage_invalid',
      ),
    };
  });

  return {
    status: requireEnum(
      coverage.status,
      SOURCE_COVERAGE_STATUSES,
      'source_coverage_invalid',
    ),
    focusTicker: requireNonEmptyString(
      coverage.focus_ticker,
      'source_coverage_invalid',
    ),
    evidenceCount: requireFiniteNumber(
      coverage.evidence_count,
      'source_coverage_invalid',
      true,
    ),
    focusEvidenceCount: requireFiniteNumber(
      coverage.focus_evidence_count,
      'source_coverage_invalid',
      true,
    ),
    primaryCount: requireFiniteNumber(
      coverage.primary_count,
      'source_coverage_invalid',
      true,
    ),
    riskCount: requireFiniteNumber(
      coverage.risk_count,
      'source_coverage_invalid',
      true,
    ),
    methodologyShare: requireFiniteNumber(
      coverage.methodology_share,
      'source_coverage_invalid',
    ),
    placeholderShare: requireFiniteNumber(
      coverage.placeholder_share,
      'source_coverage_invalid',
    ),
    externalNonSerenityCount: requireFiniteNumber(
      coverage.external_non_serenity_count,
      'source_coverage_invalid',
      true,
    ),
    flags,
  };
}

function decodeSkepticalReview(
  value: unknown,
): ReportArtifact['skepticalReview'] {
  const skepticalReview = requireRecord(value, 'skeptical_review_missing');
  const counterThesis = requireStringArray(
    skepticalReview.counter_thesis,
    'skeptical_review_invalid',
  );
  if (
    counterThesis.length === 0 ||
    counterThesis.some((item) => item.trim().length === 0)
  ) {
    fail('skeptical_review_invalid');
  }

  return {
    summary: requireNonEmptyString(
      skepticalReview.summary,
      'skeptical_review_invalid',
    ),
    counterThesis,
  };
}

function decodeReports(value: unknown): {
  markdownHref: string;
  manifestHref: string;
} {
  const reports = requireRecord(value, 'reports_missing');
  const markdownHref = requireApiHref(reports.stock_analysis);
  const manifestHref = requireApiHref(reports.manifest);

  if (markdownHref !== REPORT_HREF || manifestHref !== MANIFEST_HREF) {
    fail('artifact_href_invalid');
  }

  return { markdownHref, manifestHref };
}

function decodeSafety(value: unknown): ReportArtifact['safety'] {
  if (!isRecord(value) || value.passed !== true) {
    fail('report_safety_failed');
  }
  const boundary = requireNonEmptyString(
    value.boundary,
    'research_boundary_required',
  );
  if (!boundary.toLowerCase().includes('research only')) {
    fail('research_boundary_required');
  }

  const rawFindings = requireArray(value.findings, 'report_safety_invalid');
  const findings: SafetyFinding[] = rawFindings.map((rawFinding) => {
    const finding = requireRecord(rawFinding, 'report_safety_invalid');
    return {
      lineNumber: requireFiniteNumber(
        finding.line_number,
        'report_safety_invalid',
        true,
      ),
      phrase: requireString(finding.phrase, 'report_safety_invalid'),
      line: requireString(finding.line, 'report_safety_invalid'),
    };
  });

  return {
    passed: true,
    boundary,
    findings,
  };
}

function decodeKeyClaims(value: unknown): KeyClaim[] {
  const rawClaims = requireArray(value, 'key_claims_missing');
  if (rawClaims.length === 0) {
    fail('key_claims_missing');
  }

  return rawClaims.map((rawClaim) => {
    const claim = requireRecord(rawClaim, 'key_claim_invalid');
    const rawProvenanceRefs = requireArray(
      claim.provenance_refs,
      'key_claim_provenance_missing',
    );
    if (rawProvenanceRefs.length === 0) {
      fail('key_claim_provenance_missing');
    }
    const provenanceRefs: ProvenanceRef[] = rawProvenanceRefs.map(
      (rawProvenanceRef) => {
        const provenanceRef = requireRecord(
          rawProvenanceRef,
          'key_claim_provenance_missing',
        );
        return {
          evidenceId: requireNonEmptyString(
            provenanceRef.evidence_id,
            'key_claim_provenance_missing',
          ),
          sourceUrl: requireProvenanceUrl(provenanceRef.source_url),
          sourceTitle: requireNonEmptyString(
            provenanceRef.source_title,
            'key_claim_provenance_missing',
          ),
          excerpt: requireNonEmptyString(
            provenanceRef.excerpt,
            'key_claim_provenance_missing',
          ),
        };
      },
    );

    return {
      claimId: requireNonEmptyString(claim.claim_id, 'key_claim_invalid'),
      claim: requireNonEmptyString(claim.claim, 'key_claim_invalid'),
      provenanceRefs,
      diagnostics: requireStringArray(
        claim.diagnostics,
        'key_claim_invalid',
      ),
    };
  });
}

function requireRecord(
  value: unknown,
  code: string,
): Record<string, unknown> {
  if (!isRecord(value)) {
    fail(code);
  }
  return value;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function requireArray(value: unknown, code: string): unknown[] {
  if (!Array.isArray(value)) {
    fail(code);
  }
  return [...value];
}

function requireString(value: unknown, code: string): string {
  if (typeof value !== 'string') {
    fail(code);
  }
  return value;
}

function requireNonEmptyString(value: unknown, code: string): string {
  const result = requireString(value, code);
  if (result.trim().length === 0) {
    fail(code);
  }
  return result;
}

function requireFiniteNumber(
  value: unknown,
  code: string,
  integer = false,
): number {
  if (
    typeof value !== 'number' ||
    !Number.isFinite(value) ||
    value < 0 ||
    (integer && !Number.isInteger(value))
  ) {
    fail(code);
  }
  return value;
}

function requireStringArray(value: unknown, code: string): string[] {
  const values = requireArray(value, code);
  if (!values.every((item) => typeof item === 'string')) {
    fail(code);
  }
  return values;
}

function requireEnum<T extends string>(
  value: unknown,
  allowed: readonly T[],
  code: string,
): T {
  if (typeof value !== 'string' || !allowed.some((item) => item === value)) {
    fail(code);
  }
  return value as T;
}

function requireTimestamp(value: unknown): string {
  const timestamp = requireNonEmptyString(value, 'generated_at_invalid');
  const match =
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?(?:Z|([+-])(\d{2}):(\d{2}))$/.exec(
      timestamp,
    );
  if (!match) {
    fail('generated_at_invalid');
  }

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const hour = Number(match[4]);
  const minute = Number(match[5]);
  const second = Number(match[6]);
  const offsetHour = match[9] === undefined ? 0 : Number(match[9]);
  const offsetMinute = match[10] === undefined ? 0 : Number(match[10]);
  const leapYear =
    year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const daysInMonth = [
    31,
    leapYear ? 29 : 28,
    31,
    30,
    31,
    30,
    31,
    31,
    30,
    31,
    30,
    31,
  ];

  if (
    year < 1 ||
    month < 1 ||
    month > 12 ||
    day < 1 ||
    day > daysInMonth[month - 1] ||
    hour > 23 ||
    minute > 59 ||
    second > 59 ||
    offsetHour > 23 ||
    offsetMinute > 59
  ) {
    fail('generated_at_invalid');
  }
  return timestamp;
}

function requireApiHref(value: unknown): string {
  const href = requireNonEmptyString(value, 'artifact_href_invalid');
  if (
    !href.startsWith(API_ARTIFACT_PREFIX) ||
    href.includes('\\') ||
    href.includes('?') ||
    href.includes('#')
  ) {
    fail('artifact_href_invalid');
  }

  let decodedHref: string;
  try {
    decodedHref = decodeURIComponent(href);
  } catch {
    fail('artifact_href_invalid');
  }
  if (decodedHref.includes('..')) {
    fail('artifact_href_invalid');
  }
  return href;
}

function requireProvenanceUrl(value: unknown): string {
  const sourceUrl = requireNonEmptyString(
    value,
    'key_claim_provenance_missing',
  );
  if (/\s/.test(sourceUrl)) {
    fail('key_claim_provenance_missing');
  }

  let parsed: URL;
  try {
    parsed = new URL(sourceUrl);
  } catch {
    fail('key_claim_provenance_missing');
  }
  if (
    !['http:', 'https:', 'serenity:'].includes(parsed.protocol) ||
    !parsed.hostname ||
    parsed.username ||
    parsed.password
  ) {
    fail('key_claim_provenance_missing');
  }
  return sourceUrl;
}

function assertNoForbiddenFields(value: unknown): void {
  const visited = new WeakSet<object>();

  const visit = (candidate: unknown): void => {
    if (typeof candidate !== 'object' || candidate === null) {
      return;
    }
    if (visited.has(candidate)) {
      return;
    }
    visited.add(candidate);

    if (Array.isArray(candidate)) {
      candidate.forEach(visit);
      return;
    }

    for (const [key, child] of Object.entries(candidate)) {
      const normalized = key
        .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/^_+|_+$/g, '');
      if (FORBIDDEN_FIELDS.some((field) => normalized.includes(field))) {
        fail('forbidden_field');
      }
      visit(child);
    }
  };

  visit(value);
}

function fail(code: string): never {
  throw new Error(code);
}
