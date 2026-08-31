// Static product facts and shared palettes for the RingWatch UI.
// Centralized so About / Live Ops / Badge stay DRY and free of inline magic values.
// (These describe the shipped prototype dataset + model; they are display copy,
// not a live API source.)

export const DATASET = {
  accounts: 30000,
  orders: 70027,
  refunds: 7158,
  disputes: 570,
  rings: 140,
  ringMembers: 1500,
};

export const MODEL = {
  name: "V4 Ensemble",
  detail: "Tuned LightGBM B + GNN",
  threshold: 0.68,
};

// Shared-identity edge types — the vocabulary the whole product is built on.
// Colors match the graph views; weights are the heuristic evidence strengths.
export const EDGE_TYPES = [
  { key: "shares_device", label: "Device", weight: 1.0, color: "#3b82f6" },
  { key: "shares_phone", label: "Phone", weight: 1.0, color: "#f59e0b" },
  { key: "shares_payment_instrument", label: "Payment", weight: 1.0, color: "#ef4444" },
  { key: "shares_address", label: "Address", weight: 0.7, color: "#10b981" },
  { key: "shares_ip_prefix", label: "IP prefix", weight: 0.3, color: "#8b5cf6" },
  { key: "shares_coupon", label: "Coupon", weight: 0.2, color: "#ec4899" },
];

// Ambient backdrop hues (device / ip / address) — the "Signal field" direction.
export const AMBIENT_BLOBS = ["#3b82f6", "#8b5cf6", "#10b981"];

// Risk tiers — red / orange / blue / slate (deliberately no green).
// `badge` classes are legible in both themes; `bar`/`hex` drive Live Ops charts.
// Class strings are full literals so Tailwind's content scanner keeps them.
export const TIERS = {
  CRITICAL: {
    label: "Critical",
    hex: "#ef4444",
    badge: "bg-red-500/15 text-red-700 dark:text-red-300 border border-red-500/30",
    bar: "bg-red-500",
  },
  HIGH: {
    label: "High",
    hex: "#f97316",
    badge: "bg-orange-500/15 text-orange-700 dark:text-orange-300 border border-orange-500/30",
    bar: "bg-orange-500",
  },
  MEDIUM: {
    label: "Medium",
    hex: "#3b82f6",
    badge: "bg-blue-500/15 text-blue-700 dark:text-blue-300 border border-blue-500/30",
    bar: "bg-blue-500",
  },
  LOW: {
    label: "Low",
    hex: "#64748b",
    badge: "bg-slate-500/15 text-slate-700 dark:text-slate-300 border border-slate-500/30",
    bar: "bg-slate-500",
  },
};

export const TIER_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];

// The detection -> decision pipeline (ordered). `icon` names resolve against
// lucide-react in the About stepper.
export const PIPELINE = [
  { title: "Synthetic dataset", detail: "30k accounts seeded with hidden abuse rings.", icon: "Database" },
  { title: "Cutoff-safe features", detail: "Behavioral features engineered without leaking post-cutoff signal.", icon: "Sliders" },
  { title: "Graph + communities", detail: "Shared-identity graph, Louvain community detection.", icon: "Share2" },
  { title: "V4 Ensemble ranking", detail: "Tuned LightGBM B + a GNN score every account.", icon: "Layers" },
  { title: "SHAP + evidence gaps", detail: "Per-account explanations and missing-evidence analysis.", icon: "Search" },
  { title: "AI investigator", detail: "A Groq LLM with tool calling drafts the case narrative.", icon: "Cpu" },
  { title: "Policy engine", detail: "Deterministic rules choose the bounded action — never the LLM.", icon: "Scale" },
  { title: "Human review + audit", detail: "Analysts confirm; every decision is logged.", icon: "ClipboardCheck" },
];

export const TECH_STACK = [
  "React",
  "Vite",
  "Tailwind",
  "FastAPI",
  "LightGBM",
  "GNN",
  "SHAP",
  "Groq",
  "Louvain",
];
