import { useEffect, useMemo, useState } from "react";
import { getAudit } from "../api/audit";
import Card from "../components/Card";

export default function AuditLog() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    getAudit()
      .then((data) => setRecords(data.records))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const { predictions, investigations } = useMemo(() => {
    const preds = [];
    const invest = [];

    records.forEach((r) => {
      // Determine record type
      if (r.investigation_source === "llm" || r.investigation_source === "deterministic" || (r.tool_calls && r.summary)) {
        invest.push(r);
      } else {
        preds.push(r);
      }
    });

    return { predictions: preds, investigations: invest };
  }, [records]);

  if (loading) return <div className="p-6">Loading audit log…</div>;
  if (error) return <div className="p-6 text-destructive">{error}</div>;

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-semibold">Investigation Audit Trail</h2>
        <p className="text-sm text-muted-foreground">
          Complete decision and investigation trace
        </p>
      </div>

      {/* Prediction Section */}
      <Card>
        <div className="p-4 border-b border-border">
          <h3 className="font-medium">Model Prediction Log</h3>
          <p className="text-xs text-muted-foreground">
            Initial risk scoring and flagging by LightGBM Model B.
          </p>
        </div>
        <table className="w-full">
          <thead>
            <tr className="border-b border-border text-left text-sm text-muted-foreground">
              <th className="px-4 py-2">Timestamp</th>
              <th className="px-4 py-2">Account</th>
              <th className="px-4 py-2">Model</th>
              <th className="px-4 py-2">Score</th>
              <th className="px-4 py-2">Risk Tier</th>
              <th className="px-4 py-2">Action</th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {predictions.map((record, idx) => (
              <>
                <tr
                  key={`pred-${idx}`}
                  className="border-b border-border hover:bg-muted/50 cursor-pointer"
                  onClick={() => setExpanded(expanded === `pred-${idx}` ? null : `pred-${idx}`)}
                >
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {new Date(record.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-sm">{record.account_id}</td>
                  <td className="px-4 py-3 text-sm">{record.model_version || "LightGBM_Model_B"}</td>
                  <td className="px-4 py-3 text-sm">{record.proba ?? "-"}</td>
                  <td className="px-4 py-3 text-sm">{record.risk_tier || "-"}</td>
                  <td className="px-4 py-3 text-sm">{record.action_recommended}</td>
                  <td className="px-4 py-3 text-sm">{expanded === `pred-${idx}` ? "−" : "+"}</td>
                </tr>
                {expanded === `pred-${idx}` && (
                  <tr className="border-b border-border bg-muted/30">
                    <td colSpan="7" className="px-6 py-4">
                      <div className="space-y-1 text-sm">
                        <p><strong>Model:</strong> {record.model_version}</p>
                        <p><strong>Score:</strong> {record.proba}</p>
                        <p><strong>Tier:</strong> {record.risk_tier}</p>
                        {record.case_report_generated && <p><strong>Case Report:</strong> Generated</p>}
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </Card>

      {/* Investigation Section */}
      <Card>
        <div className="p-4 border-b border-border">
          <h3 className="font-medium">AI Investigation Log</h3>
          <p className="text-xs text-muted-foreground">
            LLM-driven investigations, tool calls, and policy decisions.
          </p>
        </div>
        <table className="w-full">
          <thead>
            <tr className="border-b border-border text-left text-sm text-muted-foreground">
              <th className="px-4 py-2">Timestamp</th>
              <th className="px-4 py-2">Account</th>
              <th className="px-4 py-2">Source</th>
              <th className="px-4 py-2">Tools</th>
              <th className="px-4 py-2">Action</th>
              <th className="px-4 py-2">Action Authority</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {investigations.map((record, idx) => (
              <>
                <tr
                  key={`inv-${idx}`}
                  className="border-b border-border hover:bg-muted/50 cursor-pointer"
                  onClick={() => setExpanded(expanded === `inv-${idx}` ? null : `inv-${idx}`)}
                >
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {new Date(record.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-sm">{record.account_id}</td>
                  <td className="px-4 py-3 text-sm">{record.investigation_source || "unknown"}</td>
                  <td className="px-4 py-3 text-sm">
                    {record.tool_calls ? JSON.parse(record.tool_calls).length : 0}
                  </td>
                  <td className="px-4 py-3 text-sm">{record.action_recommended}</td>
                  <td className="px-4 py-3 text-sm">{record.action_source || "deterministic_policy"}</td>
                  <td className="px-4 py-3 text-sm">
                    {record.error ? "Fallback" : "Completed"}
                  </td>
                  <td className="px-4 py-3 text-sm">{expanded === `inv-${idx}` ? "−" : "+"}</td>
                </tr>
                {expanded === `inv-${idx}` && (
                  <tr className="border-b border-border bg-muted/30">
                    <td colSpan="8" className="px-6 py-4">
                      <div className="space-y-2 text-sm">
                        {record.summary && <p><strong>Summary:</strong> {record.summary}</p>}
                        {record.tool_calls && (
                          <div>
                            <strong>Tool Calls:</strong>
                            <pre className="whitespace-pre-wrap text-xs">{record.tool_calls}</pre>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}