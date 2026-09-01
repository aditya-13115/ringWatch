import { apiFetch } from "./client";

export function getRings(limit = 25, detectedOnly = false) {
  return apiFetch(
    `/api/rings?limit=${encodeURIComponent(limit)}&detected_only=${detectedOnly}`
  );
}

export function getRing(candidateId) {
  return apiFetch(`/api/rings/${encodeURIComponent(candidateId)}`);
}
