import type { ReportArtifact } from '../types';

interface ReportSemanticsPanelProps {
  artifact: ReportArtifact;
}

const formatStatus = (status: string): string => status.replace(/_/g, ' ');

export function ReportSemanticsPanel({ artifact }: ReportSemanticsPanelProps) {
  return (
    <section className="semantics-panel" aria-labelledby="report-semantics-title">
      <div className="section-heading">
        <p className="eyebrow">Phase 4 artifact layer</p>
        <h2 id="report-semantics-title">Report Semantics</h2>
      </div>

      <div className="semantic-grid">
        <article className="semantic-card">
          <p className="metric-label">Readiness gate</p>
          <strong>{formatStatus(artifact.readiness.status)}</strong>
          <span>{artifact.readiness.reason}</span>
          <ul>
            {artifact.readiness.flags.map((flag) => (
              <li key={flag}>{flag}</li>
            ))}
          </ul>
        </article>

        <article className="semantic-card">
          <p className="metric-label">Source coverage</p>
          <strong>
            Primary {artifact.sourceCoverage.primarySources.collected}/
            {artifact.sourceCoverage.primarySources.required}
          </strong>
          <span>{formatStatus(artifact.sourceCoverage.status)}</span>
          <ul>
            {artifact.sourceCoverage.flags.map((flag) => (
              <li key={flag}>{flag}</li>
            ))}
          </ul>
        </article>

        <article className="semantic-card">
          <p className="metric-label">Report safety</p>
          <strong>{artifact.safety.passed ? 'Passed' : 'Blocked'}</strong>
          <span>{artifact.safety.boundary}</span>
          {artifact.safety.findings.length > 0 ? (
            <ul>
              {artifact.safety.findings.map((finding) => (
                <li key={finding}>{finding}</li>
              ))}
            </ul>
          ) : (
            <span>No unsupported actionability language detected.</span>
          )}
        </article>

        <article className="semantic-card">
          <p className="metric-label">Skeptical review</p>
          <strong>{artifact.skepticalReview.summary}</strong>
          <ul>
            {artifact.skepticalReview.counterThesis.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
      </div>

      <section className="claims-panel" aria-label="Provenance">
        <div className="section-heading">
          <p className="eyebrow">Evidence traceability</p>
          <h3>Provenance</h3>
        </div>
        <div className="claim-list">
          {artifact.keyClaims.map((claim) => (
            <article className="claim-card" data-testid={`key-claim-${claim.claimId}`} key={claim.claimId}>
              <p className="claim-id">{claim.claimId}</p>
              <h4>{claim.claim}</h4>
              {claim.diagnostics.length > 0 ? (
                <ul>
                  {claim.diagnostics.map((diagnostic) => (
                    <li key={diagnostic}>{diagnostic}</li>
                  ))}
                </ul>
              ) : null}
              <div className="provenance-list">
                {claim.provenanceRefs.map((ref) => (
                  <a data-testid="provenance-ref" href={ref.sourceUrl} key={ref.evidenceId}>
                    <strong>{ref.evidenceId}</strong>
                    <span>{ref.sourceTitle}</span>
                    <small>{ref.excerpt}</small>
                  </a>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}
