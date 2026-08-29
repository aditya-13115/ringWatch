import { apiFetch } from "./client";

export function ingestRazorpayBatch() {
  return apiFetch("/api/failure-demo/razorpay", {
    method: "POST",
  });
}