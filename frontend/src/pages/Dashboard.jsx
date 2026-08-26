import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getQueue } from "../api/queue";
import Badge from "../components/Badge";
import Card from "../components/Card";

const LIMITS = [7, 10, 25, 50, 100];
const TIERS = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"];

export default function Dashboard() {
  const [queue, setQueue] = useState([]);
  const [limit, setLimit] = useState(7);
  const [tierFilter, setTierFilter] = useState("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    getQueue(limit)
      .then((data) => setQueue(data.accounts))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [limit]);

  const filteredQueue =
    tierFilter === "ALL"
      ? queue
      : queue.filter((a) => a.risk_tier === tierFilter);

  if (loading) return <div className="p-6">Loading queue…</div>;
  if (error) return <div className="p-6 text-destructive">{error}</div>;

  return (
    <div>
      <div className="mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold">Investigation Queue</h2>
          <p className="text-sm text-muted-foreground">
            {filteredQueue.length} accounts flagged by Model B
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

      {/* Risk filter tabs */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {TIERS.map((tier) => (
          <button
            key={tier}
            onClick={() => setTierFilter(tier)}
            className={`rounded-full px-3 py-1 text-sm ${
              tierFilter === tier
                ? "bg-black text-white"
                : "border border-border text-muted-foreground hover:bg-accent"
            }`}
          >
            {tier === "ALL" ? "All" : tier.charAt(0) + tier.slice(1).toLowerCase()}
          </button>
        ))}
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
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {filteredQueue.map((account) => (
              <tr
                key={account.account_id}
                className="border-b border-border hover:bg-muted/50"
              >
                <td className="px-4 py-3 text-sm">{account.rank}</td>
                <td className="px-4 py-3 text-sm">
                  <Link
                    to={`/investigations/${account.account_id}`}
                    className="underline underline-offset-4 hover:text-primary"
                  >
                    {account.account_id}
                  </Link>
                </td>
                <td className="px-4 py-3 text-sm">{account.proba.toFixed(6)}</td>
                <td className="px-4 py-3"><Badge tier={account.risk_tier} /></td>
                <td className="px-4 py-3 text-sm">{account.recommended_action}</td>
                <td className="px-4 py-3 text-sm">
                  <Link
                    to={`/investigations/${account.account_id}`}
                    className="underline"
                  >
                    Investigate
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}