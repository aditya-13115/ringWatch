import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getGraphOverview } from "../api/graph";

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

export default function Rings() {
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [edgeFilter, setEdgeFilter] = useState("ALL");
  const [searchTerm, setSearchTerm] = useState("");
  const [zoom, setZoom] = useState(1);
  const navigate = useNavigate();

  useEffect(() => {
    getGraphOverview()
      .then((data) => {
        setGraph({
          nodes: data.nodes || [],
          edges: data.edges || [],
        });
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  }, []);

  const filteredEdges = useMemo(() => {
    if (edgeFilter === "ALL") return graph.edges;
    return graph.edges.filter((e) => e.edge_type === edgeFilter);
  }, [graph.edges, edgeFilter]);

  const filteredNodes = useMemo(() => {
    if (!searchTerm.trim()) return graph.nodes;
    const term = searchTerm.toLowerCase();
    return graph.nodes.filter((n) => n.id.toLowerCase().includes(term));
  }, [graph.nodes, searchTerm]);

  // Simple circular layout
  const positions = useMemo(() => {
    const width = 800;
    const height = 600;
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) / 2 - 100;
    const posMap = {};

    const focusNodes = graph.nodes.filter((n) => n.is_focus);
    const otherNodes = graph.nodes.filter((n) => !n.is_focus);

    focusNodes.forEach((node, i) => {
      const angle = (i / Math.max(focusNodes.length, 1)) * 2 * Math.PI;
      posMap[node.id] = {
        x: centerX + radius * 0.3 * Math.cos(angle),
        y: centerY + radius * 0.3 * Math.sin(angle),
      };
    });

    otherNodes.forEach((node, i) => {
      const angle = (i / Math.max(otherNodes.length, 1)) * 2 * Math.PI;
      posMap[node.id] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      };
    });

    return posMap;
  }, [graph.nodes]);

  if (loading) return <div className="p-6">Loading graph…</div>;
  if (error) return <div className="p-6 text-destructive">{error}</div>;
  if (!graph.nodes.length) return <div className="p-6">No graph data available.</div>;

  const handleNodeClick = (node) => {
    if (node.is_focus) {
      navigate(`/investigations/${node.id}`);
    } else {
      navigate(`/investigations/${node.id}`);
    }
  };

  const visibleNodes = searchTerm ? filteredNodes : graph.nodes;
  const visibleEdges = filteredEdges.filter(
    (e) =>
      (searchTerm
        ? visibleNodes.some((n) => n.id === e.source || n.id === e.target)
        : true)
  );

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-col md:flex-row gap-3 md:items-center">
        <input
          type="text"
          placeholder="Search account..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="border border-border rounded-md px-3 py-2 text-sm bg-background flex-1"
        />
        <div className="flex gap-2 flex-wrap">
          {["ALL", ...Object.keys(EDGE_LABELS)].map((filter) => (
            <button
              key={filter}
              onClick={() => setEdgeFilter(filter)}
              className={`px-3 py-1 rounded-full text-sm ${
                edgeFilter === filter
                  ? "bg-black text-white dark:bg-white dark:text-black"
                  : "border border-border text-muted-foreground hover:bg-accent"
              }`}
            >
              {filter === "ALL" ? "All" : EDGE_LABELS[filter]}
            </button>
          ))}
        </div>
      </div>

      {/* Zoom controls */}
      <div className="flex gap-2">
        <button
          onClick={() => setZoom((z) => Math.max(0.5, z - 0.2))}
          className="border border-border rounded px-2 py-1 text-sm"
        >
          −
        </button>
        <button
          onClick={() => setZoom((z) => Math.min(2, z + 0.2))}
          className="border border-border rounded px-2 py-1 text-sm"
        >
          +
        </button>
        <button
          onClick={() => setZoom(1)}
          className="border border-border rounded px-2 py-1 text-sm"
        >
          Reset
        </button>
      </div>

      {/* Graph SVG */}
      <div className="border border-border rounded-lg bg-card p-2 overflow-auto">
        <svg
          viewBox={`0 0 ${800 * zoom} ${600 * zoom}`}
          className="w-full min-w-[600px]"
          style={{ height: "70vh" }}
        >
          {/* Edges */}
          {visibleEdges.map((edge, i) => {
            const source = positions[edge.source];
            const target = positions[edge.target];
            if (!source || !target) return null;
            const color = EDGE_COLORS[edge.edge_type] || "var(--border)";
            return (
              <line
                key={i}
                x1={source.x * zoom}
                y1={source.y * zoom}
                x2={target.x * zoom}
                y2={target.y * zoom}
                stroke={color}
                strokeWidth={1.5}
                strokeOpacity={0.6}
              />
            );
          })}

          {/* Nodes */}
          {visibleNodes.map((node) => {
            const pos = positions[node.id];
            if (!pos) return null;
            const isHovered = hoveredNode === node.id;
            return (
              <g
                key={node.id}
                onMouseEnter={() => setHoveredNode(node.id)}
                onMouseLeave={() => setHoveredNode(null)}
                onClick={() => handleNodeClick(node)}
                style={{ cursor: "pointer" }}
              >
                <circle
                  cx={pos.x * zoom}
                  cy={pos.y * zoom}
                  r={node.is_focus ? 14 : 8}
                  fill={node.is_focus ? "var(--primary)" : "var(--card)"}
                  stroke={isHovered ? "var(--destructive)" : "var(--foreground)"}
                  strokeWidth={isHovered ? 3 : 1.5}
                />
                <text
                  x={pos.x * zoom}
                  y={pos.y * zoom + 24}
                  textAnchor="middle"
                  fontSize={12 / zoom}
                  fill="var(--foreground)"
                >
                  {node.id}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Tooltip */}
      {hoveredNode && (
        <div className="fixed top-20 right-4 bg-card border border-border rounded-md p-3 shadow-lg">
          <p className="text-sm font-medium">
            {graph.nodes.find((n) => n.id === hoveredNode)?.id}
          </p>
          <p className="text-xs text-muted-foreground">
            {graph.nodes.find((n) => n.id === hoveredNode)?.is_focus
              ? "Flagged Account"
              : "Linked Account"}
          </p>
        </div>
      )}

      {/* Legend */}
      <div className="flex flex-wrap gap-3">
        {Object.entries(EDGE_LABELS).map(([key, label]) => (
          <div key={key} className="flex items-center gap-2">
            <span
              className="inline-block w-3 h-3 rounded-full"
              style={{ backgroundColor: EDGE_COLORS[key] }}
            />
            <span className="text-xs text-muted-foreground">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}