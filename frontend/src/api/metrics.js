import { apiFetch } from "./client";

export function getMetrics() {
  return apiFetch("/api/metrics");
}