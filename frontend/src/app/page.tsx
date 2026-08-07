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
  User,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { fetchCases, type CaseData } from "@/lib/api";
import GraphExplorer from "@/components/GraphExplorer";

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
  const [activeTab, setActiveTab] = useState<"cases" | "graph">("cases");

  useEffect(() => {
    fetchCases().then(setCases);
  }, []);

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
      {/* Soft Ambient Pastel Background Mesh */}
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
              title="Cases Dashboard"
            >
              <Home className="w-5 h-5" />
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
            <button className="w-11 h-11 rounded-2xl flex items-center justify-center text-slate-400 hover:bg-slate-200/50 hover:text-slate-700 transition-all">
              <FileText className="w-5 h-5" />
            </button>
            <button className="w-11 h-11 rounded-2xl flex items-center justify-center text-slate-400 hover:bg-slate-200/50 hover:text-slate-700 transition-all">
              <Settings className="w-5 h-5" />
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
          {/* Breadcrumb & Title */}
          <div>
            <div className="flex items-center gap-2 text-xs font-medium text-slate-400 mb-1">
              <span>AgentBruce</span>
              <span>/</span>
              <span className="text-slate-600">Command Center</span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Cyberforensics Dashboard
            </h1>
          </div>

          {/* Pill Navigation & Quick Actions */}
          <div className="flex items-center gap-3">
            {/* Navigation Pills */}
            <div className="pill-nav p-1 rounded-full flex items-center gap-1">
              <button
                onClick={() => setActiveTab("cases")}
                className={`px-5 py-2 rounded-full text-xs font-semibold transition-all ${activeTab === "cases"
                  ? "bg-slate-900 text-white shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
                  }`}
              >
                Cases Overview
              </button>
              <button
                onClick={() => setActiveTab("graph")}
                className={`px-5 py-2 rounded-full text-xs font-semibold transition-all ${activeTab === "graph"
                  ? "bg-slate-900 text-white shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
                  }`}
              >
                Graph Intelligence
              </button>
            </div>

            {/* Quick Action Button */}
            <button className="px-4 py-2 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-md shadow-indigo-600/20 flex items-center gap-2 transition-all">
              <Plus className="w-3.5 h-3.5" />
              New Case
            </button>
          </div>
        </header>

        {/* Dashboard Body */}
        <main className="p-8 space-y-8 flex-1 overflow-y-auto">
          {/* Pastel Metric Cards Row */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {/* Critical Card */}
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

            {/* High Card */}
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

            {/* Medium Card */}
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

            {/* Low Card */}
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

            {/* Active Card */}
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

            {/* Total Card */}
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

          {/* Cases Overview Tab Content */}
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
                  <button className="p-2.5 rounded-full border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition-all">
                    <SlidersHorizontal className="w-4 h-4" />
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
                          Last Updated
                        </th>
                        <th className="py-3 px-4" />
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {filteredCases.map((c) => (
                        <tr
                          key={c.id}
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
                          <td className="py-4 px-4 text-slate-500 text-xs font-medium">
                            {formatDate(c.updated_at)}
                          </td>
                          <td className="py-4 px-4">
                            <div className="w-8 h-8 rounded-full bg-slate-100 group-hover:bg-indigo-50 group-hover:text-indigo-600 text-slate-400 flex items-center justify-center transition-all">
                              <ChevronRight className="w-4 h-4" />
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {filteredCases.length === 0 && (
                    <div className="text-center py-16 text-slate-400">
                      No cases found matching &ldquo;{search}&rdquo;
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Graph Intelligence Tab Content */}
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
        </main>
      </div>
    </div>
  );
}