export type ReadinessStatus = 'ready' | 'needs_work' | 'blocked';
export type ReportGateStatus = 'available' | 'blocked';
export type SourceCoverageStatus = 'ready' | 'needs_work' | 'blocked';

export interface CoverageFlag {
  code: string;
  severity: string;
  message: string;
  recommendation: string;
}

export interface SafetyFinding {
  lineNumber: number;
  phrase: string;
  line: string;
}

export interface ProvenanceRef {
  evidenceId: string;
  sourceUrl: string;
  sourceTitle: string;
  excerpt: string;
}

export interface KeyClaim {
  claimId: string;
  claim: string;
  provenanceRefs: ProvenanceRef[];
  diagnostics: string[];
}

export interface ReportArtifact {
  schemaVersion: 1;
  artifactType: 'stock_analysis_report';
  symbol: string;
  company: string;
  query: string;
  generatedAt: string;
  researchOnly: true;
  markdownHref: string;
  manifestHref: string;
  readiness: {
    status: ReadinessStatus;
    reason: string;
    flags: string[];
  };
  reportGate: {
    status: ReportGateStatus;
    reason: string;
    researchOnly: true;
  };
  sourceCoverage: {
    status: SourceCoverageStatus;
    focusTicker: string;
    evidenceCount: number;
    focusEvidenceCount: number;
    primaryCount: number;
    riskCount: number;
    methodologyShare: number;
    placeholderShare: number;
    externalNonSerenityCount: number;
    flags: CoverageFlag[];
  };
  safety: {
    passed: true;
    boundary: string;
    findings: SafetyFinding[];
  };
  skepticalReview: {
    summary: string;
    counterThesis: string[];
  };
  keyClaims: KeyClaim[];
}

export type ArtifactAvailability =
  | { status: 'loading' }
  | { status: 'ready'; artifact: ReportArtifact }
  | { status: 'unavailable'; reason: string }
  | { status: 'blocked'; reason: string };

export interface RouteItem {
  path: string;
  label: string;
}
