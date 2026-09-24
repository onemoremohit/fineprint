import { useState } from 'react';
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
    // Scroll the document viewer to the highlighted span
    const el = document.getElementById('doc-viewer');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const handleGenerateRedlines = async () => {
    if (redlineData) return;
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

  // Build lookup maps
  const verdictMap = new Map(
    analysisData.baseline_verdicts.map((v) => [v.clause_id, v])
  );
  const flagMap = new Map(
    analysisData.enforceability_flags.map((f) => [f.clause_id, f])
  );

  // Sort findings: general_law first, then document_says, then options
  const tierOrder = { general_law: 0, document_says: 1, option: 2 };
  const sortedFindings = [...analysisData.findings].sort(
    (a, b) => tierOrder[a.tier] - tierOrder[b.tier]
  );

  return (
    <div className="flex flex-col lg:flex-row gap-8 items-start w-full animate-fade-in-up">
      {/* Left Pane: Document Viewer */}
      <div className="w-full lg:w-[48%] xl:w-[46%] lg:sticky lg:top-20 lg:self-start lg:max-h-[calc(100vh-100px)] flex flex-col">
        <div className="glass-card p-5 h-full flex flex-col border border-border/60 shadow-xl">
          <div className="flex items-center justify-between pb-3.5 mb-3 border-b border-border/40">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-indigo-500/20 text-indigo-300 flex items-center justify-center text-sm font-bold">
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
              className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-500/20 text-indigo-300 hover:bg-indigo-500/30 transition-all border border-indigo-500/40 flex items-center gap-1.5 shadow-sm hover:shadow-indigo-500/20"
            >
              <span>📥</span> Download Brief PDF
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
      </div>

      {/* Right Pane: Analysis & Intelligence */}
      <div className="w-full lg:w-[52%] xl:w-[54%] space-y-6">
        {/* Navigation Tabs */}
        <div className="flex gap-2 p-1.5 rounded-xl bg-surface-2/60 border border-border/40 overflow-x-auto shadow-sm">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => {
                if (tab.key === 'redline' && !redlineData) {
                  handleGenerateRedlines();
                } else {
                  setActiveTab(tab.key);
                }
              }}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs sm:text-sm font-semibold transition-all whitespace-nowrap cursor-pointer ${
                activeTab === tab.key
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'text-text-muted hover:text-text hover:bg-surface-3/50'
              }`}
            >
              <span>{tab.icon}</span>
              {tab.label}
              {tab.count !== undefined && (
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold ${
                    activeTab === tab.key
                      ? 'bg-white/20 text-white'
                      : 'bg-surface-3 text-text-muted'
                  }`}
                >
                  {tab.count}
                </span>
              )}
              {tab.key === 'redline' && loadingRedlines && (
                <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
              )}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === 'findings' && (
          <div className="space-y-5">
            {/* Key Overview Stat Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
              <StatCard
                label="Clauses"
                value={analysisData.clauses.length}
                icon="📑"
              />
              <StatCard
                label="High Risk"
                value={analysisData.clauses.filter((c) => c.risk_score >= 4).length}
                icon="⚠️"
                accent="danger"
              />
              <StatCard
                label="Flagged"
                value={analysisData.enforceability_flags.length}
                icon="🚩"
                accent="warning"
              />
              <StatCard
                label="Obligations"
                value={analysisData.obligations.length}
                icon="📋"
                accent="info"
              />
            </div>

            {/* Findings Stack */}
            <div className="space-y-4">
              {sortedFindings.map((finding, idx) => (
                <ClauseCard
                  key={finding.id}
                  finding={finding}
                  clauses={analysisData.clauses}
                  verdict={
                    finding.clause_ids.length > 0
                      ? verdictMap.get(finding.clause_ids[0]) ?? null
                      : null
                  }
                  flag={
                    finding.clause_ids.length > 0
                      ? flagMap.get(finding.clause_ids[0]) ?? null
                      : null
                  }
                  onCitationClick={handleCitationClick}
                  style={{ animationDelay: `${idx * 0.04}s` }}
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
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
  accent,
}: {
  label: string;
  value: number;
  icon: string;
  accent?: 'danger' | 'warning' | 'info';
}) {
  const accentStyles = {
    danger: 'bg-danger/10 border-danger/30 text-danger shadow-danger/10',
    warning: 'bg-warning/10 border-warning/30 text-warning shadow-warning/10',
    info: 'bg-info/10 border-info/30 text-info shadow-info/10',
  };

  const badgeStyle = accent
    ? accentStyles[accent]
    : 'bg-surface-2/60 border-border/60 text-indigo-300';

  return (
    <div
      className={`p-3.5 rounded-xl border backdrop-blur-md transition-all duration-200 hover:translate-y-[-2px] shadow-sm flex items-center gap-3 ${badgeStyle}`}
    >
      <div className="text-xl p-2 rounded-lg bg-surface/50 border border-white/5 shrink-0">
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-xl font-extrabold tracking-tight leading-none text-text">
          {value}
        </p>
        <p className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider mt-1 truncate">
          {label}
        </p>
      </div>
    </div>
  );
}
