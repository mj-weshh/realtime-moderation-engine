"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  DEFAULT_MAX_GRAPH_NODES,
  enforceGraphLimits,
  GraphData,
  GraphNode,
  mergeGraphData,
  mapPayloadToGraph,
} from "@/lib/mapPayloadToGraph";
import { ScoredComment, useWebSocket } from "@/hooks/useWebSocket";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

const EMPTY_GRAPH: GraphData = { nodes: [], links: [] };

function getCommentColor(toxicity: number): string {
  if (toxicity >= 0.8) return "#f87171";
  if (toxicity >= 0.5) return "#fcd34d";
  return "#94a3b8";
}

function getNodeColor(node: GraphNode): string {
  if (node.nodeType === "user") return "#06b6d4";
  return getCommentColor(node.toxicity ?? 0);
}

function getNodeSize(node: GraphNode): number {
  if (node.nodeType === "user") return 4;
  return 2 + (node.toxicity ?? 0) * 6;
}

export default function NetworkGraph() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 640, height: 480 });
  const [graphData, setGraphData] = useState<GraphData>(EMPTY_GRAPH);

  const handleMessage = useCallback((payload: ScoredComment) => {
    setGraphData((prev) => {
      const merged = mergeGraphData(prev, mapPayloadToGraph(payload));
      return enforceGraphLimits(merged, DEFAULT_MAX_GRAPH_NODES);
    });
  }, []);

  const { status } = useWebSocket({ onMessage: handleMessage });

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0) {
        setDimensions({ width, height });
      }
    });

    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={containerRef} className="relative min-h-0 flex-1">
      {status === "open" && graphData.nodes.length === 0 && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <p className="text-sm text-command-muted">
            Waiting for flagged comments...
          </p>
        </div>
      )}
      {status === "connecting" && (
        <div className="pointer-events-none absolute inset-x-0 top-0 z-10 border-b border-command-border bg-command-surface/90 px-4 py-2 text-xs text-command-muted">
          Connecting to graph stream...
        </div>
      )}
      {status === "error" && (
        <div className="pointer-events-none absolute inset-x-0 top-0 z-10 border-b border-red-500/40 bg-red-950/30 px-4 py-2 text-xs text-red-400">
          WebSocket connection error
        </div>
      )}
      <ForceGraph2D
        width={dimensions.width}
        height={dimensions.height}
        graphData={graphData}
        backgroundColor="rgba(15, 20, 25, 0)"
        nodeLabel={(node) => {
          const graphNode = node as GraphNode;
          if (graphNode.nodeType === "user") return graphNode.label;
          const toxicity = graphNode.toxicity ?? 0;
          return `${graphNode.label}\nToxicity: ${(toxicity * 100).toFixed(0)}%`;
        }}
        nodeColor={(node) => getNodeColor(node as GraphNode)}
        nodeVal={(node) => getNodeSize(node as GraphNode)}
        linkColor={() => "rgba(148, 163, 184, 0.35)"}
        linkDirectionalArrowLength={3.5}
        linkDirectionalArrowRelPos={1}
        linkWidth={(link) => (link.linkType === "REPLIES_TO" ? 1.5 : 1)}
        nodeCanvasObject={(node, ctx, globalScale) => {
          const graphNode = node as GraphNode;
          const size = getNodeSize(graphNode);
          const radius = Math.sqrt(size) * 4;
          const x = node.x ?? 0;
          const y = node.y ?? 0;

          if (
            graphNode.nodeType === "comment" &&
            (graphNode.toxicity ?? 0) >= 0.8
          ) {
            ctx.beginPath();
            ctx.arc(x, y, radius * 1.8, 0, 2 * Math.PI);
            ctx.fillStyle = "rgba(248, 113, 113, 0.25)";
            ctx.fill();
          }

          ctx.beginPath();
          ctx.arc(x, y, radius, 0, 2 * Math.PI);
          ctx.fillStyle = getNodeColor(graphNode);
          ctx.fill();

          if (globalScale > 1.2 && graphNode.nodeType === "user") {
            ctx.font = `${10 / globalScale}px sans-serif`;
            ctx.fillStyle = "#94a3b8";
            ctx.textAlign = "center";
            ctx.fillText(graphNode.label, x, y + radius + 8 / globalScale);
          }
        }}
        nodeCanvasObjectMode={() => "replace"}
      />
    </div>
  );
}
