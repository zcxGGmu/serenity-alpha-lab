import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { reportArtifactFixture } from '../test/fixtures/reportArtifacts';
import { ReportSemanticsPanel } from './ReportSemanticsPanel';

describe('ReportSemanticsPanel', () => {
  it('surfaces readiness, provenance, source coverage, skeptical review, and safety', () => {
    render(<ReportSemanticsPanel artifact={reportArtifactFixture} />);

    expect(screen.getByRole('heading', { name: /report semantics/i })).toBeInTheDocument();
    expect(screen.getByText(/readiness gate/i)).toBeInTheDocument();
    expect(screen.getAllByText(/^ready$/i)).not.toHaveLength(0);
    expect(screen.getAllByText(/source coverage/i)).not.toHaveLength(0);
    expect(screen.getByText(/evidence 4/i)).toBeInTheDocument();
    expect(screen.getByText(/primary 3/i)).toBeInTheDocument();
    expect(screen.getByText(/risk 1/i)).toBeInTheDocument();
    expect(screen.getByText(/provenance/i)).toBeInTheDocument();
    expect(screen.getByText(/serenity:market-data:MSFT:quote:2026-07-10/i)).toBeInTheDocument();
    expect(screen.getAllByText(/skeptical review/i)).not.toHaveLength(0);
    expect(screen.getAllByText(/risk coverage uses 1 risk or invalidation evidence item/i)).not.toHaveLength(0);
    expect(screen.getByText(/report safety/i)).toBeInTheDocument();
    expect(screen.getByText(/research only; not investment advice/i)).toBeInTheDocument();
  });

  it('keeps unsupported trading vocabulary out of rendered report semantics', () => {
    const { container } = render(<ReportSemanticsPanel artifact={reportArtifactFixture} />);

    const renderedText = container.textContent?.toLowerCase() ?? '';
    expect(renderedText).not.toContain(['operation', 'advice'].join('_'));
    expect(renderedText).not.toContain(['sentiment', 'score'].join('_'));
    expect(renderedText).not.toContain(['you', 'should', 'buy'].join(' '));
    expect(renderedText).not.toContain(['target', 'price'].join(' '));
    expect(renderedText).not.toContain(['stop', 'loss'].join(' '));
    expect(renderedText).not.toContain(['take', 'profit'].join(' '));
  });

  it('lists every key claim with at least one provenance reference', () => {
    render(<ReportSemanticsPanel artifact={reportArtifactFixture} />);

    for (const claim of reportArtifactFixture.keyClaims) {
      const claimCard = screen.getByTestId(`key-claim-${claim.claimId}`);
      expect(within(claimCard).getByText(claim.claim)).toBeInTheDocument();
      expect(within(claimCard).getAllByTestId('provenance-ref')).toHaveLength(claim.provenanceRefs.length);
    }
  });

  it('renders structured coverage and safety findings as readable fields', () => {
    const artifact = {
      ...reportArtifactFixture,
      sourceCoverage: {
        ...reportArtifactFixture.sourceCoverage,
        flags: [
          {
            code: 'missing_primary_source_depth',
            severity: 'warning',
            message: 'Primary-source depth is incomplete.',
            recommendation: 'Collect another primary source.',
          },
        ],
      },
      safety: {
        ...reportArtifactFixture.safety,
        findings: [
          {
            lineNumber: 12,
            phrase: 'unsupported actionability',
            line: 'This line crossed the research-only boundary.',
          },
        ],
      },
    };

    render(<ReportSemanticsPanel artifact={artifact} />);

    expect(screen.getByText('missing_primary_source_depth')).toBeInTheDocument();
    expect(screen.getByText('warning')).toBeInTheDocument();
    expect(screen.getByText('Line 12')).toBeInTheDocument();
    expect(screen.getByText('unsupported actionability')).toBeInTheDocument();
    expect(
      screen.getByText('This line crossed the research-only boundary.'),
    ).toBeInTheDocument();
  });
});
