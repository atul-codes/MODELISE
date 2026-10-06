export const usd = (n) => {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return '-'
  const v = Number(n)
  if (v === 0) return '$0.00'
  if (Math.abs(v) < 0.01) return `$${v.toFixed(6)}`
  return `$${v.toFixed(2)}`
}

export const num = (n) =>
  n === null || n === undefined || Number.isNaN(Number(n)) ? '-' : Number(n).toLocaleString()

export const fixed = (n, d = 3) =>
  n === null || n === undefined || Number.isNaN(Number(n)) ? '-' : Number(n).toFixed(d)

export const ms = (n) => {
  if (n === null || n === undefined) return '-'
  const v = Number(n)
  return v >= 1000 ? `${(v / 1000).toFixed(2)} s` : `${Math.round(v)} ms`
}

export const when = (iso) => {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export const clock = (t) =>
  new Date(t).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })

export const clip = (s, n = 90) => (s && s.length > n ? `${s.slice(0, n).trimEnd()}...` : s)

// "india-dpdp" from "India DPDP" - the pack id the geo engine expects.
export const slug = (s) =>
  s
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')

export const titleize = (key) =>
  key
    .replace(/_/g, ' ')
    .replace(/^\w/, (c) => c.toUpperCase())
