import { apiFetch } from "./client";

export function getMetrics() {
  return apiFetch("/api/metrics");
}

export function getCurves() {
  return apiFetch("/api/metrics/curves");
}
export function getFeatureAblation() {
  return apiFetch("/api/metrics/feature-ablation");
}
