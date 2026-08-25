import { useEffect, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { getGraphOverview } from "../api/graph";

export default function Rings() {
  const [data, setData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getGraphOverview()
      .then((d) => {
        // Map backend edges to links for react-force-graph
        setData({
          nodes: d.nodes || [],
          links: d.edges || [],
        });
        setLoading(false);
      })
      .catch((e) => {
        console.error(e);
        setError(e.message);
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="p-6">Loading graph…</div>;
  if (error) return <div className="p-6 text-destructive">{error}</div>;
  if (!data.nodes.length) return <div className="p-6">No graph data.</div>;

  return (
    <div className="w-full h-[80vh] border border-border rounded-lg overflow-hidden">
      <ForceGraph2D
        graphData={data}
        nodeLabel="id"
        nodeRelSize={4}
        linkDirectionalArrowLength={3}
        linkDirectionalArrowRelPos={1}
        linkLabel={(edge) => edge.edge_type || ""}
        linkWidth={(edge) => edge.weight || 1}
        nodeCanvasObject={(node, ctx, globalScale) => {
          const label = node.id;
          const fontSize = 10 / globalScale;
          ctx.font = `${fontSize}px Sans-Serif`;
          ctx.fillStyle = node.is_focus ? "#000" : "#666";
          ctx.fillText(label, node.x, node.y + 6);
        }}
      />
    </div>
  );
}