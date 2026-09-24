import { useState, useEffect, useRef, useMemo } from 'react';
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

  // Determine active clause based on highlightSpan
  const activeClauseId = useMemo(() => {
    if (!highlightSpan) return null;
    return clauses.find(
      (c) =>
        (c.span.start <= highlightSpan.start && c.span.end >= highlightSpan.end) ||
        (highlightSpan.start <= c.span.start && highlightSpan.end >= c.span.start)
    )?.id;
  }, [clauses, highlightSpan]);

  // Scroll active clause into view
  useEffect(() => {
    if (activeClauseId && containerRef.current) {
      const activeEl = containerRef.current.querySelector(`[data-clause-id="${activeClauseId}"]`);
      if (activeEl) {
        activeEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [activeClauseId, highlightSpan]);

  // Extract preamble and postscript
  const sortedClauses = useMemo(
    () => [...clauses].sort((a, b) => a.span.start - b.span.start),
    [clauses]
  );
  const firstStart = sortedClauses.length > 0 ? sortedClauses[0].span.start : 0;
  const preamble = useMemo(() => fullText.slice(0, firstStart).trim(), [fullText, firstStart]);

  // Filter clauses
  const filteredClauses = useMemo(() => {
    return sortedClauses.filter((c) => {
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
  }, [sortedClauses, filterRisk, searchQuery]);

  const highRiskCount = useMemo(() => clauses.filter((c) => c.risk_score >= 4).length, [clauses]);

  return (
    <div className="flex flex-col h-full space-y-3 font-sans">
      {/* Control bar: Filters & Search */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-border/40">
        <div role="group" aria-label="Filter clauses by risk severity" className="flex items-center gap-1.5 bg-surface-2/60 p-1 rounded-lg border border-border/40 text-xs">
          <button
            type="button"
            onClick={() => setFilterRisk('all')}
            aria-pressed={filterRisk === 'all'}
            aria-label={`Show all ${clauses.length} clauses`}
            className={`px-2.5 py-1 rounded-md font-medium transition-all cursor-pointer focus-visible:ring-2 focus-visible:ring-indigo-400 ${
              filterRisk === 'all'
                ? 'bg-indigo-500/20 text-indigo-300 font-semibold shadow-xs'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            All ({clauses.length})
          </button>
          <button
            type="button"
            onClick={() => setFilterRisk('high')}
            aria-pressed={filterRisk === 'high'}
            aria-label={`Show ${highRiskCount} high risk clauses`}
            className={`px-2.5 py-1 rounded-md font-medium transition-all flex items-center gap-1 cursor-pointer focus-visible:ring-2 focus-visible:ring-indigo-400 ${
              filterRisk === 'high'
                ? 'bg-danger/20 text-danger font-semibold shadow-xs'
                : 'text-text-muted hover:text-danger/80'
            }`}
          >
            <span aria-hidden="true" className="w-1.5 h-1.5 rounded-full bg-danger"></span>
            High Risk ({highRiskCount})
          </button>
        </div>

        <div className="flex items-center gap-2">
          {/* Accessible Search Box */}
          <div className="relative">
            <label htmlFor="doc-search-input" className="sr-only">
              Search inside document text
            </label>
            <input
              id="doc-search-input"
              type="search"
              placeholder="Search in text..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search within document text"
              className="px-2.5 py-1 text-xs rounded-md bg-surface-2/60 border border-border/40 text-text placeholder:text-text-muted focus:outline-none focus:border-indigo-400 w-32 sm:w-44 transition-all"
            />
          </div>

          {/* Accessible View Toggle */}
          <button
            type="button"
            onClick={() => setViewMode(viewMode === 'structured' ? 'raw' : 'structured')}
            aria-label={`Switch to ${viewMode === 'structured' ? 'raw text' : 'structured clauses'} view`}
            className="px-2.5 py-1 text-[11px] font-medium rounded bg-surface-3/60 hover:bg-surface-3 text-text hover:text-white border border-border/40 transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-indigo-400"
          >
            {viewMode === 'structured' ? '📄 Raw Text' : '📑 Clauses'}
          </button>
        </div>
      </div>

      {/* Main Document Content */}
      <div ref={containerRef} className="space-y-4" tabIndex={0} aria-label="Document clauses and contents">
        {viewMode === 'raw' ? (
          <div className="document-paper p-6 text-[13.5px] leading-relaxed text-slate-200 font-sans whitespace-pre-wrap break-words">
            {fullText}
          </div>
        ) : (
          <>
            {/* Preamble / Letterhead */}
            {preamble && (
              <div className="document-paper p-5 border-l-2 border-indigo-400/40 bg-surface-2/30">
                <div className="text-xs uppercase tracking-wider font-semibold text-indigo-300 mb-2">
                  Document Header
                </div>
                <div className="text-xs text-text-secondary whitespace-pre-wrap leading-relaxed">
                  {preamble}
                </div>
              </div>
            )}

            {/* Filtered Clause Blocks */}
            <div className="space-y-3">
              {filteredClauses.map((clause) => {
                const isActive = activeClauseId === clause.id;
                const isHighRisk = clause.risk_score >= 4;
                const isMediumRisk = clause.risk_score >= 2 && clause.risk_score <= 3;

                return (
                  <article
                    key={clause.id}
                    data-clause-id={clause.id}
                    aria-label={`Clause ${clause.heading || clause.type}, risk score ${clause.risk_score} of 5`}
                    className={`clause-block p-4 transition-all duration-300 ${
                      isActive ? 'active-highlight' : ''
                    } ${
                      isHighRisk
                        ? 'border-l-4 border-l-danger bg-danger/5'
                        : isMediumRisk
                        ? 'border-l-4 border-l-warning bg-warning/5'
                        : 'border-l-4 border-l-indigo-500/40'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-semibold text-text uppercase tracking-wider">
                          {clause.heading || clause.type.replace(/_/g, ' ')}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-3 text-text-secondary font-mono">
                          {clause.id}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {isHighRisk && (
                          <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-danger/20 text-danger border border-danger/30">
                            High Risk
                          </span>
                        )}
                        <span className="text-[10px] text-text-muted font-mono">
                          chars {clause.span.start}–{clause.span.end}
                        </span>
                      </div>
                    </div>

                    <div className="text-xs text-slate-200 leading-relaxed whitespace-pre-wrap font-sans">
                      {clause.text}
                    </div>

                    {clause.risk_reasons && clause.risk_reasons.length > 0 && (
                      <div className="mt-2.5 pt-2 border-t border-border/30 text-[11px] text-text-secondary">
                        <span className="font-semibold text-text">Notes: </span>
                        {clause.risk_reasons.join('; ')}
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
