import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getQueue } from "../api/queue";
import Badge from "../components/Badge";
import Card from "../components/Card";

const LIMITS = [10, 25, 50, 100];
const TIERS = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"];

export default function Dashboard() {
  const [queue, setQueue] = useState([]);
  const [totalFlagged, setTotalFlagged] = useState(0);
  const [limit, setLimit] = useState(10);
  const [tierFilter, setTierFilter] = useState("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);

    // Load the complete queue so tier filters can reach MEDIUM/LOW
    // accounts instead of filtering only the first high-risk rows.
    getQueue(100000)
      .then((data) => {
        setQueue(data.accounts);
        setTotalFlagged(data.total);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [limit]);

  const filteredQueue =
    tierFilter === "ALL"
      ? queue
      : queue.filter((a) => a.risk_tier === tierFilter);

  // Keep the selector as the number of rows shown while filtering the
  // complete queue, so MEDIUM/LOW are available without changing the
  // displayed page size.
  const visibleQueue = filteredQueue.slice(0, limit);

  const formatRiskScore = (score) => {
    const percentage = Number(score) * 100;

    return `${percentage.toFixed(2)}%`;
  };

  if (loading) {
    return <div className="p-6">Loading queue…</div>;
  }

  if (error) {
    return <div className="p-6 text-destructive">{error}</div>;
  }

  return (
    <div>
      <div className="mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold">
            Investigation Queue
          </h2>

          <p className="text-sm text-muted-foreground">
            Showing {visibleQueue.length} of {totalFlagged} flagged accounts
            {" · "}
            V4 Ensemble
          </p>
        </div>

        <select
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
          className="border border-border rounded-md px-3 py-2 text-sm bg-background"
        >
          {LIMITS.map((n) => (
            <option key={n} value={n}>
              Show {n}
            </option>
          ))}
        </select>
      </div>

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
            {tier === "ALL"
              ? "All"
              : tier.charAt(0) + tier.slice(1).toLowerCase()}
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
            {visibleQueue.map((account) => (
              <tr
                key={account.account_id}
                className="border-b border-border hover:bg-muted/50"
              >
                <td className="px-4 py-3 text-sm">
                  {account.rank}
                </td>

                <td className="px-4 py-3 text-sm">
                  <Link
                    to={`/investigations/${account.account_id}`}
                    className="underline underline-offset-4 hover:text-primary"
                  >
                    {account.account_id}
                  </Link>
                </td>

                <td className="px-4 py-3 text-sm font-medium">
                  {account.proba != null
                    ? `${(Number(account.proba) * 100).toFixed(2)}%`
                    : "-"}
                </td>

                <td className="px-4 py-3">
                  <Badge tier={account.risk_tier} />
                </td>

                <td className="px-4 py-3 text-sm">
                  {account.recommended_action}
                </td>

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

            {visibleQueue.length === 0 && (
              <tr>
                <td
                  colSpan={6}
                  className="px-4 py-8 text-center text-sm text-muted-foreground"
                >
                  No accounts found for this risk tier.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}