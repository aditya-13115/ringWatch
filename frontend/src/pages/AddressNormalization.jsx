import { useMemo, useState } from "react";
import {
  extractAddress,
  verifyAddress,
} from "../api/address";
import Card from "../components/Card";

const FIELD_CONFIG = [
  {
    key: "house_no",
    label: "House / Flat No.",
    placeholder: "102",
  },
  {
    key: "building",
    label: "Building",
    placeholder: "Sai Residency",
  },
  {
    key: "street",
    label: "Street",
    placeholder: "MG Road",
  },
  {
    key: "area",
    label: "Area",
    placeholder: "Koramangala",
  },
  {
    key: "landmark",
    label: "Landmark",
    placeholder: "Near Metro",
  },
  {
    key: "city",
    label: "City",
    placeholder: "Bengaluru",
  },
  {
    key: "district",
    label: "District",
    placeholder: "Bengaluru Urban",
  },
  {
    key: "state",
    label: "State",
    placeholder: "Karnataka",
  },
  {
    key: "pincode",
    label: "Pincode",
    placeholder: "560034",
  },
  {
    key: "country",
    label: "Country",
    placeholder: "India",
  },
];

const EMPTY_COMPONENTS =
  FIELD_CONFIG.reduce(
    (result, field) => {
      result[field.key] = "";
      return result;
    },
    {}
  );

function percent(value) {
  const score = Number(value);

  if (!Number.isFinite(score)) {
    return "0%";
  }

  return `${Math.round(
    score * 100
  )}%`;
}

function scoreTone(score) {
  if (score >= 0.9) {
    return "text-foreground";
  }

  if (score >= 0.75) {
    return "text-muted-foreground";
  }

  return "text-destructive";
}

function getFieldScore(
  match,
  field
) {
  const value =
    match?.matched_fields?.[
      field
    ];

  if (
    value === undefined ||
    value === null
  ) {
    return null;
  }

  const score = Number(value);

  return Number.isFinite(score)
    ? score
    : null;
}

function humanizeStrategy(
  value
) {
  return String(
    value || "structured"
  )
    .replace(
      /^structured:/,
      ""
    )
    .replaceAll(
      "_",
      " "
    )
    .replaceAll(
      "+",
      " + "
    )
    .replace(
      /\b\w/g,
      (char) =>
        char.toUpperCase()
    );
}

export default function AddressNormalization() {
  const [
    rawAddress,
    setRawAddress,
  ] = useState("");

  const [
    components,
    setComponents,
  ] = useState({
    ...EMPTY_COMPONENTS,
  });

  const [
    result,
    setResult,
  ] = useState(null);

  const [
    extracting,
    setExtracting,
  ] = useState(false);

  const [
    verifying,
    setVerifying,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState(null);

  const [
    showRawHelper,
    setShowRawHelper,
  ] = useState(false);

  const filledFieldCount =
    useMemo(
      () =>
        FIELD_CONFIG.filter(
          ({ key }) =>
            String(
              components[key] ||
                ""
            ).trim()
        ).length,
      [components]
    );

  const updateComponent = (
    key,
    value
  ) => {
    setComponents(
      (current) => ({
        ...current,
        [key]: value,
      })
    );

    setResult(null);
    setError(null);
  };

  const handleExtract = async () => {
    const raw =
      rawAddress.trim();

    if (!raw) {
      setError(
        "Enter a raw address first."
      );
      return;
    }

    setExtracting(true);
    setError(null);
    setResult(null);

    try {
      const data =
        await extractAddress(
          raw
        );

      setComponents({
        ...EMPTY_COMPONENTS,
        ...(data.components ||
          {}),
      });
    } catch (e) {
      setError(
        e?.message ||
          "Could not extract address components."
      );
    } finally {
      setExtracting(
        false
      );
    }
  };

  const handleVerify =
    async () => {
      const cleaned =
        Object.fromEntries(
          Object.entries(
            components
          ).map(
            ([
              key,
              value,
            ]) => [
              key,
              String(
                value || ""
              ).trim(),
            ]
          )
        );

      const fieldCount =
        Object.values(
          cleaned
        ).filter(Boolean)
          .length;

      if (
        fieldCount ===
        0
      ) {
        setError(
          "Enter at least one address component before verifying."
        );
        return;
      }

      setVerifying(true);
      setError(null);
      setResult(null);

      try {
        const data =
          await verifyAddress(
            cleaned,
            rawAddress
          );

        setResult(data);
      } catch (e) {
        setError(
          e?.message ||
            "Could not verify the address."
        );
      } finally {
        setVerifying(
          false
        );
      }
    };

  const clearAll = () => {
    setRawAddress("");
    setComponents({
      ...EMPTY_COMPONENTS,
    });
    setResult(null);
    setError(null);
  };

  return (
    <div className="mx-auto w-full max-w-7xl space-y-5">
      {/* ============================================================
          PAGE HEADER
          ============================================================ */}
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
          Address intelligence
        </p>

        <h2 className="mt-1 text-2xl font-semibold tracking-tight">
          Address Normalization
        </h2>

        <p className="mt-1 max-w-4xl text-sm leading-6 text-muted-foreground">
          Enter or review the individual address components, then verify
          them against RingWatch&apos;s canonical address store.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-xs text-destructive">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        {/* ==========================================================
            LEFT COLUMN
            ========================================================== */}
        <div className="space-y-4">
          <Card className="p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
                  Step 1
                </p>

                <h3 className="mt-1 text-base font-semibold">
                  Address Details
                </h3>

                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  Enter whatever fields you know. They are verified
                  independently rather than treated as one sentence.
                </p>
              </div>

              <span className="rounded-full border border-border px-2 py-1 text-[9px] font-medium">
                {filledFieldCount}/10
              </span>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
              {FIELD_CONFIG.map(
                ({
                  key,
                  label,
                  placeholder,
                }) => (
                  <label
                    key={key}
                    className="block"
                  >
                    <span className="mb-1 block text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                      {label}
                    </span>

                    <input
                      type="text"
                      value={
                        components[
                          key
                        ] || ""
                      }
                      onChange={(
                        event
                      ) =>
                        updateComponent(
                          key,
                          event.target
                            .value
                        )
                      }
                      placeholder={
                        placeholder
                      }
                      className="w-full rounded-md border border-border bg-background px-3 py-2 text-xs outline-none transition focus:border-foreground/40 focus:ring-2 focus:ring-foreground/10"
                    />
                  </label>
                )
              )}
            </div>

            {/* Optional raw-address helper */}
            <div className="mt-4 rounded-lg border border-border bg-muted/20 p-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-[10px] font-medium">
                    Have a messy address string?
                  </p>

                  <p className="mt-1 text-[10px] leading-4 text-muted-foreground">
                    Paste it here only when you want the system to auto-fill
                    the structured fields.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() =>
                    setShowRawHelper(
                      (current) =>
                        !current
                    )
                  }
                  className="shrink-0 rounded-md border border-border px-2.5 py-1.5 text-[10px] font-medium hover:bg-accent"
                >
                  {showRawHelper
                    ? "Hide"
                    : "Auto-fill from raw address"}
                </button>
              </div>

              {showRawHelper && (
                <div className="mt-3">
                  <textarea
                    value={
                      rawAddress
                    }
                    onChange={(
                      event
                    ) => {
                      setRawAddress(
                        event.target
                          .value
                      );
                      setResult(
                        null
                      );
                      setError(
                        null
                      );
                    }}
                    className="min-h-24 w-full resize-y rounded-md border border-border bg-background px-3 py-2 text-xs outline-none focus:border-foreground/40 focus:ring-2 focus:ring-foreground/10"
                    placeholder="Flat 654, Kale St, Sector 50, Bangalore, Karnataka 560779"
                  />

                  <button
                    type="button"
                    onClick={
                      handleExtract
                    }
                    disabled={
                      extracting ||
                      verifying ||
                      !rawAddress.trim()
                    }
                    className="mt-2 rounded-md border border-border px-3 py-2 text-[10px] font-medium hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {extracting
                      ? "Extracting…"
                      : "Auto-fill components"}
                  </button>
                </div>
              )}
            </div>

            <div className="mt-4 flex gap-2">
              <button
                type="button"
                onClick={
                  handleVerify
                }
                disabled={
                  extracting ||
                  verifying ||
                  filledFieldCount ===
                    0
                }
                className="flex-1 rounded-md bg-black px-4 py-2.5 text-xs font-medium text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white dark:text-black dark:hover:bg-gray-200"
              >
                {verifying
                  ? "Verifying…"
                  : "Verify Address"}
              </button>

              <button
                type="button"
                onClick={
                  clearAll
                }
                disabled={
                  extracting ||
                  verifying
                }
                className="rounded-md border border-border px-4 py-2.5 text-xs font-medium hover:bg-accent disabled:opacity-50"
              >
                Clear
              </button>
            </div>
          </Card>

          <Card className="p-4">
            <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
              Matching approach
            </p>

            <div className="mt-3 grid grid-cols-3 gap-2">
              <InfoTile
                title="Retrieval"
                value="Pincode → City → Tokens"
              />

              <InfoTile
                title="Scoring"
                value="Weighted fields"
              />

              <InfoTile
                title="Output"
                value="Top 3 + confidence"
              />
            </div>
          </Card>
        </div>

        {/* ==========================================================
            RIGHT COLUMN
            ========================================================== */}
        <div className="space-y-4 xl:sticky xl:top-20">
          {!result ? (
            <Card className="min-h-[34rem] p-8">
              <div className="flex min-h-[30rem] items-center justify-center text-center">
                <div className="max-w-sm">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-border bg-muted/20 text-xs font-semibold">
                    02
                  </div>

                  <h3 className="mt-4 text-sm font-semibold">
                    Verification Result
                  </h3>

                  <p className="mt-2 text-xs leading-5 text-muted-foreground">
                    Verify the structured address to see the best canonical
                    match, alternatives, field-level scores, and whether
                    human review is needed.
                  </p>
                </div>
              </div>
            </Card>
          ) : (
            <>
              {/* ------------------------------------------------------
                  RESULT SUMMARY
                  ------------------------------------------------------ */}
              <Card className="p-5">
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div className="min-w-0">
                    <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                      Step 2 · Verification
                    </p>

                    <h3 className="mt-1 text-lg font-semibold">
                      {result.candidate_address_id
                        ? "Canonical candidate found"
                        : "No safe canonical match"}
                    </h3>

                    <p className="mt-1 text-xs text-muted-foreground">
                      {humanizeStrategy(
                        result.matching_strategy
                      )}
                    </p>
                  </div>

                  <div className="shrink-0 rounded-lg border border-border px-4 py-3 text-center">
                    <p className="text-[10px] text-muted-foreground">
                      Confidence
                    </p>

                    <p
                      className={`mt-1 text-2xl font-semibold ${scoreTone(
                        Number(
                          result.confidence ||
                            0
                        )
                      )}`}
                    >
                      {percent(
                        result.confidence
                      )}
                    </p>

                    <p className="mt-1 text-[9px] text-muted-foreground">
                      {result.requires_human_review
                        ? "Human review recommended"
                        : "Safe to accept"}
                    </p>
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
                  <Metric
                    label="Best score"
                    value={percent(
                      result
                        .matches?.[0]
                        ?.score
                    )}
                  />

                  <Metric
                    label="Candidates"
                    value={Number(
                      result.candidate_count ||
                        0
                    ).toLocaleString(
                      "en-IN"
                    )}
                  />

                  <Metric
                    label="Address ID"
                    value={
                      result.candidate_address_id ||
                      "—"
                    }
                  />

                  <Metric
                    label="Review"
                    value={
                      result.requires_human_review
                        ? "Required"
                        : "No"
                    }
                  />
                </div>
              </Card>

              {/* ------------------------------------------------------
                  BEST MATCH
                  ------------------------------------------------------ */}
              <Card className="p-5">
                <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  Best canonical match
                </p>

                <div className="mt-3 rounded-lg border border-border bg-muted/20 p-4">
                  <p className="break-words text-sm font-medium leading-6">
                    {result.normalized_address ||
                      "No canonical address selected"}
                  </p>

                  <p className="mt-2 font-mono text-[10px] text-muted-foreground">
                    {result.candidate_address_id ||
                      "No address ID"}
                  </p>
                </div>
              </Card>

              {/* ------------------------------------------------------
                  TOP THREE
                  ------------------------------------------------------ */}
              <Card className="p-5">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                      Candidate comparison
                    </p>

                    <h3 className="mt-1 text-sm font-semibold">
                      Top 3 matches
                    </h3>
                  </div>

                  <span className="text-[9px] text-muted-foreground">
                    Field-level scoring
                  </span>
                </div>

                <div className="mt-4 max-h-[31rem] space-y-3 overflow-y-auto pr-1">
                  {(result.matches ||
                    []).map(
                    (
                      match,
                      index
                    ) => (
                      <div
                        key={
                          match.address_id
                        }
                        className={`rounded-lg border p-4 ${
                          index === 0
                            ? "border-foreground/30 bg-muted/20"
                            : "border-border"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="text-[9px] uppercase tracking-wide text-muted-foreground">
                              Rank #
                              {index + 1}
                            </p>

                            <p className="mt-1 font-mono text-xs font-medium">
                              {
                                match.address_id
                              }
                            </p>

                            <p className="mt-2 break-words text-xs leading-5 text-muted-foreground">
                              {
                                match.canonical_address
                              }
                            </p>
                          </div>

                          <div className="shrink-0 text-right">
                            <p
                              className={`text-lg font-semibold ${scoreTone(
                                Number(
                                  match.score ||
                                    0
                                )
                              )}`}
                            >
                              {percent(
                                match.score
                              )}
                            </p>

                            <p className="text-[9px] text-muted-foreground">
                              overall
                            </p>
                          </div>
                        </div>

                        <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-3">
                          {FIELD_CONFIG.map(
                            ({
                              key,
                              label,
                            }) => {
                              const score =
                                getFieldScore(
                                  match,
                                  key
                                );

                              if (
                                score ===
                                null
                              ) {
                                return null;
                              }

                              return (
                                <div
                                  key={
                                    key
                                  }
                                  className="rounded-md border border-border bg-background p-2"
                                >
                                  <div className="flex items-center justify-between gap-2">
                                    <span className="truncate text-[9px] text-muted-foreground">
                                      {
                                        label
                                      }
                                    </span>

                                    <span className="text-[9px] font-medium">
                                      {Math.round(
                                        score *
                                          100
                                      )}
                                      %
                                    </span>
                                  </div>

                                  <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-muted">
                                    <div
                                      className="h-full rounded-full bg-foreground"
                                      style={{
                                        width: `${Math.max(
                                          0,
                                          Math.min(
                                            100,
                                            score *
                                              100
                                          )
                                        )}%`,
                                      }}
                                    />
                                  </div>
                                </div>
                              );
                            }
                          )}
                        </div>

                        {match
                          .exact_fields
                          ?.length >
                          0 && (
                          <p className="mt-3 text-[9px] leading-4 text-muted-foreground">
                            Exact:{" "}
                            {match.exact_fields.join(
                              ", "
                            )}
                          </p>
                        )}
                      </div>
                    )
                  )}
                </div>
              </Card>

              {/* ------------------------------------------------------
                  REVIEW GUIDANCE
                  ------------------------------------------------------ */}
              <Card className="p-5">
                <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  Review guidance
                </p>

                {result
                  .review_reasons
                  ?.length >
                0 ? (
                  <ul className="mt-3 max-h-48 space-y-2 overflow-y-auto pl-4 text-xs leading-5 text-muted-foreground list-disc">
                    {result.review_reasons.map(
                      (
                        reason,
                        index
                      ) => (
                        <li key={index}>
                          {reason}
                        </li>
                      )
                    )}
                  </ul>
                ) : (
                  <div className="mt-3 rounded-md border border-border bg-muted/20 p-3 text-xs">
                    No review exceptions detected.
                  </div>
                )}
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function InfoTile({
  title,
  value,
}) {
  return (
    <div className="rounded-md border border-border p-2.5">
      <p className="text-[9px] text-muted-foreground">
        {title}
      </p>

      <p className="mt-1 text-[10px] font-medium leading-4">
        {value}
      </p>
    </div>
  );
}

function Metric({
  label,
  value,
}) {
  return (
    <div className="min-w-0 rounded-lg border border-border bg-muted/10 p-3">
      <p className="truncate text-[9px] uppercase tracking-wide text-muted-foreground">
        {label}
      </p>

      <p className="mt-1 truncate text-sm font-semibold">
        {value}
      </p>
    </div>
  );
}