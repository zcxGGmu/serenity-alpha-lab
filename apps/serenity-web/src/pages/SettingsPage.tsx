export function SettingsPage() {
  return (
    <section className="page-grid">
      <div className="page-header">
        <div>
          <p className="eyebrow">Runtime guardrails</p>
          <h1>Settings</h1>
          <p>No live providers are enabled by default.</p>
        </div>
      </div>
      <div className="summary-grid">
        <article className="summary-card">
          <span>External data</span>
          <strong>Default off</strong>
          <p>Provider credentials must be configured explicitly before live calls.</p>
        </article>
        <article className="summary-card">
          <span>Research boundary</span>
          <strong>Always on</strong>
          <p>Report UI keeps conclusions tied to evidence and safety scans.</p>
        </article>
      </div>
    </section>
  );
}
