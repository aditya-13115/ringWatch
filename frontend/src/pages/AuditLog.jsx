import { useEffect, useState } from "react";
import { getAudit } from "../api/audit";
import Card from "../components/Card";

export default function AuditLog() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getAudit()
      .then((data) => setRecords(data.records))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div>Loading audit log…</div>;
  if (error) return <div className="text-destructive">{error}</div>;

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
              <th className="px-4 py-2">Summary</th>
              <th className="px-4 py-2">Tools</th>
            </tr>
          </thead>
          <tbody>
            {records.map((record, idx) => (
              <tr key={idx} className="border-b border-border hover:bg-muted/50">
                <td className="px-4 py-3 text-xs text-muted-foreground">
                  {new Date(record.timestamp).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-sm">{record.account_id}</td>
                <td className="px-4 py-3 text-sm">
                  {record.investigation_source || "model"}
                </td>
                <td className="px-4 py-3 text-sm">{record.action_recommended}</td>
                <td className="px-4 py-3 text-sm">{record.summary || ""}</td>
                <td className="px-4 py-3 text-xs text-muted-foreground">
                  {Array.isArray(record.tool_calls) ? record.tool_calls.map(t => t.tool).join(", ") : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}