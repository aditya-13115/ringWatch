import { useEffect, useState } from "react";
import { getMetrics, getCurves } from "../api/metrics";
import Card from "../components/Card";
import LineChart from "../components/LineChart";
import { Link } from "react-router-dom";

const formatPct = (val) => `${(val * 100).toFixed(1)}%`;
const formatCost = (val) => `₹${Math.round(val).toLocaleString()}`;

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

  // Compute cost reduction
  const costReduction = modelA.cost - modelB.cost;
  const costReductionPct = (costReduction / modelA.cost) * 100;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-semibold">Model Evaluation</h2>
        <p className="text-sm text-muted-foreground">
          Held-out R004 ring · Model selection and operating tradeoff
        </p>
      </div>

      {/* Decision banner */}
      <Card className="p-6 border-black">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium">✓ CURRENT OPERATING MODEL</p>
            <h3 className="text-xl font-semibold mt-1">LightGBM Model B</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Selected for the current investigation capacity because it provides
              a substantially better precision/cost tradeoff than Model A.
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground">Operating K</p>
            <p className="text-2xl font-semibold">7</p>
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
                <td className="px-4 py-2">{formatPct(modelA.precision)}</td>
                <td className="px-4 py-2 font-semibold">{formatPct(modelB.precision)} ★</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2 font-medium">Recall</td>
                <td className="px-4 py-2">{formatPct(baseline.recall)}</td>
                <td className="px-4 py-2 font-semibold">{formatPct(modelA.recall)} ★</td>
                <td className="px-4 py-2">{formatPct(modelB.recall)}</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2 font-medium">F1</td>
                <td className="px-4 py-2 font-semibold">{formatPct(baseline.f1)} ★</td>
                <td className="px-4 py-2">{formatPct(modelA.f1)}</td>
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
                <td className="px-4 py-2">{formatCost(modelA.cost)}</td>
                <td className="px-4 py-2 font-semibold">{formatCost(modelB.cost)} ★</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>

      {/* What does this mean */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4">
          <h3 className="text-sm font-medium mb-2">Model A — High recall, poor precision</h3>
          <p className="text-sm text-muted-foreground">
            Catches all observed abuse but flags too many accounts. Cost: {formatCost(modelA.cost)}.
          </p>
        </Card>
        <Card className="p-4">
          <h3 className="text-sm font-medium mb-2">Model B — More selective</h3>
          <p className="text-sm text-muted-foreground">
            Higher precision, lower recall. Cost: {formatCost(modelB.cost)}. Chosen for
            current investigation capacity.
          </p>
        </Card>
        <Card className="p-4">
          <h3 className="text-sm font-medium mb-2">Baseline</h3>
          <p className="text-sm text-muted-foreground">
            Reference point for evaluating model improvement.
          </p>
        </Card>
      </div>

      {/* Cost reduction visual */}
      <Card className="p-4">
        <h3 className="text-sm font-medium mb-3">Estimated Intervention Cost</h3>
        <div className="space-y-2">
          <div>
            <p className="text-sm">Model A</p>
            <div className="w-full bg-muted rounded h-2">
              <div className="bg-black h-2 rounded" style={{ width: "100%" }} />
            </div>
            <p className="text-sm mt-1">{formatCost(modelA.cost)}</p>
          </div>
          <div>
            <p className="text-sm">Model B</p>
            <div className="w-full bg-muted rounded h-2">
              <div className="bg-black h-2 rounded" style={{ width: `${(modelB.cost / modelA.cost) * 100}%` }} />
            </div>
            <p className="text-sm mt-1">{formatCost(modelB.cost)}</p>
          </div>
        </div>
        <p className="text-sm font-medium mt-3">
          Model B cost is ~{costReductionPct.toFixed(0)}% lower than Model A
          ({formatCost(costReduction)} saved).
        </p>
      </Card>

      {/* Precision-Recall scatter plot */}
      <Card className="p-4">
        <h3 className="text-sm font-medium mb-3">Precision / Recall Tradeoff</h3>
        <ScatterPlot
          points={[
            { name: "Baseline", precision: baseline.precision, recall: baseline.recall },
            { name: "Model A", precision: modelA.precision, recall: modelA.recall },
            { name: "Model B", precision: modelB.precision, recall: modelB.recall },
          ]}
        />
      </Card>

      {/* Why Model B */}
      <Card className="p-4">
        <h3 className="text-sm font-medium mb-2">Why Model B?</h3>
        <ul className="space-y-1 text-sm">
          <li>✓ Highest precision: {formatPct(modelB.precision)}</li>
          <li>✓ Cost: {formatCost(modelB.cost)}</li>
          <li>✓ Operating K = 7 matches investigation capacity</li>
          <li>⚠ Recall: {formatPct(modelB.recall)} — some abuse may be missed</li>
        </ul>
      </Card>

      {/* Connect to dashboard */}
      <Card className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h3 className="text-sm font-medium mb-1">Current Operating Configuration</h3>
          <p className="text-sm text-muted-foreground">
            LightGBM Model B → 7 accounts → Investigation Queue → Risk-tier actions
          </p>
        </div>
        <Link
          to="/dashboard"
          className="inline-block bg-black text-white px-4 py-2 rounded-md text-sm"
        >
          View Investigation Queue →
        </Link>
      </Card>

      {/* Curves (existing) */}
      {curves && (
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
      )}
    </div>
  );
}

// Simple scatter plot component
function ScatterPlot({ points }) {
  const width = 600;
  const height = 300;
  const margin = { top: 20, right: 20, bottom: 40, left: 50 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const x = (recall) => margin.left + (recall * innerWidth);
  const y = (precision) => margin.top + innerHeight - (precision * innerHeight);

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