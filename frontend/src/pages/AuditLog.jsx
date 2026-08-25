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
        <h2 className="text-xl font-semibold">Audit Log</h2>
        <p className="text-sm text-muted-foreground">
          Investigation trace for all flagged accounts
        </p>
      </div>
      <Card>
        <table className="w-full">
          <thead>
            <tr className="border-b border-border text-left text-sm text-muted-foreground">
              <th className="px-4 py-2">Timestamp</th>
              <th className="px-4 py-2">Account</th>
              <th className="px-4 py-2">Model Version</th>
              <th className="px-4 py-2">Score</th>
              <th className="px-4 py-2">Tier</th>
              <th className="px-4 py-2">Action</th>
              <th className="px-4 py-2">Case Report</th>
            </tr>
          </thead>
          <tbody>
            {records.map((record) => (
              <tr key={record.account_id} className="border-b border-border hover:bg-muted/50">
                <td className="px-4 py-3 text-xs text-muted-foreground">
                  {new Date(record.timestamp).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-sm">{record.account_id}</td>
                <td className="px-4 py-3 text-sm">{record.model_version}</td>
                <td className="px-4 py-3 text-sm">{record.proba.toFixed(6)}</td>
                <td className="px-4 py-3 text-sm">{record.risk_tier}</td>
                <td className="px-4 py-3 text-sm">{record.action_recommended}</td>
                <td className="px-4 py-3 text-sm">
                  {record.case_report_generated ? "✓" : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}