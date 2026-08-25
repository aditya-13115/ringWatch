import { apiFetch } from "./client";

export function getQueue(limit = 7) {
  return apiFetch(`/api/queue?limit=${limit}`);
}