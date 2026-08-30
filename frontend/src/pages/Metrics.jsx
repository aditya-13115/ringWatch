import { useEffect, useState } from "react";
import { getMetrics, getCurves, getFeatureAblation } from "../api/metrics";
import Card from "../components/Card";
import LineChart from "../components/LineChart";
import { Link } from "react-router-dom";

const formatPct = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }

  return `${(Number(value) * 100).toFixed(1)}%`;
};

const formatCost = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }

  return `₹${Math.round(Number(value)).toLocaleString("en-IN")}`;
};

const formatThreshold = (value) => {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(Number(value))
  ) {
    return "—";
  }

  return Number(value).toFixed(3);
};

function MetricCell({ value, highlight = false }) {
  return (
    <td className={`px-4 py-2 ${highlight ? "font-semibold" : ""}`}>
      {value}
      {highlight ? " ★" : ""}
    </td>
  );
}

export default function Metrics() {
  const [metrics, setMetrics] = useState(null);
  const [curves, setCurves] = useState(null);
  const [featureAblation, setFeatureAblation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;

    async function load() {
      try {
        const [metricsResponse, curvesResponse, ablationResponse] = await Promise.all([
          getMetrics(),
          getCurves().catch(() => null),
          getFeatureAblation().catch(() => null),
        ]);

        if (!mounted) return;

        setMetrics(metricsResponse);
        setCurves(curvesResponse);
        setFeatureAblation(ablationResponse);
      } catch (err) {
        if (!mounted) return;
        setError(err.message || "Failed to load metrics");
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      mounted = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="p-6">
        Loading model evaluation…
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-destructive">
        {error}
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="p-6">
        No metrics available.
      </div>
    );
  }

  // ---------------------------------------------------------
  // New API structure
  // ---------------------------------------------------------

  const models = metrics.models || {};

  const baseline = models.baseline || {};
  const modelA = models.model_A || {};
  const modelB = models.model_B || {};
  const gnn = models.gnn || {};
  const ensemble = models.ensemble || {};

  const operatingModel =
    metrics.operating_model || {};

  const operatingThreshold =
    operatingModel.threshold ??
    ensemble.threshold;

  // ---------------------------------------------------------
  // Model collection for cards/table
  // ---------------------------------------------------------

  const comparisonModels = [
    {
      key: "baseline",
      name: "Baseline",
      data: baseline,
    },
    {
      key: "model_A",
      name: "LightGBM A (Tuned)",
      data: modelA,
    },
    {
      key: "model_B",
      name: "LightGBM B (Tuned)",
      data: modelB,
    },
    {
      key: "gnn",
      name: "GNN",
      data: gnn,
    },
    {
      key: "ensemble",
      name: "V4 Ensemble",
      data: ensemble,
    },
  ];

  // ---------------------------------------------------------
  // Cost bars
  // ---------------------------------------------------------

  const costs = comparisonModels
    .map((model) => Number(model.data.cost || 0))
    .filter((value) => value > 0);

  const maxCost = Math.max(...costs, 1);

  // ---------------------------------------------------------
  // Curves
  // ---------------------------------------------------------

  const hasCurves =
    curves &&
    Object.keys(curves).some(
      (key) =>
        curves[key]?.precision?.length ||
        curves[key]?.recall?.length ||
        curves[key]?.cost?.length
    );

  const curveModels = [
    {
      key: "baseline",
      label: "Baseline",
    },
    {
      key: "model_A",
      label: "LightGBM A (Tuned)",
    },
    {
      key: "model_B",
      label: "LightGBM B (Tuned)",
    },
    {
      key: "gnn",
      label: "GNN",
    },
    {
      key: "ensemble",
      label: "V4 Ensemble",
    },
  ].filter((model) => curves?.[model.key]);

  // ---------------------------------------------------------
  // Best model by F1
  // ---------------------------------------------------------

  const bestModel = comparisonModels
    .filter(
      (model) =>
        model.key !== "baseline" &&
        model.data.f1 !== null &&
        model.data.f1 !== undefined
    )
    .sort(
      (a, b) =>
        Number(b.data.f1 || 0) -
        Number(a.data.f1 || 0)
    )[0];

  const baselineCost = Number(baseline.cost || 0);
  const ensembleCost = Number(ensemble.cost || 0);
  const costReduction = baselineCost > 0
    ? ((baselineCost - ensembleCost) / baselineCost) * 100
    : null;

  return (
    <div className="space-y-8">

      {/* =====================================================
          HEADER
      ===================================================== */}

      <div>
        <h2 className="text-2xl font-semibold">
          Model Evaluation
        </h2>

        <p className="text-sm text-muted-foreground">
          V4 realistic 30K test set · LightGBM + GNN + Ensemble
        </p>
      </div>

      {/* =====================================================
          CURRENT OPERATING MODEL
      ===================================================== */}

      <Card className="p-6 border-black">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">

          <div>
            <p className="text-sm font-medium">
              ✓ CURRENT OPERATING MODEL
            </p>

            <h3 className="text-xl font-semibold mt-1">
              {operatingModel.name || "V4 Ensemble"}
            </h3>

            <p className="text-sm text-muted-foreground mt-1">
              {operatingModel.description ||
                "Current RingWatch production scoring configuration."}
            </p>
          </div>

          <div className="text-right">
            <p className="text-xs text-muted-foreground">
              Operating Threshold
            </p>

            <p className="text-2xl font-semibold">
              {formatThreshold(operatingThreshold)}
            </p>
          </div>

        </div>
      </Card>

      {/* =====================================================
          MODEL COMPARISON
      ===================================================== */}

      <Card>
        <div className="overflow-x-auto">

          <table className="w-full text-sm">

            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="px-4 py-2">
                  Metric
                </th>

                <th className="px-4 py-2">
                  Baseline
                </th>

                <th className="px-4 py-2">
                  LightGBM A (Tuned)
                </th>

                <th className="px-4 py-2">
                  LightGBM B (Tuned)
                </th>

                <th className="px-4 py-2">
                  GNN
                </th>

                <th className="px-4 py-2">
                  V4 Ensemble
                </th>
              </tr>
            </thead>

            <tbody>

              <tr className="border-b border-border">
                <td className="px-4 py-2 font-medium">
                  Precision
                </td>

                <MetricCell value={formatPct(baseline.precision)} />
                <MetricCell value={formatPct(modelA.precision)} />
                <MetricCell value={formatPct(modelB.precision)} />
                <MetricCell value={formatPct(gnn.precision)} />
                <MetricCell
                  value={formatPct(ensemble.precision)}
                  highlight
                />
              </tr>

              <tr className="border-b border-border">
                <td className="px-4 py-2 font-medium">
                  Recall
                </td>

                <MetricCell value={formatPct(baseline.recall)} />
                <MetricCell value={formatPct(modelA.recall)} />
                <MetricCell value={formatPct(modelB.recall)} />
                <MetricCell value={formatPct(gnn.recall)} />
                <MetricCell
                  value={formatPct(ensemble.recall)}
                  highlight
                />
              </tr>

              <tr className="border-b border-border">
                <td className="px-4 py-2 font-medium">
                  F1
                </td>

                <MetricCell value={formatPct(baseline.f1)} />
                <MetricCell value={formatPct(modelA.f1)} />
                <MetricCell value={formatPct(modelB.f1)} />
                <MetricCell value={formatPct(gnn.f1)} />
                <MetricCell
                  value={formatPct(ensemble.f1)}
                  highlight
                />
              </tr>

              <tr className="border-b border-border">
                <td className="px-4 py-2 font-medium">
                  PR-AUC
                </td>

                <MetricCell value="—" />
                <MetricCell value={formatPct(modelA.pr_auc)} />
                <MetricCell value={formatPct(modelB.pr_auc)} />
                <MetricCell value={formatPct(gnn.pr_auc)} />
                <MetricCell
                  value={formatPct(ensemble.pr_auc)}
                  highlight
                />
              </tr>

              <tr className="border-b border-border">
                <td className="px-4 py-2 font-medium">
                  ROC-AUC
                </td>

                <MetricCell value="—" />
                <MetricCell value={formatPct(modelA.roc_auc)} />
                <MetricCell value={formatPct(modelB.roc_auc)} />
                <MetricCell value={formatPct(gnn.roc_auc)} />
                <MetricCell
                  value={formatPct(ensemble.roc_auc)}
                  highlight
                />
              </tr>

              <tr>
                <td className="px-4 py-2 font-medium">
                  Estimated cost
                </td>

                <MetricCell
                  value={formatCost(baseline.cost)}
                />

                <MetricCell
                  value={formatCost(modelA.cost)}
                />

                <MetricCell
                  value={formatCost(modelB.cost)}
                />

                <MetricCell
                  value={formatCost(gnn.cost)}
                />

                <MetricCell
                  value={formatCost(ensemble.cost)}
                  highlight
                />
              </tr>

            </tbody>

          </table>
        </div>
      </Card>

      {/* =====================================================
          MODEL SUMMARY CARDS
      ===================================================== */}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">

        <Card className="p-4">
          <h3 className="text-sm font-medium mb-2">
            LightGBM A (Tuned)
          </h3>

          <p className="text-sm text-muted-foreground">
            F1: {formatPct(modelA.f1)}
          </p>

          <p className="text-sm text-muted-foreground">
            PR-AUC: {formatPct(modelA.pr_auc)}
          </p>
        </Card>

        <Card className="p-4">
          <h3 className="text-sm font-medium mb-2">
            LightGBM B (Tuned)
          </h3>

          <p className="text-sm text-muted-foreground">
            F1: {formatPct(modelB.f1)}
          </p>

          <p className="text-sm text-muted-foreground">
            PR-AUC: {formatPct(modelB.pr_auc)}
          </p>
        </Card>

        <Card className="p-4">
          <h3 className="text-sm font-medium mb-2">
            GNN
          </h3>

          <p className="text-sm text-muted-foreground">
            F1: {formatPct(gnn.f1)}
          </p>

          <p className="text-sm text-muted-foreground">
            PR-AUC: {formatPct(gnn.pr_auc)}
          </p>
        </Card>

        <Card className="p-4 border-black">
          <h3 className="text-sm font-medium mb-2">
            V4 Ensemble
          </h3>

          <p className="text-sm font-semibold">
            F1: {formatPct(ensemble.f1)}
          </p>

          <p className="text-sm text-muted-foreground">
            PR-AUC: {formatPct(ensemble.pr_auc)}
          </p>
        </Card>

      </div>

      {/* =====================================================
          COST
      ===================================================== */}

      <Card className="p-4">

        <h3 className="text-sm font-medium mb-4">
          Estimated Intervention Cost
        </h3>

        <div className="space-y-4">

          {comparisonModels
            .filter((model) => Number(model.data.cost || 0) > 0)
            .map((model) => {

              const cost = Number(model.data.cost || 0);

              return (
                <div key={model.key}>

                  <div className="flex justify-between text-sm mb-1">
                    <span>
                      {model.name}
                    </span>

                    <span>
                      {formatCost(cost)}
                    </span>
                  </div>

                  <div className="w-full bg-muted rounded h-2">
                    <div
                      className="bg-black h-2 rounded"
                      style={{
                        width: `${(cost / maxCost) * 100}%`,
                      }}
                    />
                  </div>

                </div>
              );
            })}

        </div>

      </Card>

      {/* =====================================================
          PRECISION / RECALL SCATTER
      ===================================================== */}

      <Card className="p-4">

        <h3 className="text-sm font-medium mb-3">
          Precision / Recall Tradeoff
        </h3>

        <ScatterPlot
          points={comparisonModels
            .filter(
              (model) =>
                model.data.precision !== null &&
                model.data.precision !== undefined &&
                model.data.recall !== null &&
                model.data.recall !== undefined
            )
            .map((model) => ({
              name: model.name,
              precision: Number(model.data.precision),
              recall: Number(model.data.recall),
            }))}
        />

      </Card>

      {/* =====================================================
          BEST MODEL
      ===================================================== */}

      {bestModel && (
        <Card className="p-4">

          <h3 className="text-sm font-medium mb-2">
            Current Evaluation Summary
          </h3>

          <p className="text-sm">
            Best F1 among evaluated models:{" "}
            <strong>
              {bestModel.name}
            </strong>
          </p>

          <p className="text-sm text-muted-foreground mt-1">
            F1: {formatPct(bestModel.data.f1)}
            {" · "}
            Precision: {formatPct(bestModel.data.precision)}
            {" · "}
            Recall: {formatPct(bestModel.data.recall)}
          </p>

          <p className="text-xs text-muted-foreground mt-2">
            The operating model is determined independently by
            the configured RingWatch production pipeline.
          </p>

        </Card>
      )}

      {costReduction !== null && (
        <Card className="p-4 border-black">
          <h3 className="text-sm font-medium mb-2">Merchant Loss View</h3>
          <p className="text-sm">
            The V4 Ensemble reduces modeled intervention cost by <strong>{costReduction.toFixed(1)}%</strong> versus the persisted rule baseline on the held-out test set.
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Baseline: {formatCost(baselineCost)} · V4 Ensemble: {formatCost(ensembleCost)} · FP cost ₹2,000 · FN cost ₹15,000.
          </p>
        </Card>
      )}

      {/* =====================================================
          CURRENT CONFIGURATION
      ===================================================== */}

      <Card className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">

        <div>

          <h3 className="text-sm font-medium mb-1">
            Current Operating Configuration
          </h3>

          <p className="text-sm text-muted-foreground">
            {operatingModel.name || "V4 Ensemble"}
            {" → "}
            threshold{" "}
            {formatThreshold(operatingThreshold)}
            {" → "}
            Investigation Queue
          </p>

        </div>

        <Link
          to="/dashboard"
          className="inline-block bg-black text-white px-4 py-2 rounded-md text-sm"
        >
          View Investigation Queue →
        </Link>

      </Card>

      {/* =====================================================
          FEATURE ABLATION
      ===================================================== */}
      {featureAblation?.features?.length > 0 && (
        <Card className="p-4">
          <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-3 mb-4">
            <div>
              <h3 className="text-sm font-medium">Held-out Feature Ablation</h3>
              <p className="text-xs text-muted-foreground mt-1">
                LightGBM A sensitivity on the same held-out test accounts. One feature is replaced with the population median and the model is rescored; this is not a causal claim.
              </p>
            </div>
            <span className="text-xs text-muted-foreground">
              {featureAblation.test_accounts?.toLocaleString("en-IN")} test accounts
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="px-3 py-2">Feature</th>
                  <th className="px-3 py-2">Mean |SHAP|</th>
                  <th className="px-3 py-2">Δ F1</th>
                  <th className="px-3 py-2">Δ Cost</th>
                  <th className="px-3 py-2">Ablated recall</th>
                </tr>
              </thead>
              <tbody>
                {featureAblation.features.slice(0, 8).map((item) => {
                  const deltaF1 = Number(item.f1) - Number(featureAblation.baseline?.f1 || 0);
                  const deltaCost = Number(item.cost) - Number(featureAblation.baseline?.cost || 0);
                  return (
                    <tr key={item.feature} className="border-b border-border last:border-0">
                      <td className="px-3 py-2 font-medium">{item.feature}</td>
                      <td className="px-3 py-2">{Number(item.mean_abs_shap).toFixed(3)}</td>
                      <td className={`px-3 py-2 ${deltaF1 < 0 ? "text-destructive" : ""}`}>{deltaF1 >= 0 ? "+" : ""}{(deltaF1 * 100).toFixed(1)} pp</td>
                      <td className={`px-3 py-2 ${deltaCost > 0 ? "text-destructive" : ""}`}>{deltaCost >= 0 ? "+" : "−"}{formatCost(Math.abs(deltaCost))}</td>
                      <td className="px-3 py-2">{formatPct(item.recall)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* =====================================================
          CURVES
      ===================================================== */}

      {hasCurves && (
        <div className="space-y-6">

          {/* Precision / Recall Curves */}
          <Card className="p-4">

            <h3 className="text-sm font-medium mb-3">
              Precision / Recall vs Top-K
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

              {curveModels.map((model) => (
                <div key={`${model.key}-precision`}>

                  <LineChart
                    title={`${model.label} Precision`}
                    data={curves?.[model.key]?.precision || []}
                    yLabel="Precision"
                  />

                </div>
              ))}

            </div>

          </Card>


          {/* Recall Curves */}
          <Card className="p-4">

            <h3 className="text-sm font-medium mb-3">
              Recall vs Top-K
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

              {curveModels.map((model) => (
                <div key={`${model.key}-recall`}>

                  <LineChart
                    title={`${model.label} Recall`}
                    data={curves?.[model.key]?.recall || []}
                    yLabel="Recall"
                  />

                </div>
              ))}

            </div>

          </Card>


          {/* Cost Curves */}
          <Card className="p-4">

            <h3 className="text-sm font-medium mb-3">
              Intervention Cost vs Top-K
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

              {curveModels.map((model) => (
                <div key={`${model.key}-cost`}>

                  <LineChart
                    title={`${model.label} Cost`}
                    data={curves?.[model.key]?.cost || []}
                    yLabel="Cost"
                  />

                </div>
              ))}

            </div>

          </Card>

        </div>
      )}

    </div>
  );
}

function ScatterPlot({ points }) {
  const width = 700;
  const height = 400;

  const margin = {
    top: 40,
    right: 40,
    bottom: 60,
    left: 60,
  };

  const innerWidth =
    width - margin.left - margin.right;

  const innerHeight =
    height - margin.top - margin.bottom;

  const x = (recall) =>
    margin.left + recall * innerWidth;

  const y = (precision) =>
    margin.top +
    innerHeight -
    precision * innerHeight;

  const modelColors = {
    Baseline: "#6B7280",
    "LightGBM A": "#2563EB",
    "LightGBM B": "#16A34A",
    GNN: "#9333EA",
    "V4 Ensemble": "#DC2626",
  };

  return (
    <div className="w-full">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
      >
        {/* X axis */}
        <line
          x1={margin.left}
          y1={margin.top + innerHeight}
          x2={width - margin.right}
          y2={margin.top + innerHeight}
          stroke="black"
          strokeWidth="1"
        />

        {/* Y axis */}
        <line
          x1={margin.left}
          y1={margin.top}
          x2={margin.left}
          y2={margin.top + innerHeight}
          stroke="black"
          strokeWidth="1"
        />

        {/* Data points */}
        {points.map((point, index) => {
          const cx = x(
            Math.max(
              0,
              Math.min(1, point.recall)
            )
          );

          const cy = y(
            Math.max(
              0,
              Math.min(1, point.precision)
            )
          );

          const color =
            modelColors[point.name] || "#000000";

          return (
            <g
              key={`${point.name}-${index}`}
            >
              {/* Point */}
              <circle
                cx={cx}
                cy={cy}
                r={5}
                fill={color}
                stroke="black"
                strokeWidth="0.8"
              />

              {/* Label */}
              <text
                x={cx}
                y={
                  cy -
                  12 -
                  (index % 3) * 13
                }
                textAnchor="middle"
                fontSize="9"
                fontWeight={
                  point.name === "V4 Ensemble"
                    ? "600"
                    : "400"
                }
                fill={color}
              >
                {point.name}
              </text>
            </g>
          );
        })}

        {/* X-axis label */}
        <text
          x={width / 2}
          y={height - 12}
          textAnchor="middle"
          fontSize="13"
          fill="black"
        >
          Recall
        </text>

        {/* Y-axis label */}
        <text
          x={18}
          y={height / 2}
          textAnchor="middle"
          fontSize="13"
          fill="black"
          transform={`rotate(-90, 18, ${height / 2})`}
        >
          Precision
        </text>
      </svg>
    </div>
  );
}