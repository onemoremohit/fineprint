import type { Obligation } from '../types';

interface Props {
  obligations: Obligation[];
  onCitationClick: (start: number, end: number) => void;
}

export default function Timeline({ obligations, onCitationClick }: Props) {
  if (obligations.length === 0) {
    return (
      <div className="glass-card p-8 text-center" role="status">
        <span aria-hidden="true" className="text-4xl">📋</span>
        <p className="text-text-secondary mt-3">No commitments or obligations extracted from this document.</p>
      </div>
    );
  }

  // Group obligations by trigger
  const grouped: Record<string, Obligation[]> = {};
  for (const ob of obligations) {
    const key = ob.trigger || 'General Obligations';
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(ob);
  }

  const userObs = obligations.filter((o) => o.who === 'user');
  const counterpartyObs = obligations.filter((o) => o.who === 'counterparty');

  return (
    <section aria-label="Obligations Timeline" className="space-y-6 animate-fade-in-up">
      {/* Summary Stat Cards */}
      <div className="grid grid-cols-2 gap-4">
        <div
          role="region"
          aria-label={`Your commitments: ${userObs.length}`}
          className="glass-card p-4 border-l-4 border-l-warning"
        >
          <p className="text-xs text-text-muted uppercase tracking-wider mb-1 font-semibold">Your Obligations</p>
          <p className="text-2xl font-bold text-warning">{userObs.length}</p>
        </div>
        <div
          role="region"
          aria-label={`Employer commitments: ${counterpartyObs.length}`}
          className="glass-card p-4 border-l-4 border-l-info"
        >
          <p className="text-xs text-text-muted uppercase tracking-wider mb-1 font-semibold">Employer Obligations</p>
          <p className="text-2xl font-bold text-info">{counterpartyObs.length}</p>
        </div>
      </div>

      {/* Timeline List */}
      <div className="relative pl-10">
        <div aria-hidden="true" className="timeline-line" />

        <ol className="space-y-8 list-none m-0 p-0">
          {Object.entries(grouped).map(([trigger, obs], groupIdx) => (
            <li key={trigger} className="relative">
              {/* Trigger Label */}
              <div className="relative mb-4">
                <div
                  aria-hidden="true"
                  className="timeline-dot"
                  style={{ top: '4px' }}
                />
                <h3 className="text-sm font-semibold text-primary-light pl-6 uppercase tracking-wider">
                  {trigger}
                </h3>
              </div>

              {/* Obligations for this trigger */}
              <div className="space-y-3 pl-6">
                {obs.map((ob, idx) => (
                  <article
                    key={`${ob.clause_id}-${idx}`}
                    aria-label={`Obligation for ${ob.who === 'user' ? 'you' : 'employer'}: ${ob.what}`}
                    className={`glass-card p-4 animate-slide-in-right ${
                      ob.who === 'user' ? 'border-l-4 border-l-warning' : 'border-l-4 border-l-info'
                    }`}
                    style={{ animationDelay: `${(groupIdx * obs.length + idx) * 0.05}s` }}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span
                            className={`text-xs px-2 py-0.5 rounded font-semibold ${
                              ob.who === 'user'
                                ? 'bg-warning/20 text-warning'
                                : 'bg-info/20 text-info'
                            }`}
                          >
                            {ob.who === 'user' ? 'Your Responsibility' : 'Company Responsibility'}
                          </span>
                          {ob.clause_id && (
                            <span className="text-[10px] text-text-muted font-mono">
                              Clause {ob.clause_id}
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-text font-medium mt-1 leading-snug">{ob.what}</p>
                      </div>

                      {/* Financial Amount */}
                      {ob.amount_inr !== null && (
                        <div className="text-right flex-shrink-0">
                          <p className="text-xs text-text-muted">Penalty / Value</p>
                          <p className="text-sm font-bold text-danger">
                            ₹{ob.amount_inr.toLocaleString('en-IN')}
                          </p>
                        </div>
                      )}
                    </div>

                    {/* Timeline Details & Citation */}
                    <div className="mt-3 flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-border/30 text-xs text-text-muted">
                      <div className="flex items-center gap-4">
                        {ob.due && (
                          <span className="flex items-center gap-1 text-text-secondary">
                            <span aria-hidden="true">⏱️</span> Due: <strong className="text-text">{ob.due}</strong>
                          </span>
                        )}
                        {ob.trigger && (
                          <span className="flex items-center gap-1 text-text-secondary">
                            <span aria-hidden="true">⚡</span> Trigger: <strong className="text-text">{ob.trigger}</strong>
                          </span>
                        )}
                      </div>

                      {ob.citations && ob.citations.length > 0 && ob.citations[0].span && (
                        <button
                          type="button"
                          onClick={() => onCitationClick(ob.citations[0].span!.start, ob.citations[0].span!.end)}
                          aria-label={`View clause in document: characters ${ob.citations[0].span.start} to ${ob.citations[0].span.end}`}
                          className="text-[11px] px-2 py-0.5 rounded bg-surface-3 hover:bg-surface-4 text-text-secondary hover:text-white transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-indigo-400"
                        >
                          Source [{ob.citations[0].span.start}–{ob.citations[0].span.end}]
                        </button>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
