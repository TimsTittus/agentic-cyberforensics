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
  try {
    const res = await fetch(`${API_BASE}/api/v1/cases`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return getMockCases();
  }
}

export async function fetchGraphData(caseId?: string): Promise<GraphData> {
  try {
    const url = caseId
      ? `${API_BASE}/api/v1/graph?case_id=${caseId}`
      : `${API_BASE}/api/v1/graph`;
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return getMockGraphData();
  }
}

export async function searchEvidence(query: string, caseId?: string): Promise<SearchResponse> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, case_id: caseId, limit: 5 }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return getMockSearchResponse(query);
  }
}

export async function generateAiReport(caseId: string, caseTitle?: string): Promise<AiReport> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/report/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ case_id: caseId, case_title: caseTitle }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return getMockAiReport(caseId, caseTitle);
  }
}

function getMockCases(): CaseData[] {
  return [
    {
      id: "550e8400-e29b-41d4-a716-446655440000",
      title: "Operation Nighthawk – Telegram Network",
      status: "in_progress",
      risk_level: "critical",
      created_at: "2026-08-01T10:30:00Z",
      updated_at: "2026-08-06T14:22:00Z",
    },
    {
      id: "660e8400-e29b-41d4-a716-446655440001",
      title: "Case Bravo – Discord Server Infiltration",
      status: "open",
      risk_level: "high",
      created_at: "2026-08-03T08:15:00Z",
      updated_at: null,
    },
    {
      id: "770e8400-e29b-41d4-a716-446655440002",
      title: "Operation Sentinel – Image Forensics Cluster",
      status: "in_progress",
      risk_level: "high",
      created_at: "2026-08-04T12:00:00Z",
      updated_at: "2026-08-06T09:10:00Z",
    },
    {
      id: "880e8400-e29b-41d4-a716-446655440003",
      title: "Case Delta – Encrypted Channel Analysis",
      status: "open",
      risk_level: "medium",
      created_at: "2026-08-05T16:45:00Z",
      updated_at: null,
    },
    {
      id: "990e8400-e29b-41d4-a716-446655440004",
      title: "Operation Phantom – Dark Web Marketplace",
      status: "in_progress",
      risk_level: "critical",
      created_at: "2026-07-28T09:00:00Z",
      updated_at: "2026-08-07T03:30:00Z",
    },
    {
      id: "aa0e8400-e29b-41d4-a716-446655440005",
      title: "Case Echo – Social Engineering Vector",
      status: "closed",
      risk_level: "low",
      created_at: "2026-07-20T11:30:00Z",
      updated_at: "2026-08-02T17:00:00Z",
    },
  ];
}

function getMockGraphData(): GraphData {
  return {
    nodes: [
      { id: "s1", label: "phantom_x", type: "Suspect", color: "#ef4444" },
      { id: "s2", label: "dark_owl_99", type: "Suspect", color: "#ef4444" },
      { id: "v1", label: "Victim A (14F)", type: "Victim", color: "#f59e0b" },
      { id: "v2", label: "Victim B (13M)", type: "Victim", color: "#f59e0b" },
      { id: "a1", label: "@phantom_tg", type: "Account", color: "#6366f1" },
      { id: "a2", label: "@dark_owl_dc", type: "Account", color: "#6366f1" },
      { id: "a3", label: "@victim_a_tg", type: "Account", color: "#8b5cf6" },
      { id: "a4", label: "@victim_b_dc", type: "Account", color: "#8b5cf6" },
      { id: "l1", label: "VPN Exit – Frankfurt, DE", type: "Location", color: "#22c55e" },
      { id: "l2", label: "School Zone – Portland, OR", type: "Location", color: "#22c55e" },
      { id: "l3", label: "Tor Exit – Bucharest, RO", type: "Location", color: "#22c55e" },
      { id: "ip1", label: "198.51.100.42", type: "IP Address", color: "#06b6d4" },
      { id: "ip2", label: "203.0.113.77", type: "IP Address", color: "#06b6d4" },
      { id: "e1", label: "IMG_3847.jpg (AI-Gen)", type: "Evidence", color: "#ec4899" },
      { id: "e2", label: "chat_export.json", type: "Evidence", color: "#ec4899" },
    ],
    links: [
      { source: "s1", target: "a1", label: "OWNS" },
      { source: "s2", target: "a2", label: "OWNS" },
      { source: "v1", target: "a3", label: "OWNS" },
      { source: "v2", target: "a4", label: "OWNS" },
      { source: "a1", target: "a3", label: "COMMUNICATED_WITH" },
      { source: "a2", target: "a4", label: "COMMUNICATED_WITH" },
      { source: "a1", target: "a4", label: "COMMUNICATED_WITH" },
      { source: "s1", target: "ip1", label: "USES_IP" },
      { source: "s2", target: "ip2", label: "USES_IP" },
      { source: "ip1", target: "l1", label: "RESOLVES_TO" },
      { source: "ip2", target: "l3", label: "RESOLVES_TO" },
      { source: "a3", target: "l2", label: "LOCATED_AT" },
      { source: "a1", target: "e1", label: "SENT" },
      { source: "a1", target: "e2", label: "POSTED" },
    ],
  };
}

function getMockSearchResponse(query: string): SearchResponse {
  return {
    query,
    total_hits: 4,
    hits: [
      {
        id: "hit-1",
        score: 0.94,
        text: "Trust me, don't tell your parents about our chat.",
        case_id: "550e8400-e29b-41d4-a716-446655440000",
        source: "Telegram Chat Log (Message #104)",
      },
      {
        id: "hit-2",
        score: 0.88,
        text: "Meet me near the bus stop after school.",
        case_id: "550e8400-e29b-41d4-a716-446655440000",
        source: "Telegram Chat Log (Message #108)",
      },
      {
        id: "hit-3",
        score: 0.85,
        text: "EasyOCR Extracted Text: 'Bus Stop Line 4'",
        case_id: "550e8400-e29b-41d4-a716-446655440000",
        source: "Image OCR Artifact (IMG_3847.jpg)",
      },
      {
        id: "hit-4",
        score: 0.82,
        text: "YOLOv8 Detection: 'school uniform' (Confidence: 0.94)",
        case_id: "550e8400-e29b-41d4-a716-446655440000",
        source: "Vision Object Detection (IMG_3847.jpg)",
      },
    ],
  };
}

function getMockAiReport(caseId: string, caseTitle?: string): AiReport {
  return {
    case_id: caseId,
    case_title: caseTitle || "Operation Nighthawk – Telegram Network",
    generated_at: new Date().toISOString(),
    risk_level: "CRITICAL",
    risk_score: 88.5,
    executive_summary:
      "Forensic multi-agent analysis for case Operation Nighthawk has identified a CRITICAL risk level with active grooming progression across 4 distinct phases (Trust Building, Isolation, Secrecy, and Sexualization). Cross-modal fusion correlated victim chat transcripts with vision object detections (school uniform) and EasyOCR location text (Bus Stop Line 4) to establish high physical geographic proximity risk.",
    key_findings: [
      "Identified suspect handle 'phantom_x' employing sliding-window isolation tactics on Telegram.",
      "Computer vision model detected 'school uniform' correlated with OCR text 'Bus Stop Line 4'.",
      "Synthetic media analysis evaluated image artifacts with 0.85 AI-generation probability.",
      "OSINT query returned 2 public breach records matching suspect email 'suspect@darknet.org'.",
      "Neo4j relationship graph established direct communication edges between Suspect Account (@phantom_tg) and Victim Account (@victim_a_tg).",
    ],
    grooming_stages_detected: [
      "Trust Building",
      "Isolation",
      "Secrecy",
      "Sexualization",
    ],
    entities: [
      {
        name: "phantom_x",
        type: "Suspect",
        details: "Target handle active on Telegram and Darknet forums.",
      },
      {
        name: "Victim A (14F)",
        type: "Victim",
        details: "Identified minor target subjected to isolation tactics.",
      },
      {
        name: "@phantom_tg",
        type: "Account",
        details: "Telegram Account linked to IP 198.51.100.42.",
      },
      {
        name: "School Zone – Portland, OR",
        type: "Location",
        details: "Environmental match from YOLO image OCR context.",
      },
    ],
    top_evidence_vectors: [
      {
        source: "Telegram Chat Log (Message #104)",
        content: "Trust me, don't tell your parents about our chat.",
        relevance_score: 0.96,
      },
      {
        source: "Vision Object & OCR Analysis (IMG_3847.jpg)",
        content: "YOLO object 'school uniform' matched with OCR text 'Bus Stop Line 4'",
        relevance_score: 0.92,
      },
      {
        source: "OSINT Breach Intelligence",
        content: "IP 198.51.100.42 resolves to VPN Exit node in Frankfurt, DE associated with breach ID #8841.",
        relevance_score: 0.88,
      },
    ],
    recommendations: [
      "Issue emergency law enforcement warrant for IP 198.51.100.42 and ISP connection logs.",
      "Dispatch physical protective patrol to Portland school bus stop zone (Line 4).",
      "Preserve full chain-of-custody cryptographic hashes for chat export JSON and image IMG_3847.jpg.",
      "Initiate subpoena for Telegram account metadata associated with handle '@phantom_tg'.",
    ],
  };
}