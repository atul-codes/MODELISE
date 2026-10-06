import { KeyRound } from 'lucide-react'
import { EmptyState, Notice } from './ui'
import { useEngine } from '../lib/connections'

// Wraps a page that needs an admin login for one engine.
export function RequireSignIn({ engine, children }) {
  const e = useEngine(engine)
  if (e.signedIn) return children
  return (
    <div className="page">
      <EmptyState
        title={`Sign in to ${e.name}`}
        action={
          <a className="btn btn-primary" href="#/connections">
            <KeyRound size={16} aria-hidden="true" />
            Go to Connections
          </a>
        }
      >
        This page changes settings, so the service asks for its admin username and password.
      </EmptyState>
      {e.health.state === 'offline' ? (
        <Notice tone="warn" title="The service is not answering">
          {e.health.error}
        </Notice>
      ) : null}
    </div>
  )
}
