// Thin fetch wrapper around Backend-main's API. No axios/query-library
// dependency added - matches the rest of this codebase's preference for
// plain fetch and React state over extra libraries.

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8080";

async function request(path, { method = "GET", token, body, isFormData = false } = {}) {
  const headers = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!isFormData && body !== undefined) headers["Content-Type"] = "application/json";

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: isFormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
  });

  let data = null;
  try {
    data = await response.json();
  } catch {
    // no body / non-JSON response, leave data null
  }

  if (!response.ok) {
    const message =
      (data && (data.detail?.reason || data.detail || data.message)) ||
      `Request failed (${response.status})`;
    const error = new Error(typeof message === "string" ? message : JSON.stringify(message));
    error.status = response.status;
    error.body = data;
    throw error;
  }

  return data;
}

export const api = {
  login: (username, password) =>
    request("/api/v1/auth/login", { method: "POST", body: { username, password } }),

  // --- plug-and-play providers ---
  listProviders: (token) => request("/api/v1/providers", { token }),
  createProvider: (token, payload) => request("/api/v1/providers", { method: "POST", token, body: payload }),
  toggleProvider: (token, id, enabled) =>
    request(`/api/v1/providers/${id}/toggle`, { method: "PUT", token, body: { enabled } }),
  setProviderAttachments: (token, id, attached_pipelines) =>
    request(`/api/v1/providers/${id}/attachments`, { method: "PUT", token, body: { attached_pipelines } }),
  deleteProvider: (token, id) => request(`/api/v1/providers/${id}`, { method: "DELETE", token }),

  // --- custom model endpoints (Feature 1) ---
  listCustomModels: (token) => request("/api/v1/custom-models", { token }),
  createCustomModel: (token, payload) => request("/api/v1/custom-models", { method: "POST", token, body: payload }),
  toggleCustomModel: (token, id, enabled) =>
    request(`/api/v1/custom-models/${id}/toggle?enabled=${enabled}`, { method: "PUT", token }),
  deleteCustomModel: (token, id) => request(`/api/v1/custom-models/${id}`, { method: "DELETE", token }),

  // --- commercial AI credentials (Feature 2) ---
  listCredentials: (token) => request("/api/v1/credentials", { token }),
  createCredential: (token, payload) => request("/api/v1/credentials", { method: "POST", token, body: payload }),
  deleteCredential: (token, id) => request(`/api/v1/credentials/${id}`, { method: "DELETE", token }),

  // --- geo-compliance packs (Feature 3) ---
  listGeoPacks: (token) => request("/api/v1/geo-policies", { token }),
  uploadGeoPackCsv: (token, packId, displayName, countryCode, file) => {
    const form = new FormData();
    form.append("file", file);
    const params = new URLSearchParams({ display_name: displayName, ...(countryCode ? { country_code: countryCode } : {}) });
    return request(`/api/v1/geo-policies/${packId}/upload-csv?${params}`, { method: "POST", token, body: form, isFormData: true });
  },
  uploadGeoPackPdf: (token, packId, displayName, countryCode, file) => {
    const form = new FormData();
    form.append("file", file);
    const params = new URLSearchParams({ display_name: displayName, ...(countryCode ? { country_code: countryCode } : {}) });
    return request(`/api/v1/geo-policies/${packId}/upload-pdf?${params}`, { method: "POST", token, body: form, isFormData: true });
  },
  toggleGeoPack: (token, packId, enabled) =>
    request(`/api/v1/geo-policies/${packId}/toggle`, { method: "PUT", token, body: { enabled } }),

  // --- chat / execution ---
  chatCustomModel: (payload) => request("/api/v1/chat/custom", { method: "POST", body: payload }),
  chatCommercial: (payload) => request("/api/v1/chat/commercial", { method: "POST", body: payload }),
};
