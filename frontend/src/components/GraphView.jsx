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

const EDGE_LABELS = {
  shares_device: "Device",
  shares_address: "Address",
  shares_phone: "Phone",
  shares_payment_instrument: "Payment",
  shares_ip_prefix: "IP",
  shares_coupon: "Coupon",
};

export default function GraphView({ accountId }) {
  const [graph, setGraph] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [edgeFilter, setEdgeFilter] = useState("ALL");
  const [selectedEdge, setSelectedEdge] = useState(null);

  useEffect(() => {
    getAccountGraph(accountId)
      .then(setGraph)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [accountId]);

  const filteredEdges = useMemo(() => {
    if (!graph) return [];
    if (edgeFilter === "ALL") return graph.edges;
    return graph.edges.filter((e) => e.edge_type === edgeFilter);
  }, [graph, edgeFilter]);

  const degrees = useMemo(() => {
    const deg = {};
    if (!graph) return deg;
    graph.edges.forEach((e) => {
      deg[e.source] = (deg[e.source] || 0) + 1;
      deg[e.target] = (deg[e.target] || 0) + 1;
    });
    return deg;
  }, [graph]);

  const strongestEdge = useMemo(() => {
    if (!graph?.edges?.length) {
      return null;
    }

    return graph.edges.reduce(
      (strongest, edge) => {
        const weight = Number(edge.weight || 0);

        if (
          !strongest ||
          weight > Number(strongest.weight || 0)
        ) {
          return edge;
        }

        return strongest;
      },
      null
    );
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
    return filteredEdges.some(
      (e) =>
        (e.source === hoveredNode && e.target === nodeId) ||
        (e.target === hoveredNode && e.source === nodeId)
    );
  };

  const visibleEdges = filteredEdges.filter(
    (e) => positions[e.source] && positions[e.target]
  );

  return (
    <div className="space-y-3">
      {/* Edge type filter */}
      <div className="flex gap-2 flex-wrap">
        {["ALL", ...Object.keys(EDGE_LABELS)].map((filter) => (
          <button
            key={filter}
            onClick={() => setEdgeFilter(filter)}
            className={`px-2 py-0.5 rounded-full text-xs ${
              edgeFilter === filter
                ? "bg-black text-white dark:bg-white dark:text-black"
                : "border border-border text-muted-foreground hover:bg-accent"
            }`}
          >
            {filter === "ALL" ? "All" : EDGE_LABELS[filter]}
          </button>
        ))}
      </div>

      <div className="relative">
        <svg width="100%" viewBox={`0 0 ${width} ${height}`} className="rounded-lg border border-border bg-card">
          {/* Edges */}
          {visibleEdges.map((edge, i) => {
            const source = positions[edge.source];
            const target = positions[edge.target];
            const color = EDGE_COLORS[edge.edge_type] || "var(--border)";
            const isHighlighted =
              hoveredNode &&
              (edge.source === hoveredNode || edge.target === hoveredNode);
            const isSelected = selectedEdge === edge;

            return (
              <line
                key={i}
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                stroke={color}
                strokeWidth={isHighlighted || isSelected ? 3 : 1.5}
                strokeOpacity={isHighlighted || isSelected ? 1 : 0.5}
                strokeDasharray={edge.edge_type === "shares_coupon" ? "4" : "0"}
                onClick={() => setSelectedEdge(edge)}
                style={{ cursor: "pointer" }}
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
            const nodeRadius = node.is_focus ? 18 : Math.max(8, 6 + deg * 1.5);

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
                  r={nodeRadius}
                  fill={node.is_focus ? "var(--primary)" : "var(--card)"}
                  stroke={isHovered ? "var(--destructive)" : "var(--foreground)"}
                  strokeWidth={isHovered ? 3 : 1.5}
                />
                {node.is_focus && (
                  <text
                    x={pos.x}
                    y={pos.y + nodeRadius / 2}
                    textAnchor="middle"
                    fontSize="8"
                    fill="var(--primary-foreground)"
                  >
                    FOCUS
                  </text>
                )}
                <text
                  x={pos.x}
                  y={pos.y + nodeRadius + 12}
                  textAnchor="middle"
                  fontSize="10"
                  fill="var(--foreground)"
                >
                  {node.id}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Hover tooltip */}
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

      {/* Strongest relationship */}
      {strongestEdge && (
        <div className="rounded-md border border-border p-4 bg-card">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h4 className="text-sm font-semibold">
                Strongest Relationship
              </h4>

              <p className="text-xs text-muted-foreground mt-1">
                Highest-weight relationship in this account's
                available graph evidence.
              </p>
            </div>

            <span className="text-xs font-medium rounded-full border border-border px-2 py-1">
              {Number(strongestEdge.weight).toFixed(2)}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4 text-xs">
            <div>
              <span className="text-muted-foreground block">
                Relationship
              </span>

              <span className="font-semibold">
                {EDGE_LABELS[strongestEdge.edge_type] ||
                  strongestEdge.edge_type}
              </span>
            </div>

            <div>
              <span className="text-muted-foreground block">
                Source
              </span>

              <span className="font-mono">
                {strongestEdge.source}
              </span>
            </div>

            <div>
              <span className="text-muted-foreground block">
                Target
              </span>

              <span className="font-mono">
                {strongestEdge.target}
              </span>
            </div>
          </div>

          <p className="text-[11px] text-muted-foreground mt-3">
            Relationship weight is an initial heuristic evidence
            strength, not proof of coordinated abuse.
          </p>
        </div>
      )}

      {/* Selected edge details */}
      {selectedEdge && (
        <div className="rounded-md border border-border p-3 text-sm bg-card">
          <h4 className="font-semibold mb-1">Relationship Details</h4>
          <p className="text-muted-foreground">
            {selectedEdge.source} → {selectedEdge.target}
          </p>
          <p className="text-muted-foreground">
            Type: {EDGE_LABELS[selectedEdge.edge_type] || selectedEdge.edge_type}
          </p>
          <p className="text-muted-foreground">
            Relationship weight: {selectedEdge.weight != null ? Number(selectedEdge.weight).toFixed(2) : "—"}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Weight is an initial relationship heuristic, not proof of abuse.
          </p>
          <button
            onClick={() => setSelectedEdge(null)}
            className="mt-2 text-xs underline"
          >
            Close
          </button>
        </div>
      )}
    </div>
  );
}