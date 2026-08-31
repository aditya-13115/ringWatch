import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import {
  Radar,
  Users,
  ShieldAlert,
  Share2,
  Cpu,
  RefreshCw,
  Pause,
  Play,
  Server,
} from "lucide-react";
import { getQueue } from "../api/queue";
import { getAudit } from "../api/audit";
import { getGraphOverview } from "../api/graph";
import { apiFetch } from "../api/client";
import GlassPanel from "../components/GlassPanel";
import CountUp from "../components/CountUp";
import Sparkline from "../components/Sparkline";
import Badge from "../components/Badge";
import { TIERS, TIER_ORDER, MODEL } from "../constants";

const FAST_MS = 8000; // audit + health — the append-growing sources
const SLOW_MS = 60000; // queue — changes rarely

function actionOf(record) {
  return record.action_recommended || record.recommended_action || "—";
}

function isInvestigation(record) {
  return (
    record.investigation_source === "llm" ||
    record.investigation_source === "deterministic" ||
    Boolean(record.tool_calls) ||
    Boolean(record.summary)
  );
}

function timeOf(ts) {
  if (!ts) return "—";
  const d = new Date(ts);
  return isNaN(d) ? "—" : d.toLocaleTimeString();
}

// Bucket a tier's prediction timestamps across the audit window into a small
// trend series for the sparkline. Honest: this is the recorded window, not a
// rolling wall-clock feed.
function timeline(records, tier, buckets = 14) {
  const ts = records
    .filter((r) => r.risk_tier === tier && r.timestamp)
    .map((r) => new Date(r.timestamp).getTime())
    .filter((n) => !isNaN(n));
  if (!ts.length) return [];
  const min = Math.min(...ts);
  const max = Math.max(...ts);
  const span = max - min || 1;
  const arr = new Array(buckets).fill(0);
  ts.forEach((t) => {
    const idx = Math.min(buckets - 1, Math.floor(((t - min) / span) * (buckets - 1)));
    arr[idx] += 1;
  });
  return arr;
}

export default function LiveOps() {
  const reduce = useReducedMotion();

  const [accounts, setAccounts] = useState([]);
  const [total, setTotal] = useState(0);
  const [records, setRecords] = useState([]);
  const [nodes, setNodes] = useState([]);
  const [health, setHealth] = useState(null); // { ok } | null
  const [connected, setConnected] = useState(true);
  const [lastPoll, setLastPoll] = useState(null);
  const [paused, setPaused] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // ---- pollers (setters are stable; safe to define at render scope) ----
  const pingHealth = async () => {
    try {
      const h = await apiFetch("/health");
      setHealth({ ok: h?.status === "ok" });
    } catch {
      setHealth({ ok: false });
    }
  };

  const pollFast = async () => {
    try {
      const a = await getAudit();
      setRecords(Array.isArray(a?.records) ? a.records : []);
      setConnected(true);
    } catch {
      setConnected(false);
    }
    await pingHealth();
    setLastPoll(Date.now());
  };

  const pollSlow = async () => {
    try {
      const q = await getQueue(100000);
      setAccounts(q.accounts || []);
      setTotal(q.total ?? (q.accounts?.length || 0));
      setConnected(true);
    } catch {
      setConnected(false);
    }
  };

  // Initial load — everything once, graph never polled again.
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [q, a, g] = await Promise.all([getQueue(100000), getAudit(), getGraphOverview()]);
        if (!alive) return;
        setAccounts(q.accounts || []);
        setTotal(q.total ?? (q.accounts?.length || 0));
        setRecords(Array.isArray(a?.records) ? a.records : []);
        setNodes(g?.nodes || []);
      } catch (e) {
        if (alive) setError(e.message);
      } finally {
        if (alive) setLoading(false);
      }
      if (alive) {
        await pingHealth();
        setLastPoll(Date.now());
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  // Tiered polling — paused halts it; toggling restarts cleanly.
  useEffect(() => {
    if (paused) return;
    const fast = setInterval(pollFast, FAST_MS);
    const slow = setInterval(pollSlow, SLOW_MS);
    return () => {
      clearInterval(fast);
      clearInterval(slow);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paused]);

  // ---- derived ----
  const tierCounts = useMemo(() => {
    const c = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    accounts.forEach((a) => {
      if (c[a.risk_tier] != null) c[a.risk_tier] += 1;
    });
    return c;
  }, [accounts]);
  const tierMax = Math.max(1, ...TIER_ORDER.map((t) => tierCounts[t]));

  const rings = useMemo(() => {
    const groups = new Map();
    nodes.forEach((n) => {
      if (n.community_id == null) return;
      const k = String(n.community_id);
      groups.set(k, (groups.get(k) || 0) + 1);
    });
    return [...groups.entries()]
      .map(([id, size]) => ({ id, size }))
      .filter((r) => r.size > 1)
      .sort((a, b) => b.size - a.size);
  }, [nodes]);

  const investigations = useMemo(() => records.filter(isInvestigation).length, [records]);

  const feed = useMemo(
    () =>
      [...records]
        .filter((r) => r.timestamp)
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
        .slice(0, 12)
        .map((r, i) => ({ ...r, _key: `${r.timestamp}-${r.account_id ?? i}` })),
    [records]
  );

  if (loading) return <div className="p-6">Loading live operations…</div>;
  if (error) return <div className="p-6 text-destructive">{error}</div>;

  const kpis = [
    { label: "Flagged accounts", value: total, icon: Users },
    { label: "Critical risk", value: tierCounts.CRITICAL, icon: ShieldAlert },
    { label: "Rings detected", value: rings.length, icon: Share2 },
    { label: "Investigations logged", value: investigations, icon: Cpu },
  ];

  return (
    <div className="space-y-6">
      {/* Header + controls */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Radar className="h-5 w-5 text-muted-foreground" />
            <h2 className="text-2xl font-semibold">Live Operations</h2>
          </div>
          <p className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
            <span className="relative flex h-2 w-2" aria-hidden="true">
              {!paused && (
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75 motion-reduce:animate-none" />
              )}
              <span className={`relative inline-flex h-2 w-2 rounded-full ${paused ? "bg-muted-foreground" : "bg-emerald-500"}`} />
            </span>
            {paused ? "Paused" : `Live · polling every ${FAST_MS / 1000}s`}
            {lastPoll && <span>· updated {timeOf(lastPoll)}</span>}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setPaused((p) => !p)}
            className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          >
            {paused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
            {paused ? "Resume" : "Pause"}
          </button>
          <button
            onClick={() => {
              pollFast();
              pollSlow();
            }}
            className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {kpis.map((k) => (
          <GlassPanel key={k.label} hover className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">{k.label}</span>
              <k.icon className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="mt-2 text-3xl font-semibold tabular-nums">
              <CountUp value={k.value} />
            </div>
          </GlassPanel>
        ))}
      </div>

      {/* Feed + right rail */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Live feed */}
        <GlassPanel className="lg:col-span-2">
          <div className="flex items-center justify-between border-b border-border p-4">
            <div>
              <h3 className="font-medium">Live decision feed</h3>
              <p className="text-xs text-muted-foreground">
                Most recent audit records · updated {lastPoll ? timeOf(lastPoll) : "—"}
              </p>
            </div>
            <span className="text-xs text-muted-foreground">{feed.length} shown</span>
          </div>
          <div className="divide-y divide-border">
            <AnimatePresence initial={false}>
              {feed.map((r) => (
                <motion.div
                  key={r._key}
                  layout={!reduce}
                  initial={reduce ? false : { opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={reduce ? undefined : { opacity: 0 }}
                  transition={{ duration: 0.25 }}
                  className="flex items-center gap-3 px-4 py-3 text-sm"
                >
                  <span className="w-20 shrink-0 font-mono text-xs text-muted-foreground">{timeOf(r.timestamp)}</span>
                  {r.account_id ? (
                    <Link
                      to={`/investigations/${r.account_id}`}
                      className="w-28 shrink-0 truncate underline underline-offset-4 hover:text-primary"
                    >
                      {r.account_id}
                    </Link>
                  ) : (
                    <span className="w-28 shrink-0 text-muted-foreground">—</span>
                  )}
                  <span className="shrink-0">{r.risk_tier ? <Badge tier={r.risk_tier} /> : null}</span>
                  <span className="ml-auto truncate text-muted-foreground">{actionOf(r)}</span>
                </motion.div>
              ))}
            </AnimatePresence>
            {feed.length === 0 && (
              <div className="px-4 py-8 text-center text-sm text-muted-foreground">
                No audit activity recorded yet.
              </div>
            )}
          </div>
        </GlassPanel>

        {/* Right rail: system health + ring summary */}
        <div className="space-y-4">
          <GlassPanel className="p-4">
            <div className="mb-3 flex items-center gap-2">
              <Server className="h-4 w-4 text-muted-foreground" />
              <h3 className="font-medium">System health</h3>
            </div>
            <dl className="space-y-2 text-sm">
              <HealthRow label="Backend" ok={health?.ok} okText="Healthy" badText="Unreachable" />
              <HealthRow label="API" ok={connected} okText="Connected" badText="Disconnected" />
              <div className="flex items-center justify-between">
                <dt className="text-muted-foreground">Poll interval</dt>
                <dd className="tabular-nums">{FAST_MS / 1000}s</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-muted-foreground">Last poll</dt>
                <dd className="tabular-nums">{lastPoll ? timeOf(lastPoll) : "—"}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-muted-foreground">Model</dt>
                <dd>{MODEL.name}</dd>
              </div>
            </dl>
          </GlassPanel>

          <GlassPanel className="p-4">
            <h3 className="mb-1 font-medium">Ring summary</h3>
            <p className="text-xs text-muted-foreground">Multi-member communities in the shared-identity graph.</p>
            <div className="mt-3 flex gap-6">
              <div>
                <div className="text-2xl font-semibold tabular-nums">
                  <CountUp value={rings.length} />
                </div>
                <div className="text-xs text-muted-foreground">rings</div>
              </div>
              <div>
                <div className="text-2xl font-semibold tabular-nums">
                  <CountUp value={rings[0]?.size || 0} />
                </div>
                <div className="text-xs text-muted-foreground">largest ring</div>
              </div>
            </div>
            <ul className="mt-4 space-y-2">
              {rings.slice(0, 3).map((r, i) => (
                <li key={r.id} className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">
                    #{i + 1} · community {r.id}
                  </span>
                  <span className="tabular-nums">{r.size} accounts</span>
                </li>
              ))}
              {rings.length === 0 && <li className="text-sm text-muted-foreground">No rings in the current graph.</li>}
            </ul>
          </GlassPanel>
        </div>
      </div>

      {/* Tier distribution + risk timeline */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <GlassPanel className="p-4 lg:col-span-2">
          <h3 className="mb-1 font-medium">Risk tier distribution</h3>
          <p className="text-xs text-muted-foreground">Flagged accounts by tier across the full queue.</p>
          <div className="mt-4 space-y-3">
            {TIER_ORDER.map((tier) => {
              const count = tierCounts[tier];
              const pct = Math.round((count / tierMax) * 100);
              return (
                <div key={tier}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span>{TIERS[tier].label}</span>
                    <span className="tabular-nums text-muted-foreground">
                      <CountUp value={count} />
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                    <motion.div
                      className={`h-full ${TIERS[tier].bar}`}
                      style={{ transformOrigin: "left" }}
                      initial={reduce ? false : { scaleX: 0 }}
                      animate={{ scaleX: pct / 100 }}
                      transition={{ type: "spring", stiffness: 120, damping: 20 }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </GlassPanel>

        <GlassPanel className="p-4">
          <h3 className="mb-1 font-medium">Risk timeline</h3>
          <p className="text-xs text-muted-foreground">Flagging activity across the audit window (bucketed).</p>
          <div className="mt-4 space-y-4">
            {["CRITICAL", "HIGH"].map((tier) => {
              const series = timeline(records, tier);
              return (
                <div key={tier} className="flex items-center justify-between gap-3">
                  <span className="text-sm" style={{ color: TIERS[tier].hex }}>
                    {TIERS[tier].label}
                  </span>
                  <Sparkline data={series} color={TIERS[tier].hex} width={140} height={32} />
                </div>
              );
            })}
          </div>
        </GlassPanel>
      </div>
    </div>
  );
}

function HealthRow({ label, ok, okText, badText }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="flex items-center gap-2">
        <span
          className={`inline-block h-2 w-2 rounded-full ${
            ok == null ? "bg-muted-foreground" : ok ? "bg-emerald-500" : "bg-destructive"
          }`}
        />
        {ok == null ? "Checking…" : ok ? okText : badText}
      </dd>
    </div>
  );
}
