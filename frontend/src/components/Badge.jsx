import { TIERS } from "../constants";

// Tier tints: red / orange / blue / slate, translucent and legible in both
// themes (sourced from constants so Live Ops and Dashboard stay in sync).
export default function Badge({ tier }) {
  const style = (TIERS[tier] || TIERS.LOW).badge;
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${style}`}>
      {tier}
    </span>
  );
}
