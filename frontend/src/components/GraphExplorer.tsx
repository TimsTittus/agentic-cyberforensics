"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { fetchGraphData, type GraphData } from "@/lib/api";

interface NodeObject {
  id: string;
  label: string;
  type: string;
  color?: string;
  x?: number;
  y?: number;
}

interface LinkObject {
  source: string | NodeObject;
  target: string | NodeObject;
  label: string;
}

export default function GraphExplorer({ caseId }: { caseId?: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [graphData, setGraphData] = useState<{ nodes: NodeObject[]; links: LinkObject[] }>({
    nodes: [],
    links: [],
  });
  const [selectedNode, setSelectedNode] = useState<NodeObject | null>(null);
  const [ForceGraph, setForceGraph] = useState<any>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 });

  useEffect(() => {
    import("react-force-graph-2d").then((mod) => {
      setForceGraph(() => mod.default);
    });
  }, []);

  useEffect(() => {
    fetchGraphData(caseId).then((data: GraphData) => {
      // Map node colors to bright harmonious palette suitable for clean light canvas
      const lightNodeColors: Record<string, string> = {
        Suspect: "#f43f5e",
        Victim: "#f59e0b",
        Account: "#6366f1",
        Location: "#10b981",
        "IP Address": "#06b6d4",
        Evidence: "#ec4899",
      };

      setGraphData({
        nodes: data.nodes.map((n) => ({
          ...n,
          color: lightNodeColors[n.type] || "#6366f1",
        })),
        links: data.links.map((l) => ({ ...l })),
      });
    });
  }, [caseId]);

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.offsetWidth,
          height: containerRef.current.offsetHeight,
        });
      }
    };
    updateDimensions();
    window.addEventListener("resize", updateDimensions);
    return () => window.removeEventListener("resize", updateDimensions);
  }, []);

  const handleNodeClick = useCallback((node: NodeObject) => {
    setSelectedNode(node);
  }, []);

  const nodeCanvasObject = useCallback(
    (node: NodeObject, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const label = node.label || node.id;
      const fontSize = Math.max(12 / globalScale, 3);
      const nodeRadius = node.type === "Suspect" ? 8 : node.type === "Victim" ? 7 : 5;
      const isSelected = selectedNode?.id === node.id;

      // Soft pastel glow effect
      if (isSelected || node.type === "Suspect") {
        ctx.beginPath();
        ctx.arc(node.x || 0, node.y || 0, nodeRadius + 5, 0, 2 * Math.PI);
        ctx.fillStyle = `${node.color || "#6366f1"}25`;
        ctx.fill();
      }

      // Node circle
      ctx.beginPath();
      ctx.arc(node.x || 0, node.y || 0, nodeRadius, 0, 2 * Math.PI);
      ctx.fillStyle = node.color || "#6366f1";
      ctx.fill();

      if (isSelected) {
        ctx.strokeStyle = "#0f172a";
        ctx.lineWidth = 2.5 / globalScale;
        ctx.stroke();
      }

      // Label text
      ctx.font = `600 ${fontSize}px Inter, sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillStyle = "#334155";
      ctx.fillText(label, node.x || 0, (node.y || 0) + nodeRadius + 4);
    },
    [selectedNode]
  );

  const linkCanvasObject = useCallback(
    (link: LinkObject, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const src = link.source as NodeObject;
      const tgt = link.target as NodeObject;
      if (!src.x || !src.y || !tgt.x || !tgt.y) return;

      // Edge line
      ctx.beginPath();
      ctx.moveTo(src.x, src.y);
      ctx.lineTo(tgt.x, tgt.y);
      ctx.strokeStyle = "rgba(148, 163, 184, 0.4)";
      ctx.lineWidth = 1.4 / globalScale;
      ctx.stroke();

      // Directional Arrow
      const angle = Math.atan2(tgt.y - src.y, tgt.x - src.x);
      const arrowLen = 6 / globalScale;
      const midX = (src.x + tgt.x) / 2;
      const midY = (src.y + tgt.y) / 2;

      ctx.beginPath();
      ctx.moveTo(midX, midY);
      ctx.lineTo(
        midX - arrowLen * Math.cos(angle - Math.PI / 6),
        midY - arrowLen * Math.sin(angle - Math.PI / 6)
      );
      ctx.moveTo(midX, midY);
      ctx.lineTo(
        midX - arrowLen * Math.cos(angle + Math.PI / 6),
        midY - arrowLen * Math.sin(angle + Math.PI / 6)
      );
      ctx.strokeStyle = "rgba(100, 116, 139, 0.6)";
      ctx.stroke();

      // Label
      const fontSize = Math.max(9 / globalScale, 2);
      ctx.font = `500 ${fontSize}px Inter, sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = "#64748b";
      ctx.fillText(link.label, midX, midY - 6 / globalScale);
    },
    []
  );

  const typeColors: Record<string, string> = {
    Suspect: "#f43f5e",
    Victim: "#f59e0b",
    Account: "#6366f1",
    Location: "#10b981",
    "IP Address": "#06b6d4",
    Evidence: "#ec4899",
  };

  return (
    <div className="flex flex-col h-full">
      {/* Legend */}
      <div className="flex flex-wrap gap-4 mb-4 px-1">
        {Object.entries(typeColors).map(([type, color]) => (
          <div key={type} className="flex items-center gap-2 text-xs font-medium text-slate-600">
            <span
              className="w-3 h-3 rounded-full inline-block shadow-sm"
              style={{ backgroundColor: color }}
            />
            {type}
          </div>
        ))}
      </div>

      {/* Graph Canvas Container */}
      <div
        ref={containerRef}
        className="flex-1 min-h-[400px] rounded-2xl border border-slate-200/80 bg-slate-50/70 overflow-hidden relative shadow-inner"
      >
        {ForceGraph && graphData.nodes.length > 0 && (
          <ForceGraph
            graphData={graphData}
            width={dimensions.width}
            height={dimensions.height}
            nodeCanvasObject={nodeCanvasObject}
            linkCanvasObject={linkCanvasObject}
            onNodeClick={handleNodeClick}
            backgroundColor="transparent"
            nodeRelSize={6}
            linkDirectionalArrowLength={4}
            d3AlphaDecay={0.02}
            d3VelocityDecay={0.3}
            cooldownTime={3000}
            enableNodeDrag={true}
            enableZoomInteraction={true}
          />
        )}
      </div>

      {/* Selected Node Info Card */}
      {selectedNode && (
        <div className="mt-4 p-4 rounded-2xl border border-white bg-white/90 shadow-[0_4px_20px_rgba(0,0,0,0.03)] backdrop-blur-md transition-all">
          <div className="flex items-center gap-2.5 text-sm">
            <span
              className="w-3.5 h-3.5 rounded-full shadow-sm"
              style={{ backgroundColor: selectedNode.color }}
            />
            <span className="text-slate-900 font-bold">{selectedNode.type}</span>
            <span className="text-slate-300">•</span>
            <span className="text-slate-700 font-mono">{selectedNode.label}</span>
          </div>
        </div>
      )}
    </div>
  );
}