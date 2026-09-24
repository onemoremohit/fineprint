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
      <div role="status" className="glass-card p-8 text-center animate-fade-in-up">
        <span aria-hidden="true" className="text-4xl">✅</span>
        <p className="text-text-secondary mt-3">
          No aggressive clauses requiring immediate redlines were identified.
        </p>
      </div>
    );
  }

  return (
    <section aria-label="Suggested Redlines and Negotiation Drafts" className="space-y-6 animate-fade-in-up">
      {/* Redlines List */}
      <div>
        <h3 className="text-sm font-semibold text-text-secondary mb-4 flex items-center gap-2">
          <span aria-hidden="true">✏️</span> Suggested Changes & Statutory Rationales
        </h3>
        <div className="space-y-4">
          {redlineData.redlines.map((redline, idx) => (
            <article
              key={redline.clause_id}
              aria-label={`Redline for clause ${redline.clause_id}`}
              className="glass-card p-5 animate-slide-in-right border border-border/60"
              style={{ animationDelay: `${idx * 0.1}s` }}
            >
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs px-2 py-0.5 rounded bg-surface-3 text-text font-mono font-medium">
                  Clause {redline.clause_id}
                </span>
              </div>

              {/* Current Text */}
              <div className="mb-3">
                <p className="text-xs text-danger mb-1 font-semibold">Current Contract Term:</p>
                <div className="p-3 rounded-lg bg-danger/10 border border-danger/30 text-sm text-slate-200 leading-relaxed">
                  <del className="text-danger/90">{redline.current_text}</del>
                </div>
              </div>

              {/* Suggested Text */}
              <div className="mb-3">
                <p className="text-xs text-success mb-1 font-semibold">Recommended Fair Replacement:</p>
                <div className="p-3 rounded-lg bg-success/10 border border-success/30 text-sm text-slate-100 leading-relaxed">
                  <ins className="text-emerald-300 no-underline font-medium">{redline.suggested_text}</ins>
                </div>
              </div>

              {/* Rationale */}
              <div className="p-3 rounded-lg bg-surface-2/60 border border-border/30 text-xs text-text-secondary leading-relaxed">
                <strong className="font-semibold text-text">Legal Rationale: </strong>
                {redline.rationale}
              </div>
            </article>
          ))}
        </div>
      </div>

      {/* Negotiation Email Section */}
      <div className="pt-2">
        <button
          type="button"
          id="email-toggle-button"
          aria-expanded={showEmail}
          aria-controls="email-draft-panel"
          onClick={() => setShowEmail(!showEmail)}
          className="flex items-center gap-2 text-sm font-semibold text-text-secondary hover:text-white transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-indigo-400 py-1"
        >
          <span aria-hidden="true">📧</span>
          Negotiation Email Draft for Hiring Team
          <span aria-hidden="true" className="text-xs text-text-muted">
            {showEmail ? '▲ (Collapse)' : '▼ (Expand)'}
          </span>
        </button>

        {showEmail && (
          <div
            id="email-draft-panel"
            role="region"
            aria-labelledby="email-toggle-button"
            className="glass-card p-5 animate-fade-in-up mt-3"
          >
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs text-text-muted">
                Constructive, non-adversarial draft based on market standards — customize before sending:
              </p>
              <button
                type="button"
                onClick={handleCopyEmail}
                aria-label="Copy negotiation email draft to clipboard"
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer focus-visible:ring-2 focus-visible:ring-indigo-400 ${
                  copiedEmail
                    ? 'bg-success/20 text-success border border-success/30'
                    : 'bg-surface-3 text-text-secondary hover:text-white hover:bg-surface-4'
                }`}
              >
                {copiedEmail ? '✓ Copied to Clipboard!' : '📋 Copy Text'}
              </button>
            </div>
            <pre tabIndex={0} aria-label="Email draft content" className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap font-sans bg-surface-2/40 p-4 rounded-lg border border-border/40">
              {redlineData.email_draft}
            </pre>
          </div>
        )}
      </div>
    </section>
  );
}
