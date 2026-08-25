import { apiFetch } from "./client";

export function getQueue() {
  return apiFetch("/api/queue");
}