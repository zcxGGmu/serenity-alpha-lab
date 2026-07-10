import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import App from './App';
import { createHttpReportArtifactSource } from './artifacts/reportArtifactSource';
import './styles.css';

const artifactSource = createHttpReportArtifactSource();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App artifactSource={artifactSource} />
  </StrictMode>,
);
