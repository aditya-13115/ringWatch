const tierStyles = {
  CRITICAL: "bg-black text-white",
  HIGH: "bg-gray-800 text-white",
  MEDIUM: "bg-gray-200 text-black",
  LOW: "bg-white border border-gray-300 text-black",
};

export default function Badge({ tier }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${tierStyles[tier] || tierStyles.LOW}`}>
      {tier}
    </span>
  );
}