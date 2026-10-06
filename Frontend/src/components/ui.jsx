import { createContext, useCallback, useContext, useEffect, useId, useRef, useState } from 'react'
import { AlertTriangle, CheckCircle2, Info, Loader2, Upload, X, XCircle } from 'lucide-react'

export const cx = (...parts) => parts.filter(Boolean).join(' ')

export function Spinner({ size = 16 }) {
  return <Loader2 className="spin" size={size} aria-hidden="true" />
}

export function Button({ variant = 'default', busy, icon: Icon, children, className, ...rest }) {
  return (
    <button
      type="button"
      {...rest}
      disabled={rest.disabled || busy}
      className={cx('btn', `btn-${variant}`, className)}
    >
      {busy ? <Spinner /> : Icon ? <Icon size={16} aria-hidden="true" /> : null}
      {children}
    </button>
  )
}

export function Field({ label, hint, children }) {
  const id = useId()
  return (
    <div className="field">
      <label htmlFor={id} className="field-label">
        {label}
      </label>
      {typeof children === 'function' ? children(id) : children}
      {hint ? <p className="field-hint">{hint}</p> : null}
    </div>
  )
}

export function TextInput({ label, hint, mono, ...rest }) {
  return (
    <Field label={label} hint={hint}>
      {(id) => <input id={id} className={cx('input', mono && 'mono')} {...rest} />}
    </Field>
  )
}

export function Switch({ checked, onChange, label, disabled }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      className="switch"
      onClick={() => onChange(!checked)}
    >
      <span className="switch-knob" />
    </button>
  )
}

export function Segmented({ value, onChange, options, label }) {
  return (
    <div className="segmented" role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          className={cx('segment', value === o.value && 'on')}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function Pill({ tone = 'neutral', children, dot }) {
  return (
    <span className={cx('pill', `pill-${tone}`)}>
      {dot ? <span className="pill-dot" aria-hidden="true" /> : null}
      {children}
    </span>
  )
}

export function Card({ title, aside, children, className, flush }) {
  return (
    <section className={cx('card', className)}>
      {title || aside ? (
        <header className="card-head">
          {title ? <h2 className="card-title">{title}</h2> : <span />}
          {aside}
        </header>
      ) : null}
      <div className={cx('card-body', flush && 'flush')}>{children}</div>
    </section>
  )
}

export function Stat({ label, value, sub, tone }) {
  return (
    <div className={cx('stat', tone && `stat-${tone}`)}>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {sub ? <div className="stat-sub">{sub}</div> : null}
    </div>
  )
}

export function Notice({ tone = 'info', title, children }) {
  const Icon = tone === 'warn' ? AlertTriangle : tone === 'bad' ? XCircle : tone === 'good' ? CheckCircle2 : Info
  return (
    <div className={cx('notice', `notice-${tone}`)} role={tone === 'bad' ? 'alert' : 'note'}>
      <Icon size={18} aria-hidden="true" />
      <div>
        {title ? <strong>{title}</strong> : null}
        {children ? <div className="notice-body">{children}</div> : null}
      </div>
    </div>
  )
}

export function EmptyState({ title, children, action }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      {children ? <p>{children}</p> : null}
      {action}
    </div>
  )
}

export function Modal({ title, onClose, children, footer, width = 480 }) {
  const ref = useRef(null)
  const titleId = useId()
  useEffect(() => {
    const previous = document.activeElement
    const first = ref.current?.querySelector('input, select, textarea, button:not(.icon-btn)')
    first?.focus()
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      previous?.focus?.()
    }
  }, [onClose])
  return (
    <div className="scrim" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div
        ref={ref}
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        style={{ maxWidth: width }}
      >
        <header className="modal-head">
          <h2 id={titleId}>{title}</h2>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </header>
        <div className="modal-body">{children}</div>
        {footer ? <footer className="modal-foot">{footer}</footer> : null}
      </div>
    </div>
  )
}

export function FilePicker({ accept, file, onFile, label, hint }) {
  const inputRef = useRef(null)
  const [over, setOver] = useState(false)
  const id = useId()
  return (
    <div className="field">
      <span className="field-label" id={`${id}-l`}>
        {label}
      </span>
      <div
        className={cx('drop', over && 'over', file && 'has')}
        onDragOver={(e) => {
          e.preventDefault()
          setOver(true)
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setOver(false)
          const f = e.dataTransfer.files?.[0]
          if (f) onFile(f)
        }}
      >
        <input
          ref={inputRef}
          id={id}
          type="file"
          accept={accept}
          className="sr-only"
          aria-labelledby={`${id}-l`}
          onChange={(e) => onFile(e.target.files?.[0] || null)}
        />
        <Upload size={18} aria-hidden="true" />
        <div className="drop-text">
          {file ? (
            <>
              <strong>{file.name}</strong>
              <span>{(file.size / 1024).toFixed(file.size > 102400 ? 0 : 1)} KB</span>
            </>
          ) : (
            <>
              <strong>Drop a file here</strong>
              <span>or choose one from your computer</span>
            </>
          )}
        </div>
        <Button variant="quiet" onClick={() => inputRef.current?.click()}>
          {file ? 'Change' : 'Choose file'}
        </Button>
      </div>
      {hint ? <p className="field-hint">{hint}</p> : null}
    </div>
  )
}

// ---- Toasts ----------------------------------------------------------------
const ToastCtx = createContext(() => {})
export const useToast = () => useContext(ToastCtx)

export function ToastProvider({ children }) {
  const [items, setItems] = useState([])
  const notify = useCallback(({ tone = 'good', title, body }) => {
    const id = Math.random().toString(36).slice(2)
    setItems((list) => [...list, { id, tone, title, body }])
    setTimeout(() => setItems((list) => list.filter((t) => t.id !== id)), 5200)
  }, [])
  return (
    <ToastCtx.Provider value={notify}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={cx('toast', `toast-${t.tone}`)}>
            <strong>{t.title}</strong>
            {t.body ? <span>{t.body}</span> : null}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}

// ---- Distance meter --------------------------------------------------------
// The one visual that explains the whole system: the rulebook blocks a prompt when
// its distance to a blocked rule falls below the threshold. Small distance = very similar.
export function DistanceMeter({ distance, threshold, max = 2 }) {
  const t = Math.min(Math.max(threshold ?? 0, 0), max)
  const d = distance === null || distance === undefined ? null : Math.min(Math.max(distance, 0), max)
  const pct = (v) => `${(v / max) * 100}%`
  const blocked = d !== null && threshold !== undefined && threshold !== null && distance < threshold
  return (
    <div className="meter" role="img" aria-label={
      d === null
        ? `Threshold ${threshold}`
        : `Closest blocked rule is at distance ${Number(distance).toFixed(3)}. Threshold is ${threshold}. ${blocked ? 'Inside the blocking zone.' : 'Outside the blocking zone.'}`
    }>
      <div className="meter-track">
        <div className="meter-zone" style={{ width: pct(t) }} />
        <div className="meter-line" style={{ left: pct(t) }}>
          <span className="meter-line-label">Threshold {Number(threshold).toFixed(2)}</span>
        </div>
        {d !== null ? (
          <div className={cx('meter-dot', blocked && 'hit')} style={{ left: pct(d) }}>
            <span className="meter-dot-label">{Number(distance).toFixed(3)}</span>
          </div>
        ) : null}
      </div>
      <div className="meter-scale" aria-hidden="true">
        <span>0 identical</span>
        <span>{max} unrelated</span>
      </div>
      <p className="meter-note">Prompts that land left of the line are blocked when they match a blocked rule.</p>
    </div>
  )
}

export function ScoreBar({ value, label }) {
  const v = Math.min(Math.max(Number(value) || 0, 0), 1)
  return (
    <div className="score" role="img" aria-label={`${label}: ${v.toFixed(2)} out of 1`}>
      <div className="score-fill" style={{ width: `${v * 100}%` }} data-level={v >= 0.55 ? 'high' : v >= 0.3 ? 'mid' : 'low'} />
    </div>
  )
}
