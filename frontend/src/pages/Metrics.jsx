import { useEffect, useState } from "react";
import { getMetrics } from "../api/metrics";
import Card from "../components/Card";

export default function Metrics() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getMetrics()
      .then((data) => setMetrics(data))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div>Loading metrics…</div>;
  if (error) return <div className="text-destructive">{error}</div>;

  const modelB = metrics.model_metrics.model_B;
  const modelA = metrics.model_metrics.model_A;
  const baseline = metrics.model_metrics.baseline;

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold">Metrics</h2>
        <p className="text-sm text-muted-foreground">
          Model performance on held-out R004 ring
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4">
          <h3 className="text-sm font-medium text-muted-foreground">Baseline</h3>
          <dl className="mt-2 space-y-2 text-sm">
            <div><dt className="text-muted-foreground">Precision</dt><dd>{baseline.precision}</dd></div>
            <div><dt className="text-muted-foreground">Recall</dt><dd>{baseline.recall}</dd></div>
            <div><dt className="text-muted-foreground">F1</dt><dd>{baseline.f1}</dd></div>
            <div><dt className="text-muted-foreground">Cost</dt><dd>₹{baseline.cost}</dd></div>
          </dl>
        </Card>

        <Card className="p-4">
          <h3 className="text-sm font-medium text-muted-foreground">Model A</h3>
          <dl className="mt-2 space-y-2 text-sm">
            <div><dt className="text-muted-foreground">Precision</dt><dd>{modelA.precision}</dd></div>
            <div><dt className="text-muted-foreground">Recall</dt><dd>{modelA.recall}</dd></div>
            <div><dt className="text-muted-foreground">F1</dt><dd>{modelA.f1}</dd></div>
            <div><dt className="text-muted-foreground">PR-AUC</dt><dd>{modelA.pr_auc}</dd></div>
            <div><dt className="text-muted-foreground">Cost</dt><dd>₹{modelA.cost}</dd></div>
          </dl>
        </Card>

        <Card className="p-4 border-black">
          <h3 className="text-sm font-medium text-muted-foreground">Model B</h3>
          <dl className="mt-2 space-y-2 text-sm">
            <div><dt className="text-muted-foreground">Precision</dt><dd>{modelB.precision}</dd></div>
            <div><dt className="text-muted-foreground">Recall</dt><dd>{modelB.recall}</dd></div>
            <div><dt className="text-muted-foreground">F1</dt><dd>{modelB.f1}</dd></div>
            <div><dt className="text-muted-foreground">PR-AUC</dt><dd>{modelB.pr_auc}</dd></div>
            <div><dt className="text-muted-foreground">Operating K</dt><dd>{modelB.operating_k}</dd></div>
            <div><dt className="text-muted-foreground">Cost</dt><dd>₹{modelB.cost}</dd></div>
          </dl>
        </Card>
      </div>
    </div>
  );
}