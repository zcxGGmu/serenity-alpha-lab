import { useMemo } from 'react';

import { coreRoutes } from './routes';
import { sampleReportArtifact } from './data/sampleReportArtifact';
import { AnalysisPage } from './pages/AnalysisPage';
import { HistoryPage } from './pages/HistoryPage';
import { HomePage } from './pages/HomePage';
import { SettingsPage } from './pages/SettingsPage';

function currentPath(): string {
  return window.location.pathname === '' ? '/' : window.location.pathname;
}

export default function App() {
  const path = currentPath();
  const page = useMemo(() => {
    switch (path) {
      case '/':
        return <HomePage artifact={sampleReportArtifact} />;
      case '/analysis':
        return <AnalysisPage artifact={sampleReportArtifact} />;
      case '/history':
        return <HistoryPage artifact={sampleReportArtifact} />;
      case '/settings':
        return <SettingsPage />;
      default:
        return (
          <section className="page-grid">
            <div className="page-header">
              <div>
                <p className="eyebrow">Route not found</p>
                <h1>Not Found</h1>
              </div>
            </div>
          </section>
        );
    }
  }, [path]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span>S</span>
          <strong>Serenity</strong>
        </div>
        <nav aria-label="Primary">
          {coreRoutes.map((route) => (
            <a aria-current={route.path === path ? 'page' : undefined} href={route.path} key={route.path}>
              {route.label}
            </a>
          ))}
        </nav>
      </aside>
      <main>{page}</main>
    </div>
  );
}
