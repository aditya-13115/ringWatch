import { useEffect, useState } from "react";
import { getAccountGraph } from "../api/account";

export default function GraphView({ accountId }) {
  const [graph, setGraph] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getAccountGraph(accountId)
      .then(setGraph)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [accountId]);

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
  const radius = Math.min(width, height) / 2 - 40;

  const positions = {};
  positions[focus.id] = { x: centerX, y: centerY };

  others.forEach((node, index) => {
    const angle = (index / Math.max(others.length, 1)) * 2 * Math.PI;
    positions[node.id] = {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    };
  });

  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} className="rounded-lg border border-border bg-card">
      {graph.edges.map((edge, i) => {
        const source = positions[edge.source];
        const target = positions[edge.target];
        if (!source || !target) return null;
        return (
          <line
            key={i}
            x1={source.x}
            y1={source.y}
            x2={target.x}
            y2={target.y}
            stroke="var(--foreground)"
            strokeWidth="1"
            strokeDasharray={edge.edge_type === "shares_coupon" ? "4" : "0"}
          />
        );
      })}
      {graph.nodes.map((node) => {
        const pos = positions[node.id];
        if (!pos) return null;
        return (
          <g key={node.id}>
            <circle
              cx={pos.x}
              cy={pos.y}
              r={node.is_focus ? 18 : 12}
              fill={node.is_focus ? "var(--primary)" : "var(--card)"}
              stroke="var(--foreground)"
              strokeWidth="2"
            />
            <text x={pos.x} y={pos.y + 30} textAnchor="middle" fontSize="10" fill="var(--foreground)">
              {node.id}
            </text>
            {node.is_focus && (
              <text x={pos.x} y={pos.y + 5} textAnchor="middle" fontSize="8" fill="var(--primary-foreground)">
                FOCUS
              </text>
            )}
          </g>
        );
      })}
      {graph.edges.map((edge, i) => {
        const source = positions[edge.source];
        const target = positions[edge.target];
        if (!source || !target) return null;
        const midX = (source.x + target.x) / 2;
        const midY = (source.y + target.y) / 2;
        return (
          <text key={`label-${i}`} x={midX} y={midY} fontSize="8" textAnchor="middle" fill="var(--muted-foreground)">
            {edge.edge_type.replace("shares_", "")}
          </text>
        );
      })}
    </svg>
  );
}