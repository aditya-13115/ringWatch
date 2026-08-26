export default function ActionWorkflow({ tier, accountId }) {
  const getActions = (tier) => {
    switch (tier) {
      case "CRITICAL":
        return [
          {
            label: "Place Soft Hold",
            description: "Temporarily hold refunds pending human review.",
            variant: "primary",
          },
          {
            label: "Open Human Review",
            description: "Assign to investigation queue for manual review.",
            variant: "outline",
          },
        ];
      case "HIGH":
        return [
          {
            label: "Start Review",
            description: "Begin human review of this case.",
            variant: "primary",
          },
        ];
      case "MEDIUM":
        return [
          {
            label: "Start Step-Up Verification",
            description: "Require additional verification for refunds.",
            variant: "outline",
          },
        ];
      case "LOW":
        return [
          {
            label: "Continue Refund",
            description: "No immediate action required.",
            variant: "outline",
          },
        ];
      default:
        return [];
    }
  };

  const actions = getActions(tier);

  return (
    <Card className="p-6">
      <h3 className="text-sm font-medium text-muted-foreground mb-3">
        Recommended Actions
      </h3>
      <p className="text-lg font-medium mb-4">
        {tier === "CRITICAL" && "Soft-hold refund pending human approval"}
        {tier === "HIGH" && "Route to human review"}
        {tier === "MEDIUM" && "Step-up verification on refund"}
        {tier === "LOW" && "Monitor — no immediate refund action"}
      </p>
      <div className="flex flex-wrap gap-3">
        {actions.map((action, idx) => (
          <button
            key={idx}
            className={`rounded-md px-4 py-2 text-sm font-medium ${
              action.variant === "primary"
                ? "bg-black text-white hover:bg-gray-800"
                : "border border-border hover:bg-accent"
            }`}
          >
            {action.label}
          </button>
        ))}
      </div>
      <p className="text-xs text-muted-foreground mt-3">
        These actions are recommendations and require human approval before execution.
      </p>
    </Card>
  );
}