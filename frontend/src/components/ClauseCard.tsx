import type { Finding, Clause, BaselineVerdict, EnforceabilityFlag, Citation } from '../types';

interface Props {
  finding: Finding;
  clauses: Clause[];
  verdict: BaselineVerdict | null;
  flag: EnforceabilityFlag | null;
  onCitationClick: (start: number, end: number) => void;
  style?: React.CSSProperties;
}

export default function ClauseCard({
  finding,
  clauses,
  verdict,
  flag,
  onCitationClick,
  style,
}: Props) {
  const tierClasses: Record<string, string> = {
    document_says: 'tier-document-says',
    general_law: 'tier-general-law',
    option: 'tier-option',
  };

  const tierLabels: Record<string, string> = {
    document_says: 'The Document Says',
    general_law: 'Indian Law Treats This As',
    option: 'Options to Consider',
  };

  const tierIcons: Record<string, string> = {
    document_says: '📄',
    general_law: '⚖️',
    option: '💡',
  };

  const relatedClauses = clauses.filter((c) => finding.clause_ids.includes(c.id));
  const maxRisk = relatedClauses.length > 0
    ? Math.max(...relatedClauses.map((c) => c.risk_score))
    : 0;

  return (
    <div
      className={`glass-card p-5 ${tierClasses[finding.tier]} animate-fade-in-up ${
        !finding.verified ? 'opacity-75' : ''
      }`}
      style={style}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">{tierIcons[finding.tier]}</span>
          <div>
            <p className="text-xs font-medium text-text-muted uppercase tracking-wider">
              {tierLabels[finding.tier]}
            </p>
            <h3 className="text-base font-semibold text-text mt-0.5">
              {finding.title}
            </h3>
          </div>
        </div>

        {/* Badges */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {!finding.verified && (
            <span className="px-2 py-0.5 rounded text-xs font-medium bg-warning/20 text-warning border border-warning/30">
              ⚠ Unverified
            </span>
          )}
          {maxRisk > 0 && (
            <span className={`px-2 py-0.5 rounded text-xs font-bold risk-${maxRisk}`}>
              Risk {maxRisk}/5
            </span>
          )}
        </div>
      </div>

      {/* Verdict Badge */}
      {verdict && verdict.verdict !== 'no_baseline' && (
        <div className="mb-3">
          <span
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${
              verdict.verdict === 'standard'
                ? 'verdict-standard'
                : verdict.verdict === 'stricter_than_usual'
                ? 'verdict-stricter'
                : 'verdict-unusual'
            }`}
          >
            {verdict.verdict === 'standard' && '✓ Standard'}
            {verdict.verdict === 'stricter_than_usual' && '⚡ Stricter Than Usual'}
            {verdict.verdict === 'unusual' && '🔴 Unusual'}
          </span>
          {verdict.explanation && (
            <p className="text-xs text-text-muted mt-1.5 ml-1">{verdict.explanation}</p>
          )}
        </div>
      )}

      {/* Enforceability Flag */}
      {flag && (
        <div className="mb-3 p-3 rounded-lg bg-surface-2/50 border border-border/50">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium text-text-secondary">Enforceability:</span>
            <span
              className={`text-xs font-semibold ${
                flag.status === 'likely_unenforceable'
                  ? 'text-danger'
                  : flag.status === 'limited_enforceability'
                  ? 'text-warning'
                  : flag.status === 'likely_enforceable'
                  ? 'text-success'
                  : 'text-text-muted'
              }`}
            >
              {flag.status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-3 text-text-muted">
              {flag.confidence}
            </span>
          </div>
          {flag.statute_ids.length > 0 && (
            <p className="text-xs text-text-muted">
              Statute: {flag.statute_ids.join(', ')}
            </p>
          )}
        </div>
      )}

      {/* Body */}
      <div className="text-sm text-text-secondary leading-relaxed whitespace-pre-line">
        {renderBody(finding.body)}
      </div>

      {/* Citations */}
      {finding.citations.length > 0 && (
        <div className="mt-3 pt-3 border-t border-border/50">
          <p className="text-xs text-text-muted mb-2">Citations:</p>
          <div className="flex flex-wrap gap-2">
            {finding.citations.map((citation, idx) => (
              <CitationChip
                key={idx}
                citation={citation}
                onClick={onCitationClick}
              />
            ))}
          </div>
        </div>
      )}

      {/* Ask a Lawyer section for option tier */}
      {finding.tier === 'option' && (
        <div className="mt-3 pt-3 border-t border-emerald/20">
          <p className="text-xs text-emerald flex items-center gap-1">
            👨‍⚖️ Confirm with a lawyer before acting on these points
          </p>
        </div>
      )}
    </div>
  );
}

function CitationChip({
  citation,
  onClick,
}: {
  citation: Citation;
  onClick: (start: number, end: number) => void;
}) {
  const handleClick = () => {
    if (citation.kind === 'document' && citation.span) {
      onClick(citation.span.start, citation.span.end);
    }
  };

  return (
    <button
      onClick={handleClick}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all cursor-pointer ${
        citation.kind === 'document'
          ? 'bg-amber/10 text-amber-light hover:bg-amber/20 border border-amber/20'
          : 'bg-indigo/10 text-indigo-light hover:bg-indigo/20 border border-indigo/20'
      }`}
      title={citation.quote.slice(0, 100) + (citation.quote.length > 100 ? '...' : '')}
    >
      {citation.kind === 'document' ? '📄' : '📜'}
      {citation.kind === 'document'
        ? `Span ${citation.span?.start}–${citation.span?.end}`
        : citation.statute_id}
    </button>
  );
}

function renderBody(body: string) {
  // Simple markdown-like rendering for bold text
  const parts = body.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={idx} className="text-text font-semibold">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return <span key={idx}>{part}</span>;
  });
}
