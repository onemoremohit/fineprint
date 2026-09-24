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

  return (
    <div className="min-h-screen pb-12">
      {/* Header */}
      <header className="glass sticky top-0 z-40 py-3.5 border-b border-border/40">
        <div className="w-full max-w-[1680px] mx-auto flex items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3 cursor-pointer" onClick={handleReset}>
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 via-indigo-600 to-purple-600 flex items-center justify-center shadow-md shadow-indigo-500/20">
              <span className="text-white font-bold text-sm tracking-wider">FP</span>
            </div>
            <div>
              <h1 className="text-lg font-bold bg-gradient-to-r from-indigo-400 via-purple-300 to-purple-400 bg-clip-text text-transparent">
                FinePrint
              </h1>
              <p className="text-[11px] text-text-muted hidden sm:block -mt-0.5">Legal Position & Risk Intelligence</p>
            </div>
          </div>
          {stage === 'complete' && (
            <button
              onClick={handleReset}
              className="px-4 py-1.5 rounded-lg text-xs font-semibold text-text-secondary hover:text-white transition-all bg-surface-2 hover:bg-surface-3 border border-border/80 shadow-sm flex items-center gap-2 cursor-pointer"
            >
              <span>+</span> Upload Another Document
            </button>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="w-full max-w-[1680px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
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

      {/* Legal Disclaimer Footer — persistent, non-dismissable */}
      <div className="legal-footer">
        ⚖️ This tool provides <strong>information</strong>, not legal advice. Every output is for educational purposes
        and should be confirmed with a qualified legal professional.
      </div>
    </div>
  );
}

export default App;
