import { apiFetch } from "./client";

/**
 * Fetch actual Test Mode payments from Razorpay
 * and run them through the RingWatch validation pipeline.
 */
export function ingestRazorpayBatch() {
  return apiFetch("/api/failure-demo/razorpay", {
    method: "POST",
  });
}

/**
 * Generate a 100-record Razorpay-shaped synthetic batch
 * with 10 deliberately malformed records.
 *
 * Expected:
 * 100 total
 * 90 valid
 * 10 malformed
 * 10 quarantined
 */
export function generateSyntheticFailureBatch() {
  return apiFetch("/api/failure-demo/razorpay-synthetic", {
    method: "POST",
  });
}