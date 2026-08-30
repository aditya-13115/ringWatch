import { useState } from "react";
import {
  ingestRazorpayBatch,
  generateSyntheticFailureBatch,
} from "../api/failure";

function Stat({ label, value }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-gray-500">
        {label}
      </div>

      <div className="mt-1 text-2xl font-semibold text-gray-900">
        {value}
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  if (!status) return null;

  const normalized = String(status).toUpperCase();

  let className =
    "inline-flex rounded-full px-2.5 py-1 text-xs font-semibold";

  if (
    normalized.includes("FAIL") ||
    normalized.includes("QUARANT")
  ) {
    className += " bg-red-100 text-red-700";
  } else if (
    normalized.includes("SUCCESS") ||
    normalized.includes("PROCESSED")
  ) {
    className += " bg-green-100 text-green-700";
  } else {
    className += " bg-gray-100 text-gray-700";
  }

  return (
    <span className={className}>
      {status}
    </span>
  );
}

function RecordTable({ records, quarantined = false }) {
  if (!records || records.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-6 text-center text-sm text-gray-500">
        No records to display.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-semibold text-gray-600">
              Row
            </th>

            <th className="px-4 py-3 text-left font-semibold text-gray-600">
              Record ID
            </th>

            <th className="px-4 py-3 text-left font-semibold text-gray-600">
              Amount
            </th>

            <th className="px-4 py-3 text-left font-semibold text-gray-600">
              Currency
            </th>

            <th className="px-4 py-3 text-left font-semibold text-gray-600">
              Status
            </th>

            {quarantined && (
              <th className="px-4 py-3 text-left font-semibold text-gray-600">
                Failed Fields
              </th>
            )}

            {quarantined && (
              <th className="px-4 py-3 text-left font-semibold text-gray-600">
                Action
              </th>
            )}
          </tr>
        </thead>

        <tbody className="divide-y divide-gray-100 bg-white">
          {records.map((record, index) => {
            const errors = record.failed_fields || [];

            return (
              <tr key={record.record_id || record.id || index}>
                <td className="whitespace-nowrap px-4 py-3 text-gray-700">
                  {record.row_number ?? index + 1}
                </td>

                <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-gray-700">
                  {record.record_id || record.id || "—"}
                </td>

                <td className="whitespace-nowrap px-4 py-3 text-gray-700">
                  {typeof record.amount === "number"
                    ? `₹${(record.amount / 100).toLocaleString("en-IN")}`
                    : typeof record.original_input?.amount === "number"
                      ? `₹${(
                          record.original_input.amount / 100
                        ).toLocaleString("en-IN")}`
                      : "—"}
                </td>

                <td className="whitespace-nowrap px-4 py-3 text-gray-700">
                  {record.currency ||
                    record.original_input?.currency ||
                    "—"}
                </td>

                <td className="whitespace-nowrap px-4 py-3">
                  <StatusBadge
                    status={
                      quarantined
                        ? record.status
                        : record.status
                    }
                  />
                </td>

                {quarantined && (
                  <td className="px-4 py-3">
                    <div className="space-y-1">
                      {errors.length > 0 ? (
                        errors.map((error, errorIndex) => (
                          <div key={errorIndex}>
                            <div className="font-medium text-red-700">
                              {error.field}
                            </div>

                            <div className="text-xs text-gray-500">
                              {error.code}
                            </div>

                            <div className="text-xs text-gray-600">
                              {error.message}
                            </div>
                          </div>
                        ))
                      ) : (
                        <span className="text-gray-500">—</span>
                      )}
                    </div>
                  </td>
                )}

                {quarantined && (
                  <td className="whitespace-nowrap px-4 py-3">
                    <span className="rounded-full bg-orange-100 px-2.5 py-1 text-xs font-semibold text-orange-700">
                      {record.action || "HUMAN_REVIEW"}
                    </span>
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function AuditTrail({ entries }) {
  if (!entries || entries.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-5 text-sm text-gray-500">
        No audit events.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {entries.map((entry, index) => (
        <div
          key={`${entry.timestamp}-${index}`}
          className="rounded-lg border border-gray-200 bg-white p-4"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="font-medium text-gray-900">
              {entry.event}
            </div>

            <div className="text-xs text-gray-500">
              {entry.timestamp}
            </div>
          </div>

          <div className="mt-1 text-sm text-gray-600">
            {entry.details}
          </div>
        </div>
      ))}
    </div>
  );
}

function ResultPanel({ result, mode }) {
  if (!result) return null;

  const isRazorpay = mode === "razorpay";

  const razorpayPayments = result?.payments ?? [];

  const batchSize = result.batch_size ?? 0;
  const malformed = result.malformed_rows ?? 0;
  const quarantined = result.quarantined ?? 0;
  const processed = result.valid_processed ?? 0;
  const humanReview = result.human_review_routed ?? 0;

  return (
    <div className="mt-6 space-y-6">
      {/* Processing summary */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            Processing Summary
          </h3>

          <StatusBadge status={result.status} />
        </div>

        {isRazorpay ? (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat
              label="Batch Size"
              value={razorpayPayments.length}
            />

            <Stat
              label="Payments Fetched"
              value={razorpayPayments.length}
            />

            <Stat
              label="Malformed"
              value={0}
            />

            <Stat
              label="Quarantined"
              value={0}
            />
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            <Stat label="Batch Size" value={batchSize} />
            <Stat label="Malformed" value={malformed} />
            <Stat label="Quarantined" value={quarantined} />
            <Stat label="Valid Processed" value={processed} />
            <Stat label="Human Review" value={humanReview} />
          </div>
        )}
      </section>

      {/* Batch metadata */}
      <section className="rounded-lg border border-gray-200 bg-gray-50 p-4">
        <div className="grid gap-3 text-sm md:grid-cols-2">
          <div>
            <span className="font-medium text-gray-500">
              Source:
            </span>{" "}
            <span className="text-gray-900">
              {result.source || "—"}
            </span>
          </div>

          <div>
            <span className="font-medium text-gray-500">
              Environment:
            </span>{" "}
            <span className="text-gray-900">
              {result.environment || "—"}
            </span>
          </div>

          <div>
            <span className="font-medium text-gray-500">
              Batch ID:
            </span>{" "}
            <span className="font-mono text-xs text-gray-900">
              {result.batch_id || "—"}
            </span>
          </div>

          <div>
            <span className="font-medium text-gray-500">
              Request ID:
            </span>{" "}
            <span className="font-mono text-xs text-gray-900">
              {result.request_id || "—"}
            </span>
          </div>
        </div>
      </section>

      {/* Safety guarantee */}
      {result.safety && (
        <section className="rounded-lg border border-green-200 bg-green-50 p-5">
          <h3 className="font-semibold text-green-900">
            Safety Guarantee
          </h3>

          {isRazorpay ? (
            <div className="mt-3 space-y-2 text-sm text-green-800">
              <div>
                ✓ Sent to model inference:{" "}
                <strong>NO</strong>
              </div>

              <div>
                ✓ Original Razorpay data preserved:{" "}
                <strong>YES</strong>
              </div>

              <div>
                ✓ Fault injection:{" "}
                <strong>DISABLED</strong>
              </div>
            </div>
          ) : (
            <div className="mt-3 space-y-2 text-sm text-green-800">
              <div>
                ✓ Malformed entered investigation pipeline:{" "}
                <strong>
                  {result.safety.malformed_entered_investigation_pipeline
                    ? "YES"
                    : "NO"}
                </strong>
              </div>

              <div>
                ✓ Quarantined before model inference:{" "}
                <strong>
                  {result.safety.quarantined_before_model_inference
                    ? "YES"
                    : "NO"}
                </strong>
              </div>

              <div>
                ✓ Human review required:{" "}
                <strong>
                  {result.safety.human_review_required
                    ? "YES"
                    : "NO"}
                </strong>
              </div>
            </div>
          )}
        </section>
      )}

      {/* Razorpay actual records */}
      {isRazorpay && (
        <section>
          <h3 className="mb-3 text-lg font-semibold text-gray-900">
            Original Razorpay Test Mode Payments
          </h3>

          <RecordTable records={razorpayPayments} />
        </section>
      )}

      {/* Quarantined records */}
      {!isRazorpay && (
        <section>
          <h3 className="mb-3 text-lg font-semibold text-gray-900">
            Quarantined Records
          </h3>

          <RecordTable
            records={result.quarantined_records}
            quarantined
          />
        </section>
      )}

      {/* Audit trail */}
      <section>
        <h3 className="mb-3 text-lg font-semibold text-gray-900">
          Audit Trail
        </h3>

        <AuditTrail entries={result.audit_trail} />
      </section>

      {/* Fault injection */}
      {!isRazorpay && result.fault_injection && (
        <section className="rounded-lg border border-yellow-200 bg-yellow-50 p-5">
          <h3 className="font-semibold text-yellow-900">
            Fault Injection
          </h3>

          <div className="mt-2 text-sm text-yellow-800">
            <div>
              Enabled:{" "}
              <strong>
                {result.fault_injection.enabled ? "YES" : "NO"}
              </strong>
            </div>

            <div>
              Injected faults:{" "}
              <strong>
                {result.fault_injection.count}
              </strong>
            </div>

            <div className="mt-2">
              {result.fault_injection.description}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

export default function FailureDemo() {
  const [activeMode, setActiveMode] = useState("razorpay");

  const [razorpayResult, setRazorpayResult] = useState(null);
  const [syntheticResult, setSyntheticResult] = useState(null);

  const [loadingRazorpay, setLoadingRazorpay] = useState(false);
  const [loadingSynthetic, setLoadingSynthetic] = useState(false);

  const [error, setError] = useState(null);

  async function handleRazorpay() {
    setError(null);
    setLoadingRazorpay(true);

    try {
      const result = await ingestRazorpayBatch();

      setRazorpayResult(result);
      setActiveMode("razorpay");
    } catch (err) {
      setError(
        err?.message ||
          "Unable to fetch the Razorpay Test Mode batch."
      );
    } finally {
      setLoadingRazorpay(false);
    }
  }

  async function handleSynthetic() {
    setError(null);
    setLoadingSynthetic(true);

    try {
      const result = await generateSyntheticFailureBatch();

      setSyntheticResult(result);
      setActiveMode("synthetic");
    } catch (err) {
      setError(
        err?.message ||
          "Unable to generate the 100-record demo batch."
      );
    } finally {
      setLoadingSynthetic(false);
    }
  }

  const activeResult =
    activeMode === "razorpay"
      ? razorpayResult
      : syntheticResult;

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">
          Post-delivery abuse investigation
        </h1>

        <p className="mt-2 max-w-3xl text-sm text-gray-600">
          Fetch actual Razorpay Test Mode payments and display the original
          records exactly as returned by Razorpay. These records are not
          modified, fault-injected, quarantined, or sent to model inference.
        </p>
      </div>

      {/* Mode selector */}
      <div className="mt-8 border-b border-gray-200">
        <div className="flex gap-6">
          <button
            type="button"
            onClick={() => setActiveMode("razorpay")}
            className={`border-b-2 px-1 pb-3 text-sm font-medium ${
              activeMode === "razorpay"
                ? "border-gray-900 text-gray-900"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            Razorpay Test API
          </button>

          <button
            type="button"
            onClick={() => setActiveMode("synthetic")}
            className={`border-b-2 px-1 pb-3 text-sm font-medium ${
              activeMode === "synthetic"
                ? "border-gray-900 text-gray-900"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            Scripted Demo
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Razorpay section */}
      {activeMode === "razorpay" && (
        <section className="mt-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col justify-between gap-5 md:flex-row md:items-center">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Razorpay Test Mode
              </h2>

              <p className="mt-1 max-w-2xl text-sm text-gray-600">
                Fetch actual payments from the Razorpay Test API
                and display the original Test Mode records without
                modifying, fault-injecting, quarantining, or sending
                them to model inference.
              </p>

              <div className="mt-3 text-xs text-gray-500">
                Endpoint:{" "}
                <span className="font-mono">
                  POST /api/failure-demo/razorpay
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={handleRazorpay}
              disabled={loadingRazorpay}
              className="rounded-lg bg-gray-900 px-5 py-3 text-sm font-semibold text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loadingRazorpay
                ? "Fetching..."
                : "Fetch New Razorpay Batch"}
            </button>
          </div>

          {razorpayResult && (
            <ResultPanel
              result={razorpayResult}
              mode="razorpay"
            />
          )}
        </section>
      )}

      {/* Synthetic section */}
      {activeMode === "synthetic" && (
        <section className="mt-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col justify-between gap-5 md:flex-row md:items-center">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Scripted 100-Record Demo
              </h2>

              <p className="mt-1 max-w-2xl text-sm text-gray-600">
                Generate 100 Razorpay-shaped records locally.
                Ten records are deliberately corrupted after
                generation to demonstrate validation, quarantine,
                and human-review routing.
              </p>

              <div className="mt-3 flex flex-wrap gap-2 text-xs">
                <span className="rounded-full bg-gray-100 px-3 py-1 text-gray-700">
                  100 total
                </span>

                <span className="rounded-full bg-green-100 px-3 py-1 text-green-700">
                  90 valid
                </span>

                <span className="rounded-full bg-red-100 px-3 py-1 text-red-700">
                  10 malformed
                </span>

                <span className="rounded-full bg-orange-100 px-3 py-1 text-orange-700">
                  10 quarantined
                </span>
              </div>

              <div className="mt-3 text-xs text-gray-500">
                Endpoint:{" "}
                <span className="font-mono">
                  POST /api/failure-demo/razorpay-synthetic
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={handleSynthetic}
              disabled={loadingSynthetic}
              className="rounded-lg bg-gray-900 px-5 py-3 text-sm font-semibold text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loadingSynthetic
                ? "Generating..."
                : "Run 100-Record Demo"}
            </button>
          </div>

          {syntheticResult && (
            <ResultPanel
              result={syntheticResult}
              mode="synthetic"
            />
          )}
        </section>
      )}
    </div>
  );
}