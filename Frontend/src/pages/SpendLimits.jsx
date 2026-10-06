import { useCallback, useEffect, useState } from 'react'
import { Pencil, RefreshCw } from 'lucide-react'
import { Button, Card, EmptyState, Modal, Notice, Stat, TextInput, useToast } from '../components/ui'
import { RequireSignIn } from '../components/RequireSignIn'
import { guardrail, explainError } from '../lib/api'
import { useEngine } from '../lib/connections'
import { num, usd } from '../lib/format'

export default function SpendLimits() {
  return (
    <RequireSignIn engine="guardrail">
      <Inner />
    </RequireSignIn>
  )
}

function Inner() {
  const g = useEngine('guardrail')
  const toast = useToast()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(null)
  const [cap, setCap] = useState('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await g.call((base, token) => guardrail.spend(base, token)))
    } catch (err) {
      setError(explainError(err))
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [g.token, g.url])

  useEffect(() => {
    load()
  }, [load])

  async function saveCap() {
    setSaving(true)
    try {
      await g.call((base, token) => guardrail.setBudget(base, token, editing.user_id, Number(cap)))
      toast({ title: `Budget updated for ${editing.user_id}`, body: `New cap is ${usd(Number(cap))}.` })
      setEditing(null)
      load()
    } catch (err) {
      toast({ tone: 'bad', title: 'Could not update', body: explainError(err) })
    } finally {
      setSaving(false)
    }
  }

  const blocks = data
    ? [
        { key: 'Loop or token drain', value: data.total_token_burn_blocks, tone: 'bad' },
        { key: 'Budget used up', value: data.total_budget_blocks, tone: 'warn' },
        { key: 'Rate limit', value: data.total_rate_limit_blocks, tone: 'info' },
      ]
    : []
  const blockTotal = blocks.reduce((s, b) => s + b.value, 0)

  return (
    <div className="page">
      <header className="page-head with-action">
        <div>
          <h1>Spend and limits</h1>
          <p>What each user has used, what they are allowed to use, and how often the cost guard stepped in.</p>
        </div>
        <Button icon={RefreshCw} onClick={load} busy={loading}>
          Refresh
        </Button>
      </header>

      {error ? (
        <Notice tone="bad" title="Could not load the dashboard">
          {error}
        </Notice>
      ) : null}

      <div className="stat-row">
        <Stat label="Users" value={data ? num(data.total_users) : '-'} />
        <Stat label="Requests answered" value={data ? num(data.total_requests) : '-'} />
        <Stat label="Total spend" value={data ? usd(data.total_spend_usd) : '-'} />
        <Stat label="Blocked by cost guard" value={data ? num(blockTotal) : '-'} tone={blockTotal ? 'bad' : undefined} />
      </div>

      {data && blockTotal > 0 ? (
        <Card title="Why the cost guard blocked prompts">
          <div className="stack-bar" role="img" aria-label={blocks.map((b) => `${b.key}: ${b.value}`).join(', ')}>
            {blocks
              .filter((b) => b.value > 0)
              .map((b) => (
                <span key={b.key} className={`seg seg-${b.tone}`} style={{ flexGrow: b.value }} />
              ))}
          </div>
          <ul className="legend">
            {blocks.map((b) => (
              <li key={b.key}>
                <span className={`swatch seg-${b.tone}`} aria-hidden="true" />
                {b.key}
                <strong>{num(b.value)}</strong>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      <Card title="Users" flush>
        {data && data.users.length ? (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">User</th>
                  <th scope="col">Budget used</th>
                  <th scope="col" className="num">
                    Spent
                  </th>
                  <th scope="col" className="num">
                    Cap
                  </th>
                  <th scope="col" className="num">
                    Requests
                  </th>
                  <th scope="col" className="num">
                    Tokens in / out
                  </th>
                  <th scope="col" className="num">
                    Blocks
                  </th>
                  <th scope="col">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.users.map((u) => {
                  const used = u.budget_cap_usd > 0 ? Math.min(u.total_spent_usd / u.budget_cap_usd, 1) : 1
                  const b = u.blocked_token_burn_count + u.blocked_budget_count + u.blocked_rate_limit_count
                  return (
                    <tr key={u.user_id}>
                      <th scope="row" className="mono">
                        {u.user_id}
                      </th>
                      <td>
                        <div className="usage" role="img" aria-label={`${Math.round(used * 100)} percent of budget used`}>
                          <div className="usage-fill" data-level={used >= 0.9 ? 'high' : used >= 0.6 ? 'mid' : 'low'} style={{ width: `${used * 100}%` }} />
                        </div>
                      </td>
                      <td className="num mono">{usd(u.total_spent_usd)}</td>
                      <td className="num mono">{usd(u.budget_cap_usd)}</td>
                      <td className="num mono">{num(u.request_count)}</td>
                      <td className="num mono">
                        {num(u.total_prompt_tokens)} / {num(u.total_completion_tokens)}
                      </td>
                      <td className="num mono" title={`Loop or drain ${u.blocked_token_burn_count}, budget ${u.blocked_budget_count}, rate limit ${u.blocked_rate_limit_count}`}>
                        {num(b)}
                      </td>
                      <td className="num">
                        <Button
                          variant="quiet"
                          icon={Pencil}
                          onClick={() => {
                            setEditing(u)
                            setCap(String(u.budget_cap_usd))
                          }}
                        >
                          Set cap
                        </Button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : data ? (
          <EmptyState title="No usage yet">
            Users appear here after they send a prompt. On the Test prompts page, run Guardrail in Check and answer mode to create one.
          </EmptyState>
        ) : (
          <p className="pad muted">Loading</p>
        )}
      </Card>

      {editing ? (
        <Modal
          title={`Set budget for ${editing.user_id}`}
          onClose={() => setEditing(null)}
          footer={
            <>
              <Button variant="quiet" onClick={() => setEditing(null)}>
                Cancel
              </Button>
              <Button variant="primary" busy={saving} disabled={cap === '' || Number(cap) < 0} onClick={saveCap}>
                Save budget
              </Button>
            </>
          }
        >
          <TextInput
            label="Budget cap in US dollars"
            hint={`They have spent ${usd(editing.total_spent_usd)} so far. Set the cap at or below that to see the budget block in action.`}
            type="number"
            min="0"
            step="0.01"
            mono
            value={cap}
            onChange={(e) => setCap(e.target.value)}
          />
        </Modal>
      ) : null}
    </div>
  )
}
