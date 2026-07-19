import type { ScoredComment } from "@/hooks/useWebSocket";

export type GraphNodeType = "user" | "comment";

export type GraphNode = {
  id: string;
  nodeType: GraphNodeType;
  label: string;
  toxicity?: number;
  timestamp?: string;
  text?: string;
};

export type GraphLinkType = "POSTED" | "REPLIES_TO";

export type GraphLink = {
  source: string;
  target: string;
  linkType: GraphLinkType;
};

export type GraphData = {
  nodes: GraphNode[];
  links: GraphLink[];
};

export const DEFAULT_MAX_GRAPH_NODES = 200;

export function userNodeId(userId: string): string {
  return `user:${userId}`;
}

export function commentNodeId(eventId: string): string {
  return `comment:${eventId}`;
}

function linkKey(link: GraphLink): string {
  return `${link.source}|${link.target}|${link.linkType}`;
}

export function mapPayloadToGraph(payload: ScoredComment): GraphData {
  const userId = userNodeId(payload.user_id);
  const commentId = commentNodeId(payload.event_id);
  const toxicity = payload.scores.toxicity ?? 0;

  const nodes: GraphNode[] = [
    {
      id: userId,
      nodeType: "user",
      label: payload.user_id,
    },
    {
      id: commentId,
      nodeType: "comment",
      label: payload.event_id.slice(0, 8),
      toxicity,
      timestamp: payload.timestamp,
      text: payload.text,
    },
  ];

  const links: GraphLink[] = [
    {
      source: userId,
      target: commentId,
      linkType: "POSTED",
    },
  ];

  if (payload.reply_to_id) {
    const parentId = commentNodeId(payload.reply_to_id);
    nodes.push({
      id: parentId,
      nodeType: "comment",
      label: payload.reply_to_id.slice(0, 8),
    });
    links.push({
      source: commentId,
      target: parentId,
      linkType: "REPLIES_TO",
    });
  }

  return { nodes, links };
}

export function mergeGraphData(existing: GraphData, delta: GraphData): GraphData {
  const nodeMap = new Map<string, GraphNode>();
  for (const node of existing.nodes) {
    nodeMap.set(node.id, node);
  }
  for (const node of delta.nodes) {
    const prev = nodeMap.get(node.id);
    nodeMap.set(node.id, prev ? { ...prev, ...node } : node);
  }

  const linkMap = new Map<string, GraphLink>();
  for (const link of existing.links) {
    linkMap.set(linkKey(link), link);
  }
  for (const link of delta.links) {
    linkMap.set(linkKey(link), link);
  }

  return {
    nodes: Array.from(nodeMap.values()),
    links: Array.from(linkMap.values()),
  };
}

export function enforceGraphLimits(
  data: GraphData,
  maxNodes: number = DEFAULT_MAX_GRAPH_NODES,
): GraphData {
  const commentNodes = data.nodes.filter((node) => node.nodeType === "comment");
  if (commentNodes.length <= maxNodes) {
    return data;
  }

  const sortedComments = [...commentNodes].sort((a, b) => {
    const aTime = a.timestamp ? Date.parse(a.timestamp) : 0;
    const bTime = b.timestamp ? Date.parse(b.timestamp) : 0;
    if (aTime !== bTime) return aTime - bTime;
    return a.id.localeCompare(b.id);
  });

  const evictedIds = new Set(
    sortedComments.slice(0, commentNodes.length - maxNodes).map((node) => node.id),
  );

  const nodes = data.nodes.filter((node) => !evictedIds.has(node.id));
  const nodeIds = new Set(nodes.map((node) => node.id));

  const links = data.links.filter(
    (link) => nodeIds.has(link.source) && nodeIds.has(link.target),
  );

  const linkedUserIds = new Set<string>();
  for (const link of links) {
    if (link.linkType === "POSTED") {
      linkedUserIds.add(link.source);
    }
  }

  const prunedNodes = nodes.filter(
    (node) => node.nodeType === "comment" || linkedUserIds.has(node.id),
  );

  return { nodes: prunedNodes, links };
}
