// One small HTTP layer for both services. Nothing here knows about React.

export class ApiError extends Error {
  constructor(status, detail, body) {
    super(typeof detail === 'string' ? detail : `Request failed (${status})`)
    this.status = status
    this.detail = detail
    this.body = body
  }
}

const clean = (base) => (base || '').trim().replace(/\/+$/, '')

async function request(base, path, { method = 'GET', token, json, form, query, signal } = {}) {
  const url = new URL(clean(base) + path)
  if (query) {
    Object.entries(query).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v)
    })
  }
  const headers = {}
  if (token) headers.Authorization = `Bearer ${token}`
  let body
  if (json !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(json)
  } else if (form) {
    body = form
  }

  let res
  try {
    res = await fetch(url, { method, headers, body, signal })
  } catch (err) {
    if (err?.name === 'AbortError') throw err
    throw new ApiError(0, `Could not reach ${clean(base)}. Check that the service is running and the address is right.`)
  }

  let data = null
  const text = await res.text()
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }
  if (!res.ok) {
    const detail = data && typeof data === 'object' && 'detail' in data ? data.detail : data
    throw new ApiError(res.status, detail, data)
  }
  return data
}

// ---- Guardrail Layer 2 ---------------------------------------------------
export const guardrail = {
  health: (base) => request(base, '/health'),
  login: (base, username, password) =>
    request(base, '/api/v1/auth/login', { method: 'POST', json: { username, password } }),
  inspect: (base, body, signal) =>
    request(base, '/api/v1/guardrail/inspect', { method: 'POST', json: body, signal }),
  evaluate: (base, body, signal) =>
    request(base, '/api/v1/guardrail/evaluate', { method: 'POST', json: body, signal }),
  spend: (base, token) => request(base, '/api/v1/admin/spend-dashboard', { token }),
  uploadCsv: (base, token, file) => {
    const form = new FormData()
    form.append('file', file)
    return request(base, '/api/v1/admin/policy/upload-csv', { method: 'POST', token, form })
  },
  uploadPdf: (base, token, file) => {
    const form = new FormData()
    form.append('file', file)
    return request(base, '/api/v1/admin/policy/upload-pdf', { method: 'POST', token, form })
  },
  setThreshold: (base, token, threshold) =>
    request(base, '/api/v1/admin/settings/threshold', { method: 'PUT', token, json: { threshold } }),
  setBudget: (base, token, userId, budget_cap_usd) =>
    request(base, `/api/v1/admin/users/${encodeURIComponent(userId)}/budget`, {
      method: 'PUT',
      token,
      json: { budget_cap_usd },
    }),
}

// ---- Geo Policy Engine ---------------------------------------------------
export const geo = {
  health: (base) => request(base, '/health'),
  login: (base, username, password) =>
    request(base, '/api/v1/auth/login', { method: 'POST', json: { username, password } }),
  evaluate: (base, body, signal) =>
    request(base, '/api/v1/evaluate', { method: 'POST', json: body, signal }),
  packs: (base, token) => request(base, '/api/v1/packs', { token }),
  uploadCsv: (base, token, packId, { displayName, countryCode, file }) => {
    const form = new FormData()
    form.append('file', file)
    return request(base, `/api/v1/packs/${encodeURIComponent(packId)}/upload-csv`, {
      method: 'POST',
      token,
      form,
      query: { display_name: displayName, country_code: countryCode },
    })
  },
  uploadPdf: (base, token, packId, { displayName, countryCode, file }) => {
    const form = new FormData()
    form.append('file', file)
    return request(base, `/api/v1/packs/${encodeURIComponent(packId)}/upload-pdf`, {
      method: 'POST',
      token,
      form,
      query: { display_name: displayName, country_code: countryCode },
    })
  },
  toggle: (base, token, packId, enabled) =>
    request(base, `/api/v1/packs/${encodeURIComponent(packId)}/toggle`, {
      method: 'PUT',
      token,
      json: { enabled },
    }),
  remove: (base, token, packId) =>
    request(base, `/api/v1/packs/${encodeURIComponent(packId)}`, { method: 'DELETE', token }),
}

// Turn any thrown error into a sentence a person can act on.
export function explainError(err) {
  if (!(err instanceof ApiError)) return err?.message || 'Something went wrong.'
  if (err.status === 0) return err.message
  const d = err.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) {
    return d.map((x) => `${(x.loc || []).slice(1).join('.') || 'field'}: ${x.msg}`).join('; ')
  }
  if (d && typeof d === 'object' && d.reason) return String(d.reason).replace(/_/g, ' ')
  return err.message
}

// Admin endpoints answer 401 (or 403 on older FastAPI) when the token is missing or expired.
export const isAuthFailure = (err) =>
  err instanceof ApiError &&
  (err.status === 401 ||
    (err.status === 403 && typeof err.detail === 'string' && /not authenticated|credentials/i.test(err.detail)))
