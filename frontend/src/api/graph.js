import { apiFetch } from "./client";

export function getGraphOverview() {
  return apiFetch("/api/graph/overview");
}