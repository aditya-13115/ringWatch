import { apiFetch } from "./client";

export function extractAddress(rawAddress) {
  return apiFetch("/api/address/extract", {
    method: "POST",
    body: JSON.stringify({
      raw_address: rawAddress,
    }),
  });
}

export function verifyAddress(
  components,
  rawAddress = ""
) {
  return apiFetch("/api/address/verify", {
    method: "POST",
    body: JSON.stringify({
      raw_address:
        rawAddress.trim() || undefined,
      components,
    }),
  });
}

// Backward compatibility for any existing caller.
export function normalizeAddress(
  rawAddress,
  components
) {
  return apiFetch("/api/address/normalize", {
    method: "POST",
    body: JSON.stringify({
      raw_address: rawAddress,
      components:
        components || undefined,
    }),
  });
}