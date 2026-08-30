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
   * Build communities from the graph.
   *
   * Existing behavior is preserved:
   * communities are connected components and are sorted
   * by highest-risk member probability.
   */
  const communities = useMemo(() => {
  const adjacency = new Map();

  graph.nodes.forEach((node) => {
    adjacency.set(node.id, new Set());
  });

  graph.links.forEach((link) => {
    const source =
      typeof link.source === "object"
        ? link.source.id
        : link.source;

    const target =
      typeof link.target === "object"
        ? link.target.id
        : link.target;

    if (!adjacency.has(source)) {
      adjacency.set(source, new Set());
    }

    if (!adjacency.has(target)) {
      adjacency.set(target, new Set());
    }

    adjacency.get(source).add(target);
    adjacency.get(target).add(source);
  });

  const queueById = new Map(
    queue.map((account) => [
      account.account_id,
      account,
    ])
  );

  const visited = new Set();
  const result = [];

  for (const node of graph.nodes) {
    if (visited.has(node.id)) continue;

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

    const memberSet = new Set(members);

    const flaggedMembers = members
      .map((id) => queueById.get(id))
      .filter(Boolean);

    const peak = flaggedMembers.reduce(
      (best, item) =>
        !best ||
        Number(item.proba) > Number(best.proba)
          ? item
          : best,
      null
    );

    const internalLinks = graph.links.filter((link) => {
      const source =
        typeof link.source === "object"
          ? link.source.id
          : link.source;

      const target =
        typeof link.target === "object"
          ? link.target.id
          : link.target;

      return (
        memberSet.has(source) &&
        memberSet.has(target)
      );
    });

    const edgeCounts = {};

    internalLinks.forEach((link) => {
      edgeCounts[link.edge_type] =
        (edgeCounts[link.edge_type] || 0) + 1;
    });

    const strongestEdge =
      internalLinks.length > 0
        ? internalLinks.reduce(
            (strongest, link) => {
              const weight = Number(link.weight || 0);

              if (
                !strongest ||
                weight > Number(strongest.weight || 0)
              ) {
                return {
                  ...link,
                  source:
                    typeof link.source === "object"
                      ? link.source.id
                      : link.source,
                  target:
                    typeof link.target === "object"
                      ? link.target.id
                      : link.target,
                };
              }

              return strongest;
            },
            null
          )
        : null;

    result.push({
      members,
      flaggedMembers,
      peak,
      memberLinks: internalLinks.length,
      edgeCounts,
      strongestEdge,
    });
  }

  return result
    .filter(
      (community) =>
        community.members.length > 1 ||
        community.flaggedMembers.length > 0
    )
    .sort(
      (a, b) =>
        Number(b.peak?.proba || 0) -
        Number(a.peak?.proba || 0)
    );
}, [graph.nodes, graph.links, queue]);

  /*
   * Only the currently selected top N communities are highlighted.
   *
   * 3  -> top 3
   * 6  -> top 6
   * 15 -> top 15
   */
  const highlightedCommunities = useMemo(() => {
    return communities.slice(0, communityLimit);
  }, [communities, communityLimit]);

  /*
   * Map every node to the highlighted community it belongs to.
   *
   * Example:
   * A001 -> community 0
   * A002 -> community 0
   * A010 -> community 1
   *
   * Nodes outside the selected communities get null.
   */
  const communityByNode = useMemo(() => {
    const map = new Map();

    highlightedCommunities.forEach((community, communityIndex) => {
      community.members.forEach((memberId) => {
        map.set(memberId, communityIndex);
      });
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
    highlightedCommunities.forEach(
      (community, communityIndex) => {
        const members = community.members
          .map((memberId) =>
            graphData.nodes.find(
              (node) => node.id === memberId
            )
          )
          .filter(
            (node) =>
              node &&
              typeof node.x === "number" &&
              typeof node.y === "number"
          );

        if (members.length < 2) return;

        const color =
          COMMUNITY_COLORS[
            communityIndex % COMMUNITY_COLORS.length
          ];

        const centerX =
          members.reduce(
            (sum, node) => sum + node.x,
            0
          ) / members.length;

        const centerY =
          members.reduce(
            (sum, node) => sum + node.y,
            0
          ) / members.length;

        const maxDistance = members.reduce(
          (max, node) => {
            const dx = node.x - centerX;
            const dy = node.y - centerY;

            return Math.max(
              max,
              Math.sqrt(dx * dx + dy * dy)
            );
          },
          0
        );

        const padding = 35 / globalScale;
        const radius =
          Math.max(
            maxDistance + padding,
            45 / globalScale
          );

        /*
         * Low-opacity fill.
         */
        ctx.beginPath();

        ctx.arc(
          centerX,
          centerY,
          radius,
          0,
          2 * Math.PI
        );

        ctx.fillStyle = color
          .replace(")", "")
          .replace("rgb", "rgba");

        /*
         * Hex colors cannot directly use rgba(),
         * so convert the hex color to RGB.
         */
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

        ctx.fillStyle = `rgba(${r}, ${g}, ${b}, 0.045)`;
        ctx.fill();

        /*
         * Subtle border.
         */
        ctx.beginPath();

        ctx.arc(
          centerX,
          centerY,
          radius,
          0,
          2 * Math.PI
        );

        ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, 0.25)`;
        ctx.lineWidth = 1.5 / globalScale;

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
                  key={`${community.members[0]}-${index}`}
                  className="rounded-lg border border-border bg-card p-4"
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
              nodeFill = node.is_focus
                ? primary
                : muted;
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

            ctx.fillStyle = nodeFill;

            ctx.fill();

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

            if (hovered) return 2.5;

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