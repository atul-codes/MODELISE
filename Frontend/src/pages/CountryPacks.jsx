import { useCallback, useEffect, useState } from 'react'
import { Globe2, Plus, RefreshCw, Trash2, Upload } from 'lucide-react'
import { Button, Card, EmptyState, FilePicker, Modal, Notice, Pill, Switch, TextInput, useToast } from '../components/ui'
import { RequireSignIn } from '../components/RequireSignIn'
import { geo, explainError } from '../lib/api'
import { useEngine } from '../lib/connections'
import { num, slug, when } from '../lib/format'

export default function CountryPacks() {
  return (
    <RequireSignIn engine="geo">
      <Inner />
    </RequireSignIn>
  )
}

function Inner() {
  const e = useEngine('geo')
  const toast = useToast()
  const [packs, setPacks] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [upload, setUpload] = useState(null) // null | {} (new) | pack (add to existing)
  const [removing, setRemoving] = useState(null)
  const [pending, setPending] = useState({})

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setPacks(await e.call((base, token) => geo.packs(base, token)))
    } catch (err) {
      setError(explainError(err))
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [e.token, e.url])

  useEffect(() => {
    load()
  }, [load])

  async function toggle(pack, enabled) {
    setPending((p) => ({ ...p, [pack.pack_id]: true }))
    try {
      const updated = await e.call((base, token) => geo.toggle(base, token, pack.pack_id, enabled))
      setPacks((list) => list.map((x) => (x.pack_id === updated.pack_id ? updated : x)))
    } catch (err) {
      toast({ tone: 'bad', title: `Could not switch ${pack.display_name}`, body: explainError(err) })
    } finally {
      setPending((p) => ({ ...p, [pack.pack_id]: false }))
    }
  }

  async function remove() {
    const pack = removing
    setRemoving(null)
    try {
      await e.call((base, token) => geo.remove(base, token, pack.pack_id))
      setPacks((list) => list.filter((x) => x.pack_id !== pack.pack_id))
      toast({ title: `${pack.display_name} deleted` })
    } catch (err) {
      toast({ tone: 'bad', title: 'Could not delete', body: explainError(err) })
    }
  }

  const enabledCount = packs ? packs.filter((p) => p.enabled).length : 0

  return (
    <div className="page">
      <header className="page-head with-action">
        <div>
          <h1>Country packs</h1>
          <p>
            Each pack is its own rulebook for one country or regulation. Prompts are checked against every pack that is switched
            on.
          </p>
        </div>
        <div className="head-actions">
          <Button icon={RefreshCw} onClick={load} busy={loading}>
            Refresh
          </Button>
          <Button variant="primary" icon={Plus} onClick={() => setUpload({})}>
            New pack
          </Button>
        </div>
      </header>

      {error ? (
        <Notice tone="bad" title="Could not load packs">
          {error}
        </Notice>
      ) : null}

      {packs && packs.length ? (
        <>
          <p className="muted">
            {enabledCount} of {packs.length} switched on.
          </p>
          <div className="pack-grid">
            {packs.map((p) => (
              <article key={p.pack_id} className={`pack ${p.enabled ? '' : 'pack-off'}`}>
                <header className="pack-head">
                  <div>
                    <h2>{p.display_name}</h2>
                    <span className="mono muted small">{p.pack_id}</span>
                  </div>
                  <Switch
                    checked={p.enabled}
                    disabled={pending[p.pack_id]}
                    onChange={(v) => toggle(p, v)}
                    label={`${p.display_name} is ${p.enabled ? 'on' : 'off'}`}
                  />
                </header>
                <div className="pack-tags">
                  {p.country_code ? <Pill>{p.country_code}</Pill> : null}
                  <Pill tone={p.enabled ? 'good' : 'neutral'} dot>
                    {p.enabled ? 'Checking prompts' : 'Switched off'}
                  </Pill>
                </div>
                <dl className="pack-stats">
                  <div>
                    <dt>Rules</dt>
                    <dd>{num(p.total_vectors)}</dd>
                  </div>
                  <div>
                    <dt>Block</dt>
                    <dd>{num(p.block_entries)}</dd>
                  </div>
                  <div>
                    <dt>Allow</dt>
                    <dd>{num(p.allow_entries)}</dd>
                  </div>
                </dl>
                <footer className="pack-foot">
                  <span className="muted small">Updated {when(p.updated_at)}</span>
                  <div className="head-actions">
                    <Button variant="quiet" icon={Upload} onClick={() => setUpload(p)}>
                      Add rules
                    </Button>
                    <Button variant="quiet" icon={Trash2} onClick={() => setRemoving(p)} aria-label={`Delete ${p.display_name}`} />
                  </div>
                </footer>
              </article>
            ))}
          </div>
        </>
      ) : packs ? (
        <EmptyState
          title="No packs yet"
          action={
            <Button variant="primary" icon={Plus} onClick={() => setUpload({})}>
              Create your first pack
            </Button>
          }
        >
          A pack is made by uploading a CSV or PDF of rules for one country or regulation.
        </EmptyState>
      ) : !error ? (
        <Card>
          <p className="muted">
            <Globe2 size={14} aria-hidden="true" /> Loading packs
          </p>
        </Card>
      ) : null}

      {upload ? (
        <UploadModal
          pack={upload.pack_id ? upload : null}
          onClose={() => setUpload(null)}
          onDone={(msg) => {
            setUpload(null)
            toast(msg)
            load()
          }}
        />
      ) : null}

      {removing ? (
        <Modal
          title="Delete this pack?"
          onClose={() => setRemoving(null)}
          footer={
            <>
              <Button variant="quiet" onClick={() => setRemoving(null)}>
                Cancel
              </Button>
              <Button variant="danger" icon={Trash2} onClick={remove}>
                Delete pack
              </Button>
            </>
          }
        >
          <p>
            <strong>{removing.display_name}</strong> and its {num(removing.total_vectors)} rules will be removed for good. To keep
            it but stop using it, switch it off instead.
          </p>
        </Modal>
      ) : null}
    </div>
  )
}

function UploadModal({ pack, onClose, onDone }) {
  const e = useEngine('geo')
  const [name, setName] = useState(pack?.display_name || '')
  const [id, setId] = useState(pack?.pack_id || '')
  const [idTouched, setIdTouched] = useState(Boolean(pack))
  const [country, setCountry] = useState(pack?.country_code || '')
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const isPdf = file?.name.toLowerCase().endsWith('.pdf')
  const isCsv = file?.name.toLowerCase().endsWith('.csv')
  const ok = name.trim() && id.trim() && file && (isPdf || isCsv)

  async function submit() {
    setBusy(true)
    setError(null)
    const meta = { displayName: name.trim(), countryCode: country.trim() || undefined, file }
    try {
      const r = await e.call((base, token) =>
        isPdf ? geo.uploadPdf(base, token, id.trim(), meta) : geo.uploadCsv(base, token, id.trim(), meta),
      )
      onDone({
        title: isPdf ? `Added ${num(r.appended_chunks)} passages to ${r.display_name}` : `${r.display_name} now has ${num(r.total_vectors)} rules`,
        body: isPdf ? 'They were added as blocked rules.' : `${num(r.skipped_rows)} rows were skipped.`,
      })
    } catch (err) {
      setError(explainError(err))
      setBusy(false)
    }
  }

  return (
    <Modal
      title={pack ? `Add rules to ${pack.display_name}` : 'New country pack'}
      onClose={onClose}
      width={520}
      footer={
        <>
          <Button variant="quiet" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" icon={Upload} disabled={!ok} busy={busy} onClick={submit}>
            {pack ? 'Upload rules' : 'Create pack'}
          </Button>
        </>
      }
    >
      <div className="form">
        <TextInput
          label="Name"
          placeholder="India DPDP"
          value={name}
          onChange={(ev) => {
            setName(ev.target.value)
            if (!idTouched) setId(slug(ev.target.value))
          }}
        />
        <div className="form-row">
          <TextInput
            label="Pack ID"
            hint="Used in the API. Letters, numbers and dashes."
            mono
            value={id}
            disabled={Boolean(pack)}
            onChange={(ev) => {
              setIdTouched(true)
              setId(slug(ev.target.value))
            }}
          />
          <TextInput label="Country code" hint="Optional, like IN or EU." value={country} maxLength={8} onChange={(ev) => setCountry(ev.target.value.toUpperCase())} />
        </div>
        <FilePicker label="Rules file (CSV or PDF)" accept=".csv,.pdf,text/csv,application/pdf" file={file} onFile={setFile} />
        {file && !isPdf && !isCsv ? <Notice tone="bad">Choose a .csv or .pdf file.</Notice> : null}
        {isCsv ? (
          <Notice tone="warn">
            {pack
              ? 'A CSV replaces every rule in this pack. Upload a PDF instead to add on top.'
              : 'Needs the columns prompt and allow/block, where 1 means allow and 0 means block.'}
          </Notice>
        ) : null}
        {isPdf ? <Notice>Each passage of the PDF is added as a blocked rule.</Notice> : null}
        {error ? (
          <Notice tone="bad" title="Upload failed">
            {error}
          </Notice>
        ) : null}
      </div>
    </Modal>
  )
}
