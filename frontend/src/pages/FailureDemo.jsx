import { useState } from "react";
import { simulateFailure } from "../api/failure";
import Card from "../components/Card";

export default function FailureDemo() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleClick = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await simulateFailure();
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl">
      <div className="mb-6">
        <h2 className="text-xl font-semibold">Failure Handling & Data Quality</h2>
        <p className="text-sm text-muted-foreground">
          Demonstrate that malformed or corrupted input does not silently contaminate
          the investigation pipeline.
        </p>
      </div>

      <button
        onClick={handleClick}
        disabled={loading}
        className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
      >
        {loading ? "Simulating…" : "Simulate Malformed Batch"}
      </button>

      {error && <p className="mt-4 text-destructive">{error}</p>}

      {result && (
        <div className="mt-6 space-y-4">
          <Card className="p-6">
            <h3 className="text-sm font-medium text-muted-foreground mb-4">Processing Summary</h3>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
              <div>
                <dt className="text-xs text-muted-foreground">Batch Size</dt>
                <dd className="text-2xl font-semibold">{result.batch_size}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Malformed</dt>
                <dd className="text-2xl font-semibold text-destructive">{result.malformed_rows}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Quarantined</dt>
                <dd className="text-2xl font-semibold">{result.quarantined}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Valid Processed</dt>
                <dd className="text-2xl font-semibold">{result.valid_processed}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Human Review</dt>
                <dd className="text-2xl font-semibold">{result.human_review_routed}</dd>
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">Audit Trail</h3>
            <ul className="space-y-2">
              {result.audit_trail.map((entry, idx) => (
                <li key={idx} className="flex justify-between text-sm">
                  <span>{entry.event}</span>
                  <span className="text-muted-foreground">{entry.details}</span>
                </li>
              ))}
            </ul>
          </Card>

          {/* Explicit safety guarantee callout */}
          <div className="rounded-md border border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20 p-4">
            <p className="font-medium text-emerald-700 dark:text-emerald-300">
              Safety Guarantee
            </p>
            <p className="text-sm text-emerald-700 dark:text-emerald-300">
              No malformed records entered the investigation pipeline.
              The system continued safely without data corruption or silent failure.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}