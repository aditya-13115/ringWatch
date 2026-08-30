import React, { useEffect, useMemo, useState } from "react";
import { getAudit } from "../api/audit";
import Card from "../components/Card";

const OPERATING_MODEL = "Ensemble_LGBM_B_GNN";
const PER_PAGE = 20;

function parseJSON(value, fallback = null) {
  if (!value) return fallback;

  if (typeof value === "object") {
    return value;
  }

  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

function getAction(record) {
  return (
    record.action_recommended ||
    record.recommended_action ||
    "-"
  );
}

export default function AuditLog() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(null);

  const [predPage, setPredPage] = useState(1);
  const [invPage, setInvPage] = useState(1);

  const loadAudit = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await getAudit();

      setRecords(
        Array.isArray(data?.records)
          ? data.records
          : []
      );
    } catch (e) {
      setError(e.message || "Failed to load audit log");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAudit();
  }, []);

  const { predictions, investigations } = useMemo(() => {
    const preds = [];
    const invest = [];

    records.forEach((record) => {
      const isInvestigation =
        record.investigation_source === "llm" ||
        record.investigation_source === "deterministic" ||
        Boolean(record.tool_calls) ||
        Boolean(record.summary);

      if (isInvestigation) {
        invest.push(record);
      } else {
        preds.push(record);
      }
    });

    return {
      predictions: preds,
      investigations: invest,
    };
  }, [records]);

  const predictionPages = Math.max(
    1,
    Math.ceil(predictions.length / PER_PAGE)
  );

  const investigationPages = Math.max(
    1,
    Math.ceil(investigations.length / PER_PAGE)
  );

  const paginatedPredictions = predictions.slice(
    (predPage - 1) * PER_PAGE,
    predPage * PER_PAGE
  );

  const paginatedInvestigations = investigations.slice(
    (invPage - 1) * PER_PAGE,
    invPage * PER_PAGE
  );

  const toggleExpanded = (key) => {
    setExpanded(
      expanded === key
        ? null
        : key
    );
  };

  if (loading) {
    return (
      <div className="p-6">
        Loading audit log…
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-destructive">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-8">

      {/* ---------------------------------------------------------
          HEADER
      --------------------------------------------------------- */}

      <div>
        <h2 className="text-xl font-semibold">
          Investigation Audit Trail
        </h2>

        <p className="text-sm text-muted-foreground">
          Complete decision and investigation trace
        </p>
      </div>

      {/* =========================================================
          MODEL PREDICTION LOG
      ========================================================= */}

      <Card>
        <div className="p-4 border-b border-border">
          <h3 className="font-medium">
            Model Prediction Log
          </h3>

          <p className="text-xs text-muted-foreground">
            Initial risk scoring and flagging by{" "}
            {OPERATING_MODEL}.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border text-left text-sm text-muted-foreground">
                <th className="px-4 py-2">
                  Timestamp
                </th>

                <th className="px-4 py-2">
                  Account
                </th>

                <th className="px-4 py-2">
                  Model
                </th>

                <th className="px-4 py-2">
                  Score
                </th>

                <th className="px-4 py-2">
                  Risk Tier
                </th>

                <th className="px-4 py-2">
                  Action
                </th>

                <th className="px-4 py-2" />
              </tr>
            </thead>

            <tbody>
              {paginatedPredictions.map((record, idx) => {
                const key = `pred-${idx}`;

                const score =
                  record.proba != null
                    ? `${(
                        Number(record.proba) * 100
                      ).toFixed(2)}%`
                    : "-";

                return (
                  <React.Fragment key={key}>
                    <tr
                      className="border-b border-border hover:bg-muted/50 cursor-pointer"
                      onClick={() =>
                        toggleExpanded(key)
                      }
                    >
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {record.timestamp
                          ? new Date(
                              record.timestamp
                            ).toLocaleString()
                          : "-"}
                      </td>

                      <td className="px-4 py-3 text-sm">
                        {record.account_id || "-"}
                      </td>

                      <td className="px-4 py-3 text-sm">
                        {record.model_version ||
                          OPERATING_MODEL}
                      </td>

                      <td className="px-4 py-3 text-sm">
                        {score}
                      </td>

                      <td className="px-4 py-3 text-sm">
                        {record.risk_tier || "-"}
                      </td>

                      <td className="px-4 py-3 text-sm">
                        {getAction(record)}
                      </td>

                      <td className="px-4 py-3 text-sm">
                        {expanded === key
                          ? "−"
                          : "+"}
                      </td>
                    </tr>

                    {expanded === key && (
                      <tr className="border-b border-border bg-muted/30">
                        <td
                          colSpan="7"
                          className="px-6 py-4"
                        >
                          <div className="space-y-1 text-sm">
                            <p>
                              <strong>
                                Model:
                              </strong>{" "}
                              {record.model_version ||
                                OPERATING_MODEL}
                            </p>

                            <p>
                              <strong>
                                Score:
                              </strong>{" "}
                              {score}
                            </p>

                            <p>
                              <strong>
                                Risk Tier:
                              </strong>{" "}
                              {record.risk_tier ||
                                "-"}
                            </p>

                            <p>
                              <strong>
                                Action:
                              </strong>{" "}
                              {getAction(record)}
                            </p>

                            {record.case_report_generated && (
                              <p>
                                <strong>
                                  Case Report:
                                </strong>{" "}
                                Generated
                              </p>
                            )}

                            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                              <div className="rounded-md border border-border p-3">
                                <p className="text-xs text-muted-foreground">Input snapshot hash</p>
                                <p className="text-xs font-mono mt-1 break-all">{record.input_data_hash || "—"}</p>
                              </div>
                              <div className="rounded-md border border-border p-3">
                                <p className="text-xs text-muted-foreground">Threshold used</p>
                                <p className="text-sm font-medium mt-1">{record.threshold_used != null ? Number(record.threshold_used).toFixed(6) : "—"}</p>
                              </div>
                              <div className="rounded-md border border-border p-3">
                                <p className="text-xs text-muted-foreground">Human decision</p>
                                <p className="text-sm font-medium mt-1">{record.human_decision || "NOT_RECORDED"}</p>
                              </div>
                              <div className="rounded-md border border-border p-3">
                                <p className="text-xs text-muted-foreground">Outcome</p>
                                <p className="text-sm font-medium mt-1">{record.outcome || "—"}</p>
                              </div>
                            </div>

                            {record.feature_snapshot && (
                              <details className="mt-3">
                                <summary className="cursor-pointer text-xs font-medium">Recorded decision snapshot</summary>
                                <pre className="mt-2 whitespace-pre-wrap break-words rounded-md bg-muted p-3 text-[11px]">{record.feature_snapshot}</pre>
                              </details>
                            )}

                            {record.evidence_subgraph && (
                              <details className="mt-3">
                                <summary className="cursor-pointer text-xs font-medium">Evidence subgraph reference</summary>
                                <pre className="mt-2 whitespace-pre-wrap break-words rounded-md bg-muted p-3 text-[11px]">{record.evidence_subgraph}</pre>
                              </details>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Prediction pagination */}

        <div className="flex justify-between items-center p-3">
          <button
            disabled={predPage === 1}
            onClick={() =>
              setPredPage(
                Math.max(1, predPage - 1)
              )
            }
            className="text-sm border rounded px-3 py-1 disabled:opacity-50"
          >
            Previous
          </button>

          <span className="text-sm text-muted-foreground">
            Page {predPage} of {predictionPages}
          </span>

          <button
            disabled={
              predPage >= predictionPages
            }
            onClick={() =>
              setPredPage(
                Math.min(
                  predictionPages,
                  predPage + 1
                )
              )
            }
            className="text-sm border rounded px-3 py-1 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </Card>

      {/* =========================================================
          AI INVESTIGATION LOG
      ========================================================= */}

      <Card>
        <div className="p-4 border-b border-border">
          <h3 className="font-medium">
            AI Investigation Log
          </h3>

          <p className="text-xs text-muted-foreground">
            AI-driven investigations, tool calls,
            findings, and policy decisions.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border text-left text-sm text-muted-foreground">
                <th className="px-4 py-2">
                  Timestamp
                </th>

                <th className="px-4 py-2">
                  Account
                </th>

                <th className="px-4 py-2">
                  Source
                </th>

                <th className="px-4 py-2">
                  Tools
                </th>

                <th className="px-4 py-2">
                  Action
                </th>

                <th className="px-4 py-2">
                  Action Authority
                </th>

                <th className="px-4 py-2">
                  Status
                </th>

                <th className="px-4 py-2" />
              </tr>
            </thead>

            <tbody>
              {paginatedInvestigations.map(
                (record, idx) => {
                  const key = `inv-${idx}`;

                  const toolCalls =
                    parseJSON(
                      record.tool_calls,
                      []
                    );

                  const safeToolCalls =
                    Array.isArray(toolCalls)
                      ? toolCalls
                      : [];

                  const status = record.error
                    ? "Fallback"
                    : "Completed";

                  return (
                    <React.Fragment key={key}>
                      <tr
                        className="border-b border-border hover:bg-muted/50 cursor-pointer"
                        onClick={() =>
                          toggleExpanded(key)
                        }
                      >
                        <td className="px-4 py-3 text-xs text-muted-foreground">
                          {record.timestamp
                            ? new Date(
                                record.timestamp
                              ).toLocaleString()
                            : "-"}
                        </td>

                        <td className="px-4 py-3 text-sm">
                          {record.account_id || "-"}
                        </td>

                        <td className="px-4 py-3 text-sm">
                          {record.investigation_source ||
                            "unknown"}
                        </td>

                        <td className="px-4 py-3 text-sm">
                          {safeToolCalls.length}
                        </td>

                        <td className="px-4 py-3 text-sm">
                          {getAction(record)}
                        </td>

                        <td className="px-4 py-3 text-sm">
                          {record.action_source ||
                            "deterministic_policy"}
                        </td>

                        <td className="px-4 py-3 text-sm">
                          {status}
                        </td>

                        <td className="px-4 py-3 text-sm">
                          {expanded === key
                            ? "−"
                            : "+"}
                        </td>
                      </tr>

                      {expanded === key && (
                        <tr className="border-b border-border bg-muted/30">
                          <td
                            colSpan="8"
                            className="px-6 py-4"
                          >
                            <div className="space-y-3 text-sm">

                              {/* Summary */}

                              <div>
                                <strong>
                                  Investigation Summary:
                                </strong>

                                <p className="mt-1">
                                  {record.summary ||
                                    "No summary available."}
                                </p>
                              </div>

                              {/* Tool Calls */}

                              {safeToolCalls.length >
                                0 && (
                                <div>
                                  <strong>
                                    Tool Calls:
                                  </strong>

                                  <div className="mt-2 space-y-1">
                                    {safeToolCalls.map(
                                      (
                                        call,
                                        i
                                      ) => (
                                        <div
                                          key={i}
                                          className="text-xs"
                                        >
                                          <span className="font-mono">
                                            {call.tool ||
                                              "unknown_tool"}
                                          </span>

                                          {" → "}

                                          {call.result_summary ||
                                            "Executed"}
                                        </div>
                                      )
                                    )}
                                  </div>
                                </div>
                              )}

                              {/* Decision Chain */}

                              <div>
                                <strong>
                                  Decision Chain:
                                </strong>

                                <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                                  <div className="rounded-md border border-border p-3">
                                    <p className="text-muted-foreground">
                                      Risk model
                                    </p>

                                    <p className="font-medium mt-1">
                                      {record.model_version ||
                                        OPERATING_MODEL}
                                    </p>
                                  </div>

                                  <div className="rounded-md border border-border p-3">
                                    <p className="text-muted-foreground">
                                      Risk tier
                                    </p>

                                    <p className="font-medium mt-1">
                                      {record.risk_tier || "—"}
                                    </p>
                                  </div>

                                  <div className="rounded-md border border-border p-3">
                                    <p className="text-muted-foreground">
                                      Investigation
                                    </p>

                                    <p className="font-medium mt-1">
                                      {record.investigation_source ||
                                        "Not run"}
                                    </p>
                                  </div>

                                  <div className="rounded-md border border-border p-3">
                                    <p className="text-muted-foreground">
                                      Evidence / tools
                                    </p>

                                    <p className="font-medium mt-1">
                                      {safeToolCalls.length} tool call
                                      {safeToolCalls.length === 1
                                        ? ""
                                        : "s"}
                                    </p>
                                  </div>

                                  <div className="rounded-md border border-border p-3">
                                    <p className="text-muted-foreground">
                                      Recommended action
                                    </p>

                                    <p className="font-medium mt-1">
                                      {getAction(record)}
                                    </p>
                                  </div>

                                  <div className="rounded-md border border-border p-3">
                                    <p className="text-muted-foreground">
                                      Action authority
                                    </p>

                                    <p className="font-medium mt-1">
                                      {record.action_source ||
                                        "deterministic_policy"}
                                    </p>
                                  </div>
                                </div>

                                <p className="text-[11px] text-muted-foreground mt-3">
                                  The model produces the risk signal. Investigation
                                  gathers evidence. The deterministic policy controls
                                  the recommended action. AI does not directly execute
                                  financial actions.
                                </p>
                              </div>

                              <div>
                                <strong>
                                  Action Authority:
                                </strong>{" "}
                                {record.action_source ||
                                  "deterministic_policy"}
                              </div>

                              {/* Error */}

                              {record.error && (
                                <div>
                                  <strong>
                                    Error:
                                  </strong>{" "}
                                  {record.error}
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                }
              )}
            </tbody>
          </table>
        </div>

        {/* Investigation pagination */}

        <div className="flex justify-between items-center p-3">
          <button
            disabled={invPage === 1}
            onClick={() =>
              setInvPage(
                Math.max(1, invPage - 1)
              )
            }
            className="text-sm border rounded px-3 py-1 disabled:opacity-50"
          >
            Previous
          </button>

          <span className="text-sm text-muted-foreground">
            Page {invPage} of {investigationPages}
          </span>

          <button
            disabled={
              invPage >= investigationPages
            }
            onClick={() =>
              setInvPage(
                Math.min(
                  investigationPages,
                  invPage + 1
                )
              )
            }
            className="text-sm border rounded px-3 py-1 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </Card>
    </div>
  );
}