import { useParams } from "react-router-dom";

export default function VerificationWorkflow() {
  const { accountId } = useParams();

  const steps = [
    "Phone verification",
    "Email verification",
    "Government ID verification",
    "Address verification",
  ];

  return (
    <div className="max-w-lg mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Step-Up Verification</h2>
        <p className="text-sm text-muted-foreground">
          Account: {accountId}
        </p>
      </div>

      <div className="rounded-lg border border-border bg-card p-6">
        <h3 className="text-sm font-medium text-muted-foreground mb-4">
          Verification Requirements
        </h3>

        <ul className="space-y-3">
          {steps.map((step) => (
            <li key={step} className="flex items-center justify-between text-sm">
              <span>{step}</span>
              <span className="text-xs text-muted-foreground">Pending</span>
            </li>
          ))}
        </ul>
      </div>

      <button className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white hover:bg-gray-800">
        Submit Verification
      </button>
    </div>
  );
}