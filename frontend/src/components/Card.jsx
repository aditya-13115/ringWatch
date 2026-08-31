import GlassPanel from "./GlassPanel";

// Card is now a thin wrapper over GlassPanel so every existing usage frosts
// over with no per-site edits. Hover stays off by default, so these cards
// remain static and readable; new pages use GlassPanel directly to opt in.
export default function Card(props) {
  return <GlassPanel {...props} />;
}
