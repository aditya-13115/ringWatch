import { useEffect, useState } from "react";
import { getMetrics, getCurves } from "../api/metrics";
import Card from "../components/Card";
import LineChart from "../components/LineChart";
import { Link } from "react-router-dom";

export default function Metrics() {
  const [metrics, setMetrics] = useState(null);
  const [curves, setCurves] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([getMetrics(), getCurves()])
      .then(([m, c]) => {
        setMetrics(m);
        setCurves(c);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6">Loading metrics…</div>;
  if (error) return <div className="p-6 text-destructive">{error}</div>;

  const modelB = metrics.model_metrics.model_B;
  const modelA = metrics.model_metrics.model_A;
  const baseline = metrics.model_metrics.baseline;

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-semibold">Metrics</h2>
        <p className="text-sm text-muted-foreground">
          Model performance on held-out R004 ring
        </p>
      </div>

      {/* Model summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4">
          <h3 className="text-sm font-medium text-muted-foreground">Baseline</h3>
          <dl className="mt-2 space-y-1 text-sm">
            <div><dt className="text-muted-foreground">Precision</dt><dd>{baseline.precision}</dd></div>
            <div><dt className="text-muted-foreground">Recall</dt><dd>{baseline.recall}</dd></div>
            <div><dt className="text-muted-foreground">F1</dt><dd>{baseline.f1}</dd></div>
            <div><dt className="text-muted-foreground">Cost</dt><dd>₹{baseline.cost}</dd></div>
          </dl>
        </Card>

        <Card className="p-4">
          <h3 className="text-sm font-medium text-muted-foreground">Model A</h3>
          <dl className="mt-2 space-y-1 text-sm">
            <div><dt className="text-muted-foreground">Precision</dt><dd>{modelA.precision}</dd></div>
            <div><dt className="text-muted-foreground">Recall</dt><dd>{modelA.recall}</dd></div>
            <div><dt className="text-muted-foreground">F1</dt><dd>{modelA.f1}</dd></div>
            <div><dt className="text-muted-foreground">PR-AUC</dt><dd>{modelA.pr_auc}</dd></div>
            <div><dt className="text-muted-foreground">Cost</dt><dd>₹{modelA.cost}</dd></div>
          </dl>
        </Card>

        <Card className="p-4 border-black">
          <h3 className="text-sm font-medium text-muted-foreground">Model B</h3>
          <dl className="mt-2 space-y-1 text-sm">
            <div><dt className="text-muted-foreground">Precision</dt><dd>{modelB.precision}</dd></div>
            <div><dt className="text-muted-foreground">Recall</dt><dd>{modelB.recall}</dd></div>
            <div><dt className="text-muted-foreground">F1</dt><dd>{modelB.f1}</dd></div>
            <div><dt className="text-muted-foreground">PR-AUC</dt><dd>{modelB.pr_auc}</dd></div>
            <div><dt className="text-muted-foreground">Operating K</dt><dd>{modelB.operating_k}</dd></div>
            <div><dt className="text-muted-foreground">Cost</dt><dd>₹{modelB.cost}</dd></div>
          </dl>
        </Card>
      </div>

      {/* Interpretation */}
      <Card className="p-4">
        <h3 className="text-sm font-medium text-muted-foreground mb-2">
          Why Model B is used operationally
        </h3>
        <p className="text-sm text-muted-foreground">
          Model A catches almost all abuse, but flags too many accounts, causing high
          false-positive costs. Model B is much more selective: it reduces false positives
          and operational cost, at the price of lower recall. For a human-in-the-loop
          investigation queue, a small precision-focused set is more actionable.
        </p>
        <p className="text-sm font-medium mt-2">
          Estimated cost reduction relative to Model A: ₹
          {Math.round(modelA.cost - modelB.cost).toLocaleString()}
        </p>
      </Card>

      {/* Curves */}
      <div className="space-y-6">
        <Card className="p-4">
          <h3 className="text-sm font-medium mb-3">Precision-Recall Tradeoff</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <LineChart
              title="Model A Precision & Recall"
              data={curves?.model_A?.precision || []}
              yLabel="Precision"
            />
            <LineChart
              title="Model B Precision & Recall"
              data={curves?.model_B?.precision || []}
              yLabel="Precision"
            />
          </div>
        </Card>

        <Card className="p-4">
          <h3 className="text-sm font-medium mb-3">Cost Curve</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <LineChart
              title="Model A Cost"
              data={curves?.model_A?.cost || []}
              yLabel="Cost"
            />
            <LineChart
              title="Model B Cost"
              data={curves?.model_B?.cost || []}
              yLabel="Cost"
            />
          </div>
        </Card>
      </div>
    </div>
  );
}