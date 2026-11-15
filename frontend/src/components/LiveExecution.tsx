"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  Cpu,
  Download,
  Radio,
  RotateCcw,
  Trash2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  executionLogsWsUrl,
  fetchExecutionLogs,
  type ExecutionLogEntry,
} from "@/lib/api";

const SENTINEL_CASE_ID = "550e8400-e29b-41d4-a716-446655440000";

interface Props {
  caseId: string;
  // Kept for parent-component API compatibility; real cross-case events arrive
  // through the pipeline and will be surfaced here when the backend emits them.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onCrossCaseMatch?: (alerts: any[]) => void;
}

function formatClock(iso?: string): string {
  if (!iso) return new Date().toLocaleTimeString("en-US", { hour12: false });
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString("en-US", { hour12: false }) +
    "." + String(d.getMilliseconds()).padStart(3, "0");
}

function levelClass(level: string): string {
  switch (level) {
    case "error":
      return "text-rose-400";
    case "warn":
      return "text-amber-300";
    case "success":
      return "text-emerald-300";
    case "debug":
      return "text-slate-500";
    default:
      return "text-slate-200";
  }
}

function sourceBadgeClass(source: string): string {
  const map: Record<string, string> = {
    gateway: "bg-indigo-500/20 text-indigo-300",
    hash: "bg-purple-500/20 text-purple-300",
    storage: "bg-slate-500/20 text-slate-300",
    celery: "bg-cyan-500/20 text-cyan-300",
    worker: "bg-sky-500/20 text-sky-300",
    extractor: "bg-fuchsia-500/20 text-fuchsia-300",
    qdrant: "bg-emerald-500/20 text-emerald-300",
    neo4j: "bg-amber-500/20 text-amber-300",
    stream: "bg-slate-500/20 text-slate-400",
    system: "bg-slate-500/20 text-slate-300",
  };
  return map[source] || "bg-slate-500/20 text-slate-300";
}

export default function LiveExecution({ caseId }: Props) {
  const [entries, setEntries] = useState<ExecutionLogEntry[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  const wsRef = useRef<WebSocket | null>(null);
  const terminalRef = useRef<HTMLDivElement | null>(null);
  const seenIds = useRef<Set<string>>(new Set());

  const isPlaceholder = !caseId || caseId === SENTINEL_CASE_ID;

  const pushEntry = useCallback((e: ExecutionLogEntry) => {
    setEntries((prev) => {
      const key = e.id || `${e.created_at || ""}|${e.source}|${e.message}`;
      if (seenIds.current.has(key)) return prev;
      seenIds.current.add(key);
      return [...prev, e];
    });
  }, []);

  // Load history whenever the case changes.
  useEffect(() => {
    if (isPlaceholder) {
      setEntries([]);
      seenIds.current = new Set();
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    seenIds.current = new Set();
    setEntries([]);

    fetchExecutionLogs(caseId, { limit: 1000 })
      .then((rows) => {
        if (cancelled) return;
        rows.forEach(pushEntry);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err?.message || "Failed to load execution logs");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [caseId, isPlaceholder, pushEntry]);

  // Live WebSocket subscription for this case.
  useEffect(() => {
    if (isPlaceholder) return;

    let shouldReconnect = true;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      try {
        const ws = new WebSocket(executionLogsWsUrl(caseId));
        wsRef.current = ws;

        ws.onopen = () => setWsConnected(true);

        ws.onmessage = (evt) => {
          try {
            const parsed = JSON.parse(evt.data);
            if (parsed && typeof parsed === "object" && "message" in parsed) {
              pushEntry(parsed as ExecutionLogEntry);
            }
          } catch {
            // Non-JSON frame — surface verbatim
            pushEntry({
              level: "info",
              source: "stream",
              message: String(evt.data),
              created_at: new Date().toISOString(),
            });
          }
        };

        ws.onerror = () => {
          setWsConnected(false);
        };

        ws.onclose = () => {
          setWsConnected(false);
          if (shouldReconnect) {
            retryTimer = setTimeout(connect, 2500);
          }
        };
      } catch (err: unknown) {
        setWsConnected(false);
        if (shouldReconnect) {
          retryTimer = setTimeout(connect, 2500);
        }
      }
    };

    connect();

    return () => {
      shouldReconnect = false;
      if (retryTimer) clearTimeout(retryTimer);
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch {
          /* ignore */
        }
        wsRef.current = null;
      }
    };
  }, [caseId, isPlaceholder, pushEntry]);

  // Keep the terminal pinned to the bottom when new rows arrive.
  useEffect(() => {
    if (!autoScroll) return;
    const el = terminalRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [entries, autoScroll]);

  // Detect when the user scrolls away from the bottom — pause auto-scroll.
  const handleScroll = () => {
    const el = terminalRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    setAutoScroll(atBottom);
  };

  const refresh = useCallback(async () => {
    if (isPlaceholder) return;
    setLoading(true);
    setError(null);
    try {
      const rows = await fetchExecutionLogs(caseId, { limit: 1000 });
      seenIds.current = new Set();
      setEntries([]);
      rows.forEach(pushEntry);
    } catch (err: unknown) {
      setError((err as Error)?.message || "Failed to reload logs");
    } finally {
      setLoading(false);
    }
  }, [caseId, isPlaceholder, pushEntry]);

  const clearLocal = () => {
    seenIds.current = new Set();
    setEntries([]);
  };

  const downloadLog = () => {
    const txt = entries
      .map((e) => `[${formatClock(e.created_at)}] [${e.level.toUpperCase()}] [${e.source}] ${e.message}`)
      .join("\n");
    const blob = new Blob([txt], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `execution-log-${caseId.slice(0, 8)}.log`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const counts = useMemo(() => {
    const c = { total: entries.length, success: 0, warn: 0, error: 0 };
    for (const e of entries) {
      if (e.level === "success") c.success++;
      else if (e.level === "warn") c.warn++;
      else if (e.level === "error") c.error++;
    }
    return c;
  }, [entries]);

  return (
    <div className="space-y-4">
      {/* Control Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-5 rounded-3xl border border-white/90 bg-white/75 backdrop-blur-xl shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-indigo-500/10 flex items-center justify-center text-indigo-600">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-slate-900">Pipeline Execution Stream</h3>
              {wsConnected ? (
                <Badge variant="low" className="text-[10px] px-2 py-0 flex items-center gap-1">
                  <Radio className="w-2.5 h-2.5" />
                  LIVE
                </Badge>
              ) : (
                <Badge variant="medium" className="text-[10px] px-2 py-0">
                  OFFLINE
                </Badge>
              )}
            </div>
            <p className="text-xs text-slate-500">
              Real events from ingestion, extraction, Qdrant & Neo4j — streamed over WebSocket, persisted per case.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-3 text-[11px] font-semibold">
            <span className="text-slate-500">
              {counts.total} events
            </span>
            {counts.success > 0 && (
              <span className="text-emerald-600">{counts.success} ok</span>
            )}
            {counts.warn > 0 && (
              <span className="text-amber-600">{counts.warn} warn</span>
            )}
            {counts.error > 0 && (
              <span className="text-rose-600">{counts.error} err</span>
            )}
          </div>

          <button
            onClick={refresh}
            disabled={loading || isPlaceholder}
            className="px-3 py-2 rounded-full border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            title="Reload history from database"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Reload
          </button>

          <button
            onClick={downloadLog}
            disabled={entries.length === 0}
            className="px-3 py-2 rounded-full border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            title="Download log as .log file"
          >
            <Download className="w-3.5 h-3.5" />
            Export
          </button>

          <button
            onClick={clearLocal}
            disabled={entries.length === 0}
            className="px-3 py-2 rounded-full border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            title="Clear view (does not delete stored history)"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Clear view
          </button>
        </div>
      </div>

      {error && (
        <div className="px-4 py-3 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
          {error}
        </div>
      )}

      {/* Terminal pane */}
      <div className="rounded-3xl border border-slate-800 bg-[#0b0f1a] shadow-inner overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2 bg-[#0e1422] border-b border-slate-800 text-[11px] text-slate-400">
          <span className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${wsConnected ? "bg-emerald-400 animate-pulse" : "bg-slate-500"}`} />
            Execution Console — case {isPlaceholder ? "—" : `${caseId.slice(0, 8)}…`}
          </span>
          <span className="flex items-center gap-2">
            <Activity className="w-3 h-3" />
            {isPlaceholder
              ? "Select a case from the workspace to attach the live stream"
              : autoScroll ? "auto-scroll on" : "auto-scroll paused"}
          </span>
        </div>

        <div
          ref={terminalRef}
          onScroll={handleScroll}
          className="font-mono text-[12px] leading-[1.55] text-slate-200 p-4 h-[420px] overflow-y-auto"
        >
          {isPlaceholder ? (
            <p className="text-slate-500 italic">
              No case selected. Open a case workspace to view its execution timeline.
            </p>
          ) : loading && entries.length === 0 ? (
            <p className="text-slate-500 italic">Loading execution history for this case…</p>
          ) : entries.length === 0 ? (
            <p className="text-slate-500 italic">
              No events yet. Upload evidence to this case and the real pipeline logs will stream in here.
            </p>
          ) : (
            entries.map((e, i) => (
              <div
                key={e.id || `${i}-${e.created_at}`}
                className="flex items-start gap-3 py-[2px] border-b border-slate-800/40 last:border-b-0"
              >
                <span className="shrink-0 text-slate-500 text-[11px] tabular-nums w-24">
                  {formatClock(e.created_at)}
                </span>
                <span
                  className={`shrink-0 text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${sourceBadgeClass(e.source)}`}
                  title={`source: ${e.source}`}
                >
                  {e.source}
                </span>
                <span className={`shrink-0 text-[10px] font-bold uppercase w-14 ${levelClass(e.level)}`}>
                  {e.level}
                </span>
                <span className={`flex-1 break-words ${levelClass(e.level)}`}>
                  {e.message}
                  {e.evidence_id && (
                    <span className="text-slate-500 ml-2">
                      · ev={e.evidence_id.slice(0, 8)}…
                    </span>
                  )}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
