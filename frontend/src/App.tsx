import { useState } from 'react';
import './index.css';
import Upload from './pages/Upload';
import Report from './pages/Report';
import type {
  UploadResponse,
  AnalysisResponse,
  RedlineResponse,
  PipelineStage,
} from './types';

function App() {
  const [stage, setStage] = useState<PipelineStage>('idle');
  const [uploadData, setUploadData] = useState<UploadResponse | null>(null);
  const [analysisData, setAnalysisData] = useState<AnalysisResponse | null>(null);
  const [redlineData, setRedlineData] = useState<RedlineResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleReset = () => {
    setStage('idle');
    setUploadData(null);
    setAnalysisData(null);
    setRedlineData(null);
    setError(null);
  };

  const getStageAnnouncement = (): string => {
    switch (stage) {
      case 'uploading':
        return 'Uploading document to server';
      case 'extracting':
        return 'Extracting text and identifying clauses';
      case 'analyzing':
        return 'Analyzing legal clauses against Indian statutory baselines';
      case 'verifying':
        return 'Verifying citations and checking enforceability';
      case 'complete':
        return 'Position report ready with findings, timeline, and options';
      case 'error':
        return error ? `Analysis failed: ${error}` : 'An error occurred';
      default:
        return 'Ready to upload legal document';
    }
  };

  return (
    <div className="min-h-screen pb-14">
      {/* Skip to Main Content Link for Screen Readers and Keyboard Navigation */}
      <a href="#main-content" className="sr-only-focusable">
        Skip to main content
      </a>

      {/* Screen Reader Live Region for Pipeline Stage Status */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {getStageAnnouncement()}
      </div>

      {/* Header Landmark */}
      <header role="banner" className="glass sticky top-0 z-40 py-3.5 border-b border-border/40">
        <div className="w-full max-w-[1680px] mx-auto flex items-center justify-between px-4 sm:px-6 lg:px-8">
          <button
            type="button"
            onClick={handleReset}
            aria-label="FinePrint home, click to reset and upload another document"
            className="flex items-center gap-3 cursor-pointer text-left bg-transparent border-0 p-0 focus-visible:ring-2 focus-visible:ring-indigo-400 rounded-xl"
          >
            <div
              aria-hidden="true"
              className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 via-indigo-600 to-purple-600 flex items-center justify-center shadow-md shadow-indigo-500/20"
            >
              <span className="text-white font-bold text-sm tracking-wider">FP</span>
            </div>
            <div>
              <h1 className="text-lg font-bold bg-gradient-to-r from-indigo-400 via-purple-300 to-purple-400 bg-clip-text text-transparent">
                FinePrint
              </h1>
              <p className="text-[11px] text-text-secondary hidden sm:block -mt-0.5">Legal Position & Risk Intelligence</p>
            </div>
          </button>

          {stage === 'complete' && (
            <button
              type="button"
              onClick={handleReset}
              aria-label="Upload another legal document"
              className="px-4 py-1.5 rounded-lg text-xs font-semibold text-text-secondary hover:text-white transition-all bg-surface-2 hover:bg-surface-3 border border-border/80 shadow-sm flex items-center gap-2 cursor-pointer"
            >
              <span aria-hidden="true">+</span> Upload Another Document
            </button>
          )}
        </div>
      </header>

      {/* Main Content Landmark */}
      <main id="main-content" role="main" tabIndex={-1} className="w-full max-w-[1680px] mx-auto px-4 sm:px-6 lg:px-8 py-6 focus:outline-none">
        {stage === 'idle' || stage === 'uploading' || stage === 'extracting' || stage === 'analyzing' || stage === 'verifying' || stage === 'error' ? (
          <Upload
            stage={stage}
            setStage={setStage}
            setUploadData={setUploadData}
            setAnalysisData={setAnalysisData}
            setError={setError}
            error={error}
          />
        ) : stage === 'complete' && analysisData && uploadData ? (
          <Report
            uploadData={uploadData}
            analysisData={analysisData}
            redlineData={redlineData}
            setRedlineData={setRedlineData}
          />
        ) : null}
      </main>

      {/* Legal Disclaimer Footer Landmark — persistent, non-dismissable */}
      <footer role="contentinfo" className="legal-footer">
        ⚖️ This tool provides <strong>information</strong>, not legal advice. Every output is for educational purposes
        and should be confirmed with a qualified legal professional.
      </footer>
    </div>
  );
}

export default App;
