import { useState } from 'react';
import type { RedlineResponse } from '../types';

interface Props {
  redlineData: RedlineResponse;
}

export default function RedlinePanel({ redlineData }: Props) {
  const [showEmail, setShowEmail] = useState(false);
  const [copiedEmail, setCopiedEmail] = useState(false);

  const handleCopyEmail = async () => {
    try {
      await navigator.clipboard.writeText(redlineData.email_draft);
      setCopiedEmail(true);
      setTimeout(() => setCopiedEmail(false), 2000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = redlineData.email_draft;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopiedEmail(true);
      setTimeout(() => setCopiedEmail(false), 2000);
    }
  };

  if (redlineData.redlines.length === 0) {
    return (
      <div className="glass-card p-8 text-center animate-fade-in-up">
        <span className="text-4xl">✅</span>
        <p className="text-text-secondary mt-3">
          No significant issues requiring redlines were identified.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Redlines */}
      <div>
        <h3 className="text-sm font-semibold text-text-secondary mb-4 flex items-center gap-2">
          ✏️ Suggested Changes
        </h3>
        <div className="space-y-4">
          {redlineData.redlines.map((redline, idx) => (
            <div
              key={redline.clause_id}
              className="glass-card p-5 animate-slide-in-right"
              style={{ animationDelay: `${idx * 0.1}s` }}
            >
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs px-2 py-0.5 rounded bg-surface-3 text-text-muted font-medium">
                  {redline.clause_id}
                </span>
              </div>

              {/* Current Text */}
              <div className="mb-3">
                <p className="text-xs text-danger mb-1 font-medium">Current:</p>
                <div className="p-3 rounded-lg bg-danger/5 border border-danger/20 text-sm text-text-secondary leading-relaxed">
                  <del className="text-danger/70">{redline.current_text}</del>
                </div>
              </div>

              {/* Suggested Text */}
              <div className="mb-3">
                <p className="text-xs text-success mb-1 font-medium">Suggested:</p>
                <div className="p-3 rounded-lg bg-success/5 border border-success/20 text-sm text-text leading-relaxed">
                  <ins className="text-success no-underline">{redline.suggested_text}</ins>
                </div>
              </div>

              {/* Rationale */}
              <div className="p-3 rounded-lg bg-surface-2/50 text-xs text-text-muted leading-relaxed">
                <span className="font-medium text-text-secondary">Rationale:</span>{' '}
                {redline.rationale}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Email Draft */}
      <div>
        <button
          onClick={() => setShowEmail(!showEmail)}
          className="flex items-center gap-2 text-sm font-semibold text-text-secondary mb-4 hover:text-text transition-colors"
        >
          <span>📧</span>
          Negotiation Email Draft
          <span className="text-xs text-text-muted">
            {showEmail ? '▲' : '▼'}
          </span>
        </button>

        {showEmail && (
          <div className="glass-card p-5 animate-fade-in-up">
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs text-text-muted">
                Professional, non-adversarial draft — customize before sending
              </p>
              <button
                onClick={handleCopyEmail}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                  copiedEmail
                    ? 'bg-success/20 text-success'
                    : 'bg-surface-3 text-text-secondary hover:bg-surface-4'
                }`}
              >
                {copiedEmail ? '✓ Copied!' : '📋 Copy'}
              </button>
            </div>
            <pre className="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap font-sans">
              {redlineData.email_draft}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
