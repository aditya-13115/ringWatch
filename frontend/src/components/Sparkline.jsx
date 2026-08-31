// Dependency-free SVG sparkline matching the app's hand-rolled chart style.
// No axes or labels — just the trend line. Used by the Live Ops risk timeline.
export default function Sparkline({ data = [], color = "currentColor", width = 120, height = 32 }) {
  if (!data.length) {
    return <svg width={width} height={height} aria-hidden="true" />;
  }

  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = max - min || 1;
  const stepX = data.length > 1 ? width / (data.length - 1) : 0;
  const pad = 2;

  const points = data.map((v, i) => {
    const x = i * stepX;
    const y = height - pad - ((v - min) / range) * (height - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="overflow-visible">
      <polyline
        points={points.join(" ")}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx={(data.length - 1) * stepX} cy={points[points.length - 1].split(",")[1]} r={2} fill={color} />
    </svg>
  );
}
