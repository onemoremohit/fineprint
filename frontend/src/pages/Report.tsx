import { useState, useMemo } from 'react';
import type {
  UploadResponse,
  AnalysisResponse,
  RedlineResponse,
} from '../types';
import DocViewer from '../components/DocViewer';
import ClauseCard from '../components/ClauseCard';
import Timeline from '../components/Timeline';
import QaPanel from '../components/QaPanel';
import RedlinePanel from '../components/RedlinePanel';
import { generateRedlines, getBriefPdfUrl } from '../lib/api';

interface Props {
  uploadData: UploadResponse;
  analysisData: AnalysisResponse;
  redlineData: RedlineResponse | null;
  setRedlineData: (d: RedlineResponse) => void;
}

type Tab = 'findings' | 'timeline' | 'qa' | 'redline';

export default function Report({
  uploadData,
  analysisData,
  redlineData,
  setRedlineData,
}: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('findings');
  const [highlightSpan, setHighlightSpan] = useState<{ start: number; end: number } | null>(null);
  const [loadingRedlines, setLoadingRedlines] = useState(false);

  const handleCitationClick = (start: number, end: number) => {
    setHighlightSpan({ start, end });
    const el = document.getElementById('doc-viewer');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const handleGenerateRedlines = async () => {
    if (redlineData) {
      setActiveTab('redline');
      return;
    }
    setLoadingRedlines(true);
    try {
      const result = await generateRedlines(uploadData.document_id);
      setRedlineData(result);
      setActiveTab('redline');
    } catch (err) {
      console.error('Redline generation failed:', err);
    } finally {
      setLoadingRedlines(false);
    }
  };

  const tabs: { key: Tab; label: string; icon: string; count?: number }[] = [
    { key: 'findings', label: 'Findings', icon: '📋', count: analysisData.findings.length },
    { key: 'timeline', label: 'Timeline', icon: '⏱️', count: analysisData.obligations.length },
    { key: 'qa', label: 'Ask a Question', icon: '💬' },
    { key: 'redline', label: 'Your Move', icon: '✏️', count: redlineData?.redlines.length },
  ];

  // Memoize lookup maps for maximum computational efficiency
  const verdictMap = useMemo(
    () => new Map(analysisData.baseline_verdicts.map((v) => [v.clause_id, v])),
    [analysisData.baseline_verdicts]
  );
  const flagMap = useMemo(
    () => new Map(analysisData.enforceability_flags.map((f) => [f.clause_id, f])),
    [analysisData.enforceability_flags]
  );

  // Sort findings: general_law first, then document_says, then options
  const sortedFindings = useMemo(() => {
    const tierOrder = { general_law: 0, document_says: 1, option: 2 };
    return [...analysisData.findings].sort(
      (a, b) => tierOrder[a.tier] - tierOrder[b.tier]
    );
  }, [analysisData.findings]);

  return (
    <div className="flex flex-col lg:flex-row gap-8 items-start w-full animate-fade-in-up">
      {/* Left Pane: Document Viewer Landmark */}
      <section
        aria-label="Uploaded Document Viewer"
        className="w-full lg:w-[48%] xl:w-[46%] lg:sticky lg:top-20 lg:self-start lg:max-h-[calc(100vh-100px)] flex flex-col"
      >
        <div className="glass-card p-5 h-full flex flex-col border border-border/60 shadow-xl">
          <div className="flex items-center justify-between pb-3.5 mb-3 border-b border-border/40">
            <div className="flex items-center gap-2.5">
              <div aria-hidden="true" className="w-7 h-7 rounded-lg bg-indigo-500/20 text-indigo-300 flex items-center justify-center text-sm font-bold">
                §
              </div>
              <div>
                <h2 className="text-sm font-bold text-text">Source Document</h2>
                <p className="text-[11px] text-text-muted">Exact verbatim text with character grounding</p>
              </div>
            </div>
            <a
              href={getBriefPdfUrl(uploadData.document_id)}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Download Lawyer Prep Brief PDF document in a new tab"
              className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-500/20 text-indigo-300 hover:bg-indigo-500/30 transition-all border border-indigo-500/40 flex items-center gap-1.5 shadow-sm hover:shadow-indigo-500/20 focus-visible:ring-2 focus-visible:ring-indigo-400"
            >
              <span aria-hidden="true">📥</span> Download Brief PDF
            </a>
          </div>

          <div id="doc-viewer" className="overflow-y-auto max-h-[calc(100vh-190px)] pr-2 scrollbar-thin">
            <DocViewer
              fullText={uploadData.full_text}
              clauses={analysisData.clauses}
              highlightSpan={highlightSpan}
            />
          </div>
        </div>
      </section>

      {/* Right Pane: Analysis & Intelligence Landmark */}
      <section aria-label="Position Analysis and Tools" className="w-full lg:w-[52%] xl:w-[54%] space-y-6">
        {/* Navigation Tabs (WCAG 2.1 Tablist Compliant) */}
        <nav
          role="tablist"
          aria-label="Analysis report sections"
          className="flex gap-2 p-1.5 rounded-xl bg-surface-2/60 border border-border/40 overflow-x-auto shadow-sm"
        >
          {tabs.map((tab) => {
            const isSelected = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                role="tab"
                id={`tab-${tab.key}`}
                aria-selected={isSelected}
                aria-controls={`panel-${tab.key}`}
                tabIndex={isSelected ? 0 : -1}
                onClick={() => {
                  if (tab.key === 'redline' && !redlineData) {
                    handleGenerateRedlines();
                  } else {
                    setActiveTab(tab.key);
                  }
                }}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs sm:text-sm font-semibold transition-all whitespace-nowrap cursor-pointer focus-visible:ring-2 focus-visible:ring-indigo-400 ${
                  isSelected
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                    : 'text-text-muted hover:text-text hover:bg-surface-3/50'
                }`}
              >
                <span aria-hidden="true">{tab.icon}</span>
                {tab.label}
                {tab.count !== undefined && (
                  <span
                    aria-label={`${tab.count} items`}
                    className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold ${
                      isSelected
                        ? 'bg-white/20 text-white'
                        : 'bg-surface-3 text-text-secondary'
                    }`}
                  >
                    {tab.count}
                  </span>
                )}
                {tab.key === 'redline' && loadingRedlines && (
                  <div
                    role="status"
                    aria-label="Generating redlines..."
                    className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"
                  />
                )}
              </button>
            );
          })}
        </nav>

        {/* Tab Content Panel (WCAG 2.1 Tabpanel Compliant) */}
        <div
          role="tabpanel"
          id={`panel-${activeTab}`}
          aria-labelledby={`tab-${activeTab}`}
          tabIndex={0}
          className="focus:outline-none"
        >
          {activeTab === 'findings' && (
            <div className="space-y-5">
              {/* Key Overview Stat Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
                <StatCard
                  label="Clauses Analyzed"
                  value={analysisData.clauses.length}
                  icon="📑"
                  description="Distinct contractual provisions identified"
                />
                <StatCard
                  label="High Risk Flags"
                  value={analysisData.clauses.filter((c) => c.risk_score >= 4).length}
                  icon="⚠️"
                  color="danger"
                  description="Clauses with strict or unusual terms"
                />
                <StatCard
                  label="Statute Flags"
                  value={analysisData.enforceability_flags.length}
                  icon="⚖️"
                  color="warning"
                  description="Provisions evaluated under Indian law"
                />
                <StatCard
                  label="Obligations"
                  value={analysisData.obligations.length}
                  icon="⏱️"
                  color="info"
                  description="Actionable timeline commitments"
                />
              </div>

              {/* Findings List */}
              <div className="space-y-4">
                {sortedFindings.map((finding) => (
                  <ClauseCard
                    key={finding.id}
                    finding={finding}
                    clauses={analysisData.clauses}
                    verdict={verdictMap.get(finding.clause_ids[0]) || null}
                    flag={flagMap.get(finding.clause_ids[0]) || null}
                    onCitationClick={handleCitationClick}
                  />
                ))}
              </div>
            </div>
          )}

          {activeTab === 'timeline' && (
            <Timeline
              obligations={analysisData.obligations}
              onCitationClick={handleCitationClick}
            />
          )}

          {activeTab === 'qa' && (
            <QaPanel
              documentId={uploadData.document_id}
              onCitationClick={handleCitationClick}
            />
          )}

          {activeTab === 'redline' && redlineData && (
            <RedlinePanel redlineData={redlineData} />
          )}
        </div>
      </section>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
  color,
  description,
}: {
  label: string;
  value: number;
  icon: string;
  color?: 'danger' | 'warning' | 'info';
  description?: string;
}) {
  const colorClasses = {
    danger: 'text-danger border-danger/30 bg-danger/5',
    warning: 'text-warning border-warning/30 bg-warning/5',
    info: 'text-info border-info/30 bg-info/5',
  };

  return (
    <div
      role="region"
      aria-label={`${label}: ${value}`}
      className={`glass-card p-3.5 border ${color ? colorClasses[color] : 'border-border/50'} flex flex-col justify-between`}
    >
      <div className="flex items-center justify-between">
        <span aria-hidden="true" className="text-xl">{icon}</span>
        <span className="text-xl font-bold">{value}</span>
      </div>
      <div className="mt-2">
        <p className="text-xs font-semibold text-text">{label}</p>
        {description && <p className="text-[10px] text-text-muted mt-0.5 leading-tight">{description}</p>}
      </div>
    </div>
  );
}
