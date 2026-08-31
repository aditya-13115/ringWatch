import { motion, useReducedMotion } from "framer-motion";
import {
  AlertTriangle,
  Network,
  Scale,
  Database,
  Sliders,
  Share2,
  Layers,
  Search,
  Cpu,
  ClipboardCheck,
} from "lucide-react";
import Logo from "../components/Logo";
import GlassPanel from "../components/GlassPanel";
import CountUp from "../components/CountUp";
import { DATASET, MODEL, EDGE_TYPES, PIPELINE, TECH_STACK } from "../constants";

// Pipeline step names -> icon components (kept explicit so the bundle only
// pulls the icons actually used).
const STEP_ICONS = { Database, Sliders, Share2, Layers, Search, Cpu, Scale, ClipboardCheck };

function Eyebrow({ children }) {
  return (
    <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">{children}</p>
  );
}

// Static "shared-identity constellation" — the signature motif: accounts (dots)
// linked by colored identity edges, one flagged focus node. No motion.
function Constellation() {
  const nodes = [
    { x: 130, y: 60 },
    { x: 40, y: 120 },
    { x: 210, y: 110 },
    { x: 90, y: 190 },
    { x: 190, y: 200 },
    { x: 130, y: 130, focus: true },
  ];
  const edges = [
    [5, 0, "#3b82f6"],
    [5, 1, "#10b981"],
    [5, 2, "#f59e0b"],
    [5, 3, "#8b5cf6"],
    [5, 4, "#ef4444"],
    [0, 2, "#3b82f6"],
    [1, 3, "#10b981"],
  ];
  return (
    <svg viewBox="0 0 250 250" className="h-full w-full" role="img" aria-label="A network of accounts linked by shared identities">
      {edges.map(([a, b, color], i) => (
        <line
          key={i}
          x1={nodes[a].x}
          y1={nodes[a].y}
          x2={nodes[b].x}
          y2={nodes[b].y}
          stroke={color}
          strokeWidth={1.5}
          strokeOpacity={0.55}
        />
      ))}
      {nodes.map((n, i) => (
        <g key={i}>
          {n.focus && <circle cx={n.x} cy={n.y} r={16} fill="none" stroke="hsl(var(--destructive))" strokeOpacity={0.4} />}
          <circle
            cx={n.x}
            cy={n.y}
            r={n.focus ? 8 : 5}
            fill={n.focus ? "hsl(var(--destructive))" : "hsl(var(--foreground))"}
            fillOpacity={n.focus ? 1 : 0.75}
          />
        </g>
      ))}
    </svg>
  );
}

export default function About() {
  const reduce = useReducedMotion();

  const stats = [
    { value: DATASET.accounts, label: "Accounts" },
    { value: DATASET.orders, label: "Orders" },
    { value: DATASET.refunds, label: "Refunds" },
    { value: DATASET.disputes, label: "Disputes" },
    { value: DATASET.rings, label: "Rings seeded" },
    { value: DATASET.ringMembers, label: "Ring members" },
  ];

  return (
    <div className="mx-auto max-w-5xl space-y-16 pb-8">
      {/* Hero */}
      <section className="grid grid-cols-1 items-center gap-8 md:grid-cols-2">
        <div className="space-y-5">
          <div className="flex items-center gap-3">
            <Logo size="md" showName={false} />
            <Eyebrow>Fraud-ring intelligence</Eyebrow>
          </div>
          <h1 className="text-4xl font-bold leading-tight tracking-tight">
            Fraud rings hide in the connections, not the accounts.
          </h1>
          <p className="text-lg text-muted-foreground">
            RingWatch scores individual accounts, then reads the graph of shared
            devices, addresses, and payment instruments that ties them together —
            surfacing coordinated refund abuse a per-account score misses.
          </p>
          <div className="flex flex-wrap gap-x-8 gap-y-2 pt-1 text-sm text-muted-foreground">
            <span><span className="font-semibold text-foreground">{DATASET.accounts.toLocaleString()}</span> accounts monitored</span>
            <span><span className="font-semibold text-foreground">{DATASET.rings}</span> rings seeded</span>
            <span><span className="font-semibold text-foreground">{EDGE_TYPES.length}</span> identity signals</span>
          </div>
        </div>
        <GlassPanel className="mx-auto aspect-square w-full max-w-sm p-6">
          <Constellation />
        </GlassPanel>
      </section>

      {/* Problem / Solution */}
      <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <GlassPanel className="p-6">
          <AlertTriangle className="h-5 w-5 text-muted-foreground" />
          <h2 className="mt-3 text-lg font-semibold">The problem</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Refund and return abuse is usually a team sport: many accounts acting
            together, each one individually unremarkable. Per-account risk scores
            rate them in isolation and never see the coordination.
          </p>
        </GlassPanel>
        <GlassPanel className="p-6">
          <Network className="h-5 w-5 text-muted-foreground" />
          <h2 className="mt-3 text-lg font-semibold">The approach</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Build a graph of shared identities, detect communities, and combine
            behavioral features with graph structure — flagging rings from patterns
            that emerge before disputes are ever filed.
          </p>
        </GlassPanel>
      </section>

      {/* How it works — numbered stepper (the pipeline is a real ordered sequence) */}
      <section className="space-y-6">
        <div className="space-y-1">
          <Eyebrow>How it works</Eyebrow>
          <h2 className="text-2xl font-semibold">Detection to decision, in eight steps</h2>
        </div>
        <ol className="relative space-y-4 border-l border-border pl-6">
          {PIPELINE.map((step, i) => {
            const Icon = STEP_ICONS[step.icon];
            return (
              <motion.li
                key={step.title}
                initial={reduce ? false : { opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-8%" }}
                transition={{ duration: 0.4, delay: reduce ? 0 : i * 0.06 }}
                className="relative"
              >
                <span className="absolute -left-[34px] flex h-7 w-7 items-center justify-center rounded-full border border-border bg-card text-xs font-semibold tabular-nums backdrop-blur-lg">
                  {i + 1}
                </span>
                <GlassPanel className="flex items-start gap-3 p-4">
                  {Icon && <Icon className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" />}
                  <div>
                    <h3 className="font-medium">{step.title}</h3>
                    <p className="text-sm text-muted-foreground">{step.detail}</p>
                  </div>
                </GlassPanel>
              </motion.li>
            );
          })}
        </ol>
      </section>

      {/* Shared-identity edges */}
      <section className="space-y-6">
        <div className="space-y-1">
          <Eyebrow>The vocabulary</Eyebrow>
          <h2 className="text-2xl font-semibold">Shared-identity signals</h2>
          <p className="text-sm text-muted-foreground">
            Each edge type carries a heuristic weight — how strongly it hints at a real link.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {EDGE_TYPES.map((edge) => (
            <GlassPanel key={edge.key} className="p-4">
              <div className="flex items-center gap-2">
                <span className="h-3 w-3 rounded-full" style={{ backgroundColor: edge.color }} />
                <span className="font-medium">{edge.label}</span>
                <span className="ml-auto text-xs tabular-nums text-muted-foreground">{edge.weight.toFixed(1)}</span>
              </div>
              <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                <div className="h-full rounded-full" style={{ width: `${edge.weight * 100}%`, backgroundColor: edge.color }} />
              </div>
            </GlassPanel>
          ))}
        </div>
      </section>

      {/* Human-in-the-loop callout */}
      <GlassPanel className="flex flex-col gap-4 p-6 sm:flex-row sm:items-center">
        <Scale className="h-8 w-8 shrink-0 text-muted-foreground" />
        <div>
          <h2 className="text-lg font-semibold">The AI explains. A policy engine decides.</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            The AI investigator gathers evidence and drafts a case narrative, but the
            final action is always chosen by a deterministic policy engine — never the
            language model — and every decision lands in the audit trail for human review.
          </p>
        </div>
      </GlassPanel>

      {/* By the numbers */}
      <section className="space-y-6">
        <div className="space-y-1">
          <Eyebrow>By the numbers</Eyebrow>
          <h2 className="text-2xl font-semibold">The prototype dataset</h2>
        </div>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
          {stats.map((s) => (
            <GlassPanel key={s.label} className="p-4 text-center">
              <div className="text-2xl font-semibold tabular-nums">
                <CountUp value={s.value} />
              </div>
              <div className="mt-1 text-xs text-muted-foreground">{s.label}</div>
            </GlassPanel>
          ))}
        </div>
        <p className="text-sm text-muted-foreground">
          Model: <span className="font-medium text-foreground">{MODEL.name}</span> ({MODEL.detail}) · decision
          threshold ≈ {MODEL.threshold}
        </p>
      </section>

      {/* Limitations */}
      <section className="space-y-3">
        <Eyebrow>Honest limitations</Eyebrow>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li>· Built on synthetic data — patterns are seeded, not observed in the wild.</li>
          <li>· The graph model did not improve global PR-AUC, though it lifts operational precision on the accounts analysts actually review.</li>
          <li>· A prototype for demonstration, not a production fraud system.</li>
        </ul>
      </section>

      {/* Tech stack */}
      <section className="space-y-3">
        <Eyebrow>Built with</Eyebrow>
        <div className="flex flex-wrap gap-2">
          {TECH_STACK.map((tech) => (
            <span key={tech} className="rounded-full border border-border bg-card px-3 py-1 text-xs backdrop-blur-lg">
              {tech}
            </span>
          ))}
        </div>
      </section>
    </div>
  );
}
