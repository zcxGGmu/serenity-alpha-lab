import { useEffect, useState } from 'react';

import {
  ReportArtifactLoadError,
  type ReportArtifactSource,
} from './artifacts/reportArtifactSource';
import { coreRoutes } from './routes';
import { AnalysisPage } from './pages/AnalysisPage';
import { HistoryPage } from './pages/HistoryPage';
import { HomePage } from './pages/HomePage';
import { SettingsPage } from './pages/SettingsPage';
import type { ArtifactAvailability } from './types';

function currentPath(): string {
  return window.location.pathname === '' ? '/' : window.location.pathname;
}

interface AppProps {
  artifactSource: ReportArtifactSource;
}

export default function App({ artifactSource }: AppProps) {
  const path = currentPath();
  const artifactRequired = isArtifactRoute(path);
  const [requestVersion, setRequestVersion] = useState(0);
  const [availability, setAvailability] =
    useState<ArtifactAvailability>({ status: 'loading' });

  useEffect(() => {
    if (!artifactRequired) {
      return;
    }
    const controller = new AbortController();
    let active = true;
    setAvailability({ status: 'loading' });

    artifactSource
      .loadLatest(controller.signal)
      .then((artifact) => {
        if (active) {
          setAvailability({ status: 'ready', artifact });
        }
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }
        if (error instanceof ReportArtifactLoadError) {
          setAvailability({
            status: error.kind,
            reason: error.reason,
          });
          return;
        }
        setAvailability({
          status: 'unavailable',
          reason: 'artifact_unavailable',
        });
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [artifactRequired, artifactSource, requestVersion]);

  const page = renderPage(
    path,
    availability,
    () => setRequestVersion((version) => version + 1),
  );

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

function isArtifactRoute(path: string): boolean {
  return path === '/' || path === '/analysis' || path === '/history';
}

function renderPage(
  path: string,
  availability: ArtifactAvailability,
  onRetry: () => void,
) {
  if (path === '/settings') {
    return <SettingsPage />;
  }
  if (!coreRoutes.some((route) => route.path === path)) {
    return <NotFoundPage />;
  }
  if (availability.status !== 'ready') {
    return (
      <ArtifactState availability={availability} onRetry={onRetry} />
    );
  }

  switch (path) {
    case '/analysis':
      return <AnalysisPage artifact={availability.artifact} />;
    case '/history':
      return <HistoryPage artifact={availability.artifact} />;
    default:
      return <HomePage artifact={availability.artifact} />;
  }
}

function ArtifactState({
  availability,
  onRetry,
}: {
  availability: Exclude<ArtifactAvailability, { status: 'ready' }>;
  onRetry: () => void;
}) {
  if (availability.status === 'loading') {
    return (
      <section
        aria-label="Loading research artifact"
        className="artifact-state"
        role="status"
      >
        <p className="eyebrow">Canonical research artifact</p>
        <h1>Loading research artifact</h1>
        <p>Validating readiness, provenance, coverage, and report safety.</p>
      </section>
    );
  }

  return (
    <section className="artifact-state" role="alert">
      <p className="eyebrow">Canonical research artifact</p>
      <h1>
        {availability.status === 'blocked'
          ? 'Research artifact blocked'
          : 'Research artifact unavailable'}
      </h1>
      <p>{availability.reason}</p>
      <button className="primary-button" onClick={onRetry} type="button">
        Retry
      </button>
    </section>
  );
}

function NotFoundPage() {
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
