import type { Obligation } from '../types';

interface Props {
  obligations: Obligation[];
  onCitationClick: (start: number, end: number) => void;
}

export default function Timeline({ obligations, onCitationClick }: Props) {
  if (obligations.length === 0) {
    return (
      <div className="glass-card p-8 text-center">
        <span className="text-4xl">📋</span>
        <p className="text-text-secondary mt-3">No obligations extracted from this document.</p>
      </div>
    );
  }

  // Group obligations by trigger
  const grouped: Record<string, Obligation[]> = {};
  for (const ob of obligations) {
    const key = ob.trigger || 'General';
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(ob);
  }

  const userObs = obligations.filter((o) => o.who === 'user');
  const counterpartyObs = obligations.filter((o) => o.who === 'counterparty');

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Summary */}
      <div className="grid grid-cols-2 gap-4">
        <div className="glass-card p-4 border-l-3 border-l-warning">
          <p className="text-xs text-text-muted uppercase tracking-wider mb-1">Your Obligations</p>
          <p className="text-2xl font-bold text-warning">{userObs.length}</p>
        </div>
        <div className="glass-card p-4 border-l-3 border-l-info">
          <p className="text-xs text-text-muted uppercase tracking-wider mb-1">Employer Obligations</p>
          <p className="text-2xl font-bold text-info">{counterpartyObs.length}</p>
        </div>
      </div>

      {/* Timeline */}
      <div className="relative pl-10">
        <div className="timeline-line" />

        {Object.entries(grouped).map(([trigger, obs], groupIdx) => (
          <div key={trigger} className="mb-8 last:mb-0">
            {/* Trigger Label */}
            <div className="relative mb-4">
              <div className="timeline-dot" style={{ top: '4px' }} />
              <h3 className="text-sm font-semibold text-primary-light pl-6 uppercase tracking-wider">
                {trigger}
              </h3>
            </div>

            {/* Obligations */}
            <div className="space-y-3 pl-6">
              {obs.map((ob, idx) => (
                <div
                  key={`${ob.clause_id}-${idx}`}
                  className={`glass-card p-4 animate-slide-in-right ${
                    ob.who === 'user' ? 'border-l-2 border-l-warning' : 'border-l-2 border-l-info'
                  }`}
                  style={{ animationDelay: `${(groupIdx * obs.length + idx) * 0.05}s` }}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span
                          className={`text-xs px-2 py-0.5 rounded font-medium ${
                            ob.who === 'user'
                              ? 'bg-warning/20 text-warning'
                              : 'bg-info/20 text-info'
                          }`}
                        >
                          {ob.who === 'user' ? '👤 You' : '🏢 Employer'}
                        </span>
                        <span className="text-xs text-text-muted">{ob.clause_id}</span>
                      </div>
                      <p className="text-sm text-text">{ob.what}</p>
                      {ob.due && (
                        <p className="text-xs text-text-muted mt-1">
                          ⏰ {ob.due}
                        </p>
                      )}
                    </div>

                    {ob.amount_inr && (
                      <div className="text-right flex-shrink-0">
                        <p className="text-sm font-bold text-warning">
                          ₹{ob.amount_inr.toLocaleString('en-IN')}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Citation chips */}
                  {ob.citations.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {ob.citations.map((c, ci) =>
                        c.kind === 'document' && c.span ? (
                          <button
                            key={ci}
                            onClick={() => onCitationClick(c.span!.start, c.span!.end)}
                            className="text-[10px] px-1.5 py-0.5 rounded bg-amber/10 text-amber-light hover:bg-amber/20 transition-colors"
                          >
                            📄 View source
                          </button>
                        ) : null
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
