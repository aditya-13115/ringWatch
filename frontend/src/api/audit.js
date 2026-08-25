import { apiFetch } from "./client";

export function getAudit() {
  return apiFetch("/api/audit");
}