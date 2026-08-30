import { apiFetch } from "./client";

export function getAccount(accountId) {
  return apiFetch(`/api/accounts/${accountId}`);
}

export function getAccountGraph(accountId) {
  return apiFetch(`/api/accounts/${accountId}/graph`);
}

export function investigateAccount(accountId) {
  return apiFetch(`/api/accounts/${accountId}/investigate`, {
    method: "POST",
  });
}

export function getAccountTimeline(accountId) {
  return apiFetch(`/api/accounts/${accountId}/timeline`);
}

export function getFeatureAblation(accountId) {
  return apiFetch(
    `/api/accounts/${accountId}/feature-ablation`
  );
}