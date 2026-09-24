import { useState, useEffect, useRef } from 'react';
import type { Clause } from '../types';

interface Props {
  fullText: string;
  clauses: Clause[];
  highlightSpan: { start: number; end: number } | null;
}

export default function DocViewer({ fullText, clauses, highlightSpan }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [filterRisk, setFilterRisk] = useState<'all' | 'high' | 'medium'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'structured' | 'raw'>('structured');

  // Determine which clause is currently active based on highlightSpan
  const activeClauseId = clauses.find(
    (c) =>
      highlightSpan !== null &&
      ((c.span.start <= highlightSpan.start && c.span.end >= highlightSpan.end) ||
        (highlightSpan.start <= c.span.start && highlightSpan.end >= c.span.start))
  )?.id;

  // Scroll active clause into view
  useEffect(() => {
    if (activeClauseId && containerRef.current) {
      const activeEl = containerRef.current.querySelector(`[data-clause-id="${activeClauseId}"]`);
      if (activeEl) {
        activeEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [activeClauseId, highlightSpan]);

  // Extract preamble (text before first clause) and postscript (text after last clause)
  const sortedClauses = [...clauses].sort((a, b) => a.span.start - b.span.start);
  const firstStart = sortedClauses.length > 0 ? sortedClauses[0].span.start : 0;
  const lastEnd =
    sortedClauses.length > 0 ? sortedClauses[sortedClauses.length - 1].span.end : fullText.length;

  const preamble = fullText.slice(0, firstStart).trim();
  const postscript = fullText.slice(lastEnd).trim();

  // Filter clauses
  const filteredClauses = sortedClauses.filter((c) => {
    if (filterRisk === 'high' && c.risk_score < 4) return false;
    if (filterRisk === 'medium' && (c.risk_score < 2 || c.risk_score > 3)) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        (c.heading && c.heading.toLowerCase().includes(q)) ||
        c.text.toLowerCase().includes(q) ||
        c.type.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const highRiskCount = clauses.filter((c) => c.risk_score >= 4).length;

  return (
    <div className="flex flex-col h-full space-y-3 font-sans">
      {/* Control bar: Filters & Search */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-border/40">
        <div className="flex items-center gap-1.5 bg-surface-2/60 p-1 rounded-lg border border-border/40 text-xs">
          <button
            onClick={() => setFilterRisk('all')}
            className={`px-2.5 py-1 rounded-md font-medium transition-all ${
              filterRisk === 'all'
                ? 'bg-indigo-500/20 text-indigo-300 font-semibold shadow-xs'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            All ({clauses.length})
          </button>
          <button
            onClick={() => setFilterRisk('high')}
            className={`px-2.5 py-1 rounded-md font-medium transition-all flex items-center gap-1 ${
              filterRisk === 'high'
                ? 'bg-danger/20 text-danger font-semibold shadow-xs'
                : 'text-text-muted hover:text-danger/80'
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-danger"></span>
            High Risk ({highRiskCount})
          </button>
        </div>

        <div className="flex items-center gap-2">
          {/* Search Box */}
          <input
            type="text"
            placeholder="Search in text..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="px-2.5 py-1 text-xs rounded-md bg-surface-2/60 border border-border/40 text-text placeholder:text-text-muted focus:outline-none focus:border-indigo-500/60 w-32 sm:w-40 transition-all"
          />

          {/* View Toggle */}
          <button
            onClick={() => setViewMode(viewMode === 'structured' ? 'raw' : 'structured')}
            title="Toggle between structured clause view and raw document text"
            className="px-2 py-1 text-[11px] rounded bg-surface-3/50 hover:bg-surface-3 text-text-muted hover:text-text border border-border/40 transition-colors"
          >
            {viewMode === 'structured' ? '📄 Raw' : '📑 Cards'}
          </button>
        </div>
      </div>

      {/* Main Document Content */}
      <div ref={containerRef} className="space-y-4">
        {viewMode === 'raw' ? (
          <div className="document-paper p-6 text-[13.5px] leading-relaxed text-slate-300 font-sans whitespace-pre-wrap break-words">
            {fullText}
          </div>
        ) : (
          <>
            {/* Preamble / Letterhead */}
            {preamble && (
              <div className="document-paper p-5 border-l-2 border-indigo-400/40 bg-surface-2/30">
                <div className="text-xs uppercase tracking-wider font-semibold text-indigo-400/80 mb-2">
                  Document Header / Recitals
                </div>
                <div className="text-xs text-text-secondary whitespace-pre-line leading-relaxed font-sans">
                  {preamble}
                </div>
              </div>
            )}

            {/* Clauses List */}
            {filteredClauses.length === 0 ? (
              <div className="glass-card p-6 text-center text-sm text-text-muted">
                No clauses match the current filter or search criteria.
              </div>
            ) : (
              filteredClauses.map((clause, idx) => {
                const isActive = clause.id === activeClauseId;
                const isHighRisk = clause.risk_score >= 4;
                const isMedRisk = clause.risk_score === 3;

                return (
                  <div
                    key={clause.id}
                    data-clause-id={clause.id}
                    className={`clause-block p-4 transition-all duration-300 relative ${
                      isActive
                        ? 'active ring-2 ring-indigo-500 border-indigo-400 bg-indigo-950/30 shadow-lg shadow-indigo-500/10'
                        : isHighRisk
                        ? 'border-danger/30 hover:border-danger/50'
                        : 'border-border/50 hover:border-border'
                    }`}
                  >
                    {/* Clause Header Bar */}
                    <div className="flex items-center justify-between gap-2 mb-2 pb-1.5 border-b border-border/30">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-surface-3/80 text-indigo-300 shrink-0 font-mono">
                          § {idx + 1}
                        </span>
                        <h4 className="text-xs font-semibold text-text truncate">
                          {clause.heading || `Clause ${clause.id}`}
                        </h4>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        {/* Type badge */}
                        <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-surface-3/60 text-text-muted font-medium">
                          {clause.type.replace(/_/g, ' ')}
                        </span>

                        {/* Risk badge */}
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                            isHighRisk
                              ? 'bg-danger/20 text-danger border border-danger/30'
                              : isMedRisk
                              ? 'bg-warning/20 text-warning border border-warning/30'
                              : 'bg-success/15 text-success border border-success/30'
                          }`}
                        >
                          Risk {clause.risk_score}/5
                        </span>
                      </div>
                    </div>

                    {/* Clause Body Text */}
                    <div className="text-[13px] leading-relaxed text-slate-300 font-sans whitespace-pre-line">
                      {clause.text}
                    </div>

                    {/* Active Indicator Pin */}
                    {isActive && (
                      <div className="mt-2.5 pt-2 border-t border-indigo-500/30 flex items-center justify-between text-[11px] text-indigo-300 font-medium">
                        <span className="flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-indigo-400 animate-ping"></span>
                          Referenced in Selected Finding
                        </span>
                        <span className="text-text-muted font-mono text-[10px]">
                          Chars {clause.span.start}–{clause.span.end}
                        </span>
                      </div>
                    )}
                  </div>
                );
              })
            )}

            {/* Postscript / Signatures */}
            {postscript && (
              <div className="document-paper p-5 border-t border-border/40 text-xs text-text-muted whitespace-pre-line leading-relaxed font-sans bg-surface-2/20">
                <div className="text-[11px] uppercase tracking-wider font-semibold text-text-secondary mb-1">
                  Document Signatures / Closing
                </div>
                {postscript}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
