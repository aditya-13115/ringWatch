export default function LineChart({
  data,
  width = 600,
  height = 300,
  xLabel = "K",
  yLabel = "Value",
  title = "",
}) {
  if (!data || data.length === 0) {
    return <div className="text-sm text-muted-foreground">No data.</div>;
  }

  const margin = { top: 20, right: 20, bottom: 40, left: 50 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const xs = data.map((d) => d.k);
  const ys = data.map((d) => d.value);

  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const xScale = (x) =>
    margin.left + ((x - minX) / (maxX - minX)) * innerWidth;
  const yScale = (y) =>
    margin.top + innerHeight - ((y - minY) / (maxY - minY || 1)) * innerHeight;

  const points = data
    .map((d) => `${xScale(d.k)},${yScale(d.value)}`)
    .join(" ");

  return (
    <div className="space-y-2">
      {title && <h4 className="text-sm font-medium">{title}</h4>}
      <svg width="100%" viewBox={`0 0 ${width} ${height}`} className="text-foreground">
        <line
          x1={margin.left}
          y1={margin.top + innerHeight}
          x2={width - margin.right}
          y2={margin.top + innerHeight}
          stroke="currentColor"
          strokeOpacity="0.25"
          strokeWidth="1"
        />
        <line
          x1={margin.left}
          y1={margin.top}
          x2={margin.left}
          y2={margin.top + innerHeight}
          stroke="currentColor"
          strokeOpacity="0.25"
          strokeWidth="1"
        />

        <polyline
          points={points}
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        />

        <text
          x={width / 2}
          y={height - 5}
          textAnchor="middle"
          fontSize="12"
          fill="currentColor"
        >
          {xLabel}
        </text>
        <text
          x={15}
          y={height / 2}
          textAnchor="middle"
          fontSize="12"
          fill="currentColor"
          transform={`rotate(-90, 15, ${height / 2})`}
        >
          {yLabel}
        </text>
      </svg>
    </div>
  );
}