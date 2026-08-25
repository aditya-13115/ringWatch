import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getQueue } from "../api/queue";
import Badge from "../components/Badge";
import Card from "../components/Card";

const LIMITS = [7, 10, 25, 50, 100];

export default function Dashboard() {
  const [queue, setQueue] = useState([]);
  const [limit, setLimit] = useState(7);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    getQueue(limit)
      .then((data) => setQueue(data.accounts))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [limit]);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Investigation Queue</h2>
          <p className="text-sm text-muted-foreground">
            {queue.length} accounts flagged by Model B
          </p>
        </div>
        <select
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
          className="border border-border rounded-md px-3 py-2 text-sm bg-background"
        >
          {LIMITS.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
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