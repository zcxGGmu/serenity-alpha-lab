import { X } from 'lucide-react';

import { ReportSemanticsPanel } from './ReportSemanticsPanel';
import type { ReportArtifact } from '../types';

interface ReportReaderProps {
  artifact: ReportArtifact;
  open: boolean;
  onClose: () => void;
}

export function ReportReader({ artifact, open, onClose }: ReportReaderProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="modal-backdrop">
      <section
        aria-label={`${artifact.symbol} Report Reader`}
        aria-modal="true"
        className="report-reader"
        role="dialog"
      >
        <header className="reader-header">
          <div>
            <p className="eyebrow">Research artifact</p>
            <h2>{artifact.symbol} Report Reader</h2>
            <p>{artifact.company} · {artifact.generatedAt}</p>
          </div>
          <button aria-label="Close report reader" className="icon-button" onClick={onClose} type="button">
            <X aria-hidden="true" size={18} />
          </button>
        </header>

        <div className="artifact-actions">
          <a data-report-href={artifact.markdownHref} href={artifact.markdownHref}>
            Open Markdown report
          </a>
          <a href={artifact.manifestHref}>Open manifest</a>
        </div>

        <ReportSemanticsPanel artifact={artifact} />
      </section>
    </div>
  );
}
