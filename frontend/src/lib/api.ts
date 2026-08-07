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

export async function fetchCases(): Promise<CaseData[]> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/cases`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    // Return mock data when API is unavailable
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
    // Return mock graph data when API is unavailable
    return getMockGraphData();
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