import { useEffect, useMemo, useState } from "react";
import { getAccountGraph } from "../api/account";

const EDGE_COLORS = {
  shares_device: "#3b82f6",
  shares_address: "#10b981",
  shares_phone: "#f59e0b",
  shares_payment_instrument: "#ef4444",
  shares_ip_prefix: "#8b5cf6",
  shares_coupon: "#ec4899",
};

export default function GraphView({ accountId }) {
  const [graph, setGraph] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);

  useEffect(() => {
    getAccountGraph(accountId)
      .then(setGraph)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [accountId]);

  // Compute degree for each node
  const degrees = useMemo(() => {
    const deg = {};
    if (!graph) return deg;
    graph.edges.forEach((e) => {
      deg[e.source] = (deg[e.source] || 0) + 1;
      deg[e.target] = (deg[e.target] || 0) + 1;
    });
    return deg;
  }, [graph]);

  if (loading) return <div className="text-sm text-muted-foreground">Loading graph…</div>;
  if (error) return <div className="text-destructive">{error}</div>;
  if (!graph || graph.nodes.length === 0) {
    return <div className="text-sm text-muted-foreground">No graph relationships.</div>;
  }

  const focus = graph.nodes.find((n) => n.is_focus) || graph.nodes[0];
  const others = graph.nodes.filter((n) => n.id !== focus.id);

  const width = 400;
  const height = 300;
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) / 2 - 50;

  const positions = {};
  positions[focus.id] = { x: centerX, y: centerY };

  others.forEach((node, index) => {
    const angle = (index / Math.max(others.length, 1)) * 2 * Math.PI;
    positions[node.id] = {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    };
  });

  const isConnectedToHover = (nodeId) => {
    if (!hoveredNode) return false;
    return graph.edges.some(
      (e) =>
        (e.source === hoveredNode && e.target === nodeId) ||
        (e.target === hoveredNode && e.source === nodeId)
    );
  };

  return (
    <div className="relative">
      <svg width="100%" viewBox={`0 0 ${width} ${height}`} className="rounded-lg border border-border bg-card">
        {/* Edges */}
        {graph.edges.map((edge, i) => {
          const source = positions[edge.source];
          const target = positions[edge.target];
          if (!source || !target) return null;
          const color = EDGE_COLORS[edge.edge_type] || "var(--border)";
          const isHighlighted =
            hoveredNode &&
            (edge.source === hoveredNode || edge.target === hoveredNode);

          return (
            <line
              key={i}
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              stroke={color}
              strokeWidth={isHighlighted ? 2.5 : 1.5}
              strokeOpacity={isHighlighted ? 1 : 0.5}
              strokeDasharray={edge.edge_type === "shares_coupon" ? "4" : "0"}
            />
          );
        })}

        {/* Nodes */}
        {graph.nodes.map((node) => {
          const pos = positions[node.id];
          if (!pos) return null;
          const deg = degrees[node.id] || 0;
          const isHovered = hoveredNode === node.id;
          const isDimmed = hoveredNode && !isHovered && !isConnectedToHover(node.id);
          const radius = node.is_focus ? 18 : Math.max(8, 6 + deg * 1.5);

          return (
            <g
              key={node.id}
              onMouseEnter={() => setHoveredNode(node.id)}
              onMouseLeave={() => setHoveredNode(null)}
              style={{ cursor: "pointer", opacity: isDimmed ? 0.3 : 1 }}
            >
              <circle
                cx={pos.x}
                cy={pos.y}
                r={radius}
                fill={node.is_focus ? "var(--primary)" : "var(--card)"}
                stroke={isHovered ? "var(--destructive)" : "var(--foreground)"}
                strokeWidth={isHovered ? 3 : 1.5}
              />
              {node.is_focus && (
                <text
                  x={pos.x}
                  y={pos.y + radius / 2}
                  textAnchor="middle"
                  fontSize="8"
                  fill="var(--primary-foreground)"
                >
                  FOCUS
                </text>
              )}
              <text
                x={pos.x}
                y={pos.y + radius + 12}
                textAnchor="middle"
                fontSize="10"
                fill="var(--foreground)"
              >
                {node.id}
              </text>
            </g>
          );
        })}

        {/* Edge labels only on hover or for few edges */}
        {hoveredNode &&
          graph.edges
            .filter(
              (e) => e.source === hoveredNode || e.target === hoveredNode
            )
            .slice(0, 3)
            .map((edge, i) => {
              const source = positions[edge.source];
              const target = positions[edge.target];
              if (!source || !target) return null;
              const midX = (source.x + target.x) / 2;
              const midY = (source.y + target.y) / 2;
              return (
                <text
                  key={`label-${i}`}
                  x={midX}
                  y={midY - 5}
                  textAnchor="middle"
                  fontSize="7"
                  fill="var(--muted-foreground)"
                >
                  {edge.edge_type.replace("shares_", "")}
                </text>
              );
            })}
      </svg>

      {/* Tooltip */}
      {hoveredNode && (
        <div className="absolute top-0 right-0 bg-card border border-border rounded-md p-2 shadow-lg text-xs">
          <p className="font-medium">{hoveredNode}</p>
          <p className="text-muted-foreground">
            {graph.nodes.find((n) => n.id === hoveredNode)?.is_focus
              ? "Flagged Account"
              : "Linked Account"}
          </p>
          <p className="text-muted-foreground">
            Connections: {degrees[hoveredNode] || 0}
          </p>
        </div>
      )}
    </div>
  );
}