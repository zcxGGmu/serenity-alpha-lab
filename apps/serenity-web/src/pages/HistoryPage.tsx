import type { ReportArtifact } from '../types';

interface HistoryPageProps {
  artifact: ReportArtifact;
}

export function HistoryPage({ artifact }: HistoryPageProps) {
  return (
    <section className="page-grid">
      <div className="page-header">
        <div>
          <p className="eyebrow">Latest available artifact</p>
          <h1>History</h1>
          <p>
            This page shows the latest validated stock-analysis artifact. Complete run
            history is deferred to a separate source.
          </p>
        </div>
      </div>
      <article className="history-item">
        <div>
          <strong>{artifact.query}</strong>
          <p>{artifact.symbol} · {artifact.company}</p>
        </div>
        <span>{artifact.readiness.status.replace(/_/g, ' ')}</span>
      </article>
    </section>
  );
}
