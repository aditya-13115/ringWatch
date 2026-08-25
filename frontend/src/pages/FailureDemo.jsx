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
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold">Failure Demo</h2>
        <p className="text-sm text-muted-foreground">
          Simulate a batch with malformed address rows
        </p>
      </div>

      <button
        onClick={handleClick}
        disabled={loading}
        className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-gray-800 disabled:opacity-50"
      >
        {loading ? "Simulating…" : "Simulate Malformed Batch"}
      </button>

      {error && <p className="mt-4 text-destructive">{error}</p>}

      {result && (
        <div className="mt-6">
          <Card className="p-4">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">Result</h3>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
              <div><dt className="text-xs text-muted-foreground">Batch Size</dt><dd className="text-xl font-semibold">{result.batch_size}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Malformed</dt><dd className="text-xl font-semibold">{result.malformed_rows}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Quarantined</dt><dd className="text-xl font-semibold">{result.quarantined}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Valid Processed</dt><dd className="text-xl font-semibold">{result.valid_processed}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Human Review</dt><dd className="text-xl font-semibold">{result.human_review_routed}</dd></div>
            </div>
          </Card>

          <Card className="p-4 mt-4">
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
        </div>
      )}
    </div>
  );
}