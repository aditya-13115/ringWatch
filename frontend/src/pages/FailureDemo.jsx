import { useState } from "react";
import { ingestRazorpayBatch } from "../api/failure";
import Card from "../components/Card";

function StatusBadge({ status }) {
  const styles = {
    QUARANTINED:
      "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
    PROCESSED:
      "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  };

  return (
    <span
      className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${
        styles[status] || "bg-muted text-muted-foreground"
      }`}
    >
      {status}
    </span>
  );
}

function formatAmount(amount, currency = "INR") {
  if (typeof amount !== "number") return "—";

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(amount / 100);
}

export default function FailureDemo() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedRecord, setSelectedRecord] = useState(null);

  const handleIngest = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setSelectedRecord(null);

    try {
      const data = await ingestRazorpayBatch();
      setResult(data);
    } catch (e) {
      setError(e.message || "Failed to ingest Razorpay batch.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-semibold">
            Payment Ingestion & Failure Handling
          </h2>

          <span className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
            Razorpay Test Mode
          </span>
        </div>

        <p className="mt-2 text-sm text-muted-foreground">
          Fetch a real Razorpay Test Mode payment batch, validate each
          transaction, and quarantine invalid records before they enter
          the RingWatch investigation pipeline.
        </p>
      </div>

      {/* Ingestion */}
      <Card className="p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-medium">
              Razorpay batch ingestion
            </p>

            <p className="mt-1 text-xs text-muted-foreground">
              RingWatch will fetch up to 100 payments from the Razorpay
              Test Mode API.
            </p>
          </div>

          <button
            onClick={handleIngest}
            disabled={loading}
            className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white dark:text-black dark:hover:bg-gray-200"
          >
            {loading ? "Fetching & validating…" : "Fetch New Razorpay Batch"}
          </button>
        </div>
      </Card>

      {/* Error */}
      {error && (
        <div className="mt-4 rounded-md border border-red-300 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
          <p className="font-medium">Batch ingestion failed</p>
          <p className="mt-1">{error}</p>
        </div>
      )}

      {result && (
        <div className="mt-6 space-y-6">
          {/* Batch metadata */}
          <Card className="p-6">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div>
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  Batch
                </p>

                <p className="mt-1 font-mono text-sm">
                  {result.batch_id}
                </p>

                <p className="mt-2 text-xs text-muted-foreground">
                  Request: {result.request_id}
                </p>
              </div>

              <div className="text-left md:text-right">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  Source
                </p>

                <p className="mt-1 font-medium">
                  {result.source === "razorpay"
                    ? "Razorpay"
                    : result.source}
                </p>

                <p className="text-xs text-muted-foreground">
                  {result.environment}
                </p>
              </div>
            </div>
          </Card>

          {/* Processing summary */}
          <Card className="p-6">
            <h3 className="mb-4 text-sm font-medium text-muted-foreground">
              Processing Summary
            </h3>

            <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
              <Metric
                label="Received"
                value={result.batch_size}
              />

              <Metric
                label="Malformed"
                value={result.malformed_rows}
                danger
              />

              <Metric
                label="Quarantined"
                value={result.quarantined}
              />

              <Metric
                label="Valid Processed"
                value={result.valid_processed}
                success
              />

              <Metric
                label="Human Review"
                value={result.human_review_routed}
              />
            </div>
          </Card>

          {/* Pipeline guarantee */}
          <div className="rounded-md border border-emerald-500 bg-emerald-50 p-5 dark:bg-emerald-900/20">
            <p className="font-medium text-emerald-700 dark:text-emerald-300">
              Safety Guarantee
            </p>

            <p className="mt-1 text-sm text-emerald-700 dark:text-emerald-300">
              Malformed records were quarantined before model inference.
              They did not enter the RingWatch investigation pipeline.
            </p>

            <div className="mt-4 grid grid-cols-1 gap-3 text-xs md:grid-cols-3">
              <SafetyItem
                label="Entered ML pipeline"
                value={
                  result.safety?.malformed_entered_investigation_pipeline
                    ? "YES"
                    : "NO"
                }
              />

              <SafetyItem
                label="Quarantined before inference"
                value={
                  result.safety?.quarantined_before_model_inference
                    ? "YES"
                    : "NO"
                }
              />

              <SafetyItem
                label="Human review required"
                value={
                  result.safety?.human_review_required
                    ? "YES"
                    : "NO"
                }
              />
            </div>
          </div>

          {/* Fault injection disclosure */}
          {result.fault_injection?.enabled && (
            <Card className="border-amber-300 p-5 dark:border-amber-700">
              <p className="font-medium text-amber-700 dark:text-amber-300">
                Demo Fault Injection
              </p>

              <p className="mt-1 text-sm text-muted-foreground">
                {result.fault_injection.description}
              </p>

              <p className="mt-2 text-xs text-muted-foreground">
                Fault-injected records:{" "}
                <strong>{result.fault_injection.count}</strong>
              </p>
            </Card>
          )}

          {/* Quarantine records */}
          <Card className="p-6">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium">
                  Quarantine Queue
                </h3>

                <p className="mt-1 text-xs text-muted-foreground">
                  Actual records received from Razorpay and rejected by
                  RingWatch validation.
                </p>
              </div>

              <span className="rounded-full bg-red-100 px-2 py-1 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-300">
                {result.quarantined_records?.length || 0} records
              </span>
            </div>

            {result.quarantined_records?.length ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="px-3 py-3 text-xs text-muted-foreground">
                        Row
                      </th>

                      <th className="px-3 py-3 text-xs text-muted-foreground">
                        Payment
                      </th>

                      <th className="px-3 py-3 text-xs text-muted-foreground">
                        Failed Field
                      </th>

                      <th className="px-3 py-3 text-xs text-muted-foreground">
                        Reason
                      </th>

                      <th className="px-3 py-3 text-xs text-muted-foreground">
                        Status
                      </th>

                      <th className="px-3 py-3 text-xs text-muted-foreground">
                        Action
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {result.quarantined_records.map((record) => {
                      const firstError =
                        record.failed_fields?.[0];

                      return (
                        <tr
                          key={`${record.batch_id}-${record.row_number}`}
                          className="border-b last:border-0"
                        >
                          <td className="px-3 py-3 font-mono text-xs">
                            #{record.row_number}
                          </td>

                          <td className="px-3 py-3 font-mono text-xs">
                            {record.record_id || "—"}
                          </td>

                          <td className="px-3 py-3">
                            {firstError?.field || "—"}
                          </td>

                          <td className="px-3 py-3 text-muted-foreground">
                            {firstError?.message ||
                              record.quarantine_reason}
                          </td>

                          <td className="px-3 py-3">
                            <StatusBadge status={record.status} />
                          </td>

                          <td className="px-3 py-3">
                            <button
                              onClick={() =>
                                setSelectedRecord(record)
                              }
                              className="text-xs font-medium underline underline-offset-2"
                            >
                              View details
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No records were quarantined.
              </p>
            )}
          </Card>

          {/* Processed records */}
          <Card className="p-6">
            <div className="mb-4">
              <h3 className="text-sm font-medium">
                Validated & Processed
              </h3>

              <p className="mt-1 text-xs text-muted-foreground">
                These records passed the data-quality gate.
              </p>
            </div>

            <div className="max-h-80 overflow-auto rounded-md border">
              <table className="w-full text-left text-sm">
                <thead className="sticky top-0 bg-background">
                  <tr className="border-b">
                    <th className="px-3 py-3 text-xs text-muted-foreground">
                      Row
                    </th>

                    <th className="px-3 py-3 text-xs text-muted-foreground">
                      Payment
                    </th>

                    <th className="px-3 py-3 text-xs text-muted-foreground">
                      Amount
                    </th>

                    <th className="px-3 py-3 text-xs text-muted-foreground">
                      Method
                    </th>

                    <th className="px-3 py-3 text-xs text-muted-foreground">
                      Status
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {result.processed_records?.map((record) => (
                    <tr
                      key={`${record.batch_id}-${record.row_number}`}
                      className="border-b last:border-0"
                    >
                      <td className="px-3 py-2 font-mono text-xs">
                        #{record.row_number}
                      </td>

                      <td className="px-3 py-2 font-mono text-xs">
                        {record.record_id || "—"}
                      </td>

                      <td className="px-3 py-2">
                        {formatAmount(
                          record.amount,
                          record.currency
                        )}
                      </td>

                      <td className="px-3 py-2">
                        {record.method || "—"}
                      </td>

                      <td className="px-3 py-2">
                        <StatusBadge status={record.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Audit trail */}
          <Card className="p-6">
            <h3 className="mb-4 text-sm font-medium">
              Audit Trail
            </h3>

            <div className="space-y-3">
              {result.audit_trail?.map((entry, index) => (
                <div
                  key={`${entry.timestamp}-${index}`}
                  className="flex flex-col gap-1 border-b pb-3 last:border-0"
                >
                  <div className="flex flex-col justify-between gap-1 md:flex-row">
                    <span className="text-sm font-medium">
                      {entry.event}
                    </span>

                    <span className="font-mono text-xs text-muted-foreground">
                      {entry.timestamp}
                    </span>
                  </div>

                  <span className="text-sm text-muted-foreground">
                    {entry.details}
                  </span>
                </div>
              ))}
            </div>
          </Card>

          {/* Details modal */}
          {selectedRecord && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
              <div className="max-h-[90vh] w-full max-w-3xl overflow-auto rounded-lg bg-background p-6 shadow-xl">
                <div className="mb-5 flex items-start justify-between">
                  <div>
                    <h3 className="text-lg font-semibold">
                      Quarantined Record
                    </h3>

                    <p className="mt-1 font-mono text-xs text-muted-foreground">
                      {selectedRecord.record_id}
                    </p>
                  </div>

                  <button
                    onClick={() => setSelectedRecord(null)}
                    className="rounded-md px-2 py-1 text-sm hover:bg-muted"
                  >
                    ✕
                  </button>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <Detail
                    label="Row"
                    value={`#${selectedRecord.row_number}`}
                  />

                  <Detail
                    label="Status"
                    value={selectedRecord.status}
                  />

                  <Detail
                    label="Action"
                    value={selectedRecord.action}
                  />

                  <Detail
                    label="Quarantine Reason"
                    value={selectedRecord.quarantine_reason}
                  />

                  <Detail
                    label="Batch"
                    value={selectedRecord.batch_id}
                  />

                  <Detail
                    label="Request"
                    value={selectedRecord.request_id}
                  />
                </div>

                <div className="mt-6">
                  <h4 className="mb-2 text-sm font-medium">
                    Validation Failures
                  </h4>

                  <pre className="overflow-auto rounded-md bg-muted p-4 text-xs">
                    {JSON.stringify(
                      selectedRecord.failed_fields,
                      null,
                      2
                    )}
                  </pre>
                </div>

                <div className="mt-6">
                  <h4 className="mb-2 text-sm font-medium">
                    Received Input
                  </h4>

                  <pre className="overflow-auto rounded-md bg-muted p-4 text-xs">
                    {JSON.stringify(
                      selectedRecord.original_input,
                      null,
                      2
                    )}
                  </pre>
                </div>

                <div className="mt-6 rounded-md border border-emerald-500 bg-emerald-50 p-4 dark:bg-emerald-900/20">
                  <p className="font-medium text-emerald-700 dark:text-emerald-300">
                    Pipeline Safety
                  </p>

                  <p className="mt-1 text-sm text-emerald-700 dark:text-emerald-300">
                    This record was quarantined before model inference
                    and was not sent to the investigation pipeline.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Metric({ label, value, danger, success }) {
  let valueClass = "text-2xl font-semibold";

  if (danger) {
    valueClass += " text-red-600 dark:text-red-400";
  }

  if (success) {
    valueClass += " text-emerald-600 dark:text-emerald-400";
  }

  return (
    <div className="text-center">
      <dt className="text-xs text-muted-foreground">
        {label}
      </dt>

      <dd className={valueClass}>
        {value}
      </dd>
    </div>
  );
}

function SafetyItem({ label, value }) {
  return (
    <div className="rounded-md border border-emerald-200 p-3 dark:border-emerald-800">
      <p className="text-muted-foreground">{label}</p>
      <p className="mt-1 font-semibold">{value}</p>
    </div>
  );
}

function Detail({ label, value }) {
  return (
    <div className="rounded-md border p-3">
      <p className="text-xs text-muted-foreground">
        {label}
      </p>

      <p className="mt-1 break-all text-sm font-medium">
        {value || "—"}
      </p>
    </div>
  );
}