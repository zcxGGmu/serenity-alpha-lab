import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { act, fireEvent, render, screen } from '@testing-library/react';
import { StrictMode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import App from './App';
import {
  ReportArtifactLoadError,
  type ReportArtifactSource,
} from './artifacts/reportArtifactSource';
import { reportArtifactFixture } from './test/fixtures/reportArtifacts';
import type { ReportArtifact } from './types';

describe('App artifact lifecycle', () => {
  beforeEach(() => {
    window.history.replaceState({}, '', '/');
  });

  it('renders loading and then the canonical artifact', async () => {
    const deferred = createDeferred<ReportArtifact>();
    const artifactSource = sourceFrom(() => deferred.promise);

    render(<App artifactSource={artifactSource} />);

    expect(
      screen.getByRole('status', { name: /loading research artifact/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText('AAPL market data research'),
    ).not.toBeInTheDocument();

    await act(async () => {
      deferred.resolve(reportArtifactFixture);
    });

    expect(
      await screen.findByText('MSFT market data research'),
    ).toBeInTheDocument();
  });

  it('renders a sanitized unavailable state and retries with a fresh request', async () => {
    const retry = createDeferred<ReportArtifact>();
    const loadLatest = vi
      .fn<ReportArtifactSource['loadLatest']>()
      .mockRejectedValueOnce(
        new ReportArtifactLoadError(
          'unavailable',
          'stock_analysis_artifact_missing',
        ),
      )
      .mockImplementationOnce(() => retry.promise);

    render(<App artifactSource={{ loadLatest }} />);

    expect(
      await screen.findByRole('heading', {
        name: /research artifact unavailable/i,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText('stock_analysis_artifact_missing'),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /retry/i }));

    expect(loadLatest).toHaveBeenCalledTimes(2);
    expect(
      screen.getByRole('status', { name: /loading research artifact/i }),
    ).toBeInTheDocument();

    await act(async () => {
      retry.resolve(reportArtifactFixture);
    });

    expect(
      await screen.findByText('MSFT market data research'),
    ).toBeInTheDocument();
  });

  it('renders blocked artifacts without report or manifest links', async () => {
    const artifactSource = sourceFrom(() =>
      Promise.reject(
        new ReportArtifactLoadError('blocked', 'report_safety_failed'),
      ),
    );

    const { container } = render(<App artifactSource={artifactSource} />);

    expect(
      await screen.findByRole('heading', {
        name: /research artifact blocked/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText('report_safety_failed')).toBeInTheDocument();
    expect(
      screen.queryByRole('link', { name: /open markdown report/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('link', { name: /open manifest/i }),
    ).not.toBeInTheDocument();
    expect(
      container.querySelector(
        'main a[href^="/api/artifacts/stock-analysis/latest/"]',
      ),
    ).toBeNull();
  });

  it('sanitizes unexpected source failures', async () => {
    const artifactSource = sourceFrom(() =>
      Promise.reject(new Error('/Users/example/private.json')),
    );

    render(<App artifactSource={artifactSource} />);

    expect(
      await screen.findByText('artifact_unavailable'),
    ).toBeInTheDocument();
    expect(screen.queryByText(/\/Users\/example/)).not.toBeInTheDocument();
  });

  it('aborts an in-flight request when the app unmounts', () => {
    let capturedSignal: AbortSignal | undefined;
    const artifactSource = sourceFrom((signal) => {
      capturedSignal = signal;
      return new Promise<ReportArtifact>(() => undefined);
    });

    const { unmount } = render(<App artifactSource={artifactSource} />);

    expect(capturedSignal?.aborted).toBe(false);
    unmount();
    expect(capturedSignal?.aborted).toBe(true);
  });

  it('does not let an older response overwrite a newer source result', async () => {
    const first = createDeferred<ReportArtifact>();
    const second = createDeferred<ReportArtifact>();
    const firstSource = sourceFrom(() => first.promise);
    const secondSource = sourceFrom(() => second.promise);
    const newerArtifact = {
      ...reportArtifactFixture,
      symbol: 'NVDA',
      company: 'NVIDIA Corporation',
      query: 'NVDA market data research',
    } satisfies ReportArtifact;
    const { rerender } = render(<App artifactSource={firstSource} />);

    rerender(<App artifactSource={secondSource} />);

    await act(async () => {
      second.resolve(newerArtifact);
    });
    expect(
      await screen.findByText('NVDA market data research'),
    ).toBeInTheDocument();

    await act(async () => {
      first.resolve(reportArtifactFixture);
    });

    expect(screen.getByText('NVDA market data research')).toBeInTheDocument();
    expect(
      screen.queryByText('MSFT market data research'),
    ).not.toBeInTheDocument();
  });

  it('survives StrictMode effect replay without reviving the aborted request', async () => {
    const first = createDeferred<ReportArtifact>();
    const second = createDeferred<ReportArtifact>();
    const signals: AbortSignal[] = [];
    const loadLatest = vi.fn<ReportArtifactSource['loadLatest']>(
      (signal) => {
        if (signal) {
          signals.push(signal);
        }
        return signals.length === 1 ? first.promise : second.promise;
      },
    );
    const staleArtifact = {
      ...reportArtifactFixture,
      symbol: 'AAPL',
      company: 'Apple Inc.',
      query: 'AAPL stale fixture',
    } satisfies ReportArtifact;

    render(
      <StrictMode>
        <App artifactSource={{ loadLatest }} />
      </StrictMode>,
    );

    expect(loadLatest).toHaveBeenCalledTimes(2);
    expect(signals[0]?.aborted).toBe(true);
    expect(signals[1]?.aborted).toBe(false);

    await act(async () => {
      second.resolve(reportArtifactFixture);
    });
    expect(
      await screen.findByText('MSFT market data research'),
    ).toBeInTheDocument();

    await act(async () => {
      first.resolve(staleArtifact);
    });
    expect(screen.getByText('MSFT market data research')).toBeInTheDocument();
    expect(screen.queryByText('AAPL stale fixture')).not.toBeInTheDocument();
  });

  it('labels History as the latest available artifact rather than complete history', async () => {
    window.history.replaceState({}, '', '/history');

    render(
      <App artifactSource={sourceFrom(() => Promise.resolve(reportArtifactFixture))} />,
    );

    expect(
      await screen.findByRole('heading', { name: 'History' }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/latest available artifact/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /this page shows the latest validated stock-analysis artifact/i,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/complete run history is deferred to a separate source/i),
    ).toBeInTheDocument();
    expect(screen.getByText('MSFT market data research')).toBeInTheDocument();
  });

  it('keeps Settings available while the artifact request is pending', () => {
    window.history.replaceState({}, '', '/settings');
    const loadLatest = vi.fn<ReportArtifactSource['loadLatest']>(
      () => new Promise<ReportArtifact>(() => undefined),
    );

    render(<App artifactSource={{ loadLatest }} />);

    expect(
      screen.getByRole('heading', { name: 'Settings' }),
    ).toBeInTheDocument();
    expect(screen.getByText('No live providers are enabled by default.')).toBeInTheDocument();
    expect(loadLatest).not.toHaveBeenCalled();
  });

  it('keeps Not Found available while the artifact request is pending', () => {
    window.history.replaceState({}, '', '/missing');
    const loadLatest = vi.fn<ReportArtifactSource['loadLatest']>(
      () => new Promise<ReportArtifact>(() => undefined),
    );

    render(<App artifactSource={{ loadLatest }} />);

    expect(
      screen.getByRole('heading', { name: 'Not Found' }),
    ).toBeInTheDocument();
    expect(loadLatest).not.toHaveBeenCalled();
  });

  it('keeps production App and main separate from sample and test fixtures', () => {
    const appSource = readFileSync(resolve(process.cwd(), 'src/App.tsx'), 'utf8');
    const mainSource = readFileSync(resolve(process.cwd(), 'src/main.tsx'), 'utf8');

    expect(appSource).not.toContain('sampleReportArtifact');
    expect(appSource).not.toContain('test/fixtures/reportArtifacts');
    expect(mainSource).not.toContain('sampleReportArtifact');
    expect(mainSource).not.toContain('test/fixtures/reportArtifacts');
    expect(mainSource).toContain('createHttpReportArtifactSource');
  });
});

function sourceFrom(
  loadLatest: ReportArtifactSource['loadLatest'],
): ReportArtifactSource {
  return { loadLatest };
}

function createDeferred<T>(): {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason?: unknown) => void;
} {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}
