import React, { useEffect, useMemo, useState } from "react";
import { getAudit } from "../api/audit";
import Card from "../components/Card";

const OPERATING_MODEL = "LightGBM Model A";
const PER_PAGE = 20;

export default function AuditLog() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(null);

  // Pagination state
  const [predPage, setPredPage] = useState(1);
  const [invPage, setInvPage] = useState(1);

  const loadAudit = () => {
    setLoading(true);
    setError(null);
    getAudit()
      .then((data) => setRecords(data.records))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadAudit();
  }, []);

  const { predictions, investigations } = useMemo(() => {
    const preds = [];
    const invest = [];

    records.forEach((r) => {
      if (
        r.investigation_source === "llm" ||
        r.investigation_source === "deterministic" ||
        (r.tool_calls && r.summary)
      ) {
        invest.push(r);
      } else {
        preds.push(r);
      }
    });

    return { predictions: preds, investigations: invest };
  }, [records]);

  // Paginated data
  const paginatedPredictions = predictions.slice(
    (predPage - 1) * PER_PAGE,
    predPage * PER_PAGE
  );

  const paginatedInvestigations = investigations.slice(
    (invPage - 1) * PER_PAGE,
    invPage * PER_PAGE
  );

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
            Initial risk scoring and flagging by {OPERATING_MODEL}.
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
            {paginatedPredictions.map((record, idx) => (
              <React.Fragment key={`pred-${idx}`}>
                <tr
                  className="border-b border-border hover:bg-muted/50 cursor-pointer"
                  onClick={() =>
                    setExpanded(
                      expanded === `pred-${idx}` ? null : `pred-${idx}`
                    )
                  }
                >
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {new Date(record.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-sm">{record.account_id}</td>
                  <td className="px-4 py-3 text-sm">
                    {record.model_version || OPERATING_MODEL}
                  </td>
                  <td className="px-4 py-3 text-sm">{record.proba ?? "-"}</td>
                  <td className="px-4 py-3 text-sm">{record.risk_tier || "-"}</td>
                  <td className="px-4 py-3 text-sm">{record.action_recommended}</td>
                  <td className="px-4 py-3 text-sm">
                    {expanded === `pred-${idx}` ? "−" : "+"}
                  </td>
                </tr>
                {expanded === `pred-${idx}` && (
                  <tr className="border-b border-border bg-muted/30">
                    <td colSpan="7" className="px-6 py-4">
                      <div className="space-y-1 text-sm">
                        <p><strong>Model:</strong> {record.model_version}</p>
                        <p><strong>Score:</strong> {record.proba}</p>
                        <p><strong>Tier:</strong> {record.risk_tier}</p>
                        {record.case_report_generated && (
                          <p><strong>Case Report:</strong> Generated</p>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>

        {/* Pagination for predictions */}
        <div className="flex justify-between items-center p-3">
          <button
            disabled={predPage === 1}
            onClick={() => setPredPage(predPage - 1)}
            className="text-sm border rounded px-3 py-1 disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-sm text-muted-foreground">
            Page {predPage} of {Math.ceil(predictions.length / PER_PAGE)}
          </span>
          <button
            disabled={predPage >= Math.ceil(predictions.length / PER_PAGE)}
            onClick={() => setPredPage(predPage + 1)}
            className="text-sm border rounded px-3 py-1 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </Card>

      {/* Investigation Section */}
      <Card>
        <div className="p-4 border-b border-border">
          <h3 className="font-medium">AI Investigation Log</h3>
          <p className="text-xs text-muted-foreground">
            AI-driven investigations, tool calls, and policy decisions.
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
            {paginatedInvestigations.map((record, idx) => (
              <React.Fragment key={`inv-${idx}`}>
                <tr
                  className="border-b border-border hover:bg-muted/50 cursor-pointer"
                  onClick={() =>
                    setExpanded(
                      expanded === `inv-${idx}` ? null : `inv-${idx}`
                    )
                  }
                >
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {new Date(record.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-sm">{record.account_id}</td>
                  <td className="px-4 py-3 text-sm">
                    {record.investigation_source || "unknown"}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {record.tool_calls ? JSON.parse(record.tool_calls).length : 0}
                  </td>
                  <td className="px-4 py-3 text-sm">{record.action_recommended}</td>
                  <td className="px-4 py-3 text-sm">
                    {record.action_source || "deterministic_policy"}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {record.error ? "Fallback" : "Completed"}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {expanded === `inv-${idx}` ? "−" : "+"}
                  </td>
                </tr>
                {expanded === `inv-${idx}` && (
                  <tr className="border-b border-border bg-muted/30">
                    <td colSpan="8" className="px-6 py-4">
                      <div className="space-y-3 text-sm">
                        {(() => {
                          let summaryObj = null;
                          try {
                            summaryObj = JSON.parse(record.summary);
                          } catch {
                            summaryObj = null;
                          }

                          if (summaryObj && typeof summaryObj === "object") {
                            return (
                              <>
                                <p>
                                  <strong>Summary:</strong>{" "}
                                  {summaryObj.summary || "No summary"}
                                </p>

                                {summaryObj.key_findings?.length > 0 && (
                                  <div>
                                    <strong>Key Findings:</strong>
                                    <ul className="list-disc list-inside mt-1 space-y-1">
                                      {summaryObj.key_findings.map((k, i) => (
                                        <li key={i}>{k}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}

                                {summaryObj.evidence_gaps?.length > 0 && (
                                  <div>
                                    <strong>Evidence Gaps:</strong>
                                    <ul className="list-disc list-inside mt-1 space-y-1">
                                      {summaryObj.evidence_gaps.map((g, i) => (
                                        <li key={i}>{g}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}

                                {summaryObj.uncertainties?.length > 0 && (
                                  <div>
                                    <strong>Uncertainties:</strong>
                                    <ul className="list-disc list-inside mt-1 space-y-1">
                                      {summaryObj.uncertainties.map((u, i) => (
                                        <li key={i}>{u}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}

                                {summaryObj.confidence && (
                                  <p>
                                    <strong>Confidence:</strong>{" "}
                                    {summaryObj.confidence}
                                  </p>
                                )}
                              </>
                            );
                          }

                          return (
                            <p>
                              <strong>Summary:</strong> {record.summary}
                            </p>
                          );
                        })()}

                        {record.tool_calls && (
                          <div>
                            <strong>Tool Calls:</strong>
                            <div className="mt-1 space-y-1">
                              {JSON.parse(record.tool_calls).map((call, i) => (
                                <div key={i} className="text-xs">
                                  <span className="font-mono">{call.tool}</span>
                                  {" → "}
                                  {call.result_summary}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>

        {/* Pagination for investigations */}
        <div className="flex justify-between items-center p-3">
          <button
            disabled={invPage === 1}
            onClick={() => setInvPage(invPage - 1)}
            className="text-sm border rounded px-3 py-1 disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-sm text-muted-foreground">
            Page {invPage} of {Math.ceil(investigations.length / PER_PAGE)}
          </span>
          <button
            disabled={invPage >= Math.ceil(investigations.length / PER_PAGE)}
            onClick={() => setInvPage(invPage + 1)}
            className="text-sm border rounded px-3 py-1 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </Card>
    </div>
  );
}