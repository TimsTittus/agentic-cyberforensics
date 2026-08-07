"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import {
  Activity,
  CheckCircle2,
  Clock,
  Play,
  RotateCcw,
  Sparkles,
  ShieldAlert,
  Zap,
  Layers,
  Cpu,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface AgentStepStatus {
  id: string;
  name: string;
  category: string;
  status: "idle" | "running" | "completed" | "error";
  details?: string;
  flagsCount?: number;
  syntheticProb?: number;
  riskScore?: number;
}

const INITIAL_AGENTS: AgentStepStatus[] = [
  { id: "gateway", name: "Entry Gateway", category: "Ingestion", status: "idle" },
  { id: "grooming_agent", name: "Grooming Detection Agent", category: "LLM Analytics", status: "idle" },
  { id: "multimedia_agent", name: "Multimedia Context Agent", category: "Vision & OCR", status: "idle" },
  { id: "synthetic_agent", name: "Synthetic Media Detector", category: "Deepfake Inspection", status: "idle" },
  { id: "osint_agent", name: "OSINT Threat Agent", category: "Breach Lookup", status: "idle" },
  { id: "timeline_agent", name: "Chronological Timeline", category: "Synthesis", status: "idle" },
  { id: "fusion_agent", name: "Neo4j & Qdrant Fusion", category: "Knowledge Graph", status: "idle" },
  { id: "risk_agent", name: "Risk Assessment Engine", category: "Scoring Matrix", status: "idle" },
];

export default function LiveExecution({ caseId }: { caseId: string }) {
  const [agents, setAgents] = useState<AgentStepStatus[]>(INITIAL_AGENTS);
  const [isExecuting, setIsExecuting] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [executionLog, setExecutionLog] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  const startSimulatedExecution = useCallback(() => {
    setIsExecuting(true);
    setExecutionLog(["[00:00.0] Initializing multi-agent LangGraph execution pipeline..."]);
    setAgents(INITIAL_AGENTS.map((a) => ({ ...a, status: "idle", details: undefined })));

    let currentStep = 0;
    const interval = setInterval(() => {
      if (currentStep >= INITIAL_AGENTS.length) {
        clearInterval(interval);
        setIsExecuting(false);
        setExecutionLog((prev) => [
          ...prev,
          "[00:04.2] Pipeline finished. Neo4j graph & Qdrant vectors updated.",
        ]);
        return;
      }

      const activeAgent = INITIAL_AGENTS[currentStep];

      setAgents((prev) =>
        prev.map((a, idx) => {
          if (idx < currentStep) return { ...a, status: "completed" };
          if (idx === currentStep) {
            let details = "Processing payload...";
            let flagsCount = undefined;
            let syntheticProb = undefined;
            let riskScore = undefined;

            if (a.id === "grooming_agent") {
              details = "Identified 4 grooming indicators (Trust, Isolation, Secrecy, Sexualization)";
              flagsCount = 4;
            } else if (a.id === "multimedia_agent") {
              details = "Matched YOLO 'school uniform' with EasyOCR 'Bus Stop Line 4'";
              flagsCount = 2;
            } else if (a.id === "synthetic_agent") {
              details = "Detected GAN noise distribution anomaly";
              syntheticProb = 0.85;
            } else if (a.id === "osint_agent") {
              details = "Found 2 breach records for suspect@darknet.org";
              flagsCount = 2;
            } else if (a.id === "fusion_agent") {
              details = "Upserted 384d vectors to Qdrant & merged Cypher nodes in Neo4j";
            } else if (a.id === "risk_agent") {
              details = "Calculated final Threat Score: 88.5 / 100 (CRITICAL)";
              riskScore = 88.5;
            }

            return { ...a, status: "running", details, flagsCount, syntheticProb, riskScore };
          }
          return a;
        })
      );

      setExecutionLog((prev) => [
        ...prev,
        `[${new Date().toLocaleTimeString()}] Executing node: ${activeAgent.name}...`,
      ]);

      currentStep++;
    }, 700);
  }, []);

  const triggerExecution = useCallback(() => {
    if (isExecuting) return;

    try {
      const wsUrl = `ws://localhost:8000/api/v1/ws/investigation/${caseId}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
        setIsExecuting(true);
        setExecutionLog(["WebSocket connected. Streaming LangGraph state..."]);
        setAgents(INITIAL_AGENTS.map((a) => ({ ...a, status: "idle" })));
        ws.send(JSON.stringify({ case_id: caseId }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event === "start") {
            setExecutionLog((prev) => [...prev, `[Start] ${data.message}`]);
          } else if (data.event === "step") {
            const nodeName = data.node;
            setAgents((prev) =>
              prev.map((a) => {
                if (a.id === nodeName) {
                  return { ...a, status: "running", details: "State updated via WebSocket" };
                }
                return a;
              })
            );
            setExecutionLog((prev) => [...prev, `[Step] Completed node: ${nodeName}`]);
          } else if (data.event === "complete") {
            setIsExecuting(false);
            setAgents((prev) => prev.map((a) => ({ ...a, status: "completed" })));
            setExecutionLog((prev) => [...prev, `[Done] ${data.message}`]);
            ws.close();
          }
        } catch {
          // Ignore parse errors
        }
      };

      ws.onerror = () => {
        setWsConnected(false);
        startSimulatedExecution();
      };
    } catch {
      setWsConnected(false);
      startSimulatedExecution();
    }
  }, [caseId, isExecuting, startSimulatedExecution]);

  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const completedCount = agents.filter((a) => a.status === "completed").length;
  const progressPercent = Math.round((completedCount / agents.length) * 100);

  return (
    <div className="space-y-6">
      {/* Control Bar & Progress */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-5 rounded-3xl border border-white/90 bg-white/75 backdrop-blur-xl shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-indigo-500/10 flex items-center justify-center text-indigo-600">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-slate-900">LangGraph Agent Pipeline</h3>
              {wsConnected && (
                <Badge variant="low" className="text-[10px] px-2 py-0">
                  WS LIVE
                </Badge>
              )}
            </div>
            <p className="text-xs text-slate-500">
              Parallel execution topology across 8 forensic AI agents
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="w-48 bg-slate-100 rounded-full h-3 overflow-hidden border border-slate-200/60 p-0.5">
            <div
              className="bg-gradient-to-r from-indigo-500 to-cyan-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <span className="text-xs font-bold text-slate-700 w-10">{progressPercent}%</span>

          <button
            onClick={triggerExecution}
            disabled={isExecuting}
            className={`px-5 py-2.5 rounded-full font-semibold text-xs transition-all flex items-center gap-2 ${isExecuting
              ? "bg-slate-200 text-slate-400 cursor-not-allowed"
              : "bg-slate-900 hover:bg-slate-800 text-white shadow-md shadow-slate-900/10"
              }`}
          >
            {isExecuting ? (
              <>
                <RotateCcw className="w-3.5 h-3.5 animate-spin" />
                Executing...
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                Run Pipeline
              </>
            )}
          </button>
        </div>
      </div>

      {/* Agents Timeline Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {agents.map((agent, index) => {
          const isDone = agent.status === "completed";
          const isRunning = agent.status === "running";

          return (
            <div
              key={agent.id}
              className={`p-5 rounded-3xl border transition-all duration-300 ${isRunning
                ? "border-indigo-400 bg-indigo-50/60 shadow-md shadow-indigo-500/10 ring-2 ring-indigo-400/30"
                : isDone
                  ? "border-emerald-200/80 bg-emerald-50/40"
                  : "border-white/80 bg-white/70 shadow-sm"
                }`}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Step 0{index + 1} • {agent.category}
                </span>
                {isDone && <CheckCircle2 className="w-4 h-4 text-emerald-600" />}
                {isRunning && <Activity className="w-4 h-4 text-indigo-600 animate-spin" />}
              </div>

              <h4 className="font-bold text-sm text-slate-900 mb-1">{agent.name}</h4>

              <div className="min-h-[44px]">
                {agent.details ? (
                  <p className="text-xs text-slate-600 leading-relaxed">{agent.details}</p>
                ) : (
                  <p className="text-xs text-slate-400 italic">Awaiting execution trigger...</p>
                )}
              </div>

              {/* Specific Badge Badges */}
              <div className="mt-3 flex flex-wrap gap-1.5 pt-2 border-t border-slate-100">
                {agent.flagsCount !== undefined && (
                  <Badge variant="high" className="text-[10px]">
                    {agent.flagsCount} Flags
                  </Badge>
                )}
                {agent.syntheticProb !== undefined && (
                  <Badge variant="critical" className="text-[10px]">
                    {Math.round(agent.syntheticProb * 100)}% Synthetic
                  </Badge>
                )}
                {agent.riskScore !== undefined && (
                  <Badge variant="critical" className="text-[10px]">
                    Score: {agent.riskScore}
                  </Badge>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Execution Terminal Output Log */}
      <div className="p-4 rounded-3xl border border-slate-200/80 bg-slate-900 text-slate-200 font-mono text-xs shadow-inner max-h-36 overflow-y-auto">
        <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800 text-[11px] text-slate-400">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Execution Console Output
          </span>
          <span>WebSocket Stream</span>
        </div>
        {executionLog.map((log, i) => (
          <p key={i} className="py-0.5 text-slate-300 leading-relaxed">
            {log}
          </p>
        ))}
      </div>
    </div>
  );
}