import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getAccount } from "../api/account";
import Badge from "../components/Badge";
import Card from "../components/Card";

export default function AccountInvestigation() {
  const { accountId } = useParams();
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getAccount(accountId)
      .then((data) => setDetail(data))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [accountId]);

  if (loading) return <div>Loading account…</div>;
  if (error) return <div className="text-destructive">{error}</div>;

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
        <h3 className="text-sm font-medium text-muted-foreground mb-2">Case Report</h3>
        <pre className="whitespace-pre-wrap text-sm font-mono">{detail.case_report_text}</pre>
      </Card>
    </div>
  );
}