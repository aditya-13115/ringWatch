import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import ForceGraph2D from "react-force-graph-2d";
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
  const [graph, setGraph] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [edgeFilter, setEdgeFilter] = useState("ALL");
  const [searchTerm, setSearchTerm] = useState("");
  const [highlightId, setHighlightId] = useState(null);
  const fgRef = useRef();
  const navigate = useNavigate();

  // Fetch data
  useEffect(() => {
    getGraphOverview()
      .then((data) => {
        setGraph({
          nodes: data.nodes || [],
          links: (data.edges || []).map((e) => ({
            source: e.source,
            target: e.target,
            edge_type: e.edge_type,
          })),
        });
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  }, []);

  // Apply edge filter
  const filteredLinks = useMemo(() => {
    if (edgeFilter === "ALL") return graph.links;
    return graph.links.filter((l) => l.edge_type === edgeFilter);
  }, [graph.links, edgeFilter]);

  // Apply search filter
  const filteredNodes = useMemo(() => {
    if (!searchTerm.trim()) return graph.nodes;
    const term = searchTerm.toLowerCase();
    return graph.nodes.filter((n) => n.id.toLowerCase().includes(term));
  }, [graph.nodes, searchTerm]);

  // Compute node degrees for sizing
  const degrees = useMemo(() => {
    const deg = {};
    filteredLinks.forEach((l) => {
      deg[l.source] = (deg[l.source] || 0) + 1;
      deg[l.target] = (deg[l.target] || 0) + 1;
    });
    return deg;
  }, [filteredLinks]);

  const graphData = useMemo(() => {
    return {
      nodes: filteredNodes,
      links: filteredLinks.filter(
        (l) =>
          !searchTerm ||
          filteredNodes.some((n) => n.id === l.source || n.id === l.target)
      ),
    };
  }, [filteredNodes, filteredLinks, searchTerm]);

  // Tune force layout and automatically fit graph
  useEffect(() => {
    if (!fgRef.current || !graphData.nodes.length) return;

    const fg = fgRef.current;

    // Tune force layout
    fg.d3Force("charge").strength(-80);
    fg.d3Force("link").distance(30);
    fg.d3Force("center").strength(0.1);
    fg.d3ReheatSimulation();
    fg.zoomToFit(400);
  }, [graphData]);

  // Theme helpers
  const getCSSVar = (name) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim();

  const handleNodeClick = (node) => {
    if (node.is_focus) {
      navigate(`/investigations/${node.id}`);
    }
  };

  const handleNodeHover = (node) => setHighlightId(node ? node.id : null);

  const zoomIn = () => fgRef.current?.zoom(1.3);
  const zoomOut = () => fgRef.current?.zoom(0.7);
  const resetZoom = () => fgRef.current?.zoomToFit(400);

  if (loading) return <div className="p-6">Loading graph…</div>;
  if (error) return <div className="p-6 text-destructive">{error}</div>;
  if (!graph.nodes.length) return <div className="p-6">No graph data.</div>;

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
          onClick={zoomOut}
          className="border border-border rounded px-2 py-1 text-sm"
        >
          −
        </button>

        <button
          onClick={zoomIn}
          className="border border-border rounded px-2 py-1 text-sm"
        >
          +
        </button>

        <button
          onClick={resetZoom}
          className="border border-border rounded px-2 py-1 text-sm"
        >
          Reset
        </button>
      </div>

      {/* Force graph */}
      <div
        className="border border-border rounded-lg bg-card overflow-hidden"
        style={{ height: "70vh" }}
      >
        <ForceGraph2D
          ref={fgRef}
          graphData={graphData}
          nodeLabel={(node) => {
            const deg = degrees[node.id] || 0;
            const focus = node.is_focus
              ? "Flagged Account"
              : "Linked Account";

            return `${node.id}<br>${focus}<br>Connections: ${deg}`;
          }}
          nodeRelSize={4}
          nodeVal={(node) => Math.max(1, degrees[node.id] || 1)}
          nodeColor={(node) => (node.is_focus ? "#000000" : "#888888")}
          nodeCanvasObject={(node, ctx, globalScale) => {
            const isDark =
              document.documentElement.classList.contains("dark");

            const deg = degrees[node.id] || 1;

            const primary =
              getComputedStyle(document.documentElement)
                .getPropertyValue("--primary")
                .trim() || "#000000";

            const muted =
              getComputedStyle(document.documentElement)
                .getPropertyValue("--muted-foreground")
                .trim() || "#666666";

            const radius = Math.max(5, deg * 1.5);

            // Shadow
            ctx.beginPath();
            ctx.arc(
              node.x,
              node.y + 2,
              radius,
              0,
              2 * Math.PI,
              false
            );
            ctx.fillStyle = "rgba(0,0,0,0.15)";
            ctx.fill();

            // Main circle
            ctx.beginPath();
            ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
            ctx.fillStyle = node.is_focus ? primary : muted;
            ctx.fill();

            ctx.strokeStyle = isDark ? "#ffffff" : "#000000";
            ctx.lineWidth = 1.2 / globalScale;
            ctx.stroke();

            // Label
            const fontSize = 11 / globalScale;
            ctx.font = `${fontSize}px Inter, Sans-Serif`;
            ctx.textAlign = "center";
            ctx.textBaseline = "top";
            ctx.fillStyle = isDark ? "#ffffff" : "#000000";
            ctx.fillText(node.id, node.x, node.y + radius + 3);
          }}
          linkColor={(link) =>
            EDGE_COLORS[link.edge_type] || "#aaaaaa"
          }
          linkWidth={(link) =>
            highlightId === link.source.id ||
            highlightId === link.target.id
              ? 2
              : 1
          }
          linkDirectionalArrowLength={0}
          onNodeClick={handleNodeClick}
          onNodeHover={handleNodeHover}
          cooldownTicks={100}
        />
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3">
        {Object.entries(EDGE_LABELS).map(([key, label]) => (
          <div key={key} className="flex items-center gap-2">
            <span
              className="inline-block w-3 h-3 rounded-full"
              style={{ backgroundColor: EDGE_COLORS[key] }}
            />
            <span className="text-xs text-muted-foreground">
              {label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}