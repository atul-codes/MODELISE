import { Check, Minus, ShieldX, TriangleAlert } from 'lucide-react'
import { DistanceMeter, Notice, Pill, ScoreBar, Spinner, cx } from './ui'
import { fixed, ms, num, usd } from '../lib/format'

const TONE = { allowed: 'good', blocked: 'bad', error: 'warn' }
const LABEL = { allowed: 'Allowed', blocked: 'Blocked', error: 'Not checked' }

function Gate({ name, state, children }) {
  const Icon = state === 'passed' ? Check : state === 'stopped' ? ShieldX : state === 'unknown' ? TriangleAlert : Minus
  return (
    <div className={cx('gate', `gate-${state}`)}>
      <span className="gate-mark" aria-hidden="true">
        <Icon size={14} />
      </span>
      <div className="gate-main">
        <div className="gate-name">
          {name}
          <span className="gate-state">
            {state === 'passed' ? 'Passed' : state === 'stopped' ? 'Stopped here' : state === 'unknown' ? 'Unknown' : 'Not reached'}
          </span>
        </div>
        {children}
      </div>
    </div>
  )
}

function Facts({ items }) {
  return (
    <dl className="facts">
      {items
        .filter(Boolean)
        .map(([k, v]) => (
          <div key={k}>
            <dt>{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
    </dl>
  )
}

function CostGuardFacts({ cg }) {
  if (!cg) return null
  return (
    <>
      <div className="risk">
        <span>Risk score</span>
        <ScoreBar value={cg.risk_score} label="Risk score" />
        <span className="mono">{fixed(cg.risk_score, 2)}</span>
      </div>
      <Facts
        items={[
          ['Endless loop attempt', cg.is_recursive_exploit ? 'Yes' : 'No'],
          ['Token drain attempt', cg.is_token_drain_attack ? 'Yes' : 'No'],
          ['Reasoning needed', cg.estimated_reasoning_depth],
        ]}
      />
    </>
  )
}

function MatchDetail({ match }) {
  return (
    <div className="match">
      <blockquote>{match.chunk}</blockquote>
      <Facts
        items={[
          match.packId && ['Pack', <span className="mono">{match.packId}</span>],
          match.ref && ['Rule came from', match.ref],
          match.source && ['Rule type', match.source === 'pdf' ? 'PDF document' : 'CSV row'],
        ]}
      />
      <DistanceMeter distance={match.distance} threshold={match.threshold} />
    </div>
  )
}

function GuardrailBody({ v }) {
  const blockedAtCost = v.outcome === 'blocked' && v.stage === 'cost_guard'
  const blockedAtPolicy = v.outcome === 'blocked' && v.stage === 'policy'
  const failedBefore = v.outcome === 'error'
  const costState = blockedAtCost ? 'stopped' : failedBefore ? 'unknown' : blockedAtPolicy || v.outcome === 'allowed' || v.stage === 'model' ? 'passed' : 'skipped'
  const policyState = blockedAtPolicy ? 'stopped' : v.outcome === 'allowed' || v.stage === 'model' ? 'passed' : failedBefore ? 'unknown' : 'skipped'
  return (
    <div className="gates">
      <Gate name="Cost guard" state={costState}>
        <CostGuardFacts cg={v.costGuard} />
      </Gate>
      <Gate name="Rulebook" state={policyState}>
        {v.policy ? (
          <p className="gate-line">
            Compared {num(v.policy.chunks_evaluated)} of {num(v.policy.total_chunks)} parts of the prompt against{' '}
            the rulebook.
          </p>
        ) : null}
        {v.policy && v.policy.chunks_evaluated === 0 ? (
          <Notice tone="warn" title="Nothing was compared">
            The rulebook is empty, so everything is allowed. Upload a CSV on the Guardrail rules page.
          </Notice>
        ) : null}
        {v.match ? <MatchDetail match={v.match} /> : null}
      </Gate>
    </div>
  )
}

function GeoBody({ v }) {
  return (
    <div className="gates">
      <Gate name="Country packs" state={v.outcome === 'blocked' ? 'stopped' : v.outcome === 'allowed' ? 'passed' : 'unknown'}>
        {v.packsChecked ? (
          <div className="chips" aria-label="Packs checked">
            {v.packsChecked.length ? (
              v.packsChecked.map((p) => (
                <span key={p} className={cx('chip', v.match?.packId === p && 'chip-hit')}>
                  {p}
                </span>
              ))
            ) : (
              <span className="muted">No packs</span>
            )}
          </div>
        ) : null}
        {v.chunksEvaluated !== undefined ? (
          <p className="gate-line">
            {v.outcome === 'blocked'
              ? `Stopped after ${num(v.chunksEvaluated)} comparisons.`
              : `Ran ${num(v.chunksEvaluated)} comparisons at threshold ${fixed(v.threshold, 2)}.`}
          </p>
        ) : null}
        {v.match ? <MatchDetail match={v.match} /> : null}
      </Gate>
    </div>
  )
}

export function VerdictCard({ engineName, verdict, loading }) {
  if (loading) {
    return (
      <section className="verdict verdict-loading" aria-busy="true">
        <header className="verdict-head">
          <h3>{engineName}</h3>
          <span className="muted inline">
            <Spinner size={14} /> Checking
          </span>
        </header>
        <div className="skeleton" />
        <div className="skeleton short" />
      </section>
    )
  }
  if (!verdict) return null
  return (
    <section className={cx('verdict', `verdict-${verdict.outcome}`)}>
      <header className="verdict-head">
        <h3>{engineName}</h3>
        <Pill tone={TONE[verdict.outcome]}>{LABEL[verdict.outcome]}</Pill>
      </header>
      <p className="verdict-headline">{verdict.headline}</p>
      <p className="verdict-detail">{verdict.detail}</p>
      {verdict.note ? <p className="verdict-detail">{verdict.note}</p> : null}

      {verdict.outcome === 'error' && verdict.stage === 'service' ? null : verdict.engine === 'guardrail' ? (
        <GuardrailBody v={verdict} />
      ) : (
        <GeoBody v={verdict} />
      )}

      {verdict.generation ? (
        <div className="answer">
          <div className="answer-label">Model answer</div>
          <pre>{verdict.generation}</pre>
          {verdict.usage ? (
            <Facts
              items={[
                ['Tokens in / out', `${num(verdict.usage.promptTokens)} / ${num(verdict.usage.completionTokens)}`],
                ['Cost', usd(verdict.usage.costUsd)],
                ['Budget left', usd(verdict.usage.remainingBudgetUsd)],
              ]}
            />
          ) : null}
        </div>
      ) : null}
      {verdict.latencyMs !== undefined && verdict.latencyMs !== null ? (
        <p className="latency">Took {ms(verdict.latencyMs)}</p>
      ) : null}
    </section>
  )
}
