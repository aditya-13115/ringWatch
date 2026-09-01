import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  getAccount,
  investigateAccount,
  getAccountTimeline,
  getFeatureAblation,
} from "../api/account";
import { Link } from "react-router-dom";
import Badge from "../components/Badge";
import Card from "../components/Card";
import GraphView from "../components/GraphView";

const INVESTIGATION_STORAGE_VERSION = 2;

const MODEL_DISPLAY_NAMES = {
  Ensemble_LGBM_B_GNN: "V4 Ensemble",
  LightGBM_Model_A_Tuned: "LightGBM Model A (Tuned · Ablation)",
  LightGBM_Model_B_Tuned: "LightGBM Model B (Tuned · Ensemble Component)",
};

function getModelDisplayName(modelVersion) {
  return (
    MODEL_DISPLAY_NAMES[modelVersion] ||
    modelVersion ||
    "Unknown model"
  );
}

function formatScore(value) {
  const score = Number(value);

  if (!Number.isFinite(score)) {
    return "—";
  }

  return `${(score * 100).toFixed(4)}%`;
}

function formatFact(key, value) {
  if (value === null || value === undefined) {
    return "—";
  }

  if (
    key === "return_rate" ||
    key === "refund_rate" ||
    key === "dispute_rate"
  ) {
    return `${(Number(value) * 100).toFixed(1)}%`;
  }

  if (
    key === "total_amount" ||
    key === "total_refund_amount"
  ) {
    return `₹${Number(value).toLocaleString("en-IN")}`;
  }

  if (key === "total_refunds") {
    return Number(value).toLocaleString("en-IN");
  }

  if (typeof value === "number") {
    return Number.isInteger(value)
      ? value.toLocaleString("en-IN")
      : value.toFixed(2);
  }

  return String(value);
}

function formatCurrency(value) {
  const amount = Number(value);

  if (!Number.isFinite(amount)) {
    return "₹0";
  }

  return `₹${amount.toLocaleString("en-IN", {
    maximumFractionDigits: 0,
  })}`;
}

function deriveTimelineFacts(timeline, observedFacts = {}) {
  if (!Array.isArray(timeline) || timeline.length === 0) {
    return observedFacts;
  }

  const totalOrders = Number(observedFacts.total_orders ?? 0);

  const returnEvents = timeline.filter(
    (event) =>
      String(event.event || "").toLowerCase() === "return requested"
  );

  const refundEvents = timeline.filter(
    (event) =>
      String(event.event || "").toLowerCase() === "refund processed"
  );

  const refundAmounts = refundEvents.map((event) => {
    const match = String(event.details || "").match(
      /amount\s*₹?\s*([\d,]+(?:\.\d+)?)/i
    );

    return match
      ? Number(match[1].replace(/,/g, ""))
      : 0;
  });

  const timelineRefundAmount = refundAmounts.reduce(
    (sum, amount) => sum + amount,
    0
  );

  const result = {
    ...observedFacts,
  };

  // Timeline is authoritative when explicit return events exist.
  if (returnEvents.length > 0) {
    result.return_rate =
      totalOrders > 0
        ? returnEvents.length / totalOrders
        : observedFacts.return_rate;

    result.total_returns = returnEvents.length;
  }

  // Timeline is authoritative when explicit refund events exist.
  if (refundEvents.length > 0) {
    result.total_refunds = refundEvents.length;
    result.total_refund_amount = timelineRefundAmount;

    result.refund_rate =
      totalOrders > 0
        ? refundEvents.length / totalOrders
        : observedFacts.refund_rate;
  }

  return result;
}

function buildCaseReport(detail, facts) {
  if (!detail) {
    return "";
  }

  const graphEvidence = detail.graph_evidence || {};
  const evidenceStatus = detail.evidence_status || {};

  const lines = [
    `Account ID: ${detail.account_id}`,
    `Model risk score: ${Number(detail.proba ?? 0).toFixed(6)}`,
    `Investigation rank: ${detail.rank} / ${
      detail.rank_total ?? "—"
    } flagged accounts`,
    "",
    "Observed facts:",
    `  total_orders: ${facts.total_orders ?? "—"}`,
    `  total_amount: ${facts.total_amount ?? "—"}`,
    `  total_refunds: ${facts.total_refunds ?? "—"}`,
    `  total_refund_amount: ${
      facts.total_refund_amount ?? "—"
    }`,
    `  return_rate: ${facts.return_rate ?? "—"}`,
    `  refund_rate: ${facts.refund_rate ?? "—"}`,
    `  dispute_rate: ${facts.dispute_rate ?? "—"}`,
    `  shared_device_count: ${
      facts.shared_device_count ?? "—"
    }`,
    `  shared_ip_prefix_count: ${
      facts.shared_ip_prefix_count ?? "—"
    }`,
    `  community_size: ${facts.community_size ?? "—"}`,
    "",
    "Top model contributors (LightGBM components):",
  ];

  if (Array.isArray(detail.top_shap_features)) {
    detail.top_shap_features.slice(0, 5).forEach((feature) => {
      lines.push(
        `  ${feature.feature}: ${Number(
          feature.shap_value
        ).toFixed(4)}`
      );
    });
  }

  lines.push("");
  lines.push("Graph evidence:");

  if (Array.isArray(graphEvidence.edges)) {
    graphEvidence.edges.forEach((edge) => {
      lines.push(
        `  ${edge.relationship || edge.type || "related"} -> ${
          edge.account_id || edge.target || "unknown"
        }`
      );
    });
  } else {
    lines.push(
      `  ${graphEvidence.total_graph_links ?? 0} linked accounts`
    );
  }

  lines.push("");
  lines.push("Evidence status:");

  if (evidenceStatus.has_dispute_at_cutoff) {
    lines.push("  Dispute observed at prediction cutoff.");
  } else {
    lines.push("  No dispute observed at prediction cutoff.");
  }

  lines.push("");
  lines.push("Recommended action:");
  lines.push(
    `  ${detail.recommended_action || "No action available"}`
  );

  return lines.join("\n");
}

function ActionPanel({ tier, accountId }) {
  switch (tier) {
    case "CRITICAL":
      return (
        <div className="flex flex-wrap gap-2">
          <Link
            to={`/verification/${accountId}`}
            className="rounded-md bg-black px-4 py-2 text-sm text-white hover:bg-gray-800 dark:bg-white dark:text-black dark:hover:bg-gray-200"
          >
            Review Soft Hold
          </Link>

          <Link
            to={`/human-review/${accountId}`}
            className="rounded-md border border-border px-4 py-2 text-sm hover:bg-accent"
          >
            Open Human Review
          </Link>
        </div>
      );

    case "HIGH":
      return (
        <Link
          to={`/human-review/${accountId}`}
          className="inline-block rounded-md bg-black px-4 py-2 text-sm text-white hover:bg-gray-800 dark:bg-white dark:text-black dark:hover:bg-gray-200"
        >
          Start Review
        </Link>
      );

    case "MEDIUM":
      return (
        <Link
          to={`/verification/${accountId}`}
          className="inline-block rounded-md border border-border px-4 py-2 text-sm hover:bg-accent"
        >
          Start Step-Up Verification
        </Link>
      );

    case "LOW":
      return (
        <span className="inline-block rounded-md border border-border px-4 py-2 text-sm">
          Continue Refund
        </span>
      );

    default:
      return null;
  }
}

const INVESTIGATION_STEPS = [
  "Gathering graph evidence",
  "Checking evidence availability",
  "Calculating financial exposure",
  "Analyzing with AI",
  "Applying deterministic policy",
  "Complete",
];

export default function AccountInvestigation() {
  const { accountId } = useParams();

  const [detail, setDetail] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [investigation, setInvestigation] = useState(null);
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [investigationStep, setInvestigationStep] = useState(-1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedTool, setExpandedTool] = useState(null);
  const [featureAblation, setFeatureAblation] = useState(null);
  const [ablationLoading, setAblationLoading] = useState(false);
  const [ablationError, setAblationError] = useState(null);

  const displayedFacts = detail?.observed_facts || {};
  const graphEvidence = detail?.graph_evidence || {};

  const relationshipLabels = {
    shares_device: "Device",
    shares_address: "Address",
    shares_phone: "Phone",
    shares_payment_instrument: "Payment instrument",
    shares_ip_prefix: "IP prefix",
    shares_coupon: "Coupon",
  };

  const evidenceLabel = (status) => {
    if (status === "MISSING") return "Missing";
    if (status === "NO_DISPUTE_YET") return "Not applicable";
    if (status === "AVAILABLE") return "Available";
    return status || "Unknown";
  };

  const evidenceClass = (status) => {
    if (status === "MISSING") return "text-destructive";
    if (status === "AVAILABLE") return "text-foreground";
    return "text-muted-foreground";
  };

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError(null);

    Promise.all([
      getAccount(accountId),
      getAccountTimeline(accountId),
    ])
      .then(([accountData, timelineData]) => {
        if (cancelled) return;

        setDetail(accountData);
        setTimeline(timelineData.events || []);

        const stored = localStorage.getItem(
          `ringwatch_investigation_${accountId}`
        );

        if (stored) {
          try {
            const parsed = JSON.parse(stored);

            if (
              parsed?.version === INVESTIGATION_STORAGE_VERSION
            ) {
              setInvestigation(parsed.data);
            } else {
              localStorage.removeItem(
                `ringwatch_investigation_${accountId}`
              );
            }
          } catch (err) {
            console.warn(
              "Could not restore investigation:",
              err
            );

            localStorage.removeItem(
              `ringwatch_investigation_${accountId}`
            );
          }
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e?.message || "Failed to load account");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [accountId]);

  /*
   * Feature ablation is intentionally lazy.
   * It does not block the initial investigation page.
   */
  const loadFeatureAblation = async () => {
    if (
      ablationLoading ||
      featureAblation ||
      ablationError
    ) {
      return;
    }

    setAblationLoading(true);
    setAblationError(null);

    try {
      const data = await getFeatureAblation(accountId);
      setFeatureAblation(data);
    } catch (e) {
      setAblationError(
        e?.message || "Failed to load feature ablation"
      );
    } finally {
      setAblationLoading(false);
    }
  };

  const handleInvestigate = async () => {
    setIsInvestigating(true);
    setError(null);
    setInvestigation(null);
    setInvestigationStep(0);

    for (
      let i = 0;
      i < INVESTIGATION_STEPS.length - 1;
      i++
    ) {
      await new Promise((resolve) => setTimeout(resolve, 400));
      setInvestigationStep(i + 1);
    }

    try {
      const result = await investigateAccount(accountId);

      setInvestigation(result);

      localStorage.setItem(
        `ringwatch_investigation_${accountId}`,
        JSON.stringify({
          version: INVESTIGATION_STORAGE_VERSION,
          data: result,
        })
      );

      setInvestigationStep(INVESTIGATION_STEPS.length - 1);
    } catch (e) {
      setError(e?.message || "Investigation failed");
    } finally {
      setIsInvestigating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-sm text-muted-foreground">
        Loading account…
      </div>
    );
  }

  if (error && !detail) {
    return (
      <div className="p-6 text-sm text-destructive">
        {error}
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="p-6 text-sm">
        No account found.
      </div>
    );
  }

  const derivedFacts = deriveTimelineFacts(
    timeline,
    displayedFacts
  );

  return (
    <div className="space-y-4 pb-6">
      {/* ============================================================
          HEADER
          ============================================================ */}
      <div className="rounded-xl border border-border bg-card p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="truncate text-xl font-semibold">
                {detail.account_id}
              </h2>

              <Badge tier={detail.risk_tier} />
            </div>

            <p className="mt-1 text-xs text-muted-foreground">
              Investigation Rank #{detail.rank} of{" "}
              {detail.rank_total ?? "—"}
              {" · "}
              {getModelDisplayName(detail.model_version)}
              {" · "}
              Score {formatScore(detail.proba)}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Link
              to="/rings"
              className="rounded-md border border-border px-3 py-2 text-xs font-medium hover:bg-accent"
            >
              View Ring Graph
            </Link>

            <ActionPanel
              tier={detail.risk_tier}
              accountId={accountId}
            />
          </div>
        </div>
      </div>

      {/* ============================================================
          KPI STRIP
          ============================================================ */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Card className="p-3">
          <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            Risk Score
          </p>

          <p className="mt-1 text-lg font-semibold">
            {formatScore(detail.proba)}
          </p>

          <p className="text-[10px] text-muted-foreground">
            {detail.risk_tier}
          </p>
        </Card>

        <Card className="p-3">
          <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            Community
          </p>

          <p className="mt-1 text-lg font-semibold">
            {detail.observed_facts?.community_size != null
              ? Number(
                  detail.observed_facts.community_size
                ).toLocaleString("en-IN")
              : "—"}
          </p>

          <p className="text-[10px] text-muted-foreground">
            linked accounts
          </p>
        </Card>

        <Card className="p-3">
          <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            Graph Links
          </p>

          <p className="mt-1 text-lg font-semibold">
            {graphEvidence.total_graph_links ?? 0}
          </p>

          <p className="truncate text-[10px] text-muted-foreground">
            {relationshipLabels[
              graphEvidence.strongest_edge_type
            ] ||
              graphEvidence.strongest_edge_type ||
              "No dominant relationship"}
          </p>
        </Card>

        <Card className="p-3">
          <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            Policy Action
          </p>

          <p className="mt-1 line-clamp-2 text-sm font-semibold">
            {detail.recommended_action || "No action"}
          </p>

          <p className="text-[10px] text-muted-foreground">
            Deterministic policy
          </p>
        </Card>
      </div>

      {/* ============================================================
          MAIN TWO-COLUMN WORKSPACE

          IMPORTANT:
          - RIGHT COLUMN graph is always visible.
          - No graph accordion/collapse.
          - Text-heavy panels get internal scroll areas.
          ============================================================ */}
      <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(430px,0.92fr)]">
        {/* ==========================================================
            LEFT COLUMN — TEXT / EVIDENCE
            ========================================================== */}
        <div className="min-w-0 space-y-4">
          {/* Why flagged */}
          <Card className="p-4">
            <div className="mb-3">
              <h3 className="text-sm font-semibold">
                Why was this account flagged?
              </h3>

              <p className="mt-1 text-xs text-muted-foreground">
                The primary behavioral, model, and evidence signals behind
                this investigation.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              <div className="rounded-lg border border-border bg-muted/20 p-3">
                <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  Top Signal
                </p>

                <p className="mt-1 line-clamp-2 text-sm font-medium">
                  {detail.top_shap_features?.[0]?.feature ||
                    "N/A"}
                </p>

                <p className="mt-1 text-[10px] text-muted-foreground">
                  SHAP{" "}
                  {Number(
                    detail.top_shap_features?.[0]
                      ?.shap_value ?? 0
                  ).toFixed(4)}
                </p>
              </div>

              <div className="rounded-lg border border-border bg-muted/20 p-3">
                <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  Graph Evidence
                </p>

                <p className="mt-1 text-sm font-medium">
                  {graphEvidence.total_graph_links ?? 0} links
                </p>

                <p className="mt-1 truncate text-[10px] text-muted-foreground">
                  Strongest:{" "}
                  {relationshipLabels[
                    graphEvidence.strongest_edge_type
                  ] ||
                    graphEvidence.strongest_edge_type ||
                    "—"}
                </p>
              </div>

              <div className="rounded-lg border border-border bg-muted/20 p-3">
                <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  Evidence Readiness
                </p>

                <p className="mt-1 text-sm font-medium">
                  {detail.evidence_status
                    ?.has_dispute_at_cutoff
                    ? `${
                        detail.evidence_status
                          ?.missing_evidence_count ?? 0
                      } missing`
                    : "Pre-dispute"}
                </p>

                <p className="mt-1 text-[10px] text-muted-foreground">
                  {detail.evidence_status
                    ?.has_dispute_at_cutoff
                    ? "Dispute evidence evaluated."
                    : "No dispute at prediction cutoff."}
                </p>
              </div>
            </div>
          </Card>

          {/* Observed facts */}
          <Card className="p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold">
                  Observed Facts
                </h3>

                <p className="mt-1 text-xs text-muted-foreground">
                  Available behavioral features and account statistics.
                </p>
              </div>

              <span className="shrink-0 text-[10px] text-muted-foreground">
                {Object.keys(displayedFacts).length} fields
              </span>
            </div>

            <div className="max-h-64 overflow-y-auto pr-1">
              <dl className="grid grid-cols-2 gap-x-4 gap-y-3 md:grid-cols-3">
                {Object.entries(derivedFacts).map(
                  ([key, value]) => (
                    <div
                      key={key}
                      className="min-w-0"
                    >
                      <dt className="truncate text-[10px] text-muted-foreground">
                        {key}
                      </dt>

                      <dd className="mt-0.5 truncate text-xs font-medium">
                        {formatFact(key, value)}
                      </dd>
                    </div>
                  )
                )}
              </dl>
            </div>
          </Card>

          {/* Model separation */}
          <Card className="p-4">
            <div className="mb-3">
              <h3 className="text-sm font-semibold">
                Model / AI / Policy
              </h3>

              <p className="mt-1 text-xs text-muted-foreground">
                Decision authority remains deterministic; AI analysis is
                advisory.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              <div className="rounded-lg border border-border p-3">
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                  Risk Model
                </p>

                <p className="mt-1 text-sm font-medium">
                  {getModelDisplayName(
                    detail.model_version
                  )}
                </p>

                <p className="mt-1 text-[10px] text-muted-foreground">
                  Score {formatScore(detail.proba)}
                </p>
              </div>

              <div className="rounded-lg border border-border p-3">
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                  AI Investigator
                </p>

                <p className="mt-1 text-sm font-medium">
                  {investigation
                    ? "Investigation complete"
                    : "Not yet run"}
                </p>

                <p className="mt-1 text-[10px] text-muted-foreground">
                  {investigation
                    ? "Analysis available"
                    : "Run when ready"}
                </p>
              </div>

              <div className="rounded-lg border border-border p-3">
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                  Policy Authority
                </p>

                <p className="mt-1 text-sm font-medium">
                  Deterministic Policy Engine
                </p>

                <p className="mt-1 text-[10px] text-muted-foreground">
                  AI cannot execute financial actions.
                </p>
              </div>
            </div>
          </Card>

          {/* SHAP */}
          <Card className="p-4">
            <div className="mb-3">
              <h3 className="text-sm font-semibold">
                Top SHAP Contributors
              </h3>

              <p className="mt-1 text-xs text-muted-foreground">
                Model-faithful feature contributions from the LightGBM
                components used by the V4 Ensemble.
              </p>
            </div>

            <div className="max-h-56 overflow-y-auto pr-1">
              <ul className="space-y-2">
                {(detail.top_shap_features || []).map(
                  (feature) => (
                    <li
                      key={feature.feature}
                      className="flex items-center justify-between gap-4 rounded-md border border-border px-3 py-2"
                    >
                      <span className="min-w-0 truncate text-xs">
                        {feature.feature}
                      </span>

                      <span
                        className={
                          Number(feature.shap_value) >= 0
                            ? "shrink-0 font-mono text-xs"
                            : "shrink-0 font-mono text-xs text-muted-foreground"
                        }
                      >
                        {Number(
                          feature.shap_value ?? 0
                        ).toFixed(4)}
                      </span>
                    </li>
                  )
                )}
              </ul>
            </div>
          </Card>

          {/* Feature ablation */}
          <Card className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold">
                  Feature Ablation
                </h3>

                <p className="mt-1 text-xs text-muted-foreground">
                  Loaded only when requested so the investigation page stays
                  responsive.
                </p>
              </div>

              {featureAblation?.model_version && (
                <span className="shrink-0 text-[10px] text-muted-foreground">
                  {featureAblation.model_version}
                </span>
              )}
            </div>

            {!featureAblation &&
              !ablationLoading &&
              !ablationError && (
                <button
                  type="button"
                  onClick={loadFeatureAblation}
                  className="mt-3 rounded-md border border-border px-3 py-2 text-xs font-medium hover:bg-accent"
                >
                  Load Feature Ablation
                </button>
              )}

            {ablationLoading && (
              <p className="mt-3 text-xs text-muted-foreground">
                Calculating feature sensitivity…
              </p>
            )}

            {ablationError && (
              <div className="mt-3">
                <p className="text-xs text-destructive">
                  {ablationError}
                </p>

                <button
                  type="button"
                  onClick={() => {
                    setAblationError(null);
                    setFeatureAblation(null);
                    loadFeatureAblation();
                  }}
                  className="mt-2 rounded-md border border-border px-3 py-2 text-xs hover:bg-accent"
                >
                  Retry
                </button>
              </div>
            )}

            {!ablationLoading &&
              !ablationError &&
              featureAblation?.ablations?.length > 0 && (
                <div className="mt-3">
                  <div className="mb-3 rounded-md border border-border bg-muted/20 p-3">
                    <p className="text-[10px] text-muted-foreground">
                      Original model score
                    </p>

                    <p className="mt-1 text-lg font-semibold">
                      {Number(
                        featureAblation.original_score
                      ).toFixed(6)}
                    </p>
                  </div>

                  <div className="max-h-64 space-y-2 overflow-y-auto pr-1">
                    {featureAblation.ablations.map(
                      (item) => (
                        <div
                          key={item.feature}
                          className="rounded-md border border-border p-3"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <span className="min-w-0 truncate text-xs font-medium">
                              {item.feature}
                            </span>

                            <span className="shrink-0 text-[10px] text-muted-foreground">
                              SHAP{" "}
                              {Number(
                                item.shap_value ?? 0
                              ).toFixed(4)}
                            </span>
                          </div>

                          <div className="mt-3 grid grid-cols-3 gap-3 text-[10px]">
                            <div>
                              <span className="block text-muted-foreground">
                                Original
                              </span>

                              <span className="font-medium">
                                {Number(
                                  item.original_score ?? 0
                                ).toFixed(6)}
                              </span>
                            </div>

                            <div>
                              <span className="block text-muted-foreground">
                                Ablated
                              </span>

                              <span className="font-medium">
                                {Number(
                                  item.ablated_score ?? 0
                                ).toFixed(6)}
                              </span>
                            </div>

                            <div>
                              <span className="block text-muted-foreground">
                                Score change
                              </span>

                              <span
                                className={
                                  Number(
                                    item.score_delta
                                  ) < 0
                                    ? "font-medium text-destructive"
                                    : "font-medium"
                                }
                              >
                                {Number(
                                  item.score_delta
                                ) >= 0
                                  ? "+"
                                  : "−"}
                                {(
                                  Math.abs(
                                    Number(
                                      item.score_delta ??
                                        0
                                    )
                                  ) * 100
                                ).toFixed(2)}{" "}
                                pp
                              </span>
                            </div>
                          </div>
                        </div>
                      )
                    )}
                  </div>

                  <p className="mt-3 text-[10px] leading-4 text-muted-foreground">
                    Ablation shows model sensitivity, not causal influence or
                    proof of abuse.
                  </p>
                </div>
              )}
          </Card>

          {/* Evidence */}
          <Card className="p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold">
                  Evidence Readiness
                </h3>

                <p className="mt-1 text-xs text-muted-foreground">
                  Evidence availability for a potential future dispute.
                </p>
              </div>

              <span className="shrink-0 text-[10px] text-muted-foreground">
                {detail.evidence_status
                  ?.has_dispute_at_cutoff
                  ? "Dispute observed"
                  : "Pre-dispute"}
              </span>
            </div>

            <div className="max-h-60 space-y-2 overflow-y-auto pr-1">
              {Object.entries(
                detail.evidence_status?.fields || {}
              ).map(([field, status]) => (
                <div
                  key={field}
                  className="flex items-center justify-between gap-4 rounded-md border border-border px-3 py-2"
                >
                  <span className="min-w-0 truncate font-mono text-[10px]">
                    {field}
                  </span>

                  <span
                    className={`shrink-0 text-[11px] font-medium ${evidenceClass(
                      status
                    )}`}
                  >
                    {evidenceLabel(status)}
                  </span>
                </div>
              ))}
            </div>

            {!detail.evidence_status
              ?.has_dispute_at_cutoff && (
              <p className="mt-3 text-[10px] leading-4 text-muted-foreground">
                No dispute existed at the prediction cutoff; missing evidence
                is therefore not yet actionable.
              </p>
            )}
          </Card>

          {/* Case report */}
          <Card className="p-4">
            <div className="mb-3">
              <h3 className="text-sm font-semibold">
                Case Report
              </h3>

              <p className="mt-1 text-xs text-muted-foreground">
                Compact deterministic report generated from the current
                investigation state.
              </p>
            </div>

            <pre className="max-h-72 overflow-y-auto whitespace-pre-wrap break-words rounded-md border border-border bg-muted/20 p-3 font-mono text-[10px] leading-5">
              {buildCaseReport(
                detail,
                derivedFacts
              )}
            </pre>
          </Card>
        </div>

        {/* ==========================================================
            RIGHT COLUMN — GRAPH / DECISION
            ========================================================== */}
        <div className="min-w-0 space-y-4 xl:sticky xl:top-20">
          {/* Ring context */}
          <Card className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  Abuse Ring / Community Context
                </p>

                <h3 className="mt-1 truncate text-base font-semibold">
                  {detail.observed_facts?.community_size
                    ? `Community of ${Number(
                        detail.observed_facts
                          .community_size
                      ).toLocaleString("en-IN")} accounts`
                    : "Linked-account community"}
                </h3>
              </div>

              <span className="shrink-0 rounded-full border border-border px-2 py-1 text-[10px] font-medium">
                {detail.risk_tier}
              </span>
            </div>

            <p className="mt-2 text-xs leading-5 text-muted-foreground">
              The account is investigated individually while its
              shared-attribute relationships provide the surrounding
              network context.
            </p>

            <div className="mt-4 grid grid-cols-2 gap-3">
              <div>
                <p className="text-[10px] text-muted-foreground">
                  Linked accounts
                </p>

                <p className="mt-1 text-base font-semibold">
                  {graphEvidence.total_graph_links ?? 0}
                </p>
              </div>

              <div>
                <p className="text-[10px] text-muted-foreground">
                  Peak member risk
                </p>

                <p className="mt-1 text-base font-semibold">
                  {formatScore(detail.proba)}
                </p>
              </div>

              <div className="min-w-0">
                <p className="text-[10px] text-muted-foreground">
                  Strongest relationship
                </p>

                <p className="mt-1 truncate text-xs font-medium">
                  {relationshipLabels[
                    graphEvidence.strongest_edge_type
                  ] ||
                    graphEvidence.strongest_edge_type ||
                    "—"}
                </p>
              </div>

              <div>
                <p className="text-[10px] text-muted-foreground">
                  Weight
                </p>

                <p className="mt-1 text-base font-semibold">
                  {graphEvidence.strongest_edge_weight !=
                  null
                    ? Number(
                        graphEvidence.strongest_edge_weight
                      ).toFixed(2)
                    : "—"}
                </p>
              </div>
            </div>
          </Card>

          {/* ========================================================
              GRAPH — NEVER COLLAPSED
              ======================================================== */}
          <Card className="overflow-hidden p-0">
            <div className="border-b border-border px-4 py-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold">
                    Account Network
                  </h3>

                  <p className="mt-1 text-[10px] text-muted-foreground">
                    Interactive network evidence remains visible during the
                    investigation.
                  </p>
                </div>

                <span className="shrink-0 rounded-full border border-border px-2 py-1 text-[9px] font-medium">
                  GRAPH
                </span>
              </div>
            </div>

            {/* No overflow-y wrapper here.
                The graph itself is intentionally not collapsed/scroll-clipped. */}
            <div className="w-full">
              {detail.risk_tier === "CRITICAL" ||
              detail.risk_tier === "HIGH" ||
              detail.risk_tier === "MEDIUM" ? (
                <div className="w-full">
                  <GraphView accountId={accountId} />
                </div>
              ) : (
                <div className="flex min-h-[420px] items-center justify-center px-6 text-center">
                  <div>
                    <p className="text-sm font-medium">
                      No significant graph evidence.
                    </p>

                    <p className="mt-1 text-xs text-muted-foreground">
                      Shared entities:{" "}
                      {detail.graph_evidence
                        ?.total_graph_links || 0}{" "}
                      links.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* Relationships */}
          <Card className="p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold">
                Strongest Relationships
              </h3>

              <span className="text-[10px] text-muted-foreground">
                {graphEvidence.linked_accounts?.length ??
                  0}{" "}
                links
              </span>
            </div>

            {graphEvidence.linked_accounts?.length > 0 ? (
              <div className="max-h-48 space-y-2 overflow-y-auto pr-1">
                {graphEvidence.linked_accounts
                  .slice(0, 12)
                  .map((link, idx) => (
                    <div
                      key={`${link.linked_account}-${idx}`}
                      className="flex items-center justify-between gap-3 rounded-md border border-border px-3 py-2"
                    >
                      <span className="min-w-0 truncate text-[10px]">
                        {relationshipLabels[
                          link.edge_type
                        ] || link.edge_type}
                        {" · "}
                        {link.linked_account}
                      </span>

                      <span className="shrink-0 text-[10px] text-muted-foreground">
                        {link.edge_type ===
                          graphEvidence.strongest_edge_type &&
                        graphEvidence.strongest_edge_weight !=
                          null
                          ? Number(
                              graphEvidence.strongest_edge_weight
                            ).toFixed(2)
                          : "linked"}
                      </span>
                    </div>
                  ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                No linked-account details available.
              </p>
            )}

            {graphEvidence.strongest_edge_explanation && (
              <div className="mt-3 rounded-md border border-border bg-muted/20 p-3">
                <p className="text-[10px] font-medium">
                  Why this relationship is surfaced
                </p>

                <p className="mt-1 text-[10px] leading-4 text-muted-foreground">
                  {graphEvidence.strongest_edge_explanation}
                </p>
              </div>
            )}

            <p className="mt-3 text-[9px] leading-4 text-muted-foreground">
              Relationship weights are evidence-prioritization heuristics,
              not proof of coordinated abuse.
            </p>
          </Card>

          {/* Timeline */}
          <Card className="p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold">
                Investigation Timeline
              </h3>

              <span className="text-[10px] text-muted-foreground">
                {timeline.length} events
              </span>
            </div>

            {timeline.length > 0 ? (
              <div className="max-h-72 overflow-y-auto pr-2">
                <ol className="relative ml-2 border-l border-border pl-4">
                  {timeline.map((event, idx) => (
                    <li
                      key={idx}
                      className="relative mb-4 ml-2 last:mb-0"
                    >
                      <div className="absolute -left-[1.35rem] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-background bg-foreground" />

                      <time className="text-[9px] text-muted-foreground">
                        {new Date(
                          event.timestamp
                        ).toLocaleString()}
                      </time>

                      <p className="mt-0.5 text-xs font-medium">
                        {event.event}
                      </p>

                      <p className="mt-0.5 text-[10px] leading-4 text-muted-foreground">
                        {event.details}
                      </p>
                    </li>
                  ))}
                </ol>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                No events found.
              </p>
            )}
          </Card>

          {/* Recommended action */}
          <Card className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  Recommended Action
                </p>

                <p className="mt-1 text-sm font-semibold">
                  {detail.recommended_action ||
                    "No action available"}
                </p>

                <p className="mt-1 text-[10px] leading-4 text-muted-foreground">
                  Final authority: deterministic policy engine.
                  AI analysis is advisory only.
                </p>
              </div>

              <Badge tier={detail.risk_tier} />
            </div>

            <div className="mt-4">
              <ActionPanel
                tier={detail.risk_tier}
                accountId={accountId}
              />
            </div>
          </Card>

          {/* AI Investigator */}
          <Card className="p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  AI Investigator
                </p>

                <p className="mt-1 text-sm font-semibold">
                  {!investigation
                    ? "Ready to investigate"
                    : "Investigation complete"}
                </p>

                {investigation?.confidence && (
                  <p className="mt-1 text-[10px] text-muted-foreground">
                    Confidence:{" "}
                    {investigation.confidence}
                  </p>
                )}
              </div>

              <button
                type="button"
                onClick={handleInvestigate}
                disabled={isInvestigating}
                className="rounded-md bg-black px-3 py-2 text-xs font-medium text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white dark:text-black dark:hover:bg-gray-200"
              >
                {isInvestigating
                  ? "Investigating…"
                  : investigation
                    ? "Run Again"
                    : "Run Investigation"}
              </button>
            </div>

            {isInvestigating &&
              investigationStep >= 0 && (
                <div className="mt-3 rounded-md border border-border bg-muted/20 p-3">
                  <ol className="grid gap-1 text-[10px]">
                    {INVESTIGATION_STEPS.slice(
                      0,
                      investigationStep + 1
                    ).map((step, idx) => (
                      <li
                        key={idx}
                        className={
                          idx ===
                          investigationStep
                            ? "font-medium text-foreground"
                            : "text-muted-foreground"
                        }
                      >
                        {idx + 1}. {step}
                      </li>
                    ))}
                  </ol>
                </div>
              )}
          </Card>

          {/* AI results */}
          {investigation &&
            !isInvestigating && (
              <Card className="p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold">
                    AI Investigation Result
                  </h3>

                  <span className="text-[9px] text-muted-foreground">
                    Advisory only
                  </span>
                </div>

                {/* This area can scroll; the graph above never does. */}
                <div className="max-h-[34rem] space-y-4 overflow-y-auto pr-2">
                  {investigation.financial_exposure && (
                    <div className="rounded-md border border-border p-3">
                      <h4 className="text-xs font-semibold">
                        Financial Exposure
                      </h4>

                      <div className="mt-3 grid grid-cols-3 gap-3 text-[10px]">
                        <div>
                          <span className="block text-muted-foreground">
                            Gross order value
                          </span>

                          <span className="font-medium">
                            {formatCurrency(
                              investigation
                                .financial_exposure
                                .gross_order_value
                            )}
                          </span>
                        </div>

                        <div>
                          <span className="block text-muted-foreground">
                            Total refunds
                          </span>

                          <span className="font-medium">
                            {formatCurrency(
                              investigation
                                .financial_exposure
                                .refund_amount
                            )}
                          </span>
                        </div>

                        <div>
                          <span className="block text-muted-foreground">
                            Potential exposure
                          </span>

                          <span className="font-medium">
                            {formatCurrency(
                              investigation
                                .financial_exposure
                                .potential_exposure
                            )}
                          </span>
                        </div>
                      </div>

                      <p className="mt-3 text-[9px] leading-4 text-muted-foreground">
                        Financial values are calculated deterministically
                        and are authoritative over AI-generated prose.
                      </p>
                    </div>
                  )}

                  <div className="rounded-md border border-border bg-muted/20 p-3">
                    <h4 className="text-xs font-semibold">
                      Investigation Summary
                    </h4>

                    <p className="mt-2 text-xs leading-5">
                      {investigation.summary}
                    </p>

                    {investigation.confidence && (
                      <p className="mt-2 text-[10px] text-muted-foreground">
                        Confidence:{" "}
                        <span className="font-medium">
                          {investigation.confidence}
                        </span>
                      </p>
                    )}
                  </div>

                  {investigation.key_findings
                    ?.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold">
                        Key Findings
                      </h4>

                      <ul className="mt-2 list-disc space-y-1 pl-4 text-[11px]">
                        {investigation.key_findings.map(
                          (finding, idx) => (
                            <li key={idx}>{finding}</li>
                          )
                        )}
                      </ul>
                    </div>
                  )}

                  {investigation.evidence_gaps
                    ?.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold">
                        Evidence Gaps
                      </h4>

                      <ul className="mt-2 list-disc space-y-1 pl-4 text-[11px]">
                        {investigation.evidence_gaps.map(
                          (gap, idx) => (
                            <li key={idx}>{gap}</li>
                          )
                        )}
                      </ul>
                    </div>
                  )}

                  {investigation.uncertainties
                    ?.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold">
                        Uncertainties
                      </h4>

                      <ul className="mt-2 list-disc space-y-1 pl-4 text-[11px]">
                        {investigation.uncertainties.map(
                          (item, idx) => (
                            <li key={idx}>{item}</li>
                          )
                        )}
                      </ul>
                    </div>
                  )}

                  <div>
                    <h4 className="text-xs font-semibold">
                      Investigation Chain
                    </h4>

                    <div className="mt-2 grid grid-cols-2 gap-2 text-[9px] md:grid-cols-4">
                      {[
                        [
                          "Risk model",
                          "Deterministic score",
                        ],
                        [
                          "Graph evidence",
                          `${
                            graphEvidence.total_graph_links ??
                            0
                          } links`,
                        ],
                        [
                          "Evidence",
                          `${
                            Object.keys(
                              detail.evidence_status
                                ?.fields || {}
                            ).length
                          } fields checked`,
                        ],
                        [
                          "Policy",
                          detail.recommended_action ||
                            "No action",
                        ],
                      ].map(([label, value]) => (
                        <div
                          key={label}
                          className="rounded-md border border-border p-2"
                        >
                          <p className="text-muted-foreground">
                            {label}
                          </p>

                          <p className="mt-1 line-clamp-2 font-medium">
                            {value}
                          </p>
                        </div>
                      ))}
                    </div>

                    <p className="mt-2 text-[9px] leading-4 text-muted-foreground">
                      AI analysis is advisory; deterministic financial
                      values and policy remain authoritative.
                    </p>
                  </div>

                  {investigation.tool_calls
                    ?.length > 0 && (
                    <div>
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-semibold">
                          Tool Trace
                        </h4>

                        <span className="text-[9px] text-muted-foreground">
                          {
                            investigation
                              .tool_calls.length
                          }{" "}
                          calls
                        </span>
                      </div>

                      <div className="mt-2 space-y-2">
                        {investigation.tool_calls.map(
                          (call, idx) => (
                            <div
                              key={idx}
                              className="rounded-md border border-border p-2"
                            >
                              <button
                                type="button"
                                onClick={() =>
                                  setExpandedTool(
                                    expandedTool ===
                                      idx
                                      ? null
                                      : idx
                                  )
                                }
                                className="flex w-full items-center justify-between gap-3 text-left"
                              >
                                <span className="min-w-0 truncate font-mono text-[10px]">
                                  {call.tool}
                                </span>

                                <span className="shrink-0 text-[9px] text-muted-foreground">
                                  {expandedTool ===
                                  idx
                                    ? "Hide"
                                    : "Details"}
                                </span>
                              </button>

                              <p className="mt-1 text-[9px] leading-4 text-muted-foreground">
                                {call.result_summary}
                              </p>

                              {expandedTool ===
                                idx && (
                                <pre className="mt-2 max-h-40 overflow-y-auto whitespace-pre-wrap break-words rounded bg-muted p-2 text-[9px]">
                                  {JSON.stringify(
                                    call,
                                    null,
                                    2
                                  )}
                                </pre>
                              )}
                            </div>
                          )
                        )}
                      </div>
                    </div>
                  )}

                  {investigation.completion_summary && (
                    <div className="rounded-md border border-border p-3">
                      <h4 className="text-xs font-semibold">
                        Investigation Complete
                      </h4>

                      <div className="mt-3 grid grid-cols-2 gap-3 text-[10px] md:grid-cols-3">
                        <div>
                          <span className="block text-muted-foreground">
                            Tools executed
                          </span>

                          <span className="font-medium">
                            {
                              investigation
                                .completion_summary
                                .tools_executed
                            }
                          </span>
                        </div>

                        <div>
                          <span className="block text-muted-foreground">
                            Graph links
                          </span>

                          <span className="font-medium">
                            {
                              investigation
                                .completion_summary
                                .graph_links_found
                            }
                          </span>
                        </div>

                        <div>
                          <span className="block text-muted-foreground">
                            Financial exposure
                          </span>

                          <span className="font-medium">
                            ₹
                            {
                              investigation
                                .completion_summary
                                .financial_exposure
                            }
                          </span>
                        </div>

                        <div>
                          <span className="block text-muted-foreground">
                            Evidence fields
                          </span>

                          <span className="font-medium">
                            {
                              investigation
                                .completion_summary
                                .evidence_fields_checked
                            }
                          </span>
                        </div>

                        <div>
                          <span className="block text-muted-foreground">
                            AI confidence
                          </span>

                          <span className="font-medium">
                            {
                              investigation
                                .completion_summary
                                .llm_confidence
                            }
                          </span>
                        </div>

                        <div>
                          <span className="block text-muted-foreground">
                            Duration
                          </span>

                          <span className="font-medium">
                            {
                              investigation
                                .completion_summary
                                .duration_seconds
                            }
                            s
                          </span>
                        </div>
                      </div>
                    </div>
                  )}

                  {investigation.duration_seconds !=
                    null && (
                    <p className="text-[9px] text-muted-foreground">
                      Investigation duration:{" "}
                      {investigation.duration_seconds}s
                    </p>
                  )}

                  <div className="rounded-md border border-border p-3">
                    <p className="text-xs text-muted-foreground">
                      Recommended action:{" "}
                      <span className="font-medium text-foreground">
                        {investigation.recommended_action}
                      </span>
                    </p>

                    <p className="mt-1 text-[9px] text-muted-foreground">
                      Action source:{" "}
                      {investigation.action_source ===
                      "deterministic_policy"
                        ? "Deterministic Policy Engine"
                        : investigation.action_source}
                    </p>
                  </div>
                </div>
              </Card>
            )}
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
          {error}
        </div>
      )}
    </div>
  );
}