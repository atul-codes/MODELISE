import { useEffect, useState } from 'react'
import { Gauge, Globe2, Plug, ScanSearch, ShieldCheck } from 'lucide-react'
import { ToastProvider, useToast, cx } from './components/ui'
import { ConnectionProvider, useEngine } from './lib/connections'
import TestPrompts from './pages/TestPrompts'
import GuardrailRules from './pages/GuardrailRules'
import CountryPacks from './pages/CountryPacks'
import SpendLimits from './pages/SpendLimits'
import Connections from './pages/Connections'

const ROUTES = [
  { path: '/test', label: 'Test prompts', icon: ScanSearch, page: TestPrompts },
  { path: '/guardrail', label: 'Guardrail rules', icon: ShieldCheck, page: GuardrailRules },
  { path: '/geo', label: 'Country packs', icon: Globe2, page: CountryPacks },
  { path: '/spend', label: 'Spend and limits', icon: Gauge, page: SpendLimits },
  { path: '/connections', label: 'Connections', icon: Plug, page: Connections },
]

function useHashRoute() {
  const read = () => window.location.hash.replace(/^#/, '') || '/test'
  const [route, setRoute] = useState(read)
  useEffect(() => {
    const onChange = () => {
      setRoute(read())
      window.scrollTo({ top: 0 })
    }
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return route
}

function Mark() {
  return (
    <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="#22392f" />
      <path d="M8 22V10l8 8 8-8v12" fill="none" stroke="#7fd3b2" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function ServiceStatus({ engine }) {
  const e = useEngine(engine)
  const s = e.health.state
  return (
    <a className="svc" href="#/connections">
      <span className={cx('svc-dot', `svc-${s}`)} aria-hidden="true" />
      <span className="svc-text">
        <span>{e.short}</span>
        <small>
          {s === 'online' ? 'Online' : s === 'offline' ? 'Not reachable' : 'Checking'}
          {e.signedIn ? ', signed in' : ''}
        </small>
      </span>
    </a>
  )
}

function Shell() {
  const route = useHashRoute()
  const current = ROUTES.find((r) => r.path === route) || ROUTES[0]
  const Page = current.page
  return (
    <div className="shell">
      <a className="skip" href="#main">
        Skip to content
      </a>
      <aside className="side">
        <div className="brand">
          <Mark />
          <div>
            <strong>MODELISE</strong>
            <span>Console</span>
          </div>
        </div>
        <nav className="nav" aria-label="Main">
          {ROUTES.map((r) => (
            <a key={r.path} href={`#${r.path}`} className={cx('nav-item', r.path === current.path && 'on')} aria-current={r.path === current.path ? 'page' : undefined}>
              <r.icon size={18} aria-hidden="true" />
              {r.label}
            </a>
          ))}
        </nav>
        <div className="side-foot">
          <ServiceStatus engine="guardrail" />
          <ServiceStatus engine="geo" />
        </div>
      </aside>
      <main id="main" className="main">
        <Page key={current.path} />
      </main>
    </div>
  )
}

function Providers({ children }) {
  const notify = useToast()
  return <ConnectionProvider notify={notify}>{children}</ConnectionProvider>
}

export default function App() {
  return (
    <ToastProvider>
      <Providers>
        <Shell />
      </Providers>
    </ToastProvider>
  )
}
