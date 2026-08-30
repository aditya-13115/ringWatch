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
    `Investigation rank: ${detail.rank} / ${detail.rank_total ?? "—"} flagged accounts`,
    "",
    "Observed facts:",
    `  total_orders: ${facts.total_orders ?? "—"}`,
    `  total_amount: ${facts.total_amount ?? "—"}`,
    `  total_refunds: ${facts.total_refunds ?? "—"}`,
    `  total_refund_amount: ${facts.total_refund_amount ?? "—"}`,
    `  return_rate: ${facts.return_rate ?? "—"}`,
    `  refund_rate: ${facts.refund_rate ?? "—"}`,
    `  dispute_rate: ${facts.dispute_rate ?? "—"}`,
    `  shared_device_count: ${facts.shared_device_count ?? "—"}`,
    `  shared_ip_prefix_count: ${facts.shared_ip_prefix_count ?? "—"}`,
    `  community_size: ${facts.community_size ?? "—"}`,
    "",
    "Top model contributors (LightGBM components):",
  ];

  if (Array.isArray(detail.top_shap_features)) {
    detail.top_shap_features.slice(0, 5).forEach((feature) => {
      lines.push(
        `  ${feature.feature}: ${Number(feature.shap_value).toFixed(4)}`
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
        <div className="flex gap-2 mt-2">
          <Link to={`/verification/${accountId}`} className="bg-black text-white px-4 py-2 rounded-md text-sm">
            Review Soft Hold
          </Link>
          <Link to={`/human-review/${accountId}`} className="border border-black px-4 py-2 rounded-md text-sm">
            Open Human Review
          </Link>
        </div>
      );
    case "HIGH":
      return (
        <Link to={`/human-review/${accountId}`} className="bg-black text-white px-4 py-2 rounded-md text-sm inline-block">
          Start Review
        </Link>
      );
    case "MEDIUM":
      return (
        <Link to={`/verification/${accountId}`} className="border border-black px-4 py-2 rounded-md text-sm inline-block">
          Start Step-Up Verification
        </Link>
      );
    case "LOW":
      return (
        <span className="border border-black px-4 py-2 rounded-md text-sm inline-block">
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
  const [featureAblation, setFeatureAblation] =
    useState(null);

  const [ablationLoading, setAblationLoading] =
    useState(false);

  const [ablationError, setAblationError] =
    useState(null);
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
    Promise.all([
      getAccount(accountId),
      getAccountTimeline(accountId),
    ])
      .then(([accountData, timelineData]) => {
        setDetail(accountData);
        setTimeline(timelineData.events);

        // Restore persisted investigation for this account if available
        const stored = localStorage.getItem(
          `ringwatch_investigation_${accountId}`
        );

        if (stored) {
          try {
            const parsed = JSON.parse(stored);

            // Only restore investigations written by the current
            // investigation format.
            if (
              parsed?.version ===
              INVESTIGATION_STORAGE_VERSION
            ) {
              setInvestigation(parsed.data);
            } else {
              // Remove stale investigation data generated by the
              // previous prompt/data contract.
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
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [accountId]);

  useEffect(() => {
    let cancelled = false;

    setAblationLoading(true);
    setAblationError(null);

    getFeatureAblation(accountId)
      .then((data) => {
        if (!cancelled) {
          setFeatureAblation(data);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setAblationError(e.message);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setAblationLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [accountId]);


  const handleInvestigate = async () => {
    setIsInvestigating(true);
    setError(null);
    setInvestigation(null);
    setInvestigationStep(0);

    // Simulate progressive steps while waiting for the actual API call
    for (let i = 0; i < INVESTIGATION_STEPS.length - 1; i++) {
      await new Promise((resolve) => setTimeout(resolve, 400));
      setInvestigationStep(i);
    }

    try {
      const result = await investigateAccount(accountId);
      setInvestigation(result);

      // Persist result for this account
      localStorage.setItem(
        `ringwatch_investigation_${accountId}`,
        JSON.stringify({
          version: INVESTIGATION_STORAGE_VERSION,
          data: result,
        })
      );

      setInvestigationStep(INVESTIGATION_STEPS.length - 1);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsInvestigating(false);
    }
  };


  if (loading) {
    return <div className="p-6">Loading account…</div>;
  }

  if (error && !detail) {
    return <div className="p-6 text-destructive">{error}</div>;
  }

  if (!detail) {
    return <div className="p-6">No account found.</div>;
  }


  return (
    <div className="space-y-6">

      {/* Hero Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold">
            {detail.account_id}
          </h2>

          <p className="text-sm text-muted-foreground">
            Investigation Rank #{detail.rank} of{" "}
            {detail.rank_total ?? "—"}
          </p>
        </div>

        <Badge tier={detail.risk_tier} />
      </div>

      {/* Community / Ring Context */}
      <Card className="p-6">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Abuse Ring / Community Context
            </p>
            <h3 className="text-lg font-semibold mt-1">
              {detail.observed_facts?.community_size
                ? `Community of ${Number(detail.observed_facts.community_size).toLocaleString("en-IN")} accounts`
                : "Linked-account community"}
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              The account is investigated individually, while its shared-attribute relationships provide the surrounding community context.
            </p>
          </div>
          <Link
            to="/rings"
            className="border border-border rounded-md px-3 py-2 text-sm hover:bg-accent whitespace-nowrap"
          >
            View Ring Graph
          </Link>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-5">
          <div>
            <p className="text-xs text-muted-foreground">Linked accounts</p>
            <p className="text-lg font-semibold">{graphEvidence.total_graph_links ?? 0}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Strongest relationship</p>
            <p className="text-sm font-semibold">
              {relationshipLabels[graphEvidence.strongest_edge_type] || graphEvidence.strongest_edge_type || "—"}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Relationship weight</p>
            <p className="text-lg font-semibold">
              {graphEvidence.strongest_edge_weight != null ? Number(graphEvidence.strongest_edge_weight).toFixed(2) : "—"}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Peak member risk</p>
            <p className="text-lg font-semibold">{formatScore(detail.proba)}</p>
            <p className="text-[11px] text-muted-foreground">Current account score</p>
          </div>
        </div>
      </Card>


      {/* Model / AI / Policy Separation */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4">
          <h3 className="text-sm font-medium text-muted-foreground mb-2">
            Risk Model
          </h3>

          <p className="text-sm font-semibold">
            {getModelDisplayName(detail.model_version)}
          </p>

          <p className="text-xs text-muted-foreground">
            Model version: {detail.model_version}
          </p>

          <p className="text-xs text-muted-foreground">
            Score: {formatScore(detail.proba)}
          </p>

          <p className="text-xs text-muted-foreground">
            Investigation rank: #{detail.rank} /{" "}
            {detail.rank_total ?? "—"}
          </p>
        </Card>

        <Card className="p-4">
          <h3 className="text-sm font-medium text-muted-foreground mb-2">
            AI Investigator
          </h3>

          <p className="text-sm font-semibold">
            {!investigation ? "Not yet run" : "Investigation complete"}
          </p>

          <p className="text-xs text-muted-foreground">
            {investigation ? "AI analysis available" : "Run to generate AI analysis"}
          </p>

          {investigation?.confidence && (
            <p className="text-xs text-muted-foreground">
              Confidence: {investigation.confidence}
            </p>
          )}
        </Card>

        <Card className="p-4">
          <h3 className="text-sm font-medium text-muted-foreground mb-2">
            Policy Authority
          </h3>

          <p className="text-sm font-semibold">
            Deterministic Policy Engine
          </p>

          <p className="text-xs text-muted-foreground">
            Final action is determined by policy, not AI.
          </p>
        </Card>
      </div>


      {/* Why this account */}
      <Card className="p-6">
        <h3 className="text-sm font-medium text-muted-foreground mb-3">
          Why was this account flagged?
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

          <div className="p-3 rounded-md bg-muted">
            <p className="text-xs text-muted-foreground">
              Top Signal
            </p>

            <p className="text-sm font-medium">
              {detail.top_shap_features[0]?.feature || "N/A"}
            </p>

            <p className="text-xs text-muted-foreground">
              SHAP contribution:{" "}
              {detail.top_shap_features[0]?.shap_value.toFixed(4)}
            </p>
          </div>


          <div className="p-3 rounded-md bg-muted">
            <p className="text-xs text-muted-foreground">
              Graph Relationships
            </p>

            <p className="text-sm font-medium">
              {detail.graph_evidence?.total_graph_links ?? 0} links
            </p>
          </div>


          <div className="p-3 rounded-md bg-muted">
            <p className="text-xs text-muted-foreground">
              Evidence Readiness
            </p>

            <p className="text-sm font-medium">
              {detail.evidence_status?.has_dispute_at_cutoff
                ? `${detail.evidence_status?.missing_evidence_count ?? 0} missing`
                : "No dispute at cutoff"}
            </p>

            <p className="text-xs text-muted-foreground mt-1">
              {detail.evidence_status?.has_dispute_at_cutoff
                ? "Evidence availability evaluated for the dispute."
                : "No dispute existed at the prediction cutoff."}
            </p>
          </div>

        </div>
      </Card>


      {/* Recommended Action */}
      <Card className="p-6">
        <h3 className="text-sm font-medium text-muted-foreground mb-3">
          Recommended Action
        </h3>

        <p className="text-lg font-medium">
          {detail.recommended_action}
        </p>

        <p className="text-sm text-muted-foreground mt-2">
          Action authority: deterministic policy engine.
          AI analysis is advisory and does not execute financial actions.
        </p>

        <ActionPanel tier={detail.risk_tier} accountId={accountId} />
      </Card>


      {/* Main investigation grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Left column */}
        <div className="space-y-6">

          {/* Observed Facts */}
          <Card className="p-4">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">
              Observed Facts
            </h3>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {Object.entries(displayedFacts).map(
                ([key, value]) => (
                  <div key={key}>
                    <dt className="text-xs text-muted-foreground">
                      {key}
                    </dt>

                    <dd className="text-sm font-medium">
                      {formatFact(key, value)}
                    </dd>
                  </div>
                )
              )}
            </div>
          </Card>


          {/* Top SHAP Contributors */}
          <Card className="p-4">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">
              Top SHAP Contributors
            </h3>

            <p className="text-xs text-muted-foreground mb-3">
              Model-faithful feature contributions from the
              LightGBM components used by the V4 Ensemble.
            </p>

            <ul className="space-y-2">
              {detail.top_shap_features.map((f) => (
                <li
                  key={f.feature}
                  className="flex justify-between text-sm"
                >
                  <span>{f.feature}</span>

                  <span
                    className={
                      f.shap_value >= 0
                        ? "text-black"
                        : "text-gray-500"
                    }
                  >
                    {f.shap_value.toFixed(4)}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
          
          {/* Feature Ablation */}
          <Card className="p-4">
            <div className="flex items-start justify-between gap-3 mb-3">
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">
                  Feature Ablation
                </h3>

                <p className="text-xs text-muted-foreground mt-1">
                  Measures how the LightGBM A component score changes when
                  individual top-contributing features are replaced with their
                  population median. This is a component-level sensitivity
                  analysis, not the V4 Ensemble score.
                </p>
              </div>

              {featureAblation?.model_version && (
                <span className="text-xs text-muted-foreground">
                  {featureAblation.model_version}
                </span>
              )}
            </div>

            {ablationLoading && (
              <p className="text-sm text-muted-foreground">
                Calculating feature sensitivity…
              </p>
            )}

            {ablationError && (
              <p className="text-sm text-destructive">
                {ablationError}
              </p>
            )}

            {!ablationLoading &&
              !ablationError &&
              featureAblation?.ablations?.length > 0 && (
                <>
                  <div className="rounded-md border border-border p-3 mb-3">
                    <span className="text-xs text-muted-foreground block">
                      Original model score
                    </span>

                    <span className="text-lg font-semibold">
                      {Number(
                        featureAblation.original_score
                      ).toFixed(6)}
                    </span>
                  </div>

                  <div className="space-y-2">
                    {featureAblation.ablations.map(
                      (item) => (
                        <div
                          key={item.feature}
                          className="rounded-md border border-border p-3"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <span className="text-sm font-medium">
                              {item.feature}
                            </span>

                            <span className="text-xs text-muted-foreground">
                              SHAP{" "}
                              {Number(
                                item.shap_value
                              ).toFixed(4)}
                            </span>
                          </div>

                          <div className="grid grid-cols-3 gap-3 mt-3 text-xs">
                            <div>
                              <span className="text-muted-foreground block">
                                Original
                              </span>

                              <span className="font-medium">
                                {Number(
                                  item.original_score
                                ).toFixed(6)}
                              </span>
                            </div>

                            <div>
                              <span className="text-muted-foreground block">
                                Ablated
                              </span>

                              <span className="font-medium">
                                {Number(
                                  item.ablated_score
                                ).toFixed(6)}
                              </span>
                            </div>

                            <div>
                              <span className="text-muted-foreground block">
                                Score change
                              </span>

                              <span className="font-medium">
                                {item.score_delta >= 0
                                  ? "+"
                                  : ""}
                                {Number(
                                  item.score_delta
                                ).toFixed(6)}
                              </span>
                            </div>
                          </div>
                        </div>
                      )
                    )}
                  </div>

                  <p className="text-[11px] text-muted-foreground mt-3">
                    Ablation shows model sensitivity, not causal
                    influence or proof of abuse.
                  </p>
                </>
              )}

            {!ablationLoading &&
              !ablationError &&
              (!featureAblation?.ablations ||
                featureAblation.ablations.length === 0) && (
                <p className="text-sm text-muted-foreground">
                  No feature-ablation results available.
                </p>
              )}
          </Card>

          {/* Evidence Status */}
          <Card className="p-4">
            <div className="flex items-start justify-between gap-3 mb-3">
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">
                  Evidence Readiness
                </h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Evidence availability for a potential future dispute.
                </p>
              </div>
              <span className="text-xs text-muted-foreground">
                {detail.evidence_status?.has_dispute_at_cutoff ? "Dispute observed" : "Pre-dispute"}
              </span>
            </div>

            <div className="space-y-2">
              {Object.entries(detail.evidence_status?.fields || {}).map(
                ([field, status]) => (
                  <div
                    key={field}
                    className="flex items-center justify-between gap-4 rounded-md border border-border px-3 py-2 text-sm"
                  >
                    <span className="font-mono text-xs">{field}</span>
                    <span className={`font-medium ${evidenceClass(status)}`}>
                      {evidenceLabel(status)}
                    </span>
                  </div>
                )
              )}
            </div>

            {!detail.evidence_status?.has_dispute_at_cutoff && (
              <p className="text-xs text-muted-foreground mt-3">
                No dispute existed at the prediction cutoff; missing evidence is therefore not yet actionable.
              </p>
            )}
          </Card>

          {/* Adaptive Graph Relationships */}
          <Card className="p-4">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">
              Graph Relationships
            </h3>

            <div className="mb-3 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
              <div className="rounded-md border border-border p-2">
                <span className="text-muted-foreground block">Device</span>
                <span className="font-semibold">{graphEvidence.number_of_device_links ?? 0}</span>
              </div>
              <div className="rounded-md border border-border p-2">
                <span className="text-muted-foreground block">IP</span>
                <span className="font-semibold">{graphEvidence.number_of_ip_links ?? 0}</span>
              </div>
              <div className="rounded-md border border-border p-2">
                <span className="text-muted-foreground block">Coupon</span>
                <span className="font-semibold">{graphEvidence.number_of_coupon_links ?? 0}</span>
              </div>
              <div className="rounded-md border border-border p-2">
                <span className="text-muted-foreground block">Strongest</span>
                <span className="font-semibold">{relationshipLabels[graphEvidence.strongest_edge_type] || "—"}</span>
              </div>
            </div>

            {detail.risk_tier === "CRITICAL" ||
            detail.risk_tier === "HIGH" ||
            detail.risk_tier === "MEDIUM" ? (
              <>
                <GraphView accountId={accountId} />

                {graphEvidence.linked_accounts?.length > 0 && (
                <div className="mt-4 rounded-md border border-border p-3">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-semibold">Strongest Relationships</h4>
                    {graphEvidence.strongest_edge_type && (
                      <span className="text-xs text-muted-foreground">
                        Strongest: {relationshipLabels[graphEvidence.strongest_edge_type] || graphEvidence.strongest_edge_type}
                      </span>
                    )}
                  </div>
                  <div className="space-y-2">
                    {graphEvidence.linked_accounts.slice(0, 6).map((link, idx) => (
                      <div key={`${link.linked_account}-${idx}`} className="flex items-center justify-between gap-3 text-xs">
                        <span className="truncate">{relationshipLabels[link.edge_type] || link.edge_type} · {link.linked_account}</span>
                        <span className="text-muted-foreground">
                          {link.edge_type === graphEvidence.strongest_edge_type && graphEvidence.strongest_edge_weight != null
                            ? Number(graphEvidence.strongest_edge_weight).toFixed(2)
                            : "linked"}
                        </span>
                      </div>
                    ))}
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-2">
                    Relationship weights are heuristic evidence strength, not proof of coordinated abuse.
                  </p>
                </div>
                )}
              </>
            ) : (
              <div className="text-sm text-muted-foreground">
                <p>No significant graph evidence.</p>
                <p>
                  Shared entities:{" "}
                  {detail.graph_evidence?.total_graph_links || 0} links.
                </p>
              </div>
            )}
          </Card>


          {/* Investigation Timeline */}
          <Card className="p-4">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">
              Investigation Timeline
            </h3>

            {timeline.length > 0 ? (
              <ol className="relative border-l border-border ml-2 pl-4 space-y-4">
                {timeline.map((event, idx) => (
                  <li key={idx} className="ml-4">

                    <div className="absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full bg-black" />

                    <time className="text-xs text-muted-foreground">
                      {new Date(event.timestamp).toLocaleString()}
                    </time>

                    <p className="text-sm font-medium">
                      {event.event}
                    </p>

                    <p className="text-sm text-muted-foreground">
                      {event.details}
                    </p>

                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-sm text-muted-foreground">
                No events found.
              </p>
            )}
          </Card>

        </div>
      </div>


      {/* Case Report */}
      <Card className="p-4">
        <h3 className="text-sm font-medium text-muted-foreground mb-2">
          Case Report
        </h3>

        <pre className="whitespace-pre-wrap text-sm font-mono">
          {buildCaseReport(detail, displayedFacts)}
        </pre>
      </Card>


      {/* AI Investigator */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-muted-foreground">
            AI Investigator
          </h3>

          <button
            onClick={handleInvestigate}
            disabled={isInvestigating}
            className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
          >
            {isInvestigating
              ? "Investigating…"
              : investigation
                ? "Run Again"
                : "Run Investigation"}
          </button>
        </div>

        {/* Investigation Progress Steps */}
        {isInvestigating && investigationStep >= 0 && (
          <div className="mb-4">
            <ol className="list-decimal list-inside space-y-1 text-sm">
              {INVESTIGATION_STEPS.slice(0, investigationStep + 1).map((step, idx) => (
                <li
                  key={idx}
                  className={idx === investigationStep ? "font-medium" : ""}
                >
                  {step}
                </li>
              ))}
            </ol>
          </div>
        )}

        {investigation && !isInvestigating && (
          <div className="space-y-6">
            {/* Authoritative financial exposure */}
            {investigation.financial_exposure && (
              <div className="rounded-lg border border-border p-4">
                <h4 className="text-sm font-semibold mb-3">
                  Financial Exposure
                </h4>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

                  <div>
                    <dt className="text-xs text-muted-foreground">
                      Gross Order Value
                    </dt>

                    <dd className="text-sm font-medium">
                      {formatCurrency(
                        investigation.financial_exposure
                          .gross_order_value
                      )}
                    </dd>
                  </div>

                  <div>
                    <dt className="text-xs text-muted-foreground">
                      Total Refunds
                    </dt>

                    <dd className="text-sm font-medium">
                      {formatCurrency(
                        investigation.financial_exposure
                          .refund_amount
                      )}
                    </dd>
                  </div>

                  <div>
                    <dt className="text-xs text-muted-foreground">
                      Potential Exposure
                    </dt>

                    <dd className="text-sm font-medium">
                      {formatCurrency(
                        investigation.financial_exposure
                          .potential_exposure
                      )}
                    </dd>
                  </div>

                </div>

                <p className="text-xs text-muted-foreground mt-3">
                  Financial values are calculated deterministically from
                  account data and are authoritative over AI-generated prose.
                </p>
              </div>
            )}

            {/* Summary */}
            <div className="rounded-lg bg-muted p-4">
              <h4 className="text-sm font-semibold mb-2">
                Investigation Summary
              </h4>

              <p className="text-sm leading-relaxed">
                {investigation.summary}
              </p>

              {investigation.confidence && (
                <p className="mt-2 text-xs text-muted-foreground">
                  Confidence:{" "}
                  <span className="font-medium">
                    {investigation.confidence}
                  </span>
                </p>
              )}
            </div>

            {/* Key Findings */}
            {investigation.key_findings?.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold mb-2">
                  Key Findings
                </h4>

                <ul className="list-disc list-inside space-y-1 text-sm">
                  {investigation.key_findings.map((finding, idx) => (
                    <li key={idx}>{finding}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Evidence Gaps */}
            {investigation.evidence_gaps?.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold mb-2">
                  Evidence Gaps
                </h4>

                <ul className="list-disc list-inside space-y-1 text-sm">
                  {investigation.evidence_gaps.map((gap, idx) => (
                    <li key={idx}>{gap}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Uncertainties */}
            {investigation.uncertainties?.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold mb-2">
                  Uncertainties
                </h4>

                <ul className="list-disc list-inside space-y-1 text-sm">
                  {investigation.uncertainties.map((u, idx) => (
                    <li key={idx}>{u}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Investigation Chain */}
            <div>
              <h4 className="text-sm font-semibold mb-2">Investigation Chain</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                {[
                  ["Risk model", "Deterministic score"],
                  ["Graph evidence", `${graphEvidence.total_graph_links ?? 0} links`],
                  ["Evidence", `${Object.keys(detail.evidence_status?.fields || {}).length} fields checked`],
                  ["Policy", detail.recommended_action || "No action"],
                ].map(([label, value]) => (
                  <div key={label} className="rounded-md border border-border p-3">
                    <p className="text-muted-foreground">{label}</p>
                    <p className="font-medium mt-1 line-clamp-2">{value}</p>
                  </div>
                ))}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                AI analysis is advisory; deterministic financial values and policy remain authoritative.
              </p>
            </div>

            {/* Tool Trace */}
            {investigation.tool_calls?.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold mb-2">
                  Tool Trace
                </h4>

                <ul className="space-y-2 text-sm">
                  {investigation.tool_calls.map((call, idx) => (
                    <li key={idx}>
                      <button
                        onClick={() =>
                          setExpandedTool(
                            expandedTool === idx ? null : idx
                          )
                        }
                        className="w-full flex items-center justify-between text-left text-muted-foreground hover:text-foreground"
                      >
                        <span className="font-mono">
                          {call.tool}
                        </span>

                        <span>
                          {expandedTool === idx ? "−" : "+"}
                        </span>
                      </button>

                      <p className="text-xs">
                        {call.result_summary}
                      </p>

                      {expandedTool === idx && (
                        <pre className="mt-2 whitespace-pre-wrap text-xs bg-muted p-2 rounded">
                          {JSON.stringify(call, null, 2)}
                        </pre>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Completion Summary */}
            {investigation.completion_summary && (
              <div className="rounded-lg border border-border p-4">
                <h4 className="text-sm font-semibold mb-3">
                  Investigation Complete
                </h4>

                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                  <div>
                    <dt className="text-xs text-muted-foreground">
                      Tools Executed
                    </dt>
                    <dd className="font-medium">
                      {investigation.completion_summary.tools_executed}
                    </dd>
                  </div>

                  <div>
                    <dt className="text-xs text-muted-foreground">
                      Graph Links Found
                    </dt>
                    <dd className="font-medium">
                      {investigation.completion_summary.graph_links_found}
                    </dd>
                  </div>

                  <div>
                    <dt className="text-xs text-muted-foreground">
                      Financial Exposure
                    </dt>
                    <dd className="font-medium">
                      ₹{investigation.completion_summary.financial_exposure}
                    </dd>
                  </div>

                  <div>
                    <dt className="text-xs text-muted-foreground">
                      Evidence Fields Checked
                    </dt>
                    <dd className="font-medium">
                      {investigation.completion_summary.evidence_fields_checked}
                    </dd>
                  </div>

                  <div>
                    <dt className="text-xs text-muted-foreground">
                      AI Confidence
                    </dt>
                    <dd className="font-medium">
                      {investigation.completion_summary.llm_confidence}
                    </dd>
                  </div>

                  <div>
                    <dt className="text-xs text-muted-foreground">
                      Duration
                    </dt>
                    <dd className="font-medium">
                      {investigation.completion_summary.duration_seconds}s
                    </dd>
                  </div>
                </div>
              </div>
            )}

            {/* Investigation Duration */}
            {investigation.duration_seconds != null && (
              <p className="text-xs text-muted-foreground">
                Investigation duration:{" "}
                {investigation.duration_seconds}s
              </p>
            )}

            {/* Recommended Action */}
            <div className="text-sm text-muted-foreground">
              Recommended action:{" "}
              <span className="font-medium text-black dark:text-white">
                {investigation.recommended_action}
              </span>

              <p className="text-xs mt-1">
                Action source:{" "}
                {investigation.action_source === "deterministic_policy"
                  ? "Deterministic Policy Engine"
                  : investigation.action_source}
              </p>
            </div>
          </div>
        )}
      </Card>

    </div>
  );
}