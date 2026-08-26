import { useParams } from "react-router-dom";

export default function HumanReviewQueue() {
  const { accountId } = useParams();

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Human Review</h2>
        <p className="text-sm text-muted-foreground">
          Account: {accountId}
        </p>
      </div>

      <div className="rounded-lg border border-border bg-card p-6">
        <h3 className="text-sm font-medium text-muted-foreground mb-4">
          Review Checklist
        </h3>

        <ul className="space-y-3 text-sm">
          <li className="flex items-center justify-between">
            <span>Review SHAP evidence</span>
            <span className="text-xs text-muted-foreground">Pending</span>
          </li>
          <li className="flex items-center justify-between">
            <span>Review graph relationships</span>
            <span className="text-xs text-muted-foreground">Pending</span>
          </li>
          <li className="flex items-center justify-between">
            <span>Review account timeline</span>
            <span className="text-xs text-muted-foreground">Pending</span>
          </li>
          <li className="flex items-center justify-between">
            <span>Approve or reject refund hold</span>
            <span className="text-xs text-muted-foreground">Pending</span>
          </li>
        </ul>
      </div>

      <div className="flex gap-3">
        <button className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white hover:bg-gray-800">
          Approve Refund
        </button>
        <button className="rounded-md border border-border px-4 py-2 text-sm font-medium hover:bg-accent">
          Keep Hold
        </button>
      </div>
    </div>
  );
}