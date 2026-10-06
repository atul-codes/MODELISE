import { ApiError, explainError } from './api'

// Every engine answer becomes a "verdict":
//   outcome: 'allowed' | 'blocked' | 'error'
//   stage:   where it stopped (or 'passed')
//   headline / detail: plain-language explanation
// plus the raw facts the cards want to draw (costGuard, policy, match, usage...).

export function guardrailVerdict(result) {
  if (result.ok) {
    const d = result.data
    const gov = d.governance
    return {
      engine: 'guardrail',
      outcome: 'allowed',
      stage: 'passed',
      headline: 'Passed both gates',
      detail: gov
        ? 'The prompt cleared the cost guard and the rulebook, and the local model answered.'
        : 'The prompt cleared the cost guard and the rulebook. No model was called.',
      costGuard: gov ? gov.cost_guard : d.cost_guard,
      policy: gov ? gov.policy_check : d.policy_check,
      generation: d.generation ?? null,
      usage: gov
        ? {
            promptTokens: gov.prompt_tokens,
            completionTokens: gov.completion_tokens,
            costUsd: gov.cost_usd,
            remainingBudgetUsd: gov.remaining_budget_usd,
          }
        : null,
      latencyMs: gov ? gov.latency_ms : d.latency_ms,
    }
  }

  const err = result.error
  if (!(err instanceof ApiError)) return failed('guardrail', explainError(err))
  const d = err.detail

  if (err.status === 403 && d && typeof d === 'object' && d.reason === 'policy_violation') {
    return {
      engine: 'guardrail',
      outcome: 'blocked',
      stage: 'policy',
      headline: 'Blocked by the rulebook',
      detail: 'The prompt is too close to a rule marked as blocked.',
      match: {
        chunk: d.matched_chunk,
        distance: d.matched_distance,
        ref: d.matched_doc_ref,
        source: d.matched_source,
        threshold: d.threshold,
      },
    }
  }
  if (err.status === 429 && d && typeof d === 'object' && d.reason === 'token_burn_exploit_detected') {
    return {
      engine: 'guardrail',
      outcome: 'blocked',
      stage: 'cost_guard',
      headline: 'Blocked by the cost guard',
      detail: 'The judge model flagged this prompt as an attempt to burn tokens or loop forever.',
      costGuard: d.analysis,
    }
  }
  if (err.status === 429 && d && typeof d === 'object' && d.reason === 'high_cost_rate_limit_exceeded') {
    return {
      engine: 'guardrail',
      outcome: 'blocked',
      stage: 'cost_guard',
      headline: 'Rate limit reached',
      detail: `Expensive prompts are limited to ${d.limit_per_minute} per minute for each user. Wait a minute and try again.`,
    }
  }
  if (err.status === 402) {
    return {
      engine: 'guardrail',
      outcome: 'blocked',
      stage: 'cost_guard',
      headline: 'Budget used up',
      detail: typeof d === 'string' ? d : 'This user has spent their whole budget. Raise the cap on the Spend and limits page.',
    }
  }
  if (err.status === 503) {
    return failed(
      'guardrail',
      'The judge model could not be reached, so the cost guard refused to decide. Start LM Studio (or Ollama), load your model, and check OLLAMA_BASE_URL in the guardrail .env file.',
      'Judge model unavailable',
    )
  }
  if (err.status === 502) {
    return {
      ...failed('guardrail', explainError(err), 'Model call failed'),
      stage: 'model',
      note: 'Both gates passed. Only the local model call failed.',
    }
  }
  return failed('guardrail', explainError(err))
}

export function geoVerdict(result) {
  if (!result.ok) return failed('geo', explainError(result.error))
  const d = result.data
  if (d.blocked) {
    return {
      engine: 'geo',
      outcome: 'blocked',
      stage: 'policy',
      headline: 'Blocked by a country pack',
      detail: 'The prompt is too close to a rule marked as blocked.',
      packsChecked: d.packs_checked,
      chunksEvaluated: d.chunks_evaluated,
      match: {
        chunk: d.matched_chunk,
        distance: d.matched_distance,
        ref: d.matched_doc_ref,
        packId: d.matched_pack_id,
        threshold: d.threshold,
      },
    }
  }
  return {
    engine: 'geo',
    outcome: 'allowed',
    stage: 'passed',
    headline: d.packs_checked.length ? 'Passed every pack' : 'No packs were checked',
    detail: d.packs_checked.length
      ? 'No enabled pack found a close match to a blocked rule.'
      : 'No pack is switched on, so nothing was compared. Turn a pack on from the Country packs page.',
    packsChecked: d.packs_checked,
    chunksEvaluated: d.chunks_evaluated,
    threshold: d.threshold,
    empty: d.packs_checked.length === 0,
  }
}

function failed(engine, detail, headline = "Couldn't check") {
  return { engine, outcome: 'error', stage: 'service', headline, detail }
}

// Combine the verdicts of the engines that ran into one line for the top of the results.
export function overall(verdicts) {
  const list = verdicts.filter(Boolean)
  if (list.some((v) => v.outcome === 'blocked')) {
    return {
      outcome: 'blocked',
      headline: 'Stopped before the model',
      detail: 'At least one check blocked this prompt, so no model would be called and nothing would be billed.',
    }
  }
  if (list.some((v) => v.outcome === 'error')) {
    return {
      outcome: 'error',
      headline: 'Not fully checked',
      detail: 'A check could not run. Fix the problem below and try again. A prompt that was not fully checked should not be sent on.',
    }
  }
  return {
    outcome: 'allowed',
    headline: 'Clear to reach the model',
    detail: 'Every check that ran let this prompt through.',
  }
}
