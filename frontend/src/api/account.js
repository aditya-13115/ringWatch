import { apiFetch } from "./client";

export function getAccount(accountId) {
  return apiFetch(`/api/accounts/${accountId}`);
}

export function getAccountGraph(accountId) {
  return apiFetch(`/api/accounts/${accountId}/graph`);
}