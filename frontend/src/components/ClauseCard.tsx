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
    <article
      aria-labelledby={`finding-heading-${finding.id}`}
      className={`glass-card p-5 ${tierClasses[finding.tier]} animate-fade-in-up ${
        !finding.verified ? 'opacity-75' : ''
      }`}
      style={style}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <span aria-hidden="true" className="text-lg">{tierIcons[finding.tier]}</span>
          <div>
            <p className="text-xs font-semibold text-text-muted uppercase tracking-wider">
              {tierLabels[finding.tier]}
            </p>
            <h3 id={`finding-heading-${finding.id}`} className="text-base font-semibold text-text mt-0.5">
              {finding.title}
            </h3>
          </div>
        </div>

        {/* Badges */}
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {maxRisk >= 4 && (
            <span
              role="status"
              aria-label="High legal risk severity"
              className="px-2 py-0.5 rounded text-xs font-bold bg-danger/20 text-danger border border-danger/30"
            >
              High Risk
            </span>
          )}
          {maxRisk === 3 && (
            <span
              role="status"
              aria-label="Medium legal risk severity"
              className="px-2 py-0.5 rounded text-xs font-semibold bg-warning/20 text-warning border border-warning/30"
            >
              Medium Risk
            </span>
          )}
          {finding.verified ? (
            <span
              role="status"
              aria-label="Citation verified against source text"
              className="text-xs px-2 py-0.5 rounded bg-emerald/10 text-emerald border border-emerald/20 font-medium"
            >
              ✓ Verified
            </span>
          ) : (
            <span
              role="status"
              aria-label="Unverified finding"
              className="text-xs px-2 py-0.5 rounded bg-amber/10 text-amber border border-amber/20 font-medium"
            >
              Unverified
            </span>
          )}
        </div>
      </div>

      {/* Baseline Verdict Badge */}
      {verdict && (
        <div className="mb-3 flex items-center gap-2">
          <span className="text-xs text-text-muted font-medium">Market Baseline:</span>
          <VerdictBadge verdict={verdict.verdict} />
        </div>
      )}

      {/* Enforceability Status Badge */}
      {flag && (
        <div className="mb-3 flex items-center gap-2">
          <span className="text-xs text-text-muted font-medium">Enforceability:</span>
          <EnforceabilityBadge status={flag.status} />
        </div>
      )}

      {/* Body */}
      <div className="text-sm text-text-secondary leading-relaxed whitespace-pre-line">
        {finding.body}
      </div>

      {/* Citations */}
      {finding.citations.length > 0 && (
        <div className="mt-3 pt-3 border-t border-border/50">
          <p className="text-xs text-text-muted mb-2 font-semibold">Citations:</p>
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
          <p className="text-xs text-emerald flex items-center gap-1 font-medium">
            <span aria-hidden="true">👨‍⚖️</span> Confirm with a qualified lawyer before acting on these points
          </p>
        </div>
      )}
    </article>
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

  const isDoc = citation.kind === 'document' && citation.span;
  const chipLabel = isDoc
    ? `Jump to source document span: characters ${citation.span!.start} to ${citation.span!.end}`
    : `Statute citation: ${citation.statute_id || 'Statutory authority'}`;

  return (
    <button
      type="button"
      onClick={handleClick}
      aria-label={chipLabel}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all cursor-pointer focus-visible:ring-2 focus-visible:ring-indigo-400 ${
        isDoc
          ? 'bg-amber/10 text-amber-light hover:bg-amber/20 border border-amber/30'
          : 'bg-indigo/10 text-indigo-light hover:bg-indigo/20 border border-indigo/30'
      }`}
    >
      <span aria-hidden="true">{isDoc ? '📄' : '📜'}</span>
      {isDoc
        ? `Document [${citation.span!.start}–${citation.span!.end}]`
        : citation.statute_id || 'Statute'}
    </button>
  );
}

function VerdictBadge({ verdict }: { verdict: string }) {
  const config: Record<string, { label: string; className: string }> = {
    standard: { label: 'Standard', className: 'bg-emerald/10 text-emerald border-emerald/20' },
    stricter_than_usual: { label: 'Stricter Than Usual', className: 'bg-amber/10 text-amber border-amber/20' },
    unusual: { label: 'Unusual', className: 'bg-danger/10 text-danger border-danger/20' },
    no_baseline: { label: 'No Baseline Data', className: 'bg-surface-3 text-text-muted border-border/50' },
  };

  const c = config[verdict] || config.no_baseline;

  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium border ${c.className}`}>
      {c.label}
    </span>
  );
}

function EnforceabilityBadge({ status }: { status: string }) {
  const config: Record<string, { label: string; className: string }> = {
    likely_enforceable: { label: 'Likely Enforceable', className: 'bg-emerald/10 text-emerald border-emerald/20' },
    likely_unenforceable: { label: 'Likely Unenforceable', className: 'bg-danger/10 text-danger border-danger/20' },
    ambiguous: { label: 'Requires Legal Review', className: 'bg-amber/10 text-amber border-amber/20' },
  };

  const c = config[status] || { label: status, className: 'bg-surface-3 text-text-muted border-border/50' };

  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium border ${c.className}`}>
      {c.label}
    </span>
  );
}
