import { apiFetch } from "./client";

export function getQueue(limit = 10) {
  return apiFetch(`/api/queue?limit=${limit}`);
}