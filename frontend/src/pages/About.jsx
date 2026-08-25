export default function About() {
  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <h1 className="text-3xl font-bold">About RingWatch</h1>
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
        <h2 className="text-xl font-semibold">Architecture</h2>
        <ol className="list-decimal list-inside space-y-2 text-muted-foreground">
          <li>Synthetic dataset with hidden abuse rings</li>
          <li>Cutoff-safe feature engineering</li>
          <li>Graph construction & Louvain communities</li>
          <li>LightGBM model for ranking</li>
          <li>SHAP explanations & evidence gap analysis</li>
          <li>AI investigator with tool calling</li>
          <li>Deterministic bounded actions</li>
        </ol>
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