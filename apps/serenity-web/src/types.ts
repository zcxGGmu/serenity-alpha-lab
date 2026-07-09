export type ReportStatus = 'ready' | 'needs_work' | 'blocked' | 'available';

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

export interface SourceCoverageSummary {
  status: ReportStatus;
  primarySources: {
    collected: number;
    required: number;
  };
  flags: string[];
}

export interface ReportArtifact {
  symbol: string;
  company: string;
  query: string;
  generatedAt: string;
  researchOnly: boolean;
  markdownHref: string;
  manifestHref: string;
  readiness: {
    status: ReportStatus;
    reason: string;
    flags: string[];
  };
  sourceCoverage: SourceCoverageSummary;
  safety: {
    passed: boolean;
    boundary: string;
    findings: string[];
  };
  skepticalReview: {
    summary: string;
    counterThesis: string[];
  };
  keyClaims: KeyClaim[];
}

export interface RouteItem {
  path: string;
  label: string;
}
