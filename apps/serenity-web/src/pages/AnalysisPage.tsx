import { useState } from 'react';

import { ReportReader } from '../components/ReportReader';
import { ReportSemanticsPanel } from '../components/ReportSemanticsPanel';
import type { ReportArtifact } from '../types';

interface AnalysisPageProps {
  artifact: ReportArtifact;
}

export function AnalysisPage({ artifact }: AnalysisPageProps) {
  const [readerOpen, setReaderOpen] = useState(false);

  return (
    <section className="page-grid">
      <div className="page-header">
        <div>
          <p className="eyebrow">Research-only stock analysis</p>
          <h1>Analysis Workbench</h1>
          <p>
            Phase 5 reads Phase 4 artifacts through Serenity semantics: readiness, provenance,
            source coverage, skeptical review, and safety.
          </p>
        </div>
        <button className="primary-button" onClick={() => setReaderOpen(true)} type="button">
          Open report reader
        </button>
      </div>

      <ReportSemanticsPanel artifact={artifact} />
      <ReportReader artifact={artifact} onClose={() => setReaderOpen(false)} open={readerOpen} />
    </section>
  );
}
