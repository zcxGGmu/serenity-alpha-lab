import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ReportSemanticsPanel } from './ReportSemanticsPanel';
import { sampleReportArtifact } from '../data/sampleReportArtifact';

describe('ReportSemanticsPanel', () => {
  it('surfaces readiness, provenance, source coverage, skeptical review, and safety', () => {
    render(<ReportSemanticsPanel artifact={sampleReportArtifact} />);

    expect(screen.getByRole('heading', { name: /report semantics/i })).toBeInTheDocument();
    expect(screen.getByText(/readiness gate/i)).toBeInTheDocument();
    expect(screen.getAllByText(/needs work/i)).not.toHaveLength(0);
    expect(screen.getAllByText(/source coverage/i)).not.toHaveLength(0);
    expect(screen.getByText(/primary 3\/5/i)).toBeInTheDocument();
    expect(screen.getByText(/provenance/i)).toBeInTheDocument();
    expect(screen.getByText(/serenity:market-data:AAPL:quote:2026-07-09/i)).toBeInTheDocument();
    expect(screen.getAllByText(/skeptical review/i)).not.toHaveLength(0);
    expect(screen.getAllByText(/risk coverage uses 1 risk or invalidation evidence item/i)).not.toHaveLength(0);
    expect(screen.getByText(/report safety/i)).toBeInTheDocument();
    expect(screen.getByText(/research only; not investment advice/i)).toBeInTheDocument();
  });

  it('keeps unsupported trading vocabulary out of rendered report semantics', () => {
    const { container } = render(<ReportSemanticsPanel artifact={sampleReportArtifact} />);

    const renderedText = container.textContent?.toLowerCase() ?? '';
    expect(renderedText).not.toContain(['operation', 'advice'].join('_'));
    expect(renderedText).not.toContain(['sentiment', 'score'].join('_'));
    expect(renderedText).not.toContain(['you', 'should', 'buy'].join(' '));
    expect(renderedText).not.toContain(['target', 'price'].join(' '));
    expect(renderedText).not.toContain(['stop', 'loss'].join(' '));
    expect(renderedText).not.toContain(['take', 'profit'].join(' '));
  });

  it('lists every key claim with at least one provenance reference', () => {
    render(<ReportSemanticsPanel artifact={sampleReportArtifact} />);

    for (const claim of sampleReportArtifact.keyClaims) {
      const claimCard = screen.getByTestId(`key-claim-${claim.claimId}`);
      expect(within(claimCard).getByText(claim.claim)).toBeInTheDocument();
      expect(within(claimCard).getAllByTestId('provenance-ref')).toHaveLength(claim.provenanceRefs.length);
    }
  });
});
