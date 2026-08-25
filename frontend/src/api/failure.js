import { apiFetch } from "./client";

export function simulateFailure() {
  return apiFetch("/api/failure-demo", { method: "POST" });
}