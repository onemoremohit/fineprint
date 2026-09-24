import { useCallback, useRef, useState } from 'react';
import type { UploadResponse, AnalysisResponse, PipelineStage } from '../types';
import { uploadDocument, analyzeDocument } from '../lib/api';

interface Props {
  stage: PipelineStage;
  setStage: (s: PipelineStage) => void;
  setUploadData: (d: UploadResponse) => void;
  setAnalysisData: (d: AnalysisResponse) => void;
  setError: (e: string | null) => void;
  error: string | null;
}

const STAGES: { key: PipelineStage; label: string; icon: string }[] = [
  { key: 'uploading', label: 'Uploading', icon: '📤' },
  { key: 'extracting', label: 'Extracting Text', icon: '📄' },
  { key: 'analyzing', label: 'Analyzing Clauses', icon: '🔍' },
  { key: 'verifying', label: 'Verifying Citations', icon: '✅' },
  { key: 'complete', label: 'Complete', icon: '🎉' },
];

export default function Upload({
  stage, setStage, setUploadData, setAnalysisData, setError, error,
}: Props) {
  const [dragOver, setDragOver] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const processFile = useCallback(async (file: File) => {
    setFileName(file.name);
    setError(null);

    try {
      // Stage 1: Upload
      setStage('uploading');
      const uploadResp = await uploadDocument(file);
      setUploadData(uploadResp);

      // Stage 2: Extract (included in upload)
      setStage('extracting');
      await new Promise(r => setTimeout(r, 500)); // Brief visual pause

      // Stage 3: Analyze
      setStage('analyzing');
      const analysisResp = await analyzeDocument(uploadResp.document_id);
      setAnalysisData(analysisResp);

      // Stage 4: Verify (included in analysis)
      setStage('verifying');
      await new Promise(r => setTimeout(r, 800));

      // Done
      setStage('complete');
    } catch (err) {
      setStage('error');
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
    }
  }, [setStage, setUploadData, setAnalysisData, setError]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
  }, [processFile]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  }, [processFile]);

  const currentStageIdx = STAGES.findIndex(s => s.key === stage);

  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] gap-8">
      {/* Hero Section */}
      <div className="text-center animate-fade-in-up max-w-2xl">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mx-auto mb-6 shadow-lg shadow-indigo-500/25">
          <span className="text-3xl">⚖️</span>
        </div>
        <h2 className="text-3xl sm:text-4xl font-bold mb-3 bg-gradient-to-r from-white via-indigo-200 to-purple-200 bg-clip-text text-transparent">
          Understand Your Legal Document
        </h2>
        <p className="text-text-secondary text-lg">
          Upload an employment offer letter, training bond, or agreement.
          Get a grounded Position Report — not a summary, but where you stand.
        </p>
      </div>

      {/* Upload Zone */}
      {stage === 'idle' && (
        <div
          className={`upload-zone w-full max-w-xl animate-fade-in-up ${dragOver ? 'drag-over' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.doc,.png,.jpg,.jpeg,.tiff,.bmp"
            onChange={handleFileSelect}
            className="hidden"
          />
          <div className="text-4xl mb-4">📎</div>
          <p className="text-lg font-medium text-text mb-2">
            Drop your document here
          </p>
          <p className="text-text-muted text-sm">
            or click to browse — PDF, DOCX, or a phone photo
          </p>
          <div className="mt-4 flex items-center justify-center gap-3 text-xs text-text-muted">
            <span className="px-2 py-1 rounded bg-surface-2">PDF</span>
            <span className="px-2 py-1 rounded bg-surface-2">DOCX</span>
            <span className="px-2 py-1 rounded bg-surface-2">JPG/PNG</span>
          </div>
        </div>
      )}

      {/* Pipeline Progress */}
      {stage !== 'idle' && (
        <div className="w-full max-w-xl glass-card p-6 animate-fade-in-up">
          {fileName && (
            <p className="text-sm text-text-secondary mb-4 text-center">
              Processing: <span className="text-text font-medium">{fileName}</span>
            </p>
          )}

          <div className="space-y-3">
            {STAGES.map((s, idx) => {
              const isActive = s.key === stage;
              const isDone = idx < currentStageIdx;

              return (
                <div
                  key={s.key}
                  className={`flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-300 ${
                    isActive
                      ? 'bg-indigo-500/10 border border-indigo-500/30'
                      : isDone
                      ? 'opacity-60'
                      : 'opacity-30'
                  }`}
                >
                  <span className="text-lg w-7 text-center">
                    {isDone ? '✓' : isActive ? s.icon : '○'}
                  </span>
                  <span className={`text-sm font-medium ${isActive ? 'text-indigo-400' : ''}`}>
                    {s.label}
                  </span>
                  {isActive && (
                    <div className="ml-auto flex gap-1">
                      <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
                      <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" style={{ animationDelay: '0.2s' }} />
                      <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" style={{ animationDelay: '0.4s' }} />
                    </div>
                  )}
                  {isDone && (
                    <span className="ml-auto text-xs text-emerald">Done</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Error State */}
      {stage === 'error' && error && (
        <div className="w-full max-w-xl glass-card p-6 border border-danger/30 animate-fade-in-up">
          <div className="flex items-start gap-3">
            <span className="text-xl">⚠️</span>
            <div>
              <p className="font-medium text-danger mb-1">Analysis Failed</p>
              <p className="text-sm text-text-secondary">{error}</p>
              <button
                onClick={() => { setStage('idle'); setError(null); }}
                className="mt-3 px-4 py-1.5 rounded-lg text-sm font-medium bg-surface-3 hover:bg-surface-4 transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Features Grid */}
      {stage === 'idle' && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full max-w-3xl mt-4">
          {[
            { icon: '📋', title: 'Obligations Timeline', desc: 'What you must do, and by when' },
            { icon: '⚖️', title: 'Enforceability Flags', desc: 'Which clauses may not hold up' },
            { icon: '📧', title: 'Your Move', desc: 'Redlines + negotiation email draft' },
          ].map((f, i) => (
            <div
              key={f.title}
              className="glass-card p-5 text-center animate-fade-in-up"
              style={{ animationDelay: `${i * 0.1}s` }}
            >
              <div className="text-2xl mb-2">{f.icon}</div>
              <h3 className="text-sm font-semibold mb-1">{f.title}</h3>
              <p className="text-xs text-text-muted">{f.desc}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
