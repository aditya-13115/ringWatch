import { apiFetch } from "./client";

export function normalizeAddress(rawAddress) {
  return apiFetch("/api/address/normalize", {
    method: "POST",
    body: JSON.stringify({ raw_address: rawAddress }),
  });
}