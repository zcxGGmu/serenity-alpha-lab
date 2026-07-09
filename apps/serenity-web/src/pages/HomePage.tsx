import type { ReportArtifact } from '../types';

interface HomePageProps {
  artifact: ReportArtifact;
}

export function HomePage({ artifact }: HomePageProps) {
  return (
    <section className="page-grid">
      <div className="hero-panel">
        <p className="eyebrow">Evidence-first research runtime</p>
        <h1>Serenity Alpha Lab</h1>
        <p>
          Serenity remains the product shell while source-system stock-analysis capability is migrated into
          research-only, provenance-aware workflows.
        </p>
      </div>

      <div className="summary-grid">
        <article className="summary-card">
          <span>Current artifact</span>
          <strong>{artifact.symbol}</strong>
          <p>{artifact.query}</p>
        </article>
        <article className="summary-card">
          <span>Readiness</span>
          <strong>{artifact.readiness.status.replace(/_/g, ' ')}</strong>
          <p>{artifact.readiness.reason}</p>
        </article>
        <article className="summary-card">
          <span>Safety</span>
          <strong>{artifact.safety.passed ? 'Passed' : 'Blocked'}</strong>
          <p>{artifact.safety.boundary}</p>
        </article>
      </div>
    </section>
  );
}
