import { useState } from 'react'
import { LogIn, LogOut, RefreshCw } from 'lucide-react'
import { Button, Card, Notice, Pill, TextInput, useToast } from '../components/ui'
import { explainError } from '../lib/api'
import { ENGINES, useConnections, useEngine } from '../lib/connections'

const START = {
  guardrail: 'cd guardrail_layer2\n.\\venv\\Scripts\\Activate.ps1\nuvicorn app.main:app --reload --port 8001',
  geo: 'cd geo_policy_engine\n.\\venv\\Scripts\\Activate.ps1\nuvicorn app.main:app --reload --port 8000',
}

export default function Connections() {
  return (
    <div className="page">
      <header className="page-head">
        <h1>Connections</h1>
        <p>
          This console talks straight to the two services. Each one has its own admin login, and signing in is only needed for the
          pages that change settings. Testing prompts works without it.
        </p>
      </header>
      <div className="two">
        <EngineCard engine="guardrail" />
        <EngineCard engine="geo" />
      </div>
    </div>
  )
}

function EngineCard({ engine }) {
  const e = useEngine(engine)
  const { setUrl, signIn, checkHealth } = useConnections()
  const toast = useToast()
  const [draft, setDraft] = useState(e.url)
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const state = e.health.state
  const tone = state === 'online' ? 'good' : state === 'offline' ? 'bad' : 'neutral'
  const changed = draft.trim().replace(/\/+$/, '') !== e.url

  async function submit(ev) {
    ev.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await signIn(engine, username.trim(), password)
      setPassword('')
      toast({ title: `Signed in to ${ENGINES[engine].name}` })
    } catch (err) {
      setError(explainError(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card
      title={ENGINES[engine].name}
      aside={
        <Pill tone={tone} dot>
          {state === 'online' ? 'Online' : state === 'offline' ? 'Not reachable' : 'Checking'}
        </Pill>
      }
    >
      <p className="muted">{ENGINES[engine].blurb}</p>

      <div className="inline-form">
        <TextInput label="Address" mono value={draft} onChange={(ev) => setDraft(ev.target.value)} spellCheck={false} />
        <Button
          disabled={!changed}
          onClick={() => {
            const v = draft.trim().replace(/\/+$/, '')
            setDraft(v)
            setUrl(engine, v)
          }}
        >
          Use address
        </Button>
        <Button variant="quiet" icon={RefreshCw} onClick={() => checkHealth(engine)} aria-label="Check again" />
      </div>

      {state === 'online' && e.health.info ? (
        <p className="muted small">
          {e.health.info.service} version {e.health.info.version}
        </p>
      ) : null}
      {state === 'offline' ? (
        <>
          <Notice tone="bad" title="Cannot reach this service">
            {e.health.error}
          </Notice>
          <details className="how">
            <summary>How to start it</summary>
            <pre>{START[engine]}</pre>
            <p className="muted small">Run this in its own terminal and leave it open. Then press the refresh button above.</p>
          </details>
        </>
      ) : null}

      <hr className="rule" />

      {e.signedIn ? (
        <div className="signed">
          <div>
            <strong>Signed in as {e.username}</strong>
            <span className="muted small">Logins last about an hour, and end when you close this tab.</span>
          </div>
          <Button icon={LogOut} onClick={e.signOut}>
            Sign out
          </Button>
        </div>
      ) : (
        <form onSubmit={submit} className="form">
          <div className="form-row">
            <TextInput label="Username" value={username} onChange={(ev) => setUsername(ev.target.value)} autoComplete="username" />
            <TextInput
              label="Password"
              type="password"
              value={password}
              onChange={(ev) => setPassword(ev.target.value)}
              autoComplete="current-password"
            />
          </div>
          {error ? (
            <Notice tone="bad" title="Could not sign in">
              {error}
            </Notice>
          ) : null}
          <div className="actions">
            <Button variant="primary" icon={LogIn} busy={busy} disabled={!username || !password} type="submit">
              Sign in
            </Button>
          </div>
          <p className="muted small">Use the ADMIN_USERNAME and ADMIN_PASSWORD from this service's own .env file.</p>
        </form>
      )}
    </Card>
  )
}
