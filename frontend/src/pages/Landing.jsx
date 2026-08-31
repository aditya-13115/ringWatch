import Logo from "../components/Logo";
import { Link } from "react-router-dom";
import {
  motion,
  useReducedMotion,
} from "framer-motion";
import {
  Moon,
  Sun,
  ArrowRight,
  Activity,
  ShieldCheck,
} from "lucide-react";
import {
  useEffect,
  useRef,
  useState,
} from "react";

// ----------------------------------------------------------------------
// Fraud Graph Configuration
// ----------------------------------------------------------------------

const EDGE_COLORS = {
  Device: "#3b82f6",
  IP: "#8b5cf6",
  Address: "#10b981",
  Coupon: "#f59e0b",
  Payment: "#06b6d4",
  Phone: "#6366f1",
};

const IDENTITY_TYPES = Object.keys(EDGE_COLORS);

const RISK_LEVELS = [
  "LOW",
  "MEDIUM",
  "HIGH",
  "CRITICAL",
];

// ----------------------------------------------------------------------
// Interactive Fraud Graph Background
// ----------------------------------------------------------------------

function FraudGraphBackground() {
  const canvasRef = useRef(null);

  const nodesRef = useRef([]);
  const edgesRef = useRef([]);

  const mouseRef = useRef({
    x: -1000,
    y: -1000,
  });

  const draggedNodeRef = useRef(null);
  const selectedNodeRef = useRef(null);

  const animationRef = useRef(null);

  const highlightRef = useRef(0);

  const pulseRef = useRef({
    active: false,
    progress: 0,
    edgeIndex: 0,
  });

  const [hoveredNode, setHoveredNode] =
    useState(null);

  const [selectedNode, setSelectedNode] =
    useState(null);

  const [tooltipPos, setTooltipPos] =
    useState({
      x: 0,
      y: 0,
    });

  // --------------------------------------------------------------------
  // Graph creation + animation
  // --------------------------------------------------------------------

  useEffect(() => {
    const canvas = canvasRef.current;

    if (!canvas) return;

    const ctx = canvas.getContext("2d");

    if (!ctx) return;

    let width = window.innerWidth;
    let height = window.innerHeight;

    const dpr = Math.min(
      window.devicePixelRatio || 1,
      2
    );

    const resizeCanvas = () => {
      width = window.innerWidth;
      height = window.innerHeight;

      canvas.width = width * dpr;
      canvas.height = height * dpr;

      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      ctx.setTransform(
        dpr,
        0,
        0,
        dpr,
        0,
        0
      );
    };

    resizeCanvas();

    window.addEventListener(
      "resize",
      resizeCanvas
    );

    // ------------------------------------------------------------------
    // Create graph clusters
    // ------------------------------------------------------------------

    const clusterCount = 5;

    const clusters = [];

    for (
      let i = 0;
      i < clusterCount;
      i++
    ) {
      clusters.push({
        x:
          width *
          (0.08 +
            Math.random() * 0.84),

        y:
          height *
          (0.12 +
            Math.random() * 0.76),
      });
    }

    const nodes = [];
    const edges = [];

    let nodeId = 0;

    // ------------------------------------------------------------------
    // Create nodes
    // ------------------------------------------------------------------

    clusters.forEach(
      (center, clusterIndex) => {
        const nodeCount =
          11 +
          Math.floor(
            Math.random() * 5
          );

        for (
          let i = 0;
          i < nodeCount;
          i++
        ) {
          const angle =
            Math.random() *
            Math.PI *
            2;

          const radius =
            35 +
            Math.random() * 105;

          nodes.push({
            id: nodeId++,

            x:
              center.x +
              Math.cos(angle) *
                radius,

            y:
              center.y +
              Math.sin(angle) *
                radius,

            vx:
              (Math.random() - 0.5) *
              0.16,

            vy:
              (Math.random() - 0.5) *
              0.16,

            community:
              clusterIndex,

            risk:
              RISK_LEVELS[
                Math.floor(
                  Math.random() *
                    RISK_LEVELS.length
                )
              ],

            sharedIdentity:
              IDENTITY_TYPES[
                Math.floor(
                  Math.random() *
                    IDENTITY_TYPES.length
                )
              ],

            connections: 0,

            radius: 2.5,

            selected: false,

            dragged: false,
          });
        }
      }
    );

    // ------------------------------------------------------------------
    // Create edges
    // ------------------------------------------------------------------

    const connectNodes = (
      source,
      target,
      identity
    ) => {
      edges.push({
        from: source.id,

        to: target.id,

        identity,

        color:
          EDGE_COLORS[identity],

        dotProgress:
          Math.random(),

        speed:
          0.0015 +
          Math.random() * 0.0025,
      });

      source.connections += 1;
      target.connections += 1;
    };

    // Connect nodes within clusters
    nodes.forEach((node) => {
      const sameCluster =
        nodes.filter(
          (candidate) =>
            candidate.community ===
              node.community &&
            candidate.id !==
              node.id
        );

      const connectCount = Math.min(
        2 +
          Math.floor(
            Math.random() * 3
          ),
        sameCluster.length
      );

      for (
        let i = 0;
        i < connectCount;
        i++
      ) {
        const target =
          sameCluster[
            Math.floor(
              Math.random() *
                sameCluster.length
            )
          ];

        if (!target) continue;

        const exists =
          edges.some(
            (edge) =>
              (edge.from ===
                node.id &&
                edge.to ===
                  target.id) ||
              (edge.from ===
                target.id &&
                edge.to ===
                  node.id)
          );

        if (!exists) {
          connectNodes(
            node,
            target,
            IDENTITY_TYPES[
              Math.floor(
                Math.random() *
                  IDENTITY_TYPES.length
              )
            ]
          );
        }
      }
    });

    // ------------------------------------------------------------------
    // Connect clusters together
    // ------------------------------------------------------------------

    for (
      let cluster = 0;
      cluster < clusterCount;
      cluster++
    ) {
      const clusterNodes =
        nodes.filter(
          (node) =>
            node.community ===
            cluster
        );

      const otherNodes =
        nodes.filter(
          (node) =>
            node.community !==
            cluster
        );

      const source =
        clusterNodes[
          Math.floor(
            Math.random() *
              clusterNodes.length
          )
        ];

      const target =
        otherNodes[
          Math.floor(
            Math.random() *
              otherNodes.length
          )
        ];

      if (!source || !target) {
        continue;
      }

      const exists =
        edges.some(
          (edge) =>
            (edge.from ===
              source.id &&
              edge.to ===
                target.id) ||
            (edge.from ===
              target.id &&
              edge.to ===
                source.id)
        );

      if (!exists) {
        connectNodes(
          source,
          target,
          IDENTITY_TYPES[
            Math.floor(
              Math.random() *
                IDENTITY_TYPES.length
            )
          ]
        );
      }
    }

    nodesRef.current = nodes;
    edgesRef.current = edges;

    // ------------------------------------------------------------------
    // Animation
    // ------------------------------------------------------------------

    let previousSecond = -1;

    const animate = () => {
      const isDark =
        document.documentElement.classList.contains(
          "dark"
        );

      ctx.clearRect(
        0,
        0,
        width,
        height
      );

      // --------------------------------------------------------------
      // Update node positions
      // --------------------------------------------------------------

      nodesRef.current.forEach(
        (node) => {
          if (
            draggedNodeRef.current !==
            node
          ) {
            node.x += node.vx;
            node.y += node.vy;
          }

          // Boundary bounce
          if (
            node.x < 10 ||
            node.x >
              width - 10
          ) {
            node.vx *= -1;

            node.x = Math.max(
              10,
              Math.min(
                width - 10,
                node.x
              )
            );
          }

          if (
            node.y < 10 ||
            node.y >
              height - 10
          ) {
            node.vy *= -1;

            node.y = Math.max(
              10,
              Math.min(
                height - 10,
                node.y
              )
            );
          }

          // ------------------------------------------------------------
          // Cursor repulsion
          // ------------------------------------------------------------

          if (
            draggedNodeRef.current !==
            node
          ) {
            const dx =
              node.x -
              mouseRef.current.x;

            const dy =
              node.y -
              mouseRef.current.y;

            const distance =
              Math.sqrt(
                dx * dx +
                  dy * dy
              );

            if (
              distance > 0 &&
              distance < 110
            ) {
              const force =
                ((110 -
                  distance) /
                  110) *
                0.18;

              node.vx +=
                (dx /
                  distance) *
                force;

              node.vy +=
                (dy /
                  distance) *
                force;
            }
          }

          // Slow down accumulated velocity
          node.vx *= 0.995;
          node.vy *= 0.995;
        }
      );

      // --------------------------------------------------------------
      // Cluster highlight rotation
      // --------------------------------------------------------------

      const currentSecond =
        Math.floor(
          Date.now() / 1000
        );

      if (
        currentSecond !==
        previousSecond
      ) {
        previousSecond =
          currentSecond;

        highlightRef.current =
          Math.floor(
            currentSecond / 3
          );
      }

      const highlightedCluster =
        highlightRef.current %
        clusterCount;

      // --------------------------------------------------------------
      // Selected node
      // --------------------------------------------------------------

      const selected =
        selectedNodeRef.current;

      // --------------------------------------------------------------
      // Draw cluster rings / investigation zones
      // --------------------------------------------------------------

      clusters.forEach((cluster, index) => {
        const active =
          index === highlightedCluster;

        const pulse =
          1 +
          Math.sin(Date.now() / 1200 + index) *
            0.025;

        const ringRadius = active ? 150 * pulse : 125;

        ctx.beginPath();
        ctx.arc(
          cluster.x,
          cluster.y,
          ringRadius,
          0,
          Math.PI * 2
        );

        ctx.strokeStyle = isDark
          ? active
            ? "rgba(148,163,184,0.22)"
            : "rgba(148,163,184,0.08)"
          : active
          ? "rgba(51,65,85,0.16)"
          : "rgba(51,65,85,0.055)";

        ctx.globalAlpha = 1;
        ctx.lineWidth = active ? 1.2 : 0.8;
        ctx.setLineDash(active ? [5, 7] : [3, 10]);
        ctx.stroke();
        ctx.setLineDash([]);

        // Small cluster anchor
        ctx.beginPath();
        ctx.arc(
          cluster.x,
          cluster.y,
          active ? 4 : 2.5,
          0,
          Math.PI * 2
        );

        ctx.fillStyle = isDark
          ? "rgba(226,232,240,0.65)"
          : "rgba(30,41,59,0.35)";

        ctx.globalAlpha = active ? 0.9 : 0.45;
        ctx.fill();
      });

      // --------------------------------------------------------------
      // Draw edges
      // --------------------------------------------------------------

      edgesRef.current.forEach(
        (edge) => {
          const from =
            nodesRef.current[
              edge.from
            ];

          const to =
            nodesRef.current[
              edge.to
            ];

          if (!from || !to) {
            return;
          }

          const touchesSelected =
            selected &&
            (edge.from ===
              selected.id ||
              edge.to ===
                selected.id);

          const highlighted =
            touchesSelected ||
            from.community ===
              highlightedCluster ||
            to.community ===
              highlightedCluster;

          let alpha;

          let lineWidth;

          if (touchesSelected) {
            alpha = 0.78;
            lineWidth = 2;
          } else if (highlighted) {
            alpha = isDark
              ? 0.62
              : 0.48;

            lineWidth = 1.5;
          } else {
            alpha = isDark
              ? 0.30
              : 0.22;

            lineWidth = 0.9;
          }

          // ------------------------------------------------------------
          // Edge
          // ------------------------------------------------------------

          ctx.beginPath();

          ctx.moveTo(
            from.x,
            from.y
          );

          ctx.lineTo(
            to.x,
            to.y
          );

          ctx.strokeStyle =
            edge.color;

          ctx.globalAlpha =
            alpha;

          ctx.lineWidth =
            lineWidth;

          ctx.stroke();

          // ------------------------------------------------------------
          // Moving signal
          // ------------------------------------------------------------

          const dotX =
            from.x +
            (to.x - from.x) *
              edge.dotProgress;

          const dotY =
            from.y +
            (to.y - from.y) *
              edge.dotProgress;

          edge.dotProgress +=
            edge.speed;

          if (
            edge.dotProgress >
            1
          ) {
            edge.dotProgress = 0;
          }

          // Signal glow
          const glow =
            ctx.createRadialGradient(
              dotX,
              dotY,
              0,
              dotX,
              dotY,
              touchesSelected
                ? 13
                : 8
            );

          glow.addColorStop(
            0,
            "rgba(255,255,255,0.95)"
          );

          glow.addColorStop(
            0.3,
            "rgba(255,255,255,0.35)"
          );

          glow.addColorStop(
            1,
            "rgba(255,255,255,0)"
          );

          ctx.beginPath();

          ctx.arc(
            dotX,
            dotY,
            touchesSelected
              ? 12
              : 7,
            0,
            Math.PI * 2
          );

          ctx.fillStyle =
            glow;

          ctx.globalAlpha =
            touchesSelected
              ? 0.95
              : highlighted
              ? 0.7
              : 0.35;

          ctx.fill();

          // Signal core
          ctx.beginPath();

          ctx.arc(
            dotX,
            dotY,
            touchesSelected
              ? 2.2
              : 1.4,
            0,
            Math.PI * 2
          );

          ctx.fillStyle =
            edge.color;

          ctx.globalAlpha =
            touchesSelected
              ? 1
              : highlighted
              ? 0.9
              : 0.6;

          ctx.fill();
        }
      );

      // --------------------------------------------------------------
      // Investigation pulse
      // --------------------------------------------------------------

      if (
        !pulseRef.current.active &&
        edgesRef.current.length >
          0 &&
        Math.random() <
          0.008
      ) {
        pulseRef.current = {
          active: true,

          progress: 0,

          edgeIndex:
            Math.floor(
              Math.random() *
                edgesRef.current
                  .length
            ),
        };
      }

      if (
        pulseRef.current.active
      ) {
        const edge =
          edgesRef.current[
            pulseRef.current
              .edgeIndex
          ];

        if (edge) {
          const from =
            nodesRef.current[
              edge.from
            ];

          const to =
            nodesRef.current[
              edge.to
            ];

          if (from && to) {
            const x =
              from.x +
              (to.x - from.x) *
                pulseRef.current
                  .progress;

            const y =
              from.y +
              (to.y - from.y) *
                pulseRef.current
                  .progress;

            pulseRef.current.progress +=
              0.018;

            const gradient =
              ctx.createRadialGradient(
                x,
                y,
                0,
                x,
                y,
                30
              );

            gradient.addColorStop(
              0,
              "rgba(255,255,255,1)"
            );

            gradient.addColorStop(
              0.2,
              "rgba(255,255,255,0.6)"
            );

            gradient.addColorStop(
              1,
              "rgba(255,255,255,0)"
            );

            ctx.beginPath();

            ctx.arc(
              x,
              y,
              30,
              0,
              Math.PI * 2
            );

            ctx.fillStyle =
              gradient;

            ctx.globalAlpha = 0.9;

            ctx.fill();
          }
        }

        if (
          pulseRef.current
            .progress >= 1
        ) {
          pulseRef.current.active =
            false;
        }
      }

      // --------------------------------------------------------------
      // Draw nodes
      // --------------------------------------------------------------

      nodesRef.current.forEach(
        (node) => {
          const isSelected =
            selected &&
            selected.id ===
              node.id;

          const isConnected =
            selected &&
            edgesRef.current.some(
              (edge) =>
                (edge.from ===
                  selected.id &&
                  edge.to ===
                    node.id) ||
                (edge.to ===
                  selected.id &&
                  edge.from ===
                    node.id)
            );

          const isHighlighted =
            node.community ===
            highlightedCluster;

          let radius = 3.2;

          if (isSelected) {
            radius = 6;
          } else if (
            isConnected
          ) {
            radius = 4;
          } else if (
            isHighlighted
          ) {
            radius = 4.5;
          }

          // ------------------------------------------------------------
          // Node glow
          // ------------------------------------------------------------

          if (
            isSelected ||
            isConnected ||
            isHighlighted
          ) {
            const glow =
              ctx.createRadialGradient(
                node.x,
                node.y,
                0,
                node.x,
                node.y,
                isSelected
                  ? 22
                  : 13
              );

            glow.addColorStop(
              0,
              isSelected
                ? "rgba(255,255,255,0.42)"
                : "rgba(255,255,255,0.2)"
            );

            glow.addColorStop(
              1,
              "rgba(255,255,255,0)"
            );

            ctx.beginPath();

            ctx.arc(
              node.x,
              node.y,
              isSelected
                ? 22
                : 13,
              0,
              Math.PI * 2
            );

            ctx.fillStyle =
              glow;

            ctx.globalAlpha =
              isSelected
                ? 0.95
                : 0.65;

            ctx.fill();
          }

          // ------------------------------------------------------------
          // Selected ring
          // ------------------------------------------------------------

          if (isSelected) {
            ctx.beginPath();

            ctx.arc(
              node.x,
              node.y,
              10,
              0,
              Math.PI * 2
            );

            ctx.strokeStyle =
              "#ffffff";

            ctx.globalAlpha = 0.8;

            ctx.lineWidth = 1;

            ctx.stroke();
          }

          // ------------------------------------------------------------
          // Node
          // ------------------------------------------------------------

          ctx.beginPath();

          ctx.arc(
            node.x,
            node.y,
            radius,
            0,
            Math.PI * 2
          );

          ctx.fillStyle =
            isSelected
              ? "#ffffff"
              : isDark
              ? "#cbd5e1"
              : "#64748b";

          ctx.globalAlpha =
            isSelected
              ? 1
              : isConnected
              ? 0.9
              : isHighlighted
              ? 0.8
              : isDark
              ? 0.82
              : 0.72;

          ctx.fill();
        }
      );

      ctx.globalAlpha = 1;

      animationRef.current =
        requestAnimationFrame(
          animate
        );
    };

    animate();

    return () => {
      window.removeEventListener(
        "resize",
        resizeCanvas
      );

      cancelAnimationFrame(
        animationRef.current
      );
    };
  }, []);

  // --------------------------------------------------------------------
  // Find node under cursor
  // --------------------------------------------------------------------

  const getNodeAtPosition = (
    event
  ) => {
    const canvas =
      canvasRef.current;

    if (!canvas) {
      return null;
    }

    const rect =
      canvas.getBoundingClientRect();

    const x =
      event.clientX -
      rect.left;

    const y =
      event.clientY -
      rect.top;

    // Search backwards so recently drawn nodes get priority
    for (
      let i =
        nodesRef.current.length -
        1;
      i >= 0;
      i--
    ) {
      const node =
        nodesRef.current[i];

      const dx =
        node.x - x;

      const dy =
        node.y - y;

      const distance =
        Math.sqrt(
          dx * dx +
            dy * dy
        );

      if (distance < 13) {
        return {
          node,
          x,
          y,
        };
      }
    }

    return null;
  };

  // --------------------------------------------------------------------
  // Mouse move
  // --------------------------------------------------------------------

  const handleMouseMove = (
    event
  ) => {
    const canvas =
      canvasRef.current;

    if (!canvas) return;

    const rect =
      canvas.getBoundingClientRect();

    const x =
      event.clientX -
      rect.left;

    const y =
      event.clientY -
      rect.top;

    mouseRef.current = {
      x,
      y,
    };

    // --------------------------------------------------------------
    // Drag selected node
    // --------------------------------------------------------------

    if (
      draggedNodeRef.current
    ) {
      const node =
        draggedNodeRef.current;

      node.x = x;
      node.y = y;

      node.vx = 0;
      node.vy = 0;

      setTooltipPos({
        x: event.clientX,
        y: event.clientY,
      });

      setHoveredNode(node);

      canvas.style.cursor =
        "grabbing";

      return;
    }

    // --------------------------------------------------------------
    // Hover
    // --------------------------------------------------------------

    const result =
      getNodeAtPosition(
        event
      );

    if (result) {
      setHoveredNode(
        result.node
      );

      setTooltipPos({
        x: event.clientX,
        y: event.clientY,
      });

      canvas.style.cursor =
        "pointer";
    } else {
      setHoveredNode(null);

      canvas.style.cursor =
        "default";
    }
  };

  // --------------------------------------------------------------------
  // Mouse down
  // --------------------------------------------------------------------

  const handleMouseDown = (
    event
  ) => {
    const result =
      getNodeAtPosition(
        event
      );

    if (!result) {
      return;
    }

    draggedNodeRef.current =
      result.node;

    result.node.dragged = true;

    canvasRef.current.style.cursor =
      "grabbing";
  };

  // --------------------------------------------------------------------
  // Mouse up / click
  // --------------------------------------------------------------------

  const handleMouseUp = (
    event
  ) => {
    const dragged =
      draggedNodeRef.current;

    if (!dragged) {
      return;
    }

    dragged.dragged = false;

    draggedNodeRef.current =
      null;

    canvasRef.current.style.cursor =
      "default";

    // Select the node
    selectedNodeRef.current =
      dragged;

    setSelectedNode({
      ...dragged,
    });

    setHoveredNode(dragged);

    setTooltipPos({
      x: event.clientX,
      y: event.clientY,
    });
  };

  // --------------------------------------------------------------------
  // Click empty background
  // --------------------------------------------------------------------

  const handleCanvasClick = (
    event
  ) => {
    const result =
      getNodeAtPosition(
        event
      );

    if (!result) {
      selectedNodeRef.current =
        null;

      setSelectedNode(null);

      setHoveredNode(null);
    }
  };

  // --------------------------------------------------------------------
  // Mouse leave
  // --------------------------------------------------------------------

  const handleMouseLeave = () => {
    mouseRef.current = {
      x: -1000,
      y: -1000,
    };

    setHoveredNode(null);

    if (
      draggedNodeRef.current
    ) {
      draggedNodeRef.current.dragged =
        false;

      draggedNodeRef.current =
        null;
    }

    if (canvasRef.current) {
      canvasRef.current.style.cursor =
        "default";
    }
  };

  return (
    <>
      <canvas
        ref={canvasRef}
        aria-label="Interactive RingWatch fraud network"
        className="pointer-events-auto absolute inset-0 z-[1] h-full w-full touch-none"
        onMouseMove={
          handleMouseMove
        }
        onMouseDown={
          handleMouseDown
        }
        onMouseUp={
          handleMouseUp
        }
        onClick={
          handleCanvasClick
        }
        onMouseLeave={
          handleMouseLeave
        }
      />

      {/* Readability layer */}
      <div
        className="pointer-events-none absolute inset-0 z-[2] bg-white/18 dark:bg-slate-950/10"
        aria-hidden="true"
      />

      {/* --------------------------------------------------------------
          Interactive node tooltip
      -------------------------------------------------------------- */}

      {hoveredNode && (
        <div
          className="pointer-events-none fixed z-50 min-w-[210px] rounded-xl border border-border bg-card/90 p-3 text-sm shadow-xl backdrop-blur-xl"
          style={{
            left:
              tooltipPos.x + 14,
            top:
              tooltipPos.y + 14,
          }}
        >
          <div className="mb-3 flex items-center justify-between gap-4">
            <div>
              <div className="font-mono text-xs font-semibold text-foreground">
                Account #
                {
                  hoveredNode.id
                }
              </div>

              <div className="mt-0.5 text-[10px] uppercase tracking-wider text-muted-foreground">
                Network node
              </div>
            </div>

            {selectedNode?.id ===
              hoveredNode.id && (
              <span className="rounded-full border border-primary/30 bg-primary/10 px-2 py-1 text-[9px] font-semibold uppercase tracking-wide text-primary">
                Selected
              </span>
            )}
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between gap-5">
              <span className="text-muted-foreground">
                Risk
              </span>

              <span className="font-semibold text-foreground">
                {
                  hoveredNode.risk
                }
              </span>
            </div>

            <div className="flex items-center justify-between gap-5">
              <span className="text-muted-foreground">
                Identity
              </span>

              <span className="font-semibold text-foreground">
                {
                  hoveredNode.sharedIdentity
                }
              </span>
            </div>

            <div className="flex items-center justify-between gap-5">
              <span className="text-muted-foreground">
                Community
              </span>

              <span className="font-semibold text-foreground">
                #
                {
                  hoveredNode.community +
                    1
                }
              </span>
            </div>

            <div className="flex items-center justify-between gap-5">
              <span className="text-muted-foreground">
                Connections
              </span>

              <span className="font-semibold text-foreground">
                {
                  hoveredNode.connections
                }
              </span>
            </div>
          </div>

          <div className="mt-3 border-t border-border pt-2 text-[10px] text-muted-foreground">
            Click and drag to investigate
          </div>
        </div>
      )}
    </>
  );
}

// ----------------------------------------------------------------------
// Watching indicator
// ----------------------------------------------------------------------

const WATCHING_ITEMS = [
  "Shared Devices",
  "Shared Phones",
  "Shared Addresses",
  "Shared Payments",
  "Shared Coupons",
];

function WatchingText() {
  const [index, setIndex] =
    useState(0);

  const reduceMotion =
    useReducedMotion();

  useEffect(() => {
    const interval =
      setInterval(() => {
        setIndex(
          (previous) =>
            (previous + 1) %
            WATCHING_ITEMS.length
        );
      }, 2200);

    return () =>
      clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground lg:justify-start">
      <span className="inline-flex items-center gap-2">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-60" />

          <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
        </span>

        Watching
      </span>

      <span className="text-muted-foreground">
        /
      </span>

      <motion.span
        key={index}
        initial={
          reduceMotion
            ? {
                opacity: 1,
              }
            : {
                opacity: 0,
                y: 8,
              }
        }
        animate={{
          opacity: 1,
          y: 0,
        }}
        transition={{
          duration: 0.3,
        }}
        className="font-semibold text-foreground"
      >
        {
          WATCHING_ITEMS[
            index
          ]
        }
      </motion.span>
    </div>
  );
}

// ----------------------------------------------------------------------
// Live counters
// ----------------------------------------------------------------------

const TARGET_VALUES = {
  accounts: 125000,
  rings: 842,
  highRisk: 3567,
  investigations: 1204,
};

function LiveCounters() {
  const [counts, setCounts] =
    useState({
      accounts: 0,
      rings: 0,
      highRisk: 0,
      investigations: 0,
    });

  const reduceMotion =
    useReducedMotion();

  useEffect(() => {
    const duration = 1800;

    const start =
      performance.now();

    let frame;

    const step = (now) => {
      const elapsed =
        now - start;

      const progress = Math.min(
        elapsed / duration,
        1
      );

      const eased =
        1 -
        Math.pow(
          1 - progress,
          3
        );

      setCounts({
        accounts: Math.floor(
          TARGET_VALUES.accounts *
            eased
        ),

        rings: Math.floor(
          TARGET_VALUES.rings *
            eased
        ),

        highRisk: Math.floor(
          TARGET_VALUES.highRisk *
            eased
        ),

        investigations:
          Math.floor(
            TARGET_VALUES.investigations *
              eased
          ),
      });

      if (progress < 1) {
        frame =
          requestAnimationFrame(
            step
          );
      }
    };

    frame =
      requestAnimationFrame(
        step
      );

    return () =>
      cancelAnimationFrame(
        frame
      );
  }, []);

  useEffect(() => {
    const interval =
      setInterval(() => {
        setCounts(
          (previous) => ({
            accounts:
              previous.accounts +
              Math.floor(
                Math.random() * 5
              ),

            rings:
              previous.rings +
              (Math.random() <
              0.3
                ? 1
                : 0),

            highRisk:
              previous.highRisk +
              Math.floor(
                Math.random() * 3
              ),

            investigations:
              previous.investigations +
              (Math.random() <
              0.2
                ? 1
                : 0),
          })
        );
      }, 4500);

    return () =>
      clearInterval(interval);
  }, []);

  const items = [
    {
      label: "Accounts Screened",
      value:
        counts.accounts.toLocaleString(),
    },
    {
      label: "Fraud Rings",
      value:
        counts.rings.toLocaleString(),
    },
    {
      label: "High Risk Accounts",
      value:
        counts.highRisk.toLocaleString(),
    },
    {
      label: "Investigations",
      value:
        counts.investigations.toLocaleString(),
    },
  ];

  return (
    <div className="mt-10 grid grid-cols-2 gap-x-8 gap-y-6 border-y border-border/60 py-6 md:grid-cols-4">
      {items.map((item) => (
        <div
          key={item.label}
          className="text-center lg:text-left"
        >
          <div className="tabular-nums text-2xl font-bold tracking-tight text-foreground md:text-3xl">
            {reduceMotion ? (
              item.value
            ) : (
              <motion.span
                initial={{
                  opacity: 0,
                }}
                animate={{
                  opacity: 1,
                }}
                transition={{
                  duration: 0.5,
                }}
              >
                {item.value}
              </motion.span>
            )}
          </div>

          <div className="mt-1 text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground md:text-xs">
            {item.label}
          </div>
        </div>
      ))}
    </div>
  );
}

// ----------------------------------------------------------------------
// Live investigation feed
// ----------------------------------------------------------------------

const INVESTIGATION_FEED = [
  {
    id: "A021551",
    severity: "CRITICAL",
    shared: "Shared Device",
  },
  {
    id: "A015220",
    severity: "HIGH",
    shared: "Shared Address",
  },
  {
    id: "A004411",
    severity: "MEDIUM",
    shared: "Coupon Network",
  },
  {
    id: "A033728",
    severity: "HIGH",
    shared: "Shared Phone",
  },
  {
    id: "A027903",
    severity: "CRITICAL",
    shared: "Shared Payment",
  },
];

function LiveFeed() {
  const [index, setIndex] =
    useState(0);

  const reduceMotion =
    useReducedMotion();

  useEffect(() => {
    const interval =
      setInterval(() => {
        setIndex(
          (previous) =>
            (previous + 1) %
            INVESTIGATION_FEED.length
        );
      }, 3000);

    return () =>
      clearInterval(interval);
  }, []);

  const current =
    INVESTIGATION_FEED[index];

  const severityColors = {
    CRITICAL:
      "border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-300",

    HIGH:
      "border-orange-500/30 bg-orange-500/10 text-orange-600 dark:text-orange-300",

    MEDIUM:
      "border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-300",

    LOW:
      "border-slate-500/30 bg-slate-500/10 text-slate-600 dark:text-slate-300",
  };

  return (
    <div className="w-full max-w-sm rounded-2xl border border-border bg-card/70 p-5 shadow-xl backdrop-blur-2xl">
      <div className="mb-5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" />

          <span className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Live Investigation
          </span>
        </div>

        <span className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />

          Live
        </span>
      </div>

      <motion.div
        key={current.id}
        initial={
          reduceMotion
            ? {
                opacity: 1,
              }
            : {
                opacity: 0,
                y: 8,
              }
        }
        animate={{
          opacity: 1,
          y: 0,
        }}
        transition={{
          duration: 0.3,
        }}
      >
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="font-mono text-sm font-medium text-foreground">
              {current.id}
            </div>

            <div className="mt-1 text-sm text-muted-foreground">
              {current.shared}
            </div>
          </div>

          <span
            className={`rounded-full border px-2.5 py-1 text-[10px] font-bold tracking-wide ${severityColors[current.severity]}`}
          >
            {current.severity}
          </span>
        </div>

        <div className="mt-5 h-px bg-border" />

        <div className="mt-4 grid grid-cols-2 gap-3">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Signal
            </div>

            <div className="mt-1 text-xs font-medium text-foreground">
              Cross-account link
            </div>
          </div>

          <div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Status
            </div>

            <div className="mt-1 text-xs font-medium text-foreground">
              Investigating
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

// ----------------------------------------------------------------------
// Theme toggle
// ----------------------------------------------------------------------

function ThemeToggle() {
  const [dark, setDark] =
    useState(() => {
      if (
        typeof window ===
        "undefined"
      ) {
        return true;
      }

      const stored =
        localStorage.getItem(
          "theme"
        );

      return stored === null
        ? true
        : stored === "dark";
    });

  useEffect(() => {
    document.documentElement.classList.toggle(
      "dark",
      dark
    );

    try {
      localStorage.setItem(
        "theme",
        dark
          ? "dark"
          : "light"
      );
    } catch {
      // Ignore storage errors.
    }
  }, [dark]);

  return (
    <button
      type="button"
      onClick={() =>
        setDark(
          (previous) =>
            !previous
        )
      }
      aria-label={
        dark
          ? "Switch to light mode"
          : "Switch to dark mode"
      }
      title={
        dark
          ? "Switch to light mode"
          : "Switch to dark mode"
      }
      className="group flex h-10 items-center gap-2 rounded-full border border-border bg-card/75 px-3 text-muted-foreground shadow-sm backdrop-blur-xl transition-all hover:bg-accent hover:text-foreground"
    >
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-muted/70">
        {dark ? (
          <Sun className="h-3.5 w-3.5" />
        ) : (
          <Moon className="h-3.5 w-3.5" />
        )}
      </span>

      <span className="hidden text-xs font-medium sm:block">
        {dark
          ? "Light"
          : "Dark"}
      </span>
    </button>
  );
}

// ----------------------------------------------------------------------
// Landing Page
// ----------------------------------------------------------------------

export default function Landing() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-background text-foreground">
      {/* ------------------------------------------------------------
          Interactive graph
      ------------------------------------------------------------ */}

      <FraudGraphBackground />

      {/* Readability gradient */}
      <div className="pointer-events-none absolute inset-0 z-[3] bg-gradient-to-b from-background/5 via-transparent to-background/15" />

      {/* ------------------------------------------------------------
          Top navigation
      ------------------------------------------------------------ */}

      <header className="relative z-20 flex items-center justify-between px-6 py-5 md:px-10">
        <Link
          to="/"
          className="rounded-lg"
        >
          <Logo
            size="md"
            showName
          />
        </Link>

        <div className="flex items-center gap-3">
          <div className="hidden items-center gap-2 rounded-full border border-border bg-card/65 px-3 py-2 text-xs text-muted-foreground shadow-sm backdrop-blur-xl md:flex">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />

            <span>
              Investigation system online
            </span>
          </div>

          <ThemeToggle />
        </div>
      </header>

      {/* ------------------------------------------------------------
          Main content
      ------------------------------------------------------------ */}

      <main className="pointer-events-none relative z-10 mx-auto flex min-h-[calc(100vh-84px)] max-w-7xl items-center px-6 pb-16 pt-10 md:px-10 lg:pt-0">
        <div className="pointer-events-auto grid w-full items-center gap-12 lg:grid-cols-[minmax(0,1fr)_360px] lg:gap-20">
          {/* --------------------------------------------------------
              Hero
          -------------------------------------------------------- */}

          <div className="max-w-4xl text-center lg:text-left">
            <motion.div
              initial={{
                opacity: 0,
                y: 10,
              }}
              animate={{
                opacity: 1,
                y: 0,
              }}
              transition={{
                duration: 0.5,
              }}
              className="flex justify-center lg:justify-start"
            >
              <div className="rounded-2xl border border-border bg-card/65 p-3 shadow-lg backdrop-blur-xl">
                <Logo
                  size="lg"
                  showName={false}
                />
              </div>
            </motion.div>

            <motion.div
              initial={{
                opacity: 0,
                y: 20,
              }}
              animate={{
                opacity: 1,
                y: 0,
              }}
              transition={{
                delay: 0.08,
                duration: 0.6,
              }}
            >
              <h1 className="mt-7 text-5xl font-bold tracking-[-0.04em] text-foreground sm:text-6xl md:text-7xl lg:text-[5.5rem]">
                RingWatch
              </h1>

              <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg lg:mx-0">
                Post-delivery refund abuse detection
                through cross-account graph analysis.
              </p>
            </motion.div>

            {/* Watching */}
            <motion.div
              initial={{
                opacity: 0,
              }}
              animate={{
                opacity: 1,
              }}
              transition={{
                delay: 0.25,
              }}
              className="mt-5"
            >
              <WatchingText />
            </motion.div>

            {/* Counters */}
            <motion.div
              initial={{
                opacity: 0,
              }}
              animate={{
                opacity: 1,
              }}
              transition={{
                delay: 0.35,
              }}
            >
              <LiveCounters />
            </motion.div>

            {/* ------------------------------------------------------
                CTA buttons
            ------------------------------------------------------ */}

            <motion.div
              initial={{
                opacity: 0,
                y: 15,
              }}
              animate={{
                opacity: 1,
                y: 0,
              }}
              transition={{
                delay: 0.5,
                duration: 0.5,
              }}
              className="mt-8 flex flex-col justify-center gap-3 sm:flex-row lg:justify-start"
            >
              <Link
                to="/dashboard"
                className="group inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground shadow-lg transition-all hover:opacity-90 sm:w-auto"
              >
                Open Dashboard

                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </Link>

              <Link
                to="/about"
                className="inline-flex w-full items-center justify-center rounded-lg border border-border bg-card/55 px-6 py-3 text-sm font-semibold text-foreground shadow-sm backdrop-blur-xl transition-all hover:bg-accent sm:w-auto"
              >
                Explore RingWatch
              </Link>
            </motion.div>

            {/* Trust line */}
            <motion.div
              initial={{
                opacity: 0,
              }}
              animate={{
                opacity: 1,
              }}
              transition={{
                delay: 0.7,
              }}
              className="mt-6 flex flex-wrap items-center justify-center gap-2 text-[11px] text-muted-foreground lg:justify-start"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />

              Deterministic policy enforcement

              <span className="text-border">
                •
              </span>

              Human review

              <span className="text-border">
                •
              </span>

              Full audit trail
            </motion.div>
          </div>

          {/* --------------------------------------------------------
              Live investigation
          -------------------------------------------------------- */}

          <motion.div
            initial={{
              opacity: 0,
              x: 25,
            }}
            animate={{
              opacity: 1,
              x: 0,
            }}
            transition={{
              delay: 0.55,
              duration: 0.65,
            }}
            className="flex justify-center lg:justify-end"
          >
            <div className="w-full max-w-sm">
              <LiveFeed />

              {/* Graph legend */}
              <div className="mt-4 grid grid-cols-3 gap-2">
                {[
                  {
                    label: "Device",
                    color:
                      EDGE_COLORS.Device,
                  },
                  {
                    label: "Address",
                    color:
                      EDGE_COLORS.Address,
                  },
                  {
                    label: "Payment",
                    color:
                      EDGE_COLORS.Payment,
                  },
                ].map(
                  (signal) => (
                    <div
                      key={
                        signal.label
                      }
                      className="flex items-center gap-2 rounded-lg border border-border bg-card/55 px-3 py-2 backdrop-blur-xl"
                    >
                      <span
                        className="h-2 w-2 rounded-full"
                        style={{
                          backgroundColor:
                            signal.color,

                          boxShadow: `0 0 10px ${signal.color}`,
                        }}
                      />

                      <span className="text-[10px] font-medium text-muted-foreground">
                        {
                          signal.label
                        }
                      </span>
                    </div>
                  )
                )}
              </div>

              {/* Interaction hint */}
              <div className="mt-3 text-center text-[10px] uppercase tracking-[0.14em] text-muted-foreground/60">
                Hover • Click • Drag network nodes
              </div>
            </div>
          </motion.div>
        </div>
      </main>

      {/* ------------------------------------------------------------
          Footer
      ------------------------------------------------------------ */}

      <div className="pointer-events-none absolute bottom-4 left-0 right-0 z-10 text-center">
        <span className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground/60">
          RingWatch • Post-delivery abuse intelligence
        </span>
      </div>
    </div>
  );
}