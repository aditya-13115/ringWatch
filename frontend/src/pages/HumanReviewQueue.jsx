export default function HumanReviewQueue() {
  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-xl font-semibold">Human Review Queue</h2>
      <p className="text-muted-foreground">Cases awaiting manual review.</p>
      <div className="mt-6 space-y-3">
        {["A000529", "A000842", "A000841"].map((id) => (
          <div key={id} className="rounded-md border p-3 flex justify-between">
            <span>{id}</span>
            <button className="text-sm underline">Review</button>
          </div>
        ))}
      </div>
    </div>
  );
}