import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import ForceGraph2D from "react-force-graph-2d";
import { getGraphOverview } from "../api/graph";
import { getQueue } from "../api/queue";

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

const COMMUNITY_COLORS = [
  "#3b82f6",
  "#10b981",
  "#f59e0b",
  "#8b5cf6",
  "#ec4899",
  "#06b6d4",
  "#84cc16",
  "#f97316",
  "#a855f7",
  "#14b8a6",
  "#eab308",
  "#6366f1",
  "#22c55e",
  "#ef4444",
  "#0ea5e9",
];

export default function Rings() {
  const [graph, setGraph] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [edgeFilter, setEdgeFilter] = useState("ALL");
  const [searchTerm, setSearchTerm] = useState("");
  const [highlightId, setHighlightId] = useState(null);
  const [queue, setQueue] = useState([]);
  const [communityLimit, setCommunityLimit] = useState(3);
  const [selectedCommunityIndex, setSelectedCommunityIndex] = useState(0);

  const fgRef = useRef();
  const initialFitDone = useRef(false);

  const navigate = useNavigate();

  // Fetch data
  useEffect(() => {
    Promise.all([getGraphOverview(), getQueue(1000)])
      .then(([data, queueData]) => {
        setGraph({
          nodes: data.nodes || [],
          links: (data.edges || []).map((e) => ({
            source: e.source,
            target: e.target,
            edge_type: e.edge_type,
            weight: e.weight,
          })),
        });

        setQueue(queueData.accounts || []);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  }, []);

  /*
   * Build communities from the backend-provided community_id when available.
   * This keeps the UI aligned with the persisted community assignments instead
   * of silently recomputing a different connected-component definition.
   * A connected-component fallback is retained for older artifacts.
   */
  const communities = useMemo(() => {
    const queueById = new Map(
      queue.map((account) => [account.account_id, account])
    );

    const hasCommunityAssignments = graph.nodes.some(
      (node) => node.community_id !== null && node.community_id !== undefined
    );

    const groups = new Map();

    if (hasCommunityAssignments) {
      graph.nodes.forEach((node) => {
        const key = String(node.community_id ?? `node:${node.id}`);
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(node.id);
      });
    } else {
      const adjacency = new Map();
      graph.nodes.forEach((node) => adjacency.set(node.id, new Set()));
      graph.links.forEach((link) => {
        const source = typeof link.source === "object" ? link.source.id : link.source;
        const target = typeof link.target === "object" ? link.target.id : link.target;
        if (!adjacency.has(source)) adjacency.set(source, new Set());
        if (!adjacency.has(target)) adjacency.set(target, new Set());
        adjacency.get(source).add(target);
        adjacency.get(target).add(source);
      });

      const visited = new Set();
      graph.nodes.forEach((node) => {
        if (visited.has(node.id)) return;
        const stack = [node.id];
        const members = [];
        visited.add(node.id);
        while (stack.length) {
          const current = stack.pop();
          members.push(current);
          for (const next of adjacency.get(current) || []) {
            if (!visited.has(next)) {
              visited.add(next);
              stack.push(next);
            }
          }
        }
        groups.set(`component:${node.id}`, members);
      });
    }

    const result = [];

    for (const [communityId, members] of groups.entries()) {
      const memberSet = new Set(members);
      const flaggedMembers = members.map((id) => queueById.get(id)).filter(Boolean);
      const peak = flaggedMembers.reduce(
        (best, item) =>
          !best || Number(item.proba) > Number(best.proba) ? item : best,
        null
      );

      const internalLinks = graph.links.filter((link) => {
        const source = typeof link.source === "object" ? link.source.id : link.source;
        const target = typeof link.target === "object" ? link.target.id : link.target;
        return memberSet.has(source) && memberSet.has(target);
      });

      const edgeCounts = {};
      internalLinks.forEach((link) => {
        edgeCounts[link.edge_type] = (edgeCounts[link.edge_type] || 0) + 1;
      });

      const strongestEdge = internalLinks.reduce((strongest, link) => {
        const weight = Number(link.weight || 0);
        if (!strongest || weight > Number(strongest.weight || 0)) {
          return {
            ...link,
            source: typeof link.source === "object" ? link.source.id : link.source,
            target: typeof link.target === "object" ? link.target.id : link.target,
          };
        }
        return strongest;
      }, null);

      result.push({
        communityId,
        members,
        flaggedMembers,
        peak,
        memberLinks: internalLinks.length,
        edgeCounts,
        strongestEdge,
      });
    }

    return result
      .filter((community) => community.members.length > 1 || community.flaggedMembers.length > 0)
      .sort((a, b) => Number(b.peak?.proba || 0) - Number(a.peak?.proba || 0));
  }, [graph.nodes, graph.links, queue]);

  useEffect(() => {
    if (selectedCommunityIndex >= communities.length) {
      setSelectedCommunityIndex(0);
    }
  }, [communities.length, selectedCommunityIndex]);

  const highlightedCommunities = useMemo(
    () => communities.slice(0, communityLimit),
    [communities, communityLimit]
  );

  const selectedCommunity =
    highlightedCommunities[selectedCommunityIndex] || highlightedCommunities[0] || null;

  const selectedMemberSet = useMemo(
    () => new Set(selectedCommunity?.members || []),
    [selectedCommunity]
  );

  const communityByNode = useMemo(() => {
    const map = new Map();
    highlightedCommunities.forEach((community, communityIndex) => {
      community.members.forEach((memberId) => map.set(memberId, communityIndex));
    });
    return map;
  }, [highlightedCommunities]);

  // Apply edge filter
  const filteredLinks = useMemo(() => {
    if (edgeFilter === "ALL") return graph.links;

    return graph.links.filter(
      (l) => l.edge_type === edgeFilter
    );
  }, [graph.links, edgeFilter]);

  // Apply search filter
  const filteredNodes = useMemo(() => {
    if (!searchTerm.trim()) return graph.nodes;

    const term = searchTerm.toLowerCase();

    return graph.nodes.filter((n) =>
      n.id.toLowerCase().includes(term)
    );
  }, [graph.nodes, searchTerm]);

  // Compute node degrees for sizing
  const degrees = useMemo(() => {
    const deg = {};

    filteredLinks.forEach((l) => {
      const source =
        typeof l.source === "object"
          ? l.source.id
          : l.source;

      const target =
        typeof l.target === "object"
          ? l.target.id
          : l.target;

      deg[source] = (deg[source] || 0) + 1;
      deg[target] = (deg[target] || 0) + 1;
    });

    return deg;
  }, [filteredLinks]);

  const graphData = useMemo(() => {
    const nodeIds = new Set(
      filteredNodes.map((n) => n.id)
    );

    return {
      nodes: filteredNodes,
      links: filteredLinks.filter((l) => {
        const source =
          typeof l.source === "object"
            ? l.source.id
            : l.source;

        const target =
          typeof l.target === "object"
            ? l.target.id
            : l.target;

        return (
          !searchTerm ||
          (nodeIds.has(source) && nodeIds.has(target))
        );
      }),
    };
  }, [
    filteredNodes,
    filteredLinks,
    searchTerm,
  ]);

  /*
   * Tune force layout and fit graph after simulation
   * has initialized.
   */
  useEffect(() => {
    if (!fgRef.current || !graphData.nodes.length) {
      return;
    }

    const fg = fgRef.current;

    fg.d3Force("charge").strength(-80);
    fg.d3Force("link").distance(30);
    fg.d3Force("center").strength(0.1);

    fg.d3ReheatSimulation();

    if (!initialFitDone.current) {
      initialFitDone.current = true;

      const timer = setTimeout(() => {
        if (fgRef.current) {
          fgRef.current.zoomToFit(400, 40);
        }
      }, 500);

      return () => clearTimeout(timer);
    }
  }, [graphData]);

  /*
   * Draw subtle community boundaries.
   *
   * This runs behind the normal node rendering.
   */
  const drawCommunityBackgrounds = (ctx, globalScale) => {
    /*
    * Draw a boundary around the actual shape of each community.
    *
    * The previous implementation used:
    *
    *   centroid + maximum distance = large circle
    *
    * which could produce huge overlapping circles when a community
    * contained nodes spread across the graph.
    *
    * Instead, use a convex hull around the community's actual
    * node positions.
    */

    const getConvexHull = (points) => {
      if (points.length <= 1) {
        return points;
      }

      const sorted = [...points].sort((a, b) => {
        if (a.x !== b.x) return a.x - b.x;
        return a.y - b.y;
      });

      const cross = (o, a, b) =>
        (a.x - o.x) * (b.y - o.y) -
        (a.y - o.y) * (b.x - o.x);

      const lower = [];

      for (const point of sorted) {
        while (
          lower.length >= 2 &&
          cross(
            lower[lower.length - 2],
            lower[lower.length - 1],
            point
          ) <= 0
        ) {
          lower.pop();
        }

        lower.push(point);
      }

      const upper = [];

      for (let i = sorted.length - 1; i >= 0; i--) {
        const point = sorted[i];

        while (
          upper.length >= 2 &&
          cross(
            upper[upper.length - 2],
            upper[upper.length - 1],
            point
          ) <= 0
        ) {
          upper.pop();
        }

        upper.push(point);
      }

      lower.pop();
      upper.pop();

      return lower.concat(upper);
    };

    highlightedCommunities.forEach(
      (community, communityIndex) => {
        const nodeById = new Map(
          graphData.nodes.map((node) => [node.id, node])
        );

        const members = community.members
          .map((memberId) => nodeById.get(memberId))
          .filter(
            (node) =>
              node &&
              typeof node.x === "number" &&
              typeof node.y === "number"
          );

        if (!members.length) return;

        const color =
          COMMUNITY_COLORS[
            communityIndex % COMMUNITY_COLORS.length
          ];

        const hex = color.replace("#", "");

        const r = parseInt(
          hex.substring(0, 2),
          16
        );

        const g = parseInt(
          hex.substring(2, 4),
          16
        );

        const b = parseInt(
          hex.substring(4, 6),
          16
        );

        /*
        * Convert screen-space padding into graph-space padding.
        */
        const padding = 24 / globalScale;

        /*
        * Single-node community.
        */
        if (members.length === 1) {
          const node = members[0];
          const radius = 22 / globalScale;

          ctx.beginPath();

          ctx.arc(
            node.x,
            node.y,
            radius,
            0,
            2 * Math.PI
          );

          ctx.fillStyle = `rgba(${r}, ${g}, ${b}, 0.045)`;
          ctx.fill();

          ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, 0.25)`;
          ctx.lineWidth = 1.5 / globalScale;
          ctx.stroke();

          return;
        }

        /*
        * Two-node community.
        *
        * A circle around the midpoint provides a clean
        * capsule-like boundary without needing a separate
        * geometry implementation.
        */
        if (members.length === 2) {
          const [a, bPoint] = members;

          const dx = bPoint.x - a.x;
          const dy = bPoint.y - a.y;

          const distance = Math.sqrt(
            dx * dx + dy * dy
          );

          const centerX =
            (a.x + bPoint.x) / 2;

          const centerY =
            (a.y + bPoint.y) / 2;

          const radius =
            distance / 2 + padding;

          ctx.beginPath();

          ctx.arc(
            centerX,
            centerY,
            radius,
            0,
            2 * Math.PI
          );

          ctx.fillStyle = `rgba(${r}, ${g}, ${b}, 0.045)`;
          ctx.fill();

          ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, 0.25)`;
          ctx.lineWidth = 1.5 / globalScale;
          ctx.stroke();

          return;
        }

        /*
        * Build convex hull for communities with 3+ members.
        */
        const hull = getConvexHull(
          members.map((node) => ({
            x: node.x,
            y: node.y,
          }))
        );

        if (hull.length < 3) return;

        /*
        * Find the hull centroid.
        *
        * We use it only to push hull points outward slightly,
        * creating a small visual gap between the boundary and
        * the nodes.
        */
        const centerX =
          hull.reduce(
            (sum, point) => sum + point.x,
            0
          ) / hull.length;

        const centerY =
          hull.reduce(
            (sum, point) => sum + point.y,
            0
          ) / hull.length;

        const expandedHull = hull.map(
          (point) => {
            const dx = point.x - centerX;
            const dy = point.y - centerY;

            const distance = Math.sqrt(
              dx * dx + dy * dy
            );

            if (distance === 0) {
              return {
                x: point.x,
                y: point.y,
              };
            }

            return {
              x:
                point.x +
                (dx / distance) * padding,

              y:
                point.y +
                (dy / distance) * padding,
            };
          }
        );

        /*
        * Draw filled community region.
        */
        ctx.beginPath();

        ctx.moveTo(
          expandedHull[0].x,
          expandedHull[0].y
        );

        for (
          let i = 1;
          i < expandedHull.length;
          i++
        ) {
          ctx.lineTo(
            expandedHull[i].x,
            expandedHull[i].y
          );
        }

        ctx.closePath();

        ctx.fillStyle =
          `rgba(${r}, ${g}, ${b}, 0.045)`;

        ctx.fill();

        /*
        * Draw subtle boundary.
        */
        ctx.beginPath();

        ctx.moveTo(
          expandedHull[0].x,
          expandedHull[0].y
        );

        for (
          let i = 1;
          i < expandedHull.length;
          i++
        ) {
          ctx.lineTo(
            expandedHull[i].x,
            expandedHull[i].y
          );
        }

        ctx.closePath();

        ctx.strokeStyle =
          `rgba(${r}, ${g}, ${b}, 0.25)`;

        ctx.lineWidth =
          1.5 / globalScale;

        ctx.stroke();
      }
    );
  };

  // Theme helpers
  const getCSSVar = (name) =>
    getComputedStyle(document.documentElement)
      .getPropertyValue(name)
      .trim();

  const handleNodeClick = (node) => {
    if (node.is_focus) {
      navigate(`/investigations/${node.id}`);
    }
  };

  const handleNodeHover = (node) =>
    setHighlightId(node ? node.id : null);

  const zoomIn = () =>
    fgRef.current?.zoom(1.3);

  const zoomOut = () =>
    fgRef.current?.zoom(0.7);

  const resetZoom = () => {
    if (
      !fgRef.current ||
      !graphData.nodes.length
    ) {
      return;
    }

    fgRef.current.zoomToFit(400, 40);
  };

  if (loading) {
    return (
      <div className="p-6">
        Loading graph…
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-destructive">
        {error}
      </div>
    );
  }

  if (!graph.nodes.length) {
    return (
      <div className="p-6">
        No graph data.
      </div>
    );
  }

  return (
    <div className="space-y-6">

      {/* Ring / community overview */}
      <div>
        <div className="flex items-end justify-between gap-3 mb-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Ring-first investigation
            </p>

            <h2 className="text-xl font-semibold">
              Abuse Ring / Community Overview
            </h2>

            <p className="text-sm text-muted-foreground mt-1">
              Communities are derived from connected
              account relationships. Peak member risk is
              shown as a signal, not a separate ring-model
              score.
            </p>
          </div>

          <div className="text-right text-xs text-muted-foreground">
            {communities.length} communities
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {communities
            .slice(0, communityLimit)
            .map((community, index) => {
              const strongestType =
                community.strongestEdge?.edge_type;

              return (
                <div
                  key={`${community.communityId}-${index}`}
                  role="button"
                  tabIndex={0}
                  onClick={() => setSelectedCommunityIndex(index)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      setSelectedCommunityIndex(index);
                    }
                  }}
                  className={`w-full text-left rounded-lg border bg-card p-4 transition-colors cursor-pointer ${
                    selectedCommunityIndex === index
                      ? "border-black dark:border-white ring-1 ring-black/10 dark:ring-white/10"
                      : "border-border hover:bg-accent"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs text-muted-foreground">
                        Abuse Community #{index + 1}
                      </p>

                      <p className="font-semibold mt-1">
                        {community.members.length} connected accounts
                      </p>
                    </div>

                    {community.peak && (
                      <span className="text-xs font-medium rounded-full border border-border px-2 py-1">
                        {(Number(community.peak.proba) * 100).toFixed(2)}%
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-3 mt-4 text-xs">
                    <div>
                      <span className="text-muted-foreground block">
                        Flagged members
                      </span>

                      <span className="font-semibold">
                        {community.flaggedMembers.length}
                      </span>
                    </div>

                    <div>
                      <span className="text-muted-foreground block">
                        Internal links
                      </span>

                      <span className="font-semibold">
                        {community.memberLinks}
                      </span>
                    </div>

                    <div>
                      <span className="text-muted-foreground block">
                        Strongest edge
                      </span>

                      <span className="font-semibold">
                        {strongestType
                          ? EDGE_LABELS[strongestType] ||
                            strongestType
                          : "—"}
                      </span>
                    </div>

                    <div>
                      <span className="text-muted-foreground block">
                        Edge weight
                      </span>

                      <span className="font-semibold">
                        {community.strongestEdge?.weight != null
                          ? Number(
                              community.strongestEdge.weight
                            ).toFixed(2)
                          : "—"}
                      </span>
                    </div>
                  </div>

                  {community.strongestEdge && (
                    <div className="mt-4 rounded-md border border-border bg-muted/30 p-3">
                      <p className="text-xs font-medium">
                        Strongest relationship
                      </p>

                      <p className="text-xs text-muted-foreground mt-1">
                        {EDGE_LABELS[
                          community.strongestEdge.edge_type
                        ] ||
                          community.strongestEdge.edge_type}
                      </p>

                      <p className="text-xs text-muted-foreground">
                        {typeof community.strongestEdge.source === "object"
                          ? community.strongestEdge.source.id
                          : community.strongestEdge.source}{" "}
                        →{" "}
                        {typeof community.strongestEdge.target === "object"
                          ? community.strongestEdge.target.id
                          : community.strongestEdge.target}
                      </p>
                    </div>
                  )}

                  {community.peak && (
                    <button
                      onClick={() =>
                        navigate(
                          `/investigations/${community.peak.account_id}`
                        )
                      }
                      className="mt-4 text-xs underline underline-offset-4"
                    >
                      Investigate highest-risk member ·{" "}
                      {community.peak.account_id}
                    </button>
                  )}
                </div>
              );
            })}
        </div>

        {/* Community count selector */}
        {communities.length > 3 && (
          <div className="mt-4 flex items-center gap-2">
            <label
              htmlFor="community-limit"
              className="text-sm text-muted-foreground"
            >
              Highlight top
            </label>

            <select
              id="community-limit"
              value={communityLimit}
              onChange={(e) =>
                setCommunityLimit(
                  Number(e.target.value)
                )
              }
              className="border border-border rounded-md px-3 py-2 text-sm bg-background"
            >
              <option value={3}>3 communities</option>
              <option value={6}>6 communities</option>
              <option value={15}>15 communities</option>
            </select>
          </div>
        )}

        {selectedCommunity && (
          <div className="mt-4 rounded-lg border border-border bg-muted/20 p-4">
            <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Selected ring
                </p>
                <h3 className="text-base font-semibold mt-1">
                  Community #{selectedCommunityIndex + 1} · {selectedCommunity.members.length} accounts
                </h3>
                <p className="text-xs text-muted-foreground mt-1">
                  {selectedCommunity.flaggedMembers.length} flagged members · {selectedCommunity.memberLinks} internal relationships
                </p>
              </div>
              {selectedCommunity.peak && (
                <button
                  type="button"
                  onClick={() => navigate(`/investigations/${selectedCommunity.peak.account_id}`)}
                  className="border border-border rounded-md px-3 py-2 text-xs hover:bg-accent whitespace-nowrap"
                >
                  Investigate highest-risk member →
                </button>
              )}
            </div>

            {selectedCommunity.strongestEdge && (
              <div className="mt-3 rounded-md border border-border bg-background p-3">
                <p className="text-xs font-medium">Strongest configured relationship</p>
                <p className="text-sm font-semibold mt-1">
                  {EDGE_LABELS[selectedCommunity.strongestEdge.edge_type] || selectedCommunity.strongestEdge.edge_type}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {selectedCommunity.strongestEdge.source} → {selectedCommunity.strongestEdge.target} · weight {Number(selectedCommunity.strongestEdge.weight || 0).toFixed(2)}
                </p>
                <p className="text-[11px] text-muted-foreground mt-2">
                  This is the strongest configured relationship weight in the selected ring; it prioritizes evidence for review and does not establish abuse by itself.
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="flex flex-col md:flex-row gap-3 md:items-center">
        <input
          type="text"
          placeholder="Search account..."
          value={searchTerm}
          onChange={(e) =>
            setSearchTerm(e.target.value)
          }
          className="border border-border rounded-md px-3 py-2 text-sm bg-background flex-1"
        />

        <div className="flex gap-2 flex-wrap">
          {[
            "ALL",
            ...Object.keys(EDGE_LABELS),
          ].map((filter) => (
            <button
              key={filter}
              onClick={() =>
                setEdgeFilter(filter)
              }
              className={`px-3 py-1 rounded-full text-sm ${
                edgeFilter === filter
                  ? "bg-black text-white dark:bg-white dark:text-black"
                  : "border border-border text-muted-foreground hover:bg-accent"
              }`}
            >
              {filter === "ALL"
                ? "All"
                : EDGE_LABELS[filter]}
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

          /*
           * Draw community backgrounds before nodes.
           */
          onRenderFramePre={(ctx, globalScale) => {
            drawCommunityBackgrounds(
              ctx,
              globalScale
            );
          }}

          nodeLabel={(node) => {
            const deg =
              degrees[node.id] || 0;

            const focus = node.is_focus
              ? "Flagged Account"
              : "Linked Account";

            const communityIndex =
              communityByNode.get(node.id);

            const communityText =
              communityIndex != null
                ? `<br>Community #${
                    communityIndex + 1
                  }`
                : "";

            return `${node.id}<br>${focus}<br>Connections: ${deg}${communityText}`;
          }}

          nodeRelSize={4}

          nodeVal={(node) =>
            Math.max(
              1,
              degrees[node.id] || 1
            )
          }

          nodeColor={(node) => {
            const communityIndex =
              communityByNode.get(node.id);

            if (communityIndex != null) {
              return COMMUNITY_COLORS[
                communityIndex %
                  COMMUNITY_COLORS.length
              ];
            }

            return node.is_focus
              ? "#000000"
              : "#888888";
          }}

          nodeCanvasObject={(
            node,
            ctx,
            globalScale
          ) => {
            const isDark =
              document.documentElement.classList.contains(
                "dark"
              );

            const deg =
              degrees[node.id] || 1;

            const communityIndex =
              communityByNode.get(node.id);

            const primary =
              getComputedStyle(
                document.documentElement
              )
                .getPropertyValue("--primary")
                .trim() || "#000000";

            const muted =
              getComputedStyle(
                document.documentElement
              )
                .getPropertyValue(
                  "--muted-foreground"
                )
                .trim() || "#666666";

            const radius = Math.max(
              5,
              deg * 1.5
            );

            /*
             * Determine node color.
             */
            let nodeFill;

            if (communityIndex != null) {
              nodeFill =
                COMMUNITY_COLORS[
                  communityIndex %
                    COMMUNITY_COLORS.length
                ];
            } else {
              nodeFill = node.is_focus ? primary : muted;
            }

            /*
             * Shadow
             */
            ctx.beginPath();

            ctx.arc(
              node.x,
              node.y + 2,
              radius,
              0,
              2 * Math.PI,
              false
            );

            ctx.fillStyle =
              "rgba(0,0,0,0.15)";

            ctx.fill();

            /*
             * Main circle
             */
            ctx.beginPath();

            ctx.arc(
              node.x,
              node.y,
              radius,
              0,
              2 * Math.PI,
              false
            );

            const isSelected = selectedMemberSet.has(node.id);
            const isHighlighted = communityIndex != null;
            ctx.globalAlpha = isSelected ? 1 : isHighlighted ? 0.38 : 0.22;
            ctx.fillStyle = nodeFill;

            ctx.fill();
            ctx.globalAlpha = 1;

            /*
             * Border
             */
            ctx.strokeStyle = isDark
              ? "#ffffff"
              : "#000000";

            ctx.lineWidth =
              1.2 / globalScale;

            ctx.stroke();

            /*
             * Label
             */
            const fontSize =
              11 / globalScale;

            ctx.font = `${fontSize}px Inter, Sans-Serif`;

            ctx.textAlign = "center";
            ctx.textBaseline = "top";

            ctx.fillStyle = isDark
              ? "#ffffff"
              : "#000000";

            ctx.fillText(
              node.id,
              node.x,
              node.y + radius + 3
            );
          }}

          linkColor={(link) => {
            const source =
              typeof link.source === "object"
                ? link.source.id
                : link.source;

            const target =
              typeof link.target === "object"
                ? link.target.id
                : link.target;

            const sourceCommunity =
              communityByNode.get(source);

            const targetCommunity =
              communityByNode.get(target);

            /*
             * If both ends belong to the same
             * highlighted community, use that
             * community's color.
             */
            if (
              sourceCommunity != null &&
              sourceCommunity === targetCommunity
            ) {
              return COMMUNITY_COLORS[
                sourceCommunity %
                  COMMUNITY_COLORS.length
              ];
            }

            return (
              EDGE_COLORS[link.edge_type] ||
              "#aaaaaa"
            );
          }}

          linkLineDash={(link) => {
            const source = typeof link.source === "object" ? link.source.id : link.source;
            const target = typeof link.target === "object" ? link.target.id : link.target;
            return selectedMemberSet.has(source) && selectedMemberSet.has(target) ? [] : [3, 3];
          }}

          linkWidth={(link) => {
            const source =
              typeof link.source === "object"
                ? link.source.id
                : link.source;

            const target =
              typeof link.target === "object"
                ? link.target.id
                : link.target;

            const sameCommunity =
              communityByNode.has(source) &&
              communityByNode.has(target) &&
              communityByNode.get(source) ===
                communityByNode.get(target);

            const hovered =
              highlightId === source ||
              highlightId === target;

            const selectedEdge = selectedMemberSet.has(source) && selectedMemberSet.has(target);

            if (hovered) return 2.5;
            if (selectedEdge) return 2.6;
            if (sameCommunity) return 1.5;
            return 1;
          }}

          linkDirectionalArrowLength={0}

          onNodeClick={handleNodeClick}

          onNodeHover={handleNodeHover}

          cooldownTicks={150}
        />
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3">
        {Object.entries(EDGE_LABELS).map(
          ([key, label]) => (
            <div
              key={key}
              className="flex items-center gap-2"
            >
              <span
                className="inline-block w-3 h-3 rounded-full"
                style={{
                  backgroundColor:
                    EDGE_COLORS[key],
                }}
              />

              <span className="text-xs text-muted-foreground">
                {label}
              </span>
            </div>
          )
        )}
      </div>
    </div>
  );
}