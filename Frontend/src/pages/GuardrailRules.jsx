import { useCallback, useEffect, useState } from 'react'
import { FilePlus2, RefreshCw, Save } from 'lucide-react'
import { Button, Card, FilePicker, Modal, Notice, Stat, useToast } from '../components/ui'
import { RequireSignIn } from '../components/RequireSignIn'
import { guardrail, explainError } from '../lib/api'
import { useEngine } from '../lib/connections'
import { fixed, num } from '../lib/format'

export default function GuardrailRules() {
  return (
    <RequireSignIn engine="guardrail">
      <Inner />
    </RequireSignIn>
  )
}

function Inner() {
  const g = useEngine('guardrail')
  const toast = useToast()
  const [stats, setStats] = useState(null)
  const [threshold, setThreshold] = useState(0.75)
  const [savedThreshold, setSavedThreshold] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [csv, setCsv] = useState(null)
  const [pdf, setPdf] = useState(null)
  const [confirmCsv, setConfirmCsv] = useState(false)
  const [busy, setBusy] = useState('')
  const [report, setReport] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const d = await g.call((base, token) => guardrail.spend(base, token))
      setStats(d.policy_index_stats)
      setThreshold(d.active_threshold)
      setSavedThreshold(d.active_threshold)
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

  async function uploadCsv() {
    setConfirmCsv(false)
    setBusy('csv')
    setReport(null)
    try {
      const r = await g.call((base, token) => guardrail.uploadCsv(base, token, csv))
      setReport({
        tone: 'good',
        title: `Rulebook replaced with ${r.filename}`,
        body: `${num(r.indexed_rows)} rules loaded (${num(r.block_count)} block, ${num(r.allow_count)} allow). ${num(r.skipped_rows)} rows skipped.`,
      })
      setCsv(null)
      load()
    } catch (err) {
      setReport({ tone: 'bad', title: 'Upload failed', body: explainError(err) })
    } finally {
      setBusy('')
    }
  }

  async function uploadPdf() {
    setBusy('pdf')
    setReport(null)
    try {
      const r = await g.call((base, token) => guardrail.uploadPdf(base, token, pdf))
      setReport({
        tone: 'good',
        title: `Added ${r.filename}`,
        body: `${num(r.appended_chunks)} passages added as blocked rules. The rulebook now holds ${num(r.total_vectors)} rules.`,
      })
      setPdf(null)
      load()
    } catch (err) {
      setReport({ tone: 'bad', title: 'Upload failed', body: explainError(err) })
    } finally {
      setBusy('')
    }
  }

  async function saveThreshold() {
    setBusy('threshold')
    try {
      const r = await g.call((base, token) => guardrail.setThreshold(base, token, Number(threshold)))
      setSavedThreshold(r.threshold)
      toast({ title: 'Threshold saved', body: `Blocking now uses ${fixed(r.threshold, 2)}. This resets when the service restarts.` })
    } catch (err) {
      toast({ tone: 'bad', title: 'Could not save', body: explainError(err) })
    } finally {
      setBusy('')
    }
  }

  return (
    <div className="page">
      <header className="page-head with-action">
        <div>
          <h1>Guardrail rules</h1>
          <p>The rulebook that Guardrail Layer 2 compares every prompt against, and how strict that comparison is.</p>
        </div>
        <Button icon={RefreshCw} onClick={load} busy={loading}>
          Refresh
        </Button>
      </header>

      {error ? (
        <Notice tone="bad" title="Could not load the rulebook">
          {error}
        </Notice>
      ) : null}

      <div className="stat-row">
        <Stat label="Rules loaded" value={stats ? num(stats.total_vectors) : '-'} />
        <Stat label="Block rules" value={stats ? num(stats.block_entries) : '-'} tone="bad" />
        <Stat label="Allow rules" value={stats ? num(stats.allow_entries) : '-'} tone="good" />
        <Stat label="From CSV" value={stats ? num(stats.csv_entries) : '-'} />
        <Stat label="From PDF" value={stats ? num(stats.pdf_entries) : '-'} />
      </div>

      {report ? (
        <Notice tone={report.tone} title={report.title}>
          {report.body}
        </Notice>
      ) : null}

      <div className="two">
        <Card title="Replace the rulebook with a CSV">
          <p className="muted">
            One row per example prompt. Use the columns <code>prompt</code> and <code>allow/block</code>, where 1 means allow and 0
            means block.
          </p>
          <FilePicker label="CSV file" accept=".csv,text/csv" file={csv} onFile={setCsv} />
          <Notice tone="warn">This wipes every rule that is loaded now, including PDF passages added earlier.</Notice>
          <div className="actions">
            <Button variant="primary" icon={FilePlus2} disabled={!csv} busy={busy === 'csv'} onClick={() => setConfirmCsv(true)}>
              Replace rulebook
            </Button>
          </div>
        </Card>

        <Card title="Add a PDF to the rulebook">
          <p className="muted">
            The PDF is split into passages and added on top of what is already loaded. Every passage becomes a blocked rule.
          </p>
          <FilePicker label="PDF file" accept=".pdf,application/pdf" file={pdf} onFile={setPdf} />
          <div className="actions">
            <Button variant="primary" icon={FilePlus2} disabled={!pdf} busy={busy === 'pdf'} onClick={uploadPdf}>
              Add PDF rules
            </Button>
          </div>
        </Card>
      </div>

      <Card title="Blocking threshold">
        <p className="muted">
          A prompt is blocked when it lands closer to a blocked rule than this number. Raise it to block more, lower it to block
          only near-identical prompts. It applies right away and resets to the value in the service's settings after a restart.
        </p>
        <div className="threshold">
          <input
            type="range"
            className="range"
            min="0.05"
            max="2"
            step="0.01"
            value={threshold}
            aria-label="Blocking threshold"
            onChange={(e) => setThreshold(e.target.value)}
          />
          <input
            type="number"
            className="input mono narrow"
            min="0.01"
            max="2"
            step="0.01"
            value={threshold}
            aria-label="Blocking threshold value"
            onChange={(e) => setThreshold(e.target.value)}
          />
          <Button
            variant="primary"
            icon={Save}
            busy={busy === 'threshold'}
            disabled={savedThreshold !== null && Number(threshold) === Number(savedThreshold)}
            onClick={saveThreshold}
          >
            Save threshold
          </Button>
        </div>
        <p className="muted small">Currently active: {savedThreshold === null ? '-' : fixed(savedThreshold, 2)}. Allowed range is above 0 up to 2.</p>
      </Card>

      {confirmCsv ? (
        <Modal
          title="Replace the whole rulebook?"
          onClose={() => setConfirmCsv(false)}
          footer={
            <>
              <Button variant="quiet" onClick={() => setConfirmCsv(false)}>
                Cancel
              </Button>
              <Button variant="danger" onClick={uploadCsv}>
                Replace rulebook
              </Button>
            </>
          }
        >
          <p>
            <strong>{csv?.name}</strong> will become the entire rulebook. Every rule loaded now, including any PDF passages, is
            removed. This cannot be undone.
          </p>
        </Modal>
      ) : null}
    </div>
  )
}
