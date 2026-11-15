const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface CaseData {
  id: string;
  title: string;
  status: string;
  risk_level: string;
  created_at: string;
  updated_at: string | null;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  color?: string;
}

export interface GraphLink {
  source: string;
  target: string;
  label: string;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

export interface SearchHit {
  id: string;
  score: number;
  text: string;
  case_id: string;
  source: string;
}

export interface SearchResponse {
  query: string;
  total_hits: number;
  hits: SearchHit[];
}

export interface ReportEntity {
  name: string;
  type: string;
  details: string;
}

export interface ReportEvidence {
  source: string;
  content: string;
  relevance_score: number;
}

export interface AiReport {
  case_id: string;
  case_title: string;
  generated_at: string;
  risk_level: string;
  risk_score: number;
  executive_summary: string;
  key_findings: string[];
  grooming_stages_detected: string[];
  entities: ReportEntity[];
  top_evidence_vectors: ReportEvidence[];
  recommendations: string[];
}

export async function fetchCases(): Promise<CaseData[]> {
  const res = await fetch(`${API_BASE}/api/v1/cases`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch cases: HTTP ${res.status}`);
  return res.json();
}

export async function createCase(title: string, risk_level: string = "medium"): Promise<CaseData> {
  const res = await fetch(`${API_BASE}/api/v1/cases`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, risk_level }),
  });
  if (!res.ok) throw new Error(`Failed to create case: HTTP ${res.status}`);
  return res.json();
}

export async function uploadEvidence(caseId: string, file: File): Promise<any> {
  const formData = new FormData();
  formData.append("case_id", caseId);
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/v1/evidence/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail?.detail || `Failed to upload evidence: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchCaseEvidence(caseId: string): Promise<any[]> {
  const res = await fetch(`${API_BASE}/api/v1/cases/${caseId}/evidence`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch evidence: HTTP ${res.status}`);
  return res.json();
}

export async function deleteEvidence(evidenceId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/v1/evidence/${evidenceId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Failed to delete evidence: HTTP ${res.status}`);
  return res.json();
}

export async function fetchGraphData(caseId?: string): Promise<GraphData> {
  const url = caseId
    ? `${API_BASE}/api/v1/graph?case_id=${caseId}`
    : `${API_BASE}/api/v1/graph`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch graph: HTTP ${res.status}`);
  return res.json();
}

export async function searchEvidence(query: string, caseId?: string): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/api/v1/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, case_id: caseId, limit: 5 }),
  });
  if (!res.ok) throw new Error(`Search failed: HTTP ${res.status}`);
  return res.json();
}

export interface ExecutionLogEntry {
  id?: string | null;
  case_id?: string;
  evidence_id?: string | null;
  level: "debug" | "info" | "warn" | "error" | "success";
  source: string;
  message: string;
  extra?: Record<string, unknown> | null;
  created_at?: string;
}

export async function fetchExecutionLogs(
  caseId: string,
  opts: { limit?: number; after?: string } = {}
): Promise<ExecutionLogEntry[]> {
  const params = new URLSearchParams();
  if (opts.limit) params.set("limit", String(opts.limit));
  if (opts.after) params.set("after", opts.after);
  const qs = params.toString();
  const res = await fetch(
    `${API_BASE}/api/v1/cases/${caseId}/execution-logs${qs ? `?${qs}` : ""}`,
    { cache: "no-store" }
  );
  if (!res.ok) throw new Error(`Failed to fetch execution logs: HTTP ${res.status}`);
  return res.json();
}

export function executionLogsWsUrl(caseId: string): string {
  const wsBase = API_BASE.replace(/^http/, "ws");
  return `${wsBase}/api/v1/ws/execution-logs/${caseId}`;
}

export async function generateAiReport(caseId: string, caseTitle?: string): Promise<AiReport> {
  const res = await fetch(`${API_BASE}/api/v1/report/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ case_id: caseId, case_title: caseTitle }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail?.detail || `Failed to generate report: HTTP ${res.status}`);
  }
  return res.json();
}
