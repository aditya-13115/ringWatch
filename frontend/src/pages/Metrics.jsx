import { useEffect, useState } from "react";
import { getMetrics, getCurves } from "../api/metrics";
import Card from "../components/Card";
import LineChart from "../components/LineChart";
import { Link } from "react-router-dom";

const formatPct = (val) => `${(Number(val || 0) * 100).toFixed(1)}%`;
const formatCost = (val) => `₹${Math.round(Number(val || 0)).toLocaleString()}`;

export default function Metrics() {
  const [metrics, setMetrics] = useState(null);
  const [curves, setCurves] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([
      getMetrics(),
      getCurves().catch(() => null),
    ])
      .then(([m, c]) => {
        setMetrics(m);
        setCurves(c);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6">Loading metrics…</div>;
  if (error) return <div className="p-6 text-destructive">{error}</div>;
  if (!metrics) return <div className="p-6">No metrics available.</div>;

  const modelMetrics = metrics.model_metrics || metrics;

  const modelAConfig = modelMetrics.model_A || {};
  const modelBConfig = modelMetrics.model_B || {};

  const modelA = modelAConfig.test || modelAConfig;
  const modelB = modelBConfig.test || modelBConfig;

  const baseline =
    modelMetrics.baseline_test ||
    modelMetrics.baseline ||
    {};

  const thresholdA = modelAConfig.threshold ?? null;
  const thresholdB = modelBConfig.threshold ?? null;

  const modelACost = Number(modelA.cost || 0);
  const modelBCost = Number(modelB.cost || 0);

  // ----------------------------------------------------------
  // FIX: Normalize bar widths against the maximum cost.
  // This prevents overflow when Model B cost > Model A cost.
  // ----------------------------------------------------------
  const maxCost = Math.max(modelACost, modelBCost, 1);

  const widthA = (modelACost / maxCost) * 100;
  const widthB = (modelBCost / maxCost) * 100;

  const costDifference = modelBCost - modelACost;

  const hasCurves =
    curves &&
    (
      curves?.model_A?.precision?.length ||
      curves?.model_B?.precision?.length ||
      curves?.model_A?.cost?.length ||
      curves?.model_B?.cost?.length
    );

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-semibold">Model Evaluation</h2>
        <p className="text-sm text-muted-foreground">
          Held-out 30K test set · Best model selection
        </p>
      </div>

      {/* Decision banner */}
      <Card className="p-6 border-black">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium">✓ CURRENT OPERATING MODEL</p>
            <h3 className="text-xl font-semibold mt-1">LightGBM Model A</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Model A achieves the highest F1 and lowest estimated cost on the
              held-out 30K test set.
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground">Operating Threshold</p>
            <p className="text-2xl font-semibold">
              {thresholdA !== null ? Number(thresholdA).toFixed(3) : "—"}
            </p>
          </div>
        </div>
      </Card>

      {/* Performance comparison table */}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="px-4 py-2">Metric</th>
                <th className="px-4 py-2">Baseline</th>
                <th className="px-4 py-2">Model A</th>
                <th className="px-4 py-2">Model B</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border">
                <td className="px-4 py-2 font-medium">Precision</td>
                <td className="px-4 py-2">{formatPct(baseline.precision)}</td>
                <td className="px-4 py-2 font-semibold">{formatPct(modelA.precision)} ★</td>
                <td className="px-4 py-2">{formatPct(modelB.precision)}</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2 font-medium">Recall</td>
                <td className="px-4 py-2">{formatPct(baseline.recall)}</td>
                <td className="px-4 py-2 font-semibold">{formatPct(modelA.recall)} ★</td>
                <td className="px-4 py-2">{formatPct(modelB.recall)}</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2 font-medium">F1</td>
                <td className="px-4 py-2">{formatPct(baseline.f1)}</td>
                <td className="px-4 py-2 font-semibold">{formatPct(modelA.f1)} ★</td>
                <td className="px-4 py-2">{formatPct(modelB.f1)}</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2 font-medium">PR-AUC</td>
                <td className="px-4 py-2">—</td>
                <td className="px-4 py-2 font-semibold">{formatPct(modelA.pr_auc)} ★</td>
                <td className="px-4 py-2">{formatPct(modelB.pr_auc)}</td>
              </tr>
              <tr>
                <td className="px-4 py-2 font-medium">Estimated cost</td>
                <td className="px-4 py-2">{formatCost(baseline.cost)}</td>
                <td className="px-4 py-2 font-semibold">{formatCost(modelA.cost)} ★</td>
                <td className="px-4 py-2">{formatCost(modelB.cost)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>

      {/* What does this mean */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4">
          <h3 className="text-sm font-medium mb-2">Model A — Best overall</h3>
          <p className="text-sm text-muted-foreground">
            Highest F1 and lowest cost. Catches all true ring members with very few false positives.
          </p>
        </Card>
        <Card className="p-4">
          <h3 className="text-sm font-medium mb-2">Model B — Slightly behind</h3>
          <p className="text-sm text-muted-foreground">
            Graph features did not improve over behavioral features on this 30K dataset.
          </p>
        </Card>
        <Card className="p-4">
          <h3 className="text-sm font-medium mb-2">Baseline</h3>
          <p className="text-sm text-muted-foreground">
            Reference for comparing model improvement.
          </p>
        </Card>
      </div>

      {/* Cost visual */}
      <Card className="p-4">
        <h3 className="text-sm font-medium mb-3">Estimated Intervention Cost</h3>
        <div className="space-y-2">
          <div>
            <p className="text-sm">Model A</p>
            <div className="w-full bg-muted rounded h-2">
              <div
                className="bg-black h-2 rounded"
                style={{ width: `${widthA}%` }}
              />
            </div>
            <p className="text-sm mt-1">{formatCost(modelA.cost)}</p>
          </div>

          <div>
            <p className="text-sm">Model B</p>
            <div className="w-full bg-muted rounded h-2">
              <div
                className="bg-black h-2 rounded"
                style={{ width: `${widthB}%` }}
              />
            </div>
            <p className="text-sm mt-1">{formatCost(modelB.cost)}</p>
          </div>
        </div>

        <p className="text-sm font-medium mt-3">
          {costDifference > 0
            ? `Model B costs ${formatCost(costDifference)} more than Model A.`
            : `Model A saves ${formatCost(-costDifference)} compared to Model B.`}
        </p>
      </Card>

      {/* Scatter plot */}
      <Card className="p-4">
        <h3 className="text-sm font-medium mb-3">Precision / Recall Tradeoff</h3>
        <ScatterPlot
          points={[
            { name: "Baseline", precision: Number(baseline.precision || 0), recall: Number(baseline.recall || 0) },
            { name: "Model A", precision: Number(modelA.precision || 0), recall: Number(modelA.recall || 0) },
            { name: "Model B", precision: Number(modelB.precision || 0), recall: Number(modelB.recall || 0) },
          ]}
        />
      </Card>

      {/* Why Model A */}
      <Card className="p-4">
        <h3 className="text-sm font-medium mb-2">Why Model A?</h3>
        <ul className="space-y-1 text-sm">
          <li>✓ Highest F1: {formatPct(modelA.f1)}</li>
          <li>✓ Lowest cost: {formatCost(modelA.cost)}</li>
          <li>✓ Recall: {formatPct(modelA.recall)}</li>
          <li>✓ PR-AUC: {formatPct(modelA.pr_auc)}</li>
        </ul>
      </Card>

      {/* Connect to dashboard */}
      <Card className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h3 className="text-sm font-medium mb-1">Current Operating Configuration</h3>
          <p className="text-sm text-muted-foreground">
            LightGBM Model A → threshold {thresholdA !== null ? Number(thresholdA).toFixed(3) : "—"} → Investigation Queue
          </p>
        </div>
        <Link to="/dashboard" className="inline-block bg-black text-white px-4 py-2 rounded-md text-sm">
          View Investigation Queue →
        </Link>
      </Card>

      {hasCurves && (
        <div className="space-y-6">
          <Card className="p-4">
            <h3 className="text-sm font-medium mb-3">Precision-Recall Tradeoff</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <LineChart title="Model A Precision" data={curves?.model_A?.precision || []} yLabel="Precision" />
              <LineChart title="Model B Precision" data={curves?.model_B?.precision || []} yLabel="Precision" />
            </div>
          </Card>
          <Card className="p-4">
            <h3 className="text-sm font-medium mb-3">Cost Curve</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <LineChart title="Model A Cost" data={curves?.model_A?.cost || []} yLabel="Cost" />
              <LineChart title="Model B Cost" data={curves?.model_B?.cost || []} yLabel="Cost" />
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

function ScatterPlot({ points }) {
  const width = 600;
  const height = 300;
  const margin = { top: 20, right: 20, bottom: 40, left: 50 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const x = (recall) => margin.left + recall * innerWidth;
  const y = (precision) => margin.top + innerHeight - precision * innerHeight;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full">
      <line x1={margin.left} y1={margin.top + innerHeight} x2={width - margin.right} y2={margin.top + innerHeight} stroke="black" strokeWidth="1" />
      <line x1={margin.left} y1={margin.top} x2={margin.left} y2={margin.top + innerHeight} stroke="black" strokeWidth="1" />
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={x(p.recall)} cy={y(p.precision)} r={6} fill="black" />
          <text x={x(p.recall)} y={y(p.precision) - 10} textAnchor="middle" fontSize="10" fill="black">
            {p.name}
          </text>
        </g>
      ))}
      <text x={width / 2} y={height - 5} textAnchor="middle" fontSize="12" fill="black">Recall</text>
      <text x={15} y={height / 2} textAnchor="middle" fontSize="12" fill="black" transform={`rotate(-90, 15, ${height / 2})`}>Precision</text>
    </svg>
  );
}