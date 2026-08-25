import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getQueue } from "../api/queue";
import Badge from "../components/Badge";
import Card from "../components/Card";

export default function Dashboard() {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getQueue()
      .then((data) => setQueue(data.accounts))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div>Loading queue…</div>;
  if (error) return <div className="text-destructive">{error}</div>;

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold">Investigation Queue</h2>
        <p className="text-sm text-muted-foreground">
          {queue.length} accounts flagged by Model B
        </p>
      </div>
      <Card>
        <table className="w-full">
          <thead>
            <tr className="border-b border-border text-left text-sm text-muted-foreground">
              <th className="px-4 py-2">Rank</th>
              <th className="px-4 py-2">Account</th>
              <th className="px-4 py-2">Risk Score</th>
              <th className="px-4 py-2">Tier</th>
              <th className="px-4 py-2">Action</th>
            </tr>
          </thead>
          <tbody>
            {queue.map((account) => (
              <tr key={account.account_id} className="border-b border-border hover:bg-muted/50">
                <td className="px-4 py-3 text-sm">{account.rank}</td>
                <td className="px-4 py-3 text-sm">
                  <Link to={`/investigations/${account.account_id}`} className="underline underline-offset-4 hover:text-primary">
                    {account.account_id}
                  </Link>
                </td>
                <td className="px-4 py-3 text-sm">{account.proba.toFixed(6)}</td>
                <td className="px-4 py-3"><Badge tier={account.risk_tier} /></td>
                <td className="px-4 py-3 text-sm">{account.recommended_action}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}