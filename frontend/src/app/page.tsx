"use client";

import { useEffect, useState } from "react";
import {
  Shield,
  AlertTriangle,
  Activity,
  Search,
  Clock,
  Fingerprint,
  Network,
  ChevronRight,
  Zap,
  Eye,
  Plus,
  SlidersHorizontal,
  Home,
  FileText,
  Settings,
  Bell,
  Sparkles,
  Download,
  X,
  FileCheck,
  MapPin,
  ExternalLink,
  Cpu,
  ShieldAlert,
  ArrowLeft,
  Trash2,
  FolderOpen,
  Paperclip,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  fetchCases,
  createCase,
  uploadEvidence,
  fetchCaseEvidence,
  deleteEvidence,
  searchEvidence,
  generateAiReport,
  type CaseData,
  type SearchHit,
  type AiReport,
} from "@/lib/api";
import GraphExplorer from "@/components/GraphExplorer";
import LiveExecution from "@/components/LiveExecution";

function getRiskVariant(level: string) {
  const map: Record<string, "critical" | "high" | "medium" | "low"> = {
    critical: "critical",
    high: "high",
    medium: "medium",
    low: "low",
  };
  return map[level] || "default";
}

function getStatusVariant(status: string) {
  const map: Record<string, "open" | "in_progress" | "closed"> = {
    open: "open",
    in_progress: "in_progress",
    closed: "closed",
  };
  return map[status] || "default";
}

function formatDate(dateStr: string | null) {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function DashboardPage() {
  const [cases, setCases] = useState<CaseData[]>([]);
  const [search, setSearch] = useState("");
  const [activeTab, setActiveTab] = useState<"cases" | "graph" | "execution" | "evidence" | "workspace">("cases");

  // Semantic Search state
  const [searchQuery, setSearchQuery] = useState("school bus stop uniform");
  const [searchResults, setSearchResults] = useState<SearchHit[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // AI Report state
  const [report, setReport] = useState<AiReport | null>(null);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [showReportModal, setShowReportModal] = useState(false);

  // New Case Creation state
  const [showNewCaseModal, setShowNewCaseModal] = useState(false);
  const [newCaseTitle, setNewCaseTitle] = useState("");
  const [newCaseRisk, setNewCaseRisk] = useState("high");
  const [newCaseFiles, setNewCaseFiles] = useState<File[]>([]);
  const [isCreatingCase, setIsCreatingCase] = useState(false);
  const [selectedCaseId, setSelectedCaseId] = useState<string>("550e8400-e29b-41d4-a716-446655440000");

  // Case Workspace state
  const [caseEvidence, setCaseEvidence] = useState<any[]>([]);
  const [isLoadingEvidence, setIsLoadingEvidence] = useState(false);
  const [workspaceSubTab, setWorkspaceSubTab] = useState<"details" | "execution" | "graph" | "search">("details");

  useEffect(() => {
    fetchCases().then(setCases);
  }, []);

  const fetchEvidenceForCase = async (caseId: string) => {
    setIsLoadingEvidence(true);
    try {
      const items = await fetchCaseEvidence(caseId);
      setCaseEvidence(items);
    } catch {
      setCaseEvidence([]);
    } finally {
      setIsLoadingEvidence(false);
    }
  };

  useEffect(() => {
    if (selectedCaseId) {
      fetchEvidenceForCase(selectedCaseId);
    }
  }, [selectedCaseId]);

  const handleCreateCaseSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCaseTitle.trim()) return;
    setIsCreatingCase(true);
    try {
      const created = await createCase(newCaseTitle, newCaseRisk);
      if (newCaseFiles.length > 0) {
        await Promise.all(newCaseFiles.map((file) => uploadEvidence(created.id, file)));
      }
      setCases((prev) => [created, ...prev]);
      setSelectedCaseId(created.id);
      setActiveTab("workspace");
      setWorkspaceSubTab("details");
      setShowNewCaseModal(false);
      setNewCaseTitle("");
      setNewCaseFiles([]);
    } catch {
      // Fallback
    } finally {
      setIsCreatingCase(false);
    }
  };

  const handleVectorSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    try {
      const res = await searchEvidence(searchQuery);
      setSearchResults(res.hits);
    } catch {
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleGenerateReport = async (caseId: string, caseTitle?: string) => {
    setIsGeneratingReport(true);
    try {
      const res = await generateAiReport(caseId, caseTitle);
      setReport(res);
      setShowReportModal(true);
    } catch {
      // Fallback
    } finally {
      setIsGeneratingReport(false);
    }
  };

  const filteredCases = cases.filter(
    (c) =>
      c.title.toLowerCase().includes(search.toLowerCase()) ||
      c.id.toLowerCase().includes(search.toLowerCase())
  );

  const metrics = {
    critical: cases.filter((c) => c.risk_level === "critical").length,
    high: cases.filter((c) => c.risk_level === "high").length,
    medium: cases.filter((c) => c.risk_level === "medium").length,
    low: cases.filter((c) => c.risk_level === "low").length,
    active: cases.filter((c) => c.status !== "closed").length,
    total: cases.length,
  };

  return (
    <div className="min-h-screen bg-[#f4f6fb] text-slate-800 flex">
      {/* Soft Ambient Background Mesh */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute -top-[10%] -left-[10%] w-[50vw] h-[50vw] rounded-full bg-gradient-to-br from-indigo-200/30 via-purple-100/20 to-transparent blur-3xl" />
        <div className="absolute top-[20%] right-[-5%] w-[45vw] h-[45vw] rounded-full bg-gradient-to-br from-cyan-100/40 via-sky-100/20 to-transparent blur-3xl" />
        <div className="absolute -bottom-[10%] left-[20%] w-[50vw] h-[50vw] rounded-full bg-gradient-to-br from-emerald-100/30 via-teal-100/20 to-transparent blur-3xl" />
      </div>

      {/* Left Icon Dock / Sidebar */}
      <aside className="relative z-20 w-20 py-8 px-4 flex flex-col items-center justify-between border-r border-slate-200/50 bg-white/60 backdrop-blur-xl">
        <div className="flex flex-col items-center gap-8">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-800 text-white flex items-center justify-center shadow-lg shadow-slate-900/10">
            <Shield className="w-6 h-6" />
          </div>

          <nav className="flex flex-col gap-3">
            <button
              onClick={() => setActiveTab("cases")}
              className={`w-11 h-11 rounded-2xl flex items-center justify-center transition-all ${activeTab === "cases"
                ? "bg-slate-900 text-white shadow-md shadow-slate-900/15 scale-105"
                : "text-slate-500 hover:bg-slate-200/50 hover:text-slate-800"
                }`}
              title="Cases Overview"
            >
              <Home className="w-5 h-5" />
            </button>
            <button
              onClick={() => setActiveTab("execution")}
              className={`w-11 h-11 rounded-2xl flex items-center justify-center transition-all ${activeTab === "execution"
                ? "bg-slate-900 text-white shadow-md shadow-slate-900/15 scale-105"
                : "text-slate-500 hover:bg-slate-200/50 hover:text-slate-800"
                }`}
              title="Live LangGraph Execution"
            >
              <Cpu className="w-5 h-5" />
            </button>
            <button
              onClick={() => setActiveTab("graph")}
              className={`w-11 h-11 rounded-2xl flex items-center justify-center transition-all ${activeTab === "graph"
                ? "bg-slate-900 text-white shadow-md shadow-slate-900/15 scale-105"
                : "text-slate-500 hover:bg-slate-200/50 hover:text-slate-800"
                }`}
              title="Graph Intelligence Explorer"
            >
              <Network className="w-5 h-5" />
            </button>
            <button
              onClick={() => setActiveTab("evidence")}
              className={`w-11 h-11 rounded-2xl flex items-center justify-center transition-all ${activeTab === "evidence"
                ? "bg-slate-900 text-white shadow-md shadow-slate-900/15 scale-105"
                : "text-slate-500 hover:bg-slate-200/50 hover:text-slate-800"
                }`}
              title="Semantic Evidence Explorer"
            >
              <Search className="w-5 h-5" />
            </button>
          </nav>
        </div>

        <div className="flex flex-col items-center gap-4">
          <button className="w-10 h-10 rounded-full bg-slate-200/70 text-slate-600 flex items-center justify-center hover:bg-slate-300/70 transition-all">
            <Bell className="w-4 h-4" />
          </button>
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white flex items-center justify-center font-bold text-sm shadow-sm">
            BW
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="relative z-10 flex-1 flex flex-col min-w-0">
        {/* Top Header Bar */}
        <header className="px-8 py-6 flex flex-wrap items-center justify-between gap-4 border-b border-slate-200/40 bg-white/40 backdrop-blur-md">
          <div>
            <div className="flex items-center gap-2 text-xs font-medium text-slate-400 mb-1">
              <span>AgentBruce</span>
              <span>/</span>
              <span className="text-slate-600">Command Center</span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Cyberforensics Operating System
            </h1>
          </div>

          {/* Nav Pills & Generate AI Report Trigger */}
          <div className="flex items-center gap-3">
            <div className="pill-nav p-1 rounded-full flex items-center gap-1">
              <button
                onClick={() => setActiveTab("cases")}
                className={`px-4 py-2 rounded-full text-xs font-semibold transition-all ${activeTab === "cases"
                  ? "bg-slate-900 text-white shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
                  }`}
              >
                Cases
              </button>
              <button
                onClick={() => setActiveTab("execution")}
                className={`px-4 py-2 rounded-full text-xs font-semibold transition-all ${activeTab === "execution"
                  ? "bg-slate-900 text-white shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
                  }`}
              >
                Live Execution
              </button>
              <button
                onClick={() => setActiveTab("graph")}
                className={`px-4 py-2 rounded-full text-xs font-semibold transition-all ${activeTab === "graph"
                  ? "bg-slate-900 text-white shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
                  }`}
              >
                Graph Topology
              </button>
              <button
                onClick={() => setActiveTab("evidence")}
                className={`px-4 py-2 rounded-full text-xs font-semibold transition-all ${activeTab === "evidence"
                  ? "bg-slate-900 text-white shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
                  }`}
              >
                Evidence Explorer
              </button>
            </div>

            <button
              onClick={() => setShowNewCaseModal(true)}
              className="px-4 py-2.5 rounded-full bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-md shadow-slate-900/10 flex items-center gap-1.5 transition-all"
            >
              <Plus className="w-4 h-4" />
              New Case
            </button>

            <button
              onClick={() =>
                handleGenerateReport(
                  selectedCaseId,
                  cases.find((c) => c.id === selectedCaseId)?.title || "Operation Nighthawk – Telegram Network"
                )
              }
              disabled={isGeneratingReport}
              className="px-4 py-2.5 rounded-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white text-xs font-semibold shadow-md shadow-indigo-600/20 flex items-center gap-2 transition-all"
            >
              <Sparkles className="w-3.5 h-3.5" />
              {isGeneratingReport ? "Synthesizing..." : "Generate AI Report"}
            </button>
          </div>
        </header>

        {/* Dashboard Body */}
        <main className="p-8 space-y-8 flex-1 overflow-y-auto">
          {/* Pastel Metric Cards Row */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="glass-card-pastel-rose rounded-3xl p-5 flex flex-col justify-between transition-transform duration-300 hover:-translate-y-1">
              <div className="flex items-center justify-between mb-4">
                <span className="w-9 h-9 rounded-2xl bg-rose-500/15 flex items-center justify-center text-rose-600">
                  <AlertTriangle className="w-4 h-4" />
                </span>
                <span className="text-[11px] font-bold text-rose-700 bg-rose-200/50 px-2 py-0.5 rounded-full">
                  URGENT
                </span>
              </div>
              <div>
                <p className="text-3xl font-extrabold text-slate-900">{metrics.critical}</p>
                <p className="text-xs font-semibold text-rose-800/80 mt-1 uppercase tracking-wider">Critical Risk</p>
              </div>
            </div>

            <div className="glass-card-pastel-amber rounded-3xl p-5 flex flex-col justify-between transition-transform duration-300 hover:-translate-y-1">
              <div className="flex items-center justify-between mb-4">
                <span className="w-9 h-9 rounded-2xl bg-amber-500/15 flex items-center justify-center text-amber-600">
                  <Zap className="w-4 h-4" />
                </span>
                <span className="text-[11px] font-bold text-amber-800 bg-amber-200/50 px-2 py-0.5 rounded-full">
                  HIGH
                </span>
              </div>
              <div>
                <p className="text-3xl font-extrabold text-slate-900">{metrics.high}</p>
                <p className="text-xs font-semibold text-amber-900/80 mt-1 uppercase tracking-wider">High Risk</p>
              </div>
            </div>

            <div className="glass-card-pastel-cyan rounded-3xl p-5 flex flex-col justify-between transition-transform duration-300 hover:-translate-y-1">
              <div className="flex items-center justify-between mb-4">
                <span className="w-9 h-9 rounded-2xl bg-cyan-500/15 flex items-center justify-center text-cyan-600">
                  <Eye className="w-4 h-4" />
                </span>
                <span className="text-[11px] font-bold text-cyan-800 bg-cyan-200/50 px-2 py-0.5 rounded-full">
                  MED
                </span>
              </div>
              <div>
                <p className="text-3xl font-extrabold text-slate-900">{metrics.medium}</p>
                <p className="text-xs font-semibold text-cyan-900/80 mt-1 uppercase tracking-wider">Medium Risk</p>
              </div>
            </div>

            <div className="glass-card-pastel-emerald rounded-3xl p-5 flex flex-col justify-between transition-transform duration-300 hover:-translate-y-1">
              <div className="flex items-center justify-between mb-4">
                <span className="w-9 h-9 rounded-2xl bg-emerald-500/15 flex items-center justify-center text-emerald-600">
                  <Shield className="w-4 h-4" />
                </span>
                <span className="text-[11px] font-bold text-emerald-800 bg-emerald-200/50 px-2 py-0.5 rounded-full">
                  LOW
                </span>
              </div>
              <div>
                <p className="text-3xl font-extrabold text-slate-900">{metrics.low}</p>
                <p className="text-xs font-semibold text-emerald-900/80 mt-1 uppercase tracking-wider">Low Risk</p>
              </div>
            </div>

            <div className="glass-card-pastel-indigo rounded-3xl p-5 flex flex-col justify-between transition-transform duration-300 hover:-translate-y-1">
              <div className="flex items-center justify-between mb-4">
                <span className="w-9 h-9 rounded-2xl bg-indigo-500/15 flex items-center justify-center text-indigo-600">
                  <Activity className="w-4 h-4" />
                </span>
                <span className="text-[11px] font-bold text-indigo-800 bg-indigo-200/50 px-2 py-0.5 rounded-full">
                  ACTIVE
                </span>
              </div>
              <div>
                <p className="text-3xl font-extrabold text-slate-900">{metrics.active}</p>
                <p className="text-xs font-semibold text-indigo-900/80 mt-1 uppercase tracking-wider">Active Cases</p>
              </div>
            </div>

            <div className="glass-card-pastel-purple rounded-3xl p-5 flex flex-col justify-between transition-transform duration-300 hover:-translate-y-1">
              <div className="flex items-center justify-between mb-4">
                <span className="w-9 h-9 rounded-2xl bg-purple-500/15 flex items-center justify-center text-purple-600">
                  <Fingerprint className="w-4 h-4" />
                </span>
                <span className="text-[11px] font-bold text-purple-800 bg-purple-200/50 px-2 py-0.5 rounded-full">
                  TOTAL
                </span>
              </div>
              <div>
                <p className="text-3xl font-extrabold text-slate-900">{metrics.total}</p>
                <p className="text-xs font-semibold text-purple-900/80 mt-1 uppercase tracking-wider">Total Docket</p>
              </div>
            </div>
          </div>

          {/* Cases Overview Tab */}
          {activeTab === "cases" && (
            <Card className="rounded-3xl">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-6 border-b border-slate-100">
                <div>
                  <CardTitle className="text-lg font-bold text-slate-900">
                    Active Forensic Cases
                  </CardTitle>
                  <CardDescription className="mt-1">
                    Real-time status tracking across automated multi-agent pipelines
                  </CardDescription>
                </div>
                <div className="flex items-center gap-3">
                  <div className="relative w-72">
                    <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <Input
                      placeholder="Search cases by name or ID..."
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                  <button
                    onClick={() => setShowNewCaseModal(true)}
                    className="px-4 py-2 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs shadow-sm flex items-center gap-1.5 transition-all"
                  >
                    <Plus className="w-4 h-4" />
                    New Case
                  </button>
                </div>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-100">
                        <th className="text-left py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                          Case Title
                        </th>
                        <th className="text-left py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                          Status
                        </th>
                        <th className="text-left py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                          Risk Level
                        </th>
                        <th className="text-left py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                          Created At
                        </th>
                        <th className="text-left py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {filteredCases.map((c) => (
                        <tr
                          key={c.id}
                          onClick={() => {
                            setSelectedCaseId(c.id);
                            setActiveTab("workspace");
                            setWorkspaceSubTab("details");
                          }}
                          className="hover:bg-slate-50/70 transition-colors group cursor-pointer"
                        >
                          <td className="py-4 px-4">
                            <div>
                              <p className="font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors">
                                {c.title}
                              </p>
                              <p className="text-xs text-slate-400 font-mono mt-0.5">
                                ID: {c.id.slice(0, 8)}…
                              </p>
                            </div>
                          </td>
                          <td className="py-4 px-4">
                            <Badge variant={getStatusVariant(c.status)}>
                              {c.status.replace("_", " ")}
                            </Badge>
                          </td>
                          <td className="py-4 px-4">
                            <Badge variant={getRiskVariant(c.risk_level)}>
                              {c.risk_level}
                            </Badge>
                          </td>
                          <td className="py-4 px-4 text-slate-500 text-xs font-medium">
                            {formatDate(c.created_at)}
                          </td>
                          <td className="py-4 px-4" onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => handleGenerateReport(c.id, c.title)}
                                className="px-3 py-1.5 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium transition-all flex items-center gap-1.5"
                              >
                                <Sparkles className="w-3 h-3 text-indigo-600" />
                                AI Report
                              </button>
                              <button
                                onClick={() => {
                                  setSelectedCaseId(c.id);
                                  setActiveTab("workspace");
                                  setWorkspaceSubTab("details");
                                }}
                                className="w-8 h-8 rounded-full bg-slate-100 hover:bg-indigo-50 hover:text-indigo-600 text-slate-400 flex items-center justify-center transition-all"
                              >
                                <ChevronRight className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Live Execution Tab */}
          {activeTab === "execution" && (
            <Card className="rounded-3xl">
              <CardHeader className="border-b border-slate-100">
                <CardTitle className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <Activity className="w-5 h-5 text-indigo-600 animate-pulse" />
                  Real-Time LangGraph Execution Tracking
                </CardTitle>
                <CardDescription>
                  Streaming agent state transitions over persistent WebSocket socket
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                <LiveExecution caseId="550e8400-e29b-41d4-a716-446655440000" />
              </CardContent>
            </Card>
          )}

          {/* Graph Intelligence Tab */}
          {activeTab === "graph" && (
            <Card className="rounded-3xl min-h-[620px]">
              <CardHeader className="border-b border-slate-100">
                <CardTitle className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <Network className="w-5 h-5 text-indigo-600" />
                  Knowledge Graph Topology
                </CardTitle>
                <CardDescription>
                  Interactive cross-evidence entity link analysis powered by Neo4j
                </CardDescription>
              </CardHeader>
              <CardContent className="h-[550px] pt-6">
                <GraphExplorer />
              </CardContent>
            </Card>
          )}

          {/* Semantic Evidence Explorer Tab */}
          {activeTab === "evidence" && (
            <Card className="rounded-3xl">
              <CardHeader className="border-b border-slate-100">
                <CardTitle className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <Search className="w-5 h-5 text-indigo-600" />
                  Vector Evidence Explorer
                </CardTitle>
                <CardDescription>
                  Natural language semantic search powered by Qdrant vector database (384d all-MiniLM-L6-v2 embeddings)
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6 space-y-6">
                <form onSubmit={handleVectorSearch} className="flex gap-3">
                  <div className="relative flex-1">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <Input
                      placeholder="Ask any natural language query (e.g., 'school bus stop uniform', 'trust isolation messages')..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-11 h-12 text-sm"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={isSearching}
                    className="px-6 py-3 rounded-full bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs shadow-md shadow-slate-900/10 flex items-center gap-2 transition-all"
                  >
                    {isSearching ? "Embedding..." : "Vector Search"}
                  </button>
                </form>

                {/* Quick Suggestion Pills */}
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="text-slate-400 font-medium">Try searching:</span>
                  {[
                    "school bus stop uniform",
                    "trust isolation secret",
                    "dark web breach email",
                    "image EXIF camera model",
                  ].map((suggest) => (
                    <button
                      key={suggest}
                      onClick={() => {
                        setSearchQuery(suggest);
                        searchEvidence(suggest).then((res) => setSearchResults(res.hits));
                      }}
                      className="px-3 py-1 rounded-full bg-slate-100 hover:bg-indigo-50 hover:text-indigo-600 text-slate-600 transition-all"
                    >
                      {suggest}
                    </button>
                  ))}
                </div>

                {/* Vector Match Hits */}
                <div className="space-y-3 pt-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Semantic Search Results ({searchResults.length} hits)
                  </h4>
                  {searchResults.map((hit) => (
                    <div
                      key={hit.id}
                      className="p-4 rounded-2xl border border-slate-200/80 bg-white/80 backdrop-blur-md shadow-sm hover:border-indigo-300 transition-all flex items-start justify-between gap-4"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded-full">
                            {hit.source}
                          </span>
                          <span className="text-[11px] text-slate-400 font-mono">
                            Case: {hit.case_id.slice(0, 8)}…
                          </span>
                        </div>
                        <p className="text-sm font-semibold text-slate-900 pt-1">{hit.text}</p>
                      </div>
                      <div className="text-right flex flex-col items-end shrink-0">
                        <span className="text-xs font-bold text-indigo-600 bg-indigo-50 border border-indigo-200/60 px-2.5 py-1 rounded-full">
                          {Math.round(hit.score * 100)}% Similarity
                        </span>
                      </div>
                    </div>
                  ))}

                  {searchResults.length === 0 && (
                    <div className="text-center py-12 text-slate-400 italic">
                      Click &ldquo;Vector Search&rdquo; to query Qdrant embeddings.
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Dynamic Interactive Case Workspace */}
          {activeTab === "workspace" && selectedCaseId && (
            <div className="space-y-6">
              {/* Back Button & Header */}
              <div className="flex flex-wrap items-center justify-between gap-4 p-5 rounded-3xl border border-white/90 bg-white/75 backdrop-blur-xl shadow-sm">
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setActiveTab("cases")}
                    className="p-2.5 rounded-full border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition-all"
                    title="Back to Cases"
                  >
                    <ArrowLeft className="w-4 h-4" />
                  </button>
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-600">
                      Active Investigation Space
                    </span>
                    <h3 className="font-bold text-lg text-slate-900 leading-tight">
                      {cases.find((c) => c.id === selectedCaseId)?.title || "Case Workspace"}
                    </h3>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() =>
                      handleGenerateReport(
                        selectedCaseId,
                        cases.find((c) => c.id === selectedCaseId)?.title || ""
                      )
                    }
                    disabled={isGeneratingReport}
                    className="px-4 py-2.5 rounded-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white text-xs font-semibold shadow-md flex items-center gap-1.5 transition-all"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    AI report
                  </button>
                </div>
              </div>

              {/* Workspace Dashboard Layout */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left Panel: Profile & Evidence Ledger */}
                <div className="space-y-6 lg:col-span-1">
                  {/* Case Profile details */}
                  <Card className="rounded-3xl shadow-sm border-white bg-white/70 backdrop-blur-md">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm font-bold uppercase tracking-wider text-slate-400">
                        Case Information
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4 text-xs font-medium text-slate-700">
                      <div>
                        <span className="text-slate-400 block font-normal mb-0.5">Case UUID:</span>
                        <span className="font-mono text-slate-900 bg-slate-50 border border-slate-100 px-2 py-1 rounded-lg select-all block truncate">
                          {selectedCaseId}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <span className="text-slate-400 block font-normal mb-0.5">Status:</span>
                          <Badge variant={getStatusVariant(cases.find((c) => c.id === selectedCaseId)?.status || "open")}>
                            {(cases.find((c) => c.id === selectedCaseId)?.status || "open").replace("_", " ")}
                          </Badge>
                        </div>
                        <div>
                          <span className="text-slate-400 block font-normal mb-0.5">Risk Level:</span>
                          <Badge variant={getRiskVariant(cases.find((c) => c.id === selectedCaseId)?.risk_level || "medium")}>
                            {cases.find((c) => c.id === selectedCaseId)?.risk_level || "medium"}
                          </Badge>
                        </div>
                      </div>
                      <div>
                        <span className="text-slate-400 block font-normal mb-0.5">Created At:</span>
                        <span className="text-slate-955 font-semibold">
                          {formatDate(cases.find((c) => c.id === selectedCaseId)?.created_at || "")}
                        </span>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Evidence Ledger */}
                  <Card className="rounded-3xl shadow-sm border-white bg-white/70 backdrop-blur-md">
                    <CardHeader className="pb-3 border-b border-slate-100 flex flex-row items-center justify-between">
                      <div>
                        <CardTitle className="text-sm font-bold uppercase tracking-wider text-slate-400">
                          Forensic Ledger
                        </CardTitle>
                        <CardDescription className="text-[10px] mt-0.5">
                          Cryptographic chain-of-custody log
                        </CardDescription>
                      </div>
                      <span className="text-xs font-bold text-slate-500 bg-slate-100/80 px-2.5 py-0.5 rounded-full">
                        {caseEvidence.length} Files
                      </span>
                    </CardHeader>
                    <CardContent className="pt-4 space-y-4">
                      {/* Evidence Files List */}
                      <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
                        {caseEvidence.map((ev) => (
                          <div
                            key={ev.id}
                            className="p-3 rounded-2xl border border-slate-200/80 bg-white/90 shadow-sm space-y-2 hover:border-indigo-200 transition-all"
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div className="flex items-center gap-2 min-w-0">
                                <FileText className="w-4 h-4 text-indigo-500 shrink-0" />
                                <span className="text-xs font-bold text-slate-800 truncate" title={ev.file_path}>
                                  {ev.file_path.split("/").pop()}
                                </span>
                              </div>
                              <div className="flex items-center gap-1.5 shrink-0">
                                <Badge
                                  variant={
                                    ev.processed_status === "completed"
                                      ? "low"
                                      : ev.processed_status === "processing"
                                        ? "medium"
                                        : "high"
                                  }
                                  className="text-[9px] px-1.5 py-0 animate-fade-in"
                                >
                                  {ev.processed_status}
                                </Badge>
                                <button
                                  onClick={async (e) => {
                                    e.stopPropagation();
                                    if (confirm(`Are you sure you want to delete "${ev.file_path.split("/").pop()}"?`)) {
                                      await deleteEvidence(ev.id);
                                      fetchEvidenceForCase(selectedCaseId);
                                    }
                                  }}
                                  className="p-1 hover:bg-rose-50 rounded-lg text-slate-400 hover:text-rose-500 transition-colors"
                                  title="Delete evidence"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            </div>
                            <div className="text-[10px] text-slate-400 space-y-0.5">
                              <p className="font-mono truncate select-all" title={ev.sha256_hash}>
                                SHA-256: {ev.sha256_hash.slice(0, 16)}…
                              </p>
                              <p>Type: {ev.file_type || "binary"} • Ingested: {formatDate(ev.ingested_at)}</p>
                            </div>
                          </div>
                        ))}

                        {caseEvidence.length === 0 && !isLoadingEvidence && (
                          <div className="text-center py-8 text-xs text-slate-400 italic">
                            No digital evidence attached to this case docket.
                          </div>
                        )}

                        {isLoadingEvidence && (
                          <div className="text-center py-8 text-xs text-slate-400 animate-pulse">
                            Loading chain-of-custody records...
                          </div>
                        )}
                      </div>

                      {/* Attach More Evidence Upload Zone */}
                      <div className="pt-2 border-t border-slate-100">
                        <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-2">
                          Ingest Additional Evidence
                        </label>
                        <div className="border border-dashed border-slate-200 hover:border-indigo-400 rounded-2xl p-3 text-center transition-all bg-slate-50/50 cursor-pointer">
                          <input
                            type="file"
                            multiple
                            id="workspace-upload"
                            className="hidden"
                            onChange={async (e) => {
                              if (e.target.files && e.target.files.length > 0) {
                                const filesArray = Array.from(e.target.files);
                                await Promise.all(
                                  filesArray.map((file) => uploadEvidence(selectedCaseId, file))
                                );
                                fetchEvidenceForCase(selectedCaseId);
                              }
                            }}
                          />
                          <label htmlFor="workspace-upload" className="cursor-pointer space-y-1 block">
                            <Paperclip className="w-5 h-5 text-slate-400 mx-auto" />
                            <span className="text-[11px] font-semibold text-slate-700 block">
                              Attach Evidence Files
                            </span>
                            <span className="text-[9px] text-slate-400 block">
                              Supports multiple text, image, or audio files
                            </span>
                          </label>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Right Column: Forensic Sub-tab Spaces */}
                <div className="lg:col-span-2 space-y-6">
                  {/* Sub-tab Navigation */}
                  <div className="flex items-center gap-1.5 p-1 rounded-2xl bg-slate-100 w-fit">
                    {[
                      { id: "details", label: "Executive Info" },
                      { id: "execution", label: "Live Execution" },
                      { id: "graph", label: "Graph Topology" },
                      { id: "search", label: "Semantic Search" },
                    ].map((tab) => (
                      <button
                        key={tab.id}
                        onClick={() => setWorkspaceSubTab(tab.id as any)}
                        className={`px-4 py-1.5 rounded-xl text-xs font-semibold transition-all ${workspaceSubTab === tab.id
                          ? "bg-slate-900 text-white shadow-sm"
                          : "text-slate-600 hover:text-slate-900"
                          }`}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>

                  {/* Sub-tab Content mapping */}
                  {workspaceSubTab === "details" && (
                    <Card className="rounded-3xl border-white bg-white/70 backdrop-blur-md shadow-sm">
                      <CardHeader>
                        <CardTitle className="text-base font-bold text-slate-900 flex items-center gap-2">
                          <Eye className="w-4 h-4 text-indigo-600" />
                          Executive Investigation Overview
                        </CardTitle>
                        <CardDescription>
                          Automated threat summary & system telemetry metrics
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-6 pt-2">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="p-4 rounded-2xl bg-indigo-50/50 border border-indigo-100 flex flex-col justify-between">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-600">
                              Threat Assessment Matrix
                            </span>
                            <div className="py-3">
                              <p className="text-4xl font-extrabold text-indigo-900">88.5</p>
                              <p className="text-xs text-indigo-700/80 mt-1 font-semibold">
                                Synthesized Risk Score (0-100)
                              </p>
                            </div>
                            <span className="text-[10px] text-slate-400">
                              Calculated across 8 forensic nodes
                            </span>
                          </div>

                          <div className="p-4 rounded-2xl bg-purple-50/50 border border-purple-100 flex flex-col justify-between">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-purple-600">
                              Cognitive Graph Links
                            </span>
                            <div className="py-3">
                              <p className="text-4xl font-extrabold text-purple-900">24</p>
                              <p className="text-xs text-purple-700/80 mt-1 font-semibold">
                                Tracked Entity Associations
                              </p>
                            </div>
                            <span className="text-[10px] text-slate-400">
                              Persisted inside Neo4j topology DB
                            </span>
                          </div>
                        </div>

                        <div className="space-y-3">
                          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                            Analytical Summary Findings
                          </h4>
                          <div className="p-4 rounded-2xl border border-slate-200/80 bg-white/95 text-xs text-slate-600 space-y-2 leading-relaxed">
                            <p>
                              System detected high-risk patterns of trust formation and child isolation across digital communication evidence.
                            </p>
                            <p>
                              OSINT breach records link the suspect's registered contact channels to known black-market breach credentials.
                            </p>
                          </div>
                        </div>

                        <div className="flex justify-end">
                          <button
                            onClick={() =>
                              handleGenerateReport(
                                selectedCaseId,
                                cases.find((c) => c.id === selectedCaseId)?.title || ""
                              )
                            }
                            disabled={isGeneratingReport}
                            className="px-5 py-2.5 rounded-full bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-md shadow-slate-900/10 flex items-center gap-1.5 transition-all"
                          >
                            <Sparkles className="w-3.5 h-3.5 text-indigo-400 animate-pulse" />
                            Run AI Case Evaluation Report
                          </button>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {workspaceSubTab === "execution" && (
                    <LiveExecution caseId={selectedCaseId} />
                  )}

                  {workspaceSubTab === "graph" && (
                    <Card className="rounded-3xl border-white bg-white/70 backdrop-blur-md shadow-sm">
                      <CardHeader>
                        <CardTitle className="text-base font-bold text-slate-900 flex items-center gap-2">
                          <Network className="w-4 h-4 text-indigo-600" />
                          Interactive Neo4j Entity Map
                        </CardTitle>
                        <CardDescription>
                          Visual link analysis mapped specific to this case
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="h-[450px]">
                        <GraphExplorer caseId={selectedCaseId} />
                      </CardContent>
                    </Card>
                  )}

                  {workspaceSubTab === "search" && (
                    <Card className="rounded-3xl border-white bg-white/70 backdrop-blur-md shadow-sm">
                      <CardHeader>
                        <CardTitle className="text-base font-bold text-slate-900 flex items-center gap-2">
                          <Search className="w-4 h-4 text-indigo-600" />
                          Semantic Search Vector Explorer
                        </CardTitle>
                        <CardDescription>
                          Query Qdrant evidence embeddings specifically filtered for this case
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-4 pt-2">
                        {/* Search Input bar */}
                        <form
                          onSubmit={async (e) => {
                            e.preventDefault();
                            if (!searchQuery.trim()) return;
                            setIsSearching(true);
                            try {
                              const res = await searchEvidence(searchQuery, selectedCaseId);
                              setSearchResults(res.hits);
                            } catch {
                              setSearchResults([]);
                            } finally {
                              setIsSearching(false);
                            }
                          }}
                          className="flex gap-2"
                        >
                          <div className="relative flex-1">
                            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                            <Input
                              placeholder="Search vector embeddings for this case..."
                              value={searchQuery}
                              onChange={(e) => setSearchQuery(e.target.value)}
                              className="pl-11 h-11 text-sm"
                            />
                          </div>
                          <button
                            type="submit"
                            disabled={isSearching}
                            className="px-5 py-2.5 rounded-full bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs transition-all shrink-0"
                          >
                            Search Case
                          </button>
                        </form>

                        {/* Search Results list */}
                        <div className="space-y-3 pt-2 max-h-[300px] overflow-y-auto pr-1">
                          {searchResults.map((hit) => (
                            <div
                              key={hit.id}
                              className="p-3 rounded-2xl border border-slate-200/80 bg-white shadow-sm flex items-start justify-between gap-4"
                            >
                              <div>
                                <span className="text-[10px] font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
                                  {hit.source}
                                </span>
                                <p className="text-xs text-slate-700 font-semibold mt-1.5">{hit.text}</p>
                              </div>
                              <span className="text-[10px] font-bold text-indigo-600 bg-indigo-50 border border-indigo-200/60 px-2 py-0.5 rounded-full shrink-0">
                                {Math.round(hit.score * 100)}% Match
                              </span>
                            </div>
                          ))}

                          {searchResults.length === 0 && (
                            <div className="text-center py-10 text-xs text-slate-400 italic">
                              Type a query to search vector embeddings inside this case.
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
      {/* New Case Creation & Execution Modal */}
      {showNewCaseModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-lg w-full border border-slate-200 shadow-2xl p-6 space-y-6">
            <div className="flex items-start justify-between border-b border-slate-100 pb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-indigo-600 text-white flex items-center justify-center shadow-md shadow-indigo-600/20">
                  <Shield className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-900">Start New Forensic Case</h3>
                  <p className="text-xs text-slate-400">Initialize investigation docket & launch LangGraph pipeline</p>
                </div>
              </div>
              <button
                onClick={() => setShowNewCaseModal(false)}
                className="p-2 rounded-full text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateCaseSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5">
                  Case Title / Codename *
                </label>
                <Input
                  required
                  placeholder="e.g. Operation Nighthawk – Telegram Network"
                  value={newCaseTitle}
                  onChange={(e) => setNewCaseTitle(e.target.value)}
                  className="h-11 text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5">
                  Initial Threat Assessment Risk Level
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {(["critical", "high", "medium", "low"] as const).map((level) => (
                    <button
                      key={level}
                      type="button"
                      onClick={() => setNewCaseRisk(level)}
                      className={`py-2 rounded-xl text-xs font-bold capitalize transition-all border ${newCaseRisk === level
                        ? "bg-slate-900 text-white border-slate-900 shadow-sm"
                        : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
                        }`}
                    >
                      {level}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5">
                  Attach Evidence Files (Optional)
                </label>
                <div className="border-2 border-dashed border-slate-200 hover:border-indigo-400 rounded-2xl p-4 text-center transition-all bg-slate-50/50">
                  <input
                    type="file"
                    multiple
                    id="evidence-upload"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files.length > 0) {
                        setNewCaseFiles((prev) => [...prev, ...Array.from(e.target.files as FileList)]);
                      }
                    }}
                  />
                  <label htmlFor="evidence-upload" className="cursor-pointer space-y-1 block">
                    <FileText className="w-6 h-6 text-slate-400 mx-auto" />
                    <p className="text-xs font-semibold text-slate-700">
                      Click to browse or drop digital evidence files
                    </p>
                    <p className="text-[11px] text-slate-400">
                      Supports multiple .txt, .json, .jpg, .png, .mp3, .wav files
                    </p>
                  </label>
                </div>

                {/* Display list of selected files */}
                {newCaseFiles.length > 0 && (
                  <div className="mt-3 space-y-1.5 max-h-24 overflow-y-auto">
                    {newCaseFiles.map((file, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-2 rounded-xl bg-slate-50 border border-slate-200/60 text-xs"
                      >
                        <span className="font-semibold text-slate-700 truncate max-w-[280px]">
                          {file.name} ({(file.size / 1024).toFixed(1)} KB)
                        </span>
                        <button
                          type="button"
                          onClick={() => setNewCaseFiles((prev) => prev.filter((_, i) => i !== idx))}
                          className="p-1 rounded-full text-rose-500 hover:bg-rose-50 transition-all"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowNewCaseModal(false)}
                  className="px-4 py-2.5 rounded-full border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreatingCase}
                  className="px-5 py-2.5 rounded-full bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-md shadow-slate-900/10 flex items-center gap-2 transition-all"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  {isCreatingCase ? "Launching..." : "Create Case & Launch Pipeline"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* AI Lead Report Printable Modal */}
      {showReportModal && report && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-4xl w-full max-h-[90vh] overflow-y-auto border border-slate-200 shadow-2xl p-8 space-y-6">
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-slate-100 pb-6">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-rose-500 to-indigo-600 text-white flex items-center justify-center shadow-lg shadow-rose-500/20">
                  <ShieldAlert className="w-6 h-6" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl font-bold text-slate-900">{report.case_title}</h2>
                    <Badge variant="critical">{report.risk_level}</Badge>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Case ID: {report.case_id} • Generated {new Date(report.generated_at).toLocaleString()}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowReportModal(false)}
                className="p-2 rounded-full text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Executive Summary */}
            <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <FileCheck className="w-4 h-4 text-indigo-600" />
                Executive Summary & Threat Assessment
              </h3>
              <p className="text-sm text-slate-700 leading-relaxed font-medium">
                {report.executive_summary}
              </p>
              <div className="pt-2 flex items-center gap-4 text-xs font-semibold text-slate-600">
                <span>Threat Score: <strong className="text-rose-600">{report.risk_score} / 100</strong></span>
                <span>•</span>
                <span>Grooming Stages: <span className="text-indigo-600">{report.grooming_stages_detected.join(", ")}</span></span>
              </div>
            </div>

            {/* Key Findings */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Key Analytical Findings
              </h3>
              <ul className="space-y-2">
                {report.key_findings.map((finding, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm text-slate-700">
                    <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    <span>{finding}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Entities & Qdrant Vectors Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              {/* Neo4j Entities */}
              <div className="p-4 rounded-2xl border border-slate-200/80 bg-slate-50/50 space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <Network className="w-3.5 h-3.5 text-indigo-600" />
                  Neo4j Graph Entity Nodes
                </h4>
                <div className="space-y-2">
                  {report.entities.map((ent, idx) => (
                    <div key={idx} className="p-2.5 rounded-xl bg-white border border-slate-200/60 text-xs">
                      <div className="flex items-center justify-between font-bold text-slate-800">
                        <span>{ent.name}</span>
                        <span className="text-[10px] text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">{ent.type}</span>
                      </div>
                      <p className="text-slate-500 mt-1">{ent.details}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Qdrant Vectors */}
              <div className="p-4 rounded-2xl border border-slate-200/80 bg-slate-50/50 space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <Search className="w-3.5 h-3.5 text-purple-600" />
                  Top Qdrant Vector Matches
                </h4>
                <div className="space-y-2">
                  {report.top_evidence_vectors.map((vec, idx) => (
                    <div key={idx} className="p-2.5 rounded-xl bg-white border border-slate-200/60 text-xs">
                      <div className="flex items-center justify-between font-bold text-slate-800">
                        <span className="text-slate-500">{vec.source}</span>
                        <span className="text-[10px] text-purple-600 bg-purple-50 px-2 py-0.5 rounded-full">
                          {Math.round(vec.relevance_score * 100)}% Sim
                        </span>
                      </div>
                      <p className="text-slate-800 font-medium mt-1">&ldquo;{vec.content}&rdquo;</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Recommendations */}
            <div className="p-5 rounded-2xl bg-indigo-50/70 border border-indigo-200/80 space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-900">
                Actionable Law Enforcement Next Steps
              </h3>
              <ul className="space-y-1.5 text-xs text-indigo-950 font-medium">
                {report.recommendations.map((rec, i) => (
                  <li key={i} className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-600" />
                    {rec}
                  </li>
                ))}
              </ul>
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-between pt-4 border-t border-slate-100">
              <span className="text-xs text-slate-400">AgentBruce Forensic Lead Report v1.0</span>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => window.print()}
                  className="px-4 py-2 rounded-full border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-all"
                >
                  <Download className="w-3.5 h-3.5" />
                  Print / Export PDF
                </button>
                <button
                  onClick={() => setShowReportModal(false)}
                  className="px-5 py-2 rounded-full bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-sm transition-all"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}