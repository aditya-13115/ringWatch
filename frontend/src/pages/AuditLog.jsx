import { useEffect, useState } from "react";
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

  if (loading) return <div className="p-6">Loading audit log…</div>;
  if (error) return <div className="p-6 text-destructive">{error}</div>;

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold">Investigation Audit Trail</h2>
        <p className="text-sm text-muted-foreground">
          Complete decision and investigation trace
        </p>
      </div>
      <Card>
        <table className="w-full">
          <thead>
            <tr className="border-b border-border text-left text-sm text-muted-foreground">
              <th className="px-4 py-2">Timestamp</th>
              <th className="px-4 py-2">Account</th>
              <th className="px-4 py-2">Source</th>
              <th className="px-4 py-2">Action</th>
              <th className="px-4 py-2">Details</th>
            </tr>
          </thead>
          <tbody>
            {records.map((record, idx) => (
              <>
                <tr
                  key={idx}
                  className="border-b border-border hover:bg-muted/50 cursor-pointer"
                  onClick={() => setExpanded(expanded === idx ? null : idx)}
                >
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {new Date(record.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-sm">{record.account_id}</td>
                  <td className="px-4 py-3 text-sm">
                    {record.investigation_source || "model"}
                  </td>
                  <td className="px-4 py-3 text-sm">{record.action_recommended}</td>
                  <td className="px-4 py-3 text-sm">
                    {expanded === idx ? "−" : "+"}
                  </td>
                </tr>
                {expanded === idx && (
                  <tr key={`expanded-${idx}`} className="border-b border-border bg-muted/30">
                    <td colSpan="5" className="px-6 py-4">
                      <div className="space-y-2">
                        <p><strong>Model:</strong> {record.model_version}</p>
                        <p><strong>Score:</strong> {record.proba}</p>
                        <p><strong>Tier:</strong> {record.risk_tier}</p>
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