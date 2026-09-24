/* ─── Core Schema Types ─────────────────────────────────────── */

export interface Span {
  start: number;
  end: number;
  page: number | null;
}

export interface Citation {
  kind: 'document' | 'statute';
  span: Span | null;
  statute_id: string | null;
  quote: string;
}

export type ClauseType =
  | 'compensation' | 'notice_period' | 'probation' | 'training_bond'
  | 'non_compete' | 'non_solicit' | 'confidentiality' | 'ip_assignment'
  | 'termination' | 'penalty_liquidated_damages' | 'indemnity'
  | 'dispute_resolution' | 'jurisdiction' | 'arbitration'
  | 'working_hours' | 'leave' | 'benefits' | 'amendment'
  | 'severability' | 'other';

export interface Clause {
  id: string;
  index: number;
  heading: string | null;
  text: string;
  span: Span;
  type: ClauseType;
  burden_on: 'user' | 'counterparty' | 'mutual' | 'unclear';
  risk_score: number;
  risk_reasons: string[];
}

export interface BaselineVerdict {
  clause_id: string;
  verdict: 'standard' | 'stricter_than_usual' | 'unusual' | 'no_baseline';
  baseline_id: string | null;
  baseline_text: string | null;
  explanation: string;
  citations: Citation[];
}

export interface EnforceabilityFlag {
  clause_id: string;
  status: 'likely_unenforceable' | 'limited_enforceability' | 'likely_enforceable' | 'unclear';
  statute_ids: string[];
  explanation: string;
  ask_a_lawyer: string[];
  confidence: 'high' | 'medium' | 'low';
}

export interface Obligation {
  clause_id: string;
  who: 'user' | 'counterparty';
  what: string;
  due: string | null;
  trigger: string | null;
  amount_inr: number | null;
  citations: Citation[];
}

export interface Finding {
  id: string;
  title: string;
  tier: 'document_says' | 'general_law' | 'option';
  body: string;
  clause_ids: string[];
  citations: Citation[];
  verified: boolean;
}

export interface Redline {
  clause_id: string;
  current_text: string;
  suggested_text: string;
  rationale: string;
}

/* ─── API Response Types ────────────────────────────────────── */

export interface PageMapEntry {
  page_no: number;
  start: number;
  end: number;
}

export interface UploadResponse {
  document_id: string;
  full_text: string;
  pages: PageMapEntry[];
}

export interface AnalysisResponse {
  document_id: string;
  clauses: Clause[];
  baseline_verdicts: BaselineVerdict[];
  enforceability_flags: EnforceabilityFlag[];
  obligations: Obligation[];
  findings: Finding[];
}

export interface QAResponse {
  answer: string;
  citations: Citation[];
  abstained: boolean;
}

export interface RedlineResponse {
  redlines: Redline[];
  email_draft: string;
}

/* ─── App State Types ───────────────────────────────────────── */

export type PipelineStage =
  | 'idle'
  | 'uploading'
  | 'extracting'
  | 'analyzing'
  | 'verifying'
  | 'complete'
  | 'error';

export interface QAMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  abstained?: boolean;
}
