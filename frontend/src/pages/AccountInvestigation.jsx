import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  getAccount,
  investigateAccount,
  getAccountTimeline,
} from "../api/account";
import { Link } from "react-router-dom";
import Badge from "../components/Badge";
import Card from "../components/Card";
import GraphView from "../components/GraphView";


function ActionPanel({ tier, accountId }) {
  switch (tier) {
    case "CRITICAL":
      return (
        <div className="flex gap-2 mt-2">
          <Link to={`/verification/${accountId}`} className="bg-black text-white px-4 py-2 rounded-md text-sm">
            Place Soft Hold
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
  "Analyzing with Groq",
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


  useEffect(() => {
    Promise.all([
      getAccount(accountId),
      getAccountTimeline(accountId),
    ])
      .then(([accountData, timelineData]) => {
        setDetail(accountData);
        setTimeline(timelineData.events);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
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
            Investigation Rank #{detail.rank} of 7
          </p>
        </div>

        <Badge tier={detail.risk_tier} />
      </div>


      {/* Model / LLM / Policy Separation */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4">
          <h3 className="text-sm font-medium text-muted-foreground mb-2">Risk Model</h3>
          <p className="text-sm font-semibold">LightGBM Model B</p>
          <p className="text-xs text-muted-foreground">
            Score: {detail.proba.toFixed(6)}
          </p>
          <p className="text-xs text-muted-foreground">
            Rank: #{detail.rank}
          </p>
        </Card>

        <Card className="p-4">
          <h3 className="text-sm font-medium text-muted-foreground mb-2">
            AI Investigator
          </h3>
          <p className="text-sm font-semibold">
            {!investigation
              ? "Not yet run"
              : investigation.source === "llm"
                ? "Groq / Llama"
                : "Deterministic Fallback"}
          </p>
          <p className="text-xs text-muted-foreground">
            {investigation ? "Investigation complete" : "Not yet run"}
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
          <p className="text-sm font-semibold">Deterministic Policy Engine</p>
          <p className="text-xs text-muted-foreground">
            Final action is determined by policy, not LLM.
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
              {detail.evidence_status?.missing_evidence_count === null
                ? "No dispute yet"
                : `${detail.evidence_status.missing_evidence_count} missing`}
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
          Action authority: deterministic policy
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
              {Object.entries(detail.observed_facts).map(
                ([key, value]) => (
                  <div key={key}>
                    <dt className="text-xs text-muted-foreground">
                      {key}
                    </dt>

                    <dd className="text-sm font-medium">
                      {value}
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


          {/* Evidence Status */}
          <Card className="p-4">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">
              Evidence Status
            </h3>

            <div className="space-y-1">
              {Object.entries(detail.evidence_status.fields).map(
                ([field, status]) => (
                  <div
                    key={field}
                    className="flex justify-between text-sm"
                  >
                    <span>{field}</span>

                    <span
                      className={
                        status === "MISSING"
                          ? "text-destructive"
                          : "text-muted-foreground"
                      }
                    >
                      {status}
                    </span>
                  </div>
                )
              )}
            </div>
          </Card>

        </div>


        {/* Right column */}
        <div className="space-y-6">

          {/* Adaptive Graph Relationships */}
          <Card className="p-4">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">
              Graph Relationships
            </h3>

            {detail.risk_tier === "CRITICAL" ||
            detail.risk_tier === "HIGH" ? (
              <GraphView accountId={accountId} />
            ) : detail.risk_tier === "MEDIUM" ? (
              <div className="text-sm text-muted-foreground">
                <p>
                  {detail.graph_evidence?.total_graph_links || 0} graph
                  links found.
                </p>

                <p>
                  No significant network evidence to display.
                </p>
              </div>
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
          {detail.case_report_text}
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
            {/* Summary */}
            <div className="rounded-lg bg-muted p-4">
              <h4 className="text-sm font-semibold mb-2">Investigation Summary</h4>
              <p className="text-sm leading-relaxed">{investigation.summary}</p>
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
                <h4 className="text-sm font-semibold mb-2">Key Findings</h4>
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
                <h4 className="text-sm font-semibold mb-2">Evidence Gaps</h4>
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
                <h4 className="text-sm font-semibold mb-2">Uncertainties</h4>
                <ul className="list-disc list-inside space-y-1 text-sm">
                  {investigation.uncertainties.map((u, idx) => (
                    <li key={idx}>{u}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Tool Trace */}
            {investigation.tool_calls?.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold mb-2">Tool Trace</h4>

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
                        <span className="font-mono">{call.tool}</span>

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
                      LLM Confidence
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
                Action source: {investigation.action_source}
              </p>
            </div>
          </div>
        )}
      </Card>

    </div>
  );
}