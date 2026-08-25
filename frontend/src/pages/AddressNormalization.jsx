import { useState } from "react";
import { normalizeAddress } from "../api/address";
import Card from "../components/Card";

export default function AddressNormalization() {
  const [rawAddress, setRawAddress] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!rawAddress.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await normalizeAddress(rawAddress);
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <div className="mb-6">
        <h2 className="text-xl font-semibold">Address Normalization</h2>
        <p className="text-sm text-muted-foreground">
          Convert messy raw addresses into canonical entities using component parsing.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <textarea
          value={rawAddress}
          onChange={(e) => setRawAddress(e.target.value)}
          className="w-full rounded-md border border-border bg-card px-3 py-2 text-sm"
          rows={3}
          placeholder="Apt 201, ABC Apartments, Mumbai 400001"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
        >
          {loading ? "Normalizing…" : "Normalize"}
        </button>
      </form>

      {error && <p className="mt-4 text-destructive">{error}</p>}

      {result && (
        <Card className="p-4 mt-6">
          <h3 className="text-sm font-medium text-muted-foreground mb-2">Result</h3>
          <dl className="space-y-2 text-sm">
            <div>
              <dt className="text-muted-foreground">Raw Address</dt>
              <dd>{result.raw_address}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Normalized Address</dt>
              <dd>{result.normalized_address || "Not resolved"}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Canonical Address ID</dt>
              <dd>{result.candidate_address_id || "Not resolved"}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Confidence</dt>
              <dd>{(result.confidence * 100).toFixed(0)}%</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Human Review</dt>
              <dd>{result.requires_human_review ? "Required" : "Not required"}</dd>
            </div>
          </dl>
        </Card>
      )}
    </div>
  );
}