import { useParams } from "react-router-dom";

export default function VerificationWorkflow() {
  const { accountId } = useParams();
  return (
    <div className="max-w-lg mx-auto space-y-6">
      <h2 className="text-xl font-semibold">Step-Up Verification</h2>
      <p className="text-muted-foreground">Account {accountId}</p>
      <div className="space-y-3">
        {["Phone", "Email", "Government ID", "Address"].map((step) => (
          <div key={step} className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-black" />
            <span className="text-sm">{step}</span>
            <span className="ml-auto text-xs text-muted-foreground">Pending</span>
          </div>
        ))}
      </div>
      <button className="rounded-md bg-black px-4 py-2 text-sm text-white">
        Submit Verification
      </button>
    </div>
  );
}