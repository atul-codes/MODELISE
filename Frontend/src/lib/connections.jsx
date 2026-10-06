import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { guardrail, geo, isAuthFailure, explainError } from './api'

const URL_KEY = 'modelise.console.urls'
const TOKEN_KEY = 'modelise.console.tokens'

const DEFAULT_URLS = {
  guardrail: import.meta.env.VITE_GUARDRAIL_URL || 'http://localhost:8001',
  geo: import.meta.env.VITE_GEO_URL || 'http://localhost:8000',
}

export const ENGINES = {
  guardrail: {
    id: 'guardrail',
    name: 'Guardrail Layer 2',
    short: 'Guardrail',
    api: guardrail,
    blurb: 'Cost guard, your own rulebook, and the local model.',
  },
  geo: {
    id: 'geo',
    name: 'Geo Policy Engine',
    short: 'Country packs',
    api: geo,
    blurb: 'One rulebook per country or regulation, checked together.',
  },
}

function readJson(storage, key, fallback) {
  try {
    const raw = storage.getItem(key)
    return raw ? { ...fallback, ...JSON.parse(raw) } : fallback
  } catch {
    return fallback
  }
}

const Ctx = createContext(null)

export function ConnectionProvider({ children, notify }) {
  const [urls, setUrls] = useState(() => readJson(localStorage, URL_KEY, DEFAULT_URLS))
  const [sessions, setSessions] = useState(() => {
    const saved = readJson(sessionStorage, TOKEN_KEY, {})
    const now = Date.now()
    const live = {}
    Object.entries(saved).forEach(([k, v]) => {
      if (v && v.token && v.expiresAt > now) live[k] = v
    })
    return live
  })
  const [health, setHealth] = useState({
    guardrail: { state: 'checking' },
    geo: { state: 'checking' },
  })

  useEffect(() => localStorage.setItem(URL_KEY, JSON.stringify(urls)), [urls])
  useEffect(() => sessionStorage.setItem(TOKEN_KEY, JSON.stringify(sessions)), [sessions])

  const urlsRef = useRef(urls)
  urlsRef.current = urls
  const sessionsRef = useRef(sessions)
  sessionsRef.current = sessions

  const checkHealth = useCallback(async (engine) => {
    setHealth((h) => ({ ...h, [engine]: { ...h[engine], state: 'checking' } }))
    try {
      const info = await ENGINES[engine].api.health(urlsRef.current[engine])
      setHealth((h) => ({ ...h, [engine]: { state: 'online', info } }))
    } catch (err) {
      setHealth((h) => ({ ...h, [engine]: { state: 'offline', error: explainError(err) } }))
    }
  }, [])

  // Check both on load, then every 30 seconds while the tab is open.
  useEffect(() => {
    checkHealth('guardrail')
    checkHealth('geo')
    const t = setInterval(() => {
      checkHealth('guardrail')
      checkHealth('geo')
    }, 30000)
    return () => clearInterval(t)
  }, [checkHealth])

  const setUrl = useCallback(
    (engine, value) => {
      setUrls((u) => ({ ...u, [engine]: value }))
      // The old token belongs to the old address.
      setSessions((s) => {
        const next = { ...s }
        delete next[engine]
        return next
      })
      setTimeout(() => checkHealth(engine), 0)
    },
    [checkHealth],
  )

  const signIn = useCallback(async (engine, username, password) => {
    const res = await ENGINES[engine].api.login(urlsRef.current[engine], username, password)
    setSessions((s) => ({
      ...s,
      [engine]: {
        token: res.access_token,
        username,
        expiresAt: Date.now() + (res.expires_in || 3600) * 1000,
      },
    }))
  }, [])

  const signOut = useCallback((engine) => {
    setSessions((s) => {
      const next = { ...s }
      delete next[engine]
      return next
    })
  }, [])

  // Run an admin call. If the token has expired, sign out and say so.
  const call = useCallback(
    async (engine, fn) => {
      const session = sessionsRef.current[engine]
      try {
        return await fn(urlsRef.current[engine], session?.token)
      } catch (err) {
        if (isAuthFailure(err)) {
          signOut(engine)
          notify?.({
            tone: 'warn',
            title: `Signed out of ${ENGINES[engine].name}`,
            body: 'Your login expired. Sign in again on the Connections page.',
          })
        }
        throw err
      }
    },
    [notify, signOut],
  )

  const value = useMemo(
    () => ({ urls, sessions, health, setUrl, signIn, signOut, checkHealth, call }),
    [urls, sessions, health, setUrl, signIn, signOut, checkHealth, call],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useConnections() {
  const v = useContext(Ctx)
  if (!v) throw new Error('useConnections must be used inside ConnectionProvider')
  return v
}

// Convenience view of one engine.
export function useEngine(engine) {
  const c = useConnections()
  const session = c.sessions[engine]
  return {
    ...ENGINES[engine],
    url: c.urls[engine],
    health: c.health[engine],
    signedIn: Boolean(session),
    username: session?.username,
    token: session?.token,
    signOut: () => c.signOut(engine),
    call: (fn) => c.call(engine, fn),
  }
}
