import Logo from "../components/Logo";

export default function About() {
  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div className="flex items-center gap-4">
        <Logo size="lg" showName={false} />

        <div>
          <h1 className="text-3xl font-bold">
            About RingWatch
          </h1>

          <p className="mt-1 text-sm text-muted-foreground">
            Fraud investigation and risk intelligence
          </p>
        </div>
      </div>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold">Problem</h2>
        <p className="text-muted-foreground">
          Refund/return abuse often involves multiple accounts acting together.
          Individual account risk scores miss coordinated behavior.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold">Solution</h2>
        <p className="text-muted-foreground">
          RingWatch detects abuse rings by building a graph of shared identities
          (device, address, phone, payment instrument) and analyzing behavioral
          patterns before disputes occur.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold">System Architecture</h2>

        <div className="rounded-lg border border-border p-4 bg-card">
          <ol className="list-decimal list-inside space-y-2 text-sm">
            <li>Synthetic dataset with hidden abuse rings</li>
            <li>Cutoff-safe feature engineering</li>
            <li>Graph construction & Louvain communities</li>
            <li>V4 Ensemble (Tuned LightGBM B + GNN) for risk ranking</li>
            <li>SHAP explanations & evidence gap analysis</li>
            <li>AI Investigator (Groq) with tool calling</li>
            <li>Deterministic Policy Engine for action decision</li>
            <li>Human review and audit trail</li>
          </ol>
        </div>

        <p className="text-sm text-muted-foreground">
          <strong>Important:</strong> The AI Investigator provides analysis and
          recommendations, but the final action is always determined by the
          deterministic policy engine, never the LLM.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold">Limitations</h2>
        <p className="text-muted-foreground">
          Prototype uses synthetic data. Graph model did not improve global PR-AUC,
          but improves operational precision. Not production-ready.
        </p>
      </section>
    </div>
  );
}