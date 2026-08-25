import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getAccount, investigateAccount, getAccountTimeline } from "../api/account";
import Badge from "../components/Badge";
import Card from "../components/Card";
import GraphView from "../components/GraphView";

export default function AccountInvestigation() {
  const { accountId } = useParams();
  const [detail, setDetail] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [investigation, setInvestigation] = useState(null);
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
    try {
      const result = await investigateAccount(accountId);
      setInvestigation(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsInvestigating(false);
    }
  };

  if (loading) return <div>Loading account…</div>;
  if (error && !detail) return <div className="text-destructive">{error}</div>;
  if (!detail) return <div>No account found.</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">{detail.account_id}</h2>
          <p className="text-sm text-muted-foreground">Rank #{detail.rank}</p>
        </div>
        <Badge tier={detail.risk_tier} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="p-4">
          <h3 className="text-sm font-medium text-muted-foreground">Risk Score</h3>
          <p className="text-2xl font-semibold">{detail.proba.toFixed(6)}</p>
        </Card>
        <Card className="p-4">
          <h3 className="text-sm font-medium text-muted-foreground">Recommended Action</h3>
          <p className="text-lg font-medium">{detail.recommended_action}</p>
        </Card>
      </div>

      <Card className="p-4">
        <h3 className="text-sm font-medium text-muted-foreground mb-2">Observed Facts</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(detail.observed_facts).map(([key, value]) => (
            <div key={key}>
              <dt className="text-xs text-muted-foreground">{key}</dt>
              <dd className="text-sm font-medium">{value}</dd>
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-4">
        <h3 className="text-sm font-medium text-muted-foreground mb-2">Top SHAP Contributors</h3>
        <ul className="space-y-2">
          {detail.top_shap_features.map((f) => (
            <li key={f.feature} className="flex justify-between text-sm">
              <span>{f.feature}</span>
              <span className={f.shap_value >= 0 ? "text-black" : "text-gray-500"}>
                {f.shap_value.toFixed(4)}
              </span>
            </li>
          ))}
        </ul>
      </Card>

      <Card className="p-4">
        <h3 className="text-sm font-medium text-muted-foreground mb-2">Graph Relationships</h3>
        <GraphView accountId={accountId} />
      </Card>

      <Card className="p-4">
        <h3 className="text-sm font-medium text-muted-foreground mb-2">Evidence Status</h3>
        <div className="space-y-1">
          {Object.entries(detail.evidence_status.fields).map(([field, status]) => (
            <div key={field} className="flex justify-between text-sm">
              <span>{field}</span>
              <span className={status === "MISSING" ? "text-destructive" : "text-muted-foreground"}>
                {status}
              </span>
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-4">
        <h3 className="text-sm font-medium text-muted-foreground mb-2">Investigation Timeline</h3>
        {timeline.length > 0 ? (
          <ol className="relative border-l border-border ml-2 pl-4 space-y-4">
            {timeline.map((event, idx) => (
              <li key={idx} className="ml-4">
                <div className="absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full bg-black" />
                <time className="text-xs text-muted-foreground">
                  {new Date(event.timestamp).toLocaleString()}
                </time>
                <p className="text-sm font-medium">{event.event}</p>
                <p className="text-sm text-muted-foreground">{event.details}</p>
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-sm text-muted-foreground">No events found.</p>
        )}
      </Card>

      <Card className="p-4">
        <h3 className="text-sm font-medium text-muted-foreground mb-2">Case Report</h3>
        <pre className="whitespace-pre-wrap text-sm font-mono">{detail.case_report_text}</pre>
      </Card>

      <Card className="p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-muted-foreground">AI Investigator</h3>
          <button
            onClick={handleInvestigate}
            disabled={isInvestigating}
            className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
          >
            {isInvestigating ? "Investigating…" : "Run Investigation"}
          </button>
        </div>

        {investigation && (
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-semibold">Summary</h4>
              <p className="text-sm">{investigation.summary}</p>
            </div>

            {investigation.key_findings.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold">Key Findings</h4>
                <ul className="list-disc list-inside text-sm">
                  {investigation.key_findings.map((finding, idx) => (
                    <li key={idx}>{finding}</li>
                  ))}
                </ul>
              </div>
            )}

            {investigation.evidence_gaps.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold">Evidence Gaps</h4>
                <ul className="list-disc list-inside text-sm">
                  {investigation.evidence_gaps.map((gap, idx) => (
                    <li key={idx}>{gap}</li>
                  ))}
                </ul>
              </div>
            )}

            {investigation.uncertainties.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold">Uncertainties</h4>
                <ul className="list-disc list-inside text-sm">
                  {investigation.uncertainties.map((u, idx) => (
                    <li key={idx}>{u}</li>
                  ))}
                </ul>
              </div>
            )}

            {investigation.tool_calls.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold">Tool Trace</h4>
                <ul className="space-y-2 text-sm">
                  {investigation.tool_calls.map((call, idx) => (
                    <li key={idx} className="text-muted-foreground">
                      <span className="font-mono">{call.tool}</span> → {call.result_summary}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="text-sm text-muted-foreground">
              Recommended action: <span className="font-medium text-black">{investigation.recommended_action}</span>
              <p className="text-xs">Action source: {investigation.action_source}</p>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}