"use client";

import { useState } from "react";
import {
  AlertTriangle,
  Link2,
  Network,
  CheckCircle2,
  X,
  ShieldAlert,
  Zap,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export interface CrossCaseAlert {
  alert_id: string;
  current_case_id: string;
  matched_case_id: string;
  matched_case_title: string;
  matched_entity_type: string;
  matched_entity_value: string;
  confidence_score: number;
  linking_reason: string;
}

interface CrossCaseFusionModalProps {
  open: boolean;
  onClose: () => void;
  alerts: CrossCaseAlert[];
  currentCaseTitle: string;
}

export default function CrossCaseFusionModal({
  open,
  onClose,
  alerts,
  currentCaseTitle,
}: CrossCaseFusionModalProps) {
  const [acknowledged, setAcknowledged] = useState<Set<string>>(new Set());

  if (!open || alerts.length === 0) return null;

  const primaryAlert = alerts[0];
  const confidencePercent = Math.round(primaryAlert.confidence_score * 100);

  const getConfidenceColor = (score: number) => {
    if (score >= 0.9) return "from-rose-500 to-red-600";
    if (score >= 0.8) return "from-amber-500 to-orange-600";
    return "from-yellow-400 to-amber-500";
  };

  const getEntityIcon = (type: string) => {
    switch (type) {
      case "Account":
        return "👤";
      case "Location":
        return "📍";
      case "IPAddress":
        return "🌐";
      case "Device":
        return "💻";
      case "CameraSerial":
        return "📷";
      case "VectorSimilarity":
        return "🧬";
      default:
        return "🔗";
    }
  };

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center"
      style={{ animation: "fadeIn 0.3s ease-out" }}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div
        className="relative w-full max-w-2xl mx-4 rounded-3xl overflow-hidden shadow-2xl border border-red-500/30"
        style={{
          animation: "slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1)",
          background: "linear-gradient(145deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
        }}
      >
        {/* Pulsing Alert Header */}
        <div className="relative px-6 py-4 bg-gradient-to-r from-red-900/80 to-rose-800/80 border-b border-red-500/30">
          <div className="absolute inset-0 bg-red-500/10 animate-pulse" />
          <div className="relative flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-red-500/20 border border-red-500/40 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-red-400 animate-pulse" />
              </div>
              <div>
                <h2 className="text-sm font-black tracking-wider text-red-300 uppercase">
                  Critical Cross-Case Pattern Detected
                </h2>
                <p className="text-[11px] text-red-400/80 mt-0.5">
                  Serial network engine identified {alerts.length} entity overlap{alerts.length > 1 ? "s" : ""}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-xl hover:bg-white/10 text-red-300 hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5">
          {/* Side-by-side Case Comparison */}
          <div className="grid grid-cols-2 gap-3">
            {/* Current Case */}
            <Card className="rounded-2xl border-indigo-500/30 bg-indigo-950/40 shadow-none">
              <CardContent className="p-4 space-y-2">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-indigo-400" />
                  <span className="text-[10px] font-bold tracking-wider text-indigo-400 uppercase">
                    Active Case
                  </span>
                </div>
                <p className="text-sm font-bold text-white leading-snug">
                  {currentCaseTitle}
                </p>
                <p className="text-[10px] text-indigo-300/60 font-mono">
                  {primaryAlert.current_case_id.slice(0, 8)}…
                </p>
              </CardContent>
            </Card>

            {/* Matched Case */}
            <Card className="rounded-2xl border-rose-500/30 bg-rose-950/40 shadow-none">
              <CardContent className="p-4 space-y-2">
                <div className="flex items-center gap-2">
                  <Link2 className="w-4 h-4 text-rose-400" />
                  <span className="text-[10px] font-bold tracking-wider text-rose-400 uppercase">
                    Historical / Cold Case
                  </span>
                </div>
                <p className="text-sm font-bold text-white leading-snug">
                  {primaryAlert.matched_case_title}
                </p>
                <p className="text-[10px] text-rose-300/60 font-mono">
                  {primaryAlert.matched_case_id.slice(0, 8)}…
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Matching Entity Tag */}
          <div className="p-4 rounded-2xl border border-amber-500/30 bg-amber-950/30">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-4 h-4 text-amber-400" />
              <span className="text-[10px] font-bold tracking-wider text-amber-400 uppercase">
                Matching Entity
              </span>
            </div>
            <div className="space-y-2">
              {alerts.map((alert) => (
                <div
                  key={alert.alert_id}
                  className={`flex items-center justify-between p-3 rounded-xl border transition-all ${
                    acknowledged.has(alert.alert_id)
                      ? "border-emerald-500/30 bg-emerald-950/20"
                      : "border-amber-500/20 bg-amber-950/20"
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="text-lg">{getEntityIcon(alert.matched_entity_type)}</span>
                    <div className="min-w-0">
                      <p className="text-xs font-bold text-white truncate">
                        {alert.matched_entity_type}: {alert.matched_entity_value}
                      </p>
                      <p className="text-[10px] text-slate-400 truncate">
                        {alert.linking_reason}
                      </p>
                    </div>
                  </div>
                  <Badge
                    variant={alert.confidence_score >= 0.9 ? "critical" : "high"}
                    className="text-[9px] px-2 py-0 shrink-0 ml-2"
                  >
                    {Math.round(alert.confidence_score * 100)}%
                  </Badge>
                </div>
              ))}
            </div>
          </div>

          {/* Confidence Gauge */}
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">
              Confidence
            </span>
            <div className="flex-1 h-2.5 rounded-full bg-slate-800 overflow-hidden border border-slate-700/50">
              <div
                className={`h-full rounded-full bg-gradient-to-r ${getConfidenceColor(primaryAlert.confidence_score)} transition-all duration-1000`}
                style={{
                  width: `${confidencePercent}%`,
                  animation: "gaugeExpand 1.2s cubic-bezier(0.16, 1, 0.3, 1)",
                }}
              />
            </div>
            <span className="text-sm font-black text-white tabular-nums">
              {confidencePercent}%
            </span>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2 pt-1">
            <button
              onClick={() => {
                onClose();
              }}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-2xl bg-gradient-to-r from-indigo-600 to-cyan-600 text-white text-xs font-bold hover:from-indigo-500 hover:to-cyan-500 transition-all shadow-lg shadow-indigo-500/25"
            >
              <Network className="w-3.5 h-3.5" />
              Merge Intelligence Streams
            </button>
            <button
              onClick={() => {
                onClose();
              }}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-2xl bg-white/10 border border-white/20 text-white text-xs font-bold hover:bg-white/20 transition-all"
            >
              <Link2 className="w-3.5 h-3.5" />
              Explore Linked Graph
            </button>
            <button
              onClick={() => {
                alerts.forEach((a) => setAcknowledged((prev) => new Set(prev).add(a.alert_id)));
                setTimeout(onClose, 600);
              }}
              className="px-4 py-2.5 rounded-2xl bg-emerald-600/20 border border-emerald-500/30 text-emerald-400 text-xs font-bold hover:bg-emerald-600/30 transition-all"
            >
              <CheckCircle2 className="w-3.5 h-3.5 inline mr-1" />
              Acknowledge
            </button>
          </div>
        </div>
      </div>

      {/* Keyframe animations */}
      <style jsx>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(40px) scale(0.95); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes gaugeExpand {
          from { width: 0%; }
        }
      `}</style>
    </div>
  );
}
