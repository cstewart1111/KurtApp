import { useState, useEffect, useRef, useCallback } from 'react'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, PieChart, Pie
} from 'recharts'
import {
  Upload, CheckCircle, AlertCircle, TrendingUp, TrendingDown,
  Users, DollarSign, Heart, ArrowUpRight, ArrowDownRight,
  RefreshCw, FileText, Map, ChevronRight, Info, Sparkles,
  Download, Building2, Lock, Eye, EyeOff
} from 'lucide-react'

// ── Helpers ──────────────────────────────────────────────────────────────────

const fmt = (n) => {
  if (n == null) return '—'
  if (n >= 1_000_000) return `$${(n/1_000_000).toFixed(2)}M`
  if (n >= 1_000) return `$${n.toLocaleString('en-US', {maximumFractionDigits: 0})}`
  return `$${n.toFixed(2)}`
}
const fmtNum = (n) => n?.toLocaleString('en-US') ?? '—'
const fmtPct = (n) => n != null ? `${n.toFixed(1)}%` : '—'

// ── Auth-aware fetch helper ───────────────────────────────────────────────────
// Reads the dashboard key from sessionStorage and injects it on every request.
const apiCall = (url, opts = {}) => {
  const key = sessionStorage.getItem('dhc_key') || ''
  return fetch(url, {
    ...opts,
    headers: { ...(opts.headers || {}), 'X-Dashboard-Key': key },
  })
}

const SEGMENT_META = {
  new_donors:              { label: 'New Donors',          color: '#2e7589', emoji: '✦' },
  second_year_from_new:    { label: '2nd Year',            color: '#E8924A', emoji: '◈' },
  multi_year:              { label: 'Multi-Year',          color: '#1B4F5A', emoji: '◆' },
  second_year_regained:    { label: 'Regained',            color: '#246070', emoji: '↩' },
  lapsed_13_24:            { label: 'Lapsed 1yr',          color: '#9e9589', emoji: '○' },
  multi_year_lapsed_25plus:{ label: 'Lapsed 2yr+',         color: '#d6cec4', emoji: '◌' },
}
const SEGMENT_ORDER = Object.keys(SEGMENT_META)

// ── Animated Counter ──────────────────────────────────────────────────────────

function AnimCounter({ value, prefix = '', suffix = '', decimals = 0, duration = 900 }) {
  const [display, setDisplay] = useState(0)
  const start = useRef(null)
  const frame = useRef(null)

  useEffect(() => {
    if (value == null) return
    start.current = null
    const target = parseFloat(value)
    const step = (ts) => {
      if (!start.current) start.current = ts
      const progress = Math.min((ts - start.current) / duration, 1)
      const ease = 1 - Math.pow(1 - progress, 3)
      setDisplay(target * ease)
      if (progress < 1) frame.current = requestAnimationFrame(step)
    }
    frame.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame.current)
  }, [value, duration])

  const formatted = decimals > 0
    ? display.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
    : Math.round(display).toLocaleString('en-US')

  return <span>{prefix}{formatted}{suffix}</span>
}

// ── Upload Screen ─────────────────────────────────────────────────────────────

function UploadScreen({ onAnalysisComplete }) {
  const [clientName, setClientName] = useState('')
  const [fiscalYearEnd, setFiscalYearEnd] = useState(6)
  const [donorFile, setDonorFile] = useState(null)
  const [ohpFile, setOhpFile] = useState(null)
  const [step, setStep] = useState('idle') // idle | uploading | analyzing | done | error
  const [error, setError] = useState(null)
  const [donorResult, setDonorResult] = useState(null)
  const donorRef = useRef()
  const ohpRef = useRef()

  const handleDonorUpload = async () => {
    if (!donorFile || !clientName.trim()) return
    setStep('uploading')
    setError(null)

    const fd = new FormData()
    fd.append('donor_file', donorFile)
    fd.append('client_name', clientName.trim())
    fd.append('fiscal_year_end_month', fiscalYearEnd)
    if (ohpFile) fd.append('ohp_file', ohpFile)
    try {
      const res = await apiCall('/api/analyze', { method: 'POST', body: fd })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Analysis failed')
      onAnalysisComplete(data)
    } catch (e) {
      setError(e.message)
      setStep('error')
    }
  }

  const handleAnalyze = () => {}

  const stepIdx = { idle: 0, uploading: 0, donor_done: 1, analyzing: 2, done: 3 }[step] ?? 0

  return (
    <div className="animate-in" style={{ maxWidth: 680, margin: '3rem auto' }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
        <p className="label" style={{ marginBottom: '0.75rem', color: 'var(--teal-600)' }}>
          StoryCause · Donor Health Check™
        </p>
        <h1 className="display-lg" style={{ color: 'var(--slate-900)', marginBottom: '0.5rem' }}>
          Begin your analysis
        </h1>
        <p style={{ color: 'var(--stone-400)', fontSize: '0.9rem' }}>
          Upload your donor giving history to uncover lifecycle insights
          powered by story intelligence.
        </p>
      </div>

      {/* Step indicator */}
      <div className="step-indicator" style={{ marginBottom: '2rem' }}>
        {['Client Setup', 'Donor Data', 'OHP Stories', 'Analyze'].map((label, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
            <div className={`step ${stepIdx > i ? 'done' : stepIdx === i ? 'active' : ''}`}>
              <div className="step-num">{stepIdx > i ? '✓' : i + 1}</div>
              <span className="step-label">{label}</span>
            </div>
            {i < 3 && <div className="step-connector" style={{ flex: 1, height: 1, background: stepIdx > i ? 'var(--teal-200)' : 'var(--cream-dark)', margin: '0 0.5rem' }} />}
          </div>
        ))}
      </div>

      {/* Setup Card */}
      <div className="card animate-in" style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem' }}>
          <div style={{ width: 28, height: 28, borderRadius: '50%', background: stepIdx > 0 ? 'var(--teal-800)' : 'var(--amber-500)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 700, flexShrink: 0 }}>
            {stepIdx > 0 ? '✓' : '1'}
          </div>
          <p className="label">Client Setup</p>
        </div>
        <div style={{ display: 'grid', gap: '0.75rem' }}>
          <div>
            <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--slate-500)', display: 'block', marginBottom: '0.4rem', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
              Institution Name
            </label>
            <input
              value={clientName}
              onChange={e => setClientName(e.target.value)}
              placeholder="e.g. University of Texas Foundation"
              disabled={step !== 'idle' && step !== 'error'}
              style={{ width: '100%', padding: '0.65rem 0.9rem', border: '1.5px solid var(--cream-dark)', borderRadius: 'var(--radius-md)', fontFamily: 'var(--font-body)', fontSize: '0.88rem', color: 'var(--slate-700)', background: 'white', outline: 'none', transition: 'border-color 150ms' }}
              onFocus={e => e.target.style.borderColor = 'var(--teal-600)'}
              onBlur={e => e.target.style.borderColor = 'var(--cream-dark)'}
            />
          </div>
          <div>
            <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--slate-500)', display: 'block', marginBottom: '0.4rem', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
              Fiscal Year End
            </label>
            <select
              value={fiscalYearEnd}
              onChange={e => setFiscalYearEnd(Number(e.target.value))}
              disabled={step !== 'idle' && step !== 'error'}
              style={{ width: '100%', padding: '0.65rem 0.9rem', border: '1.5px solid var(--cream-dark)', borderRadius: 'var(--radius-md)', fontFamily: 'var(--font-body)', fontSize: '0.88rem', color: 'var(--slate-700)', background: 'white', outline: 'none' }}
            >
              <option value={6}>June 30 (Jul–Jun)</option>
              <option value={12}>December 31 (Calendar Year)</option>
              <option value={9}>September 30 (Oct–Sep)</option>
              <option value={3}>March 31 (Apr–Mar)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Donor File Card */}
      <div className="card animate-in animate-in-delay-1" style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem' }}>
          <div style={{ width: 28, height: 28, borderRadius: '50%', background: donorResult ? 'var(--teal-800)' : 'var(--stone-200)', color: donorResult ? 'white' : 'var(--stone-400)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 700 }}>
            {donorResult ? '✓' : '2'}
          </div>
          <p className="label">Donor Giving History <span style={{ color: 'var(--amber-500)' }}>*</span></p>
        </div>

        {!donorResult ? (
          <div
            className="upload-zone"
            onClick={() => donorRef.current?.click()}
            style={{ cursor: donorFile ? 'default' : 'pointer' }}
          >
            <input ref={donorRef} type="file" accept=".csv" onChange={e => setDonorFile(e.target.files[0])} />
            {donorFile ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', justifyContent: 'center' }}>
                <CheckCircle size={20} color="var(--teal-600)" />
                <div>
                  <p style={{ fontWeight: 600, color: 'var(--teal-800)', fontSize: '0.9rem' }}>{donorFile.name}</p>
                  <p style={{ fontSize: '0.75rem', color: 'var(--stone-400)' }}>{(donorFile.size / 1024).toFixed(1)} KB</p>
                </div>
              </div>
            ) : (
              <div>
                <Upload size={28} color="var(--stone-400)" style={{ margin: '0 auto 0.75rem' }} />
                <p style={{ fontWeight: 500, color: 'var(--slate-700)', fontSize: '0.9rem', marginBottom: '0.25rem' }}>
                  Drop your CSV here or click to browse
                </p>
                <p style={{ fontSize: '0.78rem', color: 'var(--stone-400)' }}>
                  StoryCause data export format · One row per donation
                </p>
              </div>
            )}
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '0.75rem' }}>
            {[
              { label: 'Donors', val: fmtNum(donorResult.unique_donors) },
              { label: 'Records', val: fmtNum(donorResult.records_parsed) },
              { label: 'Confidence', val: `${donorResult.confidence_score}/100` },
            ].map(({ label, val }) => (
              <div key={label} style={{ textAlign: 'center', padding: '0.75rem', background: 'var(--teal-50)', borderRadius: 'var(--radius-md)' }}>
                <p className="label" style={{ marginBottom: '0.25rem' }}>{label}</p>
                <p style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', fontWeight: 600, color: 'var(--teal-800)' }}>{val}</p>
              </div>
            ))}
          </div>
        )}

        {!donorResult && donorFile && clientName.trim() && (
          <button
            className="btn btn-primary"
            onClick={handleDonorUpload}
            disabled={step === 'uploading'}
            style={{ width: '100%', justifyContent: 'center', marginTop: '1rem' }}
          >
            {step === 'uploading' ? <><RefreshCw size={14} style={{ animation: 'spin 1s linear infinite' }} /> Validating…</> : <><Sparkles size={14} /> Upload & Analyze</>}
          </button>
        )}
      </div>

      {/* OHP Card */}
      <div className="card animate-in animate-in-delay-2" style={{ marginBottom: '1.5rem', opacity: donorResult ? 1 : 0.5 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem' }}>
          <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'var(--stone-200)', color: 'var(--stone-400)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 700 }}>3</div>
          <p className="label">OHP Interview Data <span style={{ color: 'var(--stone-400)', fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>— optional</span></p>
        </div>
        <div
          className="upload-zone"
          onClick={() => donorResult && ohpRef.current?.click()}
          style={{ padding: '1.5rem', cursor: donorResult ? 'pointer' : 'not-allowed' }}
        >
          <input ref={ohpRef} type="file" accept=".csv" onChange={e => setOhpFile(e.target.files[0])} disabled={!donorResult} />
          {ohpFile ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', justifyContent: 'center' }}>
              <CheckCircle size={18} color="var(--teal-600)" />
              <p style={{ fontWeight: 500, color: 'var(--teal-800)', fontSize: '0.88rem' }}>{ohpFile.name}</p>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', justifyContent: 'center' }}>
              <Heart size={18} color="var(--stone-400)" />
              <p style={{ fontSize: '0.82rem', color: 'var(--stone-400)' }}>
                {donorResult ? 'Upload OHP interview CSV to overlay story sentiment' : 'Upload donor file first'}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{ display: 'flex', gap: '0.75rem', padding: '1rem', background: '#fee2e2', borderRadius: 'var(--radius-md)', marginBottom: '1rem', color: '#991b1b', fontSize: '0.85rem' }}>
          <AlertCircle size={16} style={{ flexShrink: 0, marginTop: 2 }} />
          <span>{error}</span>
        </div>
      )}

      {/* Run Analysis */}
      {donorResult && (
        <button
          className="btn btn-amber btn-lg animate-in"
          onClick={handleAnalyze}
          disabled={step === 'analyzing'}
          style={{ width: '100%', justifyContent: 'center' }}
        >
          {step === 'analyzing'
            ? <><RefreshCw size={16} style={{ animation: 'spin 1s linear infinite' }} /> Running DHC Analysis…</>
            : <><Sparkles size={16} /> Run Donor Health Check™</>
          }
        </button>
      )}
    </div>
  )
}

// ── KPI Card ─────────────────────────────────────────────────────────────────

function KPICard({ label, value, prefix = '', suffix = '', icon: Icon, trend, delay = 0, decimals = 0 }) {
  return (
    <div className={`metric-card animate-in animate-in-delay-${delay}`}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
        <p className="label">{label}</p>
        {Icon && <Icon size={16} color="var(--teal-200)" />}
      </div>
      <div className="metric-value">
        <AnimCounter value={value} prefix={prefix} suffix={suffix} decimals={decimals} />
      </div>
      {trend != null && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', marginTop: '0.5rem', fontSize: '0.75rem', color: trend >= 0 ? '#166534' : '#991b1b' }}>
          {trend >= 0 ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
          <span>{Math.abs(trend).toFixed(1)}% vs prior year</span>
        </div>
      )}
    </div>
  )
}

// ── Segment Arc ───────────────────────────────────────────────────────────────

function SegmentArc({ metrics, selected, onSelect }) {
  const segs = metrics?.segments ?? {}
  return (
    <div className="segment-arc">
      {SEGMENT_ORDER.map(key => {
        const seg = segs[key]
        if (!seg) return null
        const meta = SEGMENT_META[key]
        const ret = key === 'new_donors' ? null : seg.pct_donors_giving
        return (
          <button
            key={key}
            className={`segment-pill ${selected === key ? 'active' : ''}`}
            onClick={() => onSelect(selected === key ? null : key)}
          >
            <span className="segment-pill-label">{meta.label}</span>
            <span className="segment-pill-count">{fmtNum(key === 'new_donors' ? seg.available : seg.available)}</span>
            <span className="segment-pill-ret">{ret != null ? fmtPct(ret) : 'acquired'}</span>
          </button>
        )
      })}
    </div>
  )
}

// ── Segment Detail Panel ──────────────────────────────────────────────────────

function SegmentPanel({ segKey, metrics }) {
  const seg = metrics?.segments?.[segKey]
  if (!seg) return null
  const meta = SEGMENT_META[segKey]

  const rows = [
    { label: 'Available Donors', value: fmtNum(seg.available) },
    { label: 'Active Donors', value: fmtNum(seg.active) },
    { label: '% Donors Giving', value: segKey === 'new_donors' ? 'N/A' : fmtPct(seg.pct_donors_giving) },
    { label: 'Gifts', value: fmtNum(seg.gifts) },
    { label: 'Gifts / Active Donor', value: seg.gifts_per_active_donor?.toFixed(2) ?? '—' },
    { label: 'Revenue', value: fmt(seg.revenue) },
    { label: 'Average Gift', value: fmt(seg.average_gift) },
    { label: 'Revenue / Active', value: fmt(seg.revenue_per_active) },
    { label: 'Revenue / Available', value: fmt(seg.revenue_per_available) },
  ]
  if (seg.conversion_pct != null) {
    rows.splice(2, 0, { label: 'Conversion % (2+ gifts)', value: fmtPct(seg.conversion_pct) })
  }

  return (
    <div className="card animate-in" style={{ borderTop: `3px solid ${meta.color}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <p className="label" style={{ marginBottom: '0.2rem' }}>Segment Detail</p>
          <h3 className="display-md" style={{ color: meta.color }}>{meta.label}</h3>
        </div>
        {segKey !== 'new_donors' && (
          <div style={{ textAlign: 'right' }}>
            <p className="label" style={{ marginBottom: '0.2rem' }}>Retention</p>
            <p style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', fontWeight: 600, color: meta.color, lineHeight: 1 }}>
              {fmtPct(seg.pct_donors_giving)}
            </p>
          </div>
        )}
      </div>
      <div style={{ height: 6, background: 'var(--cream-dark)', borderRadius: 99, marginBottom: '1.25rem', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${Math.min(seg.pct_donors_giving ?? 100, 100)}%`, background: `linear-gradient(90deg, ${meta.color}, ${meta.color}88)`, borderRadius: 99, transition: 'width 800ms cubic-bezier(0.4,0,0.2,1)' }} />
      </div>
      <table className="dhc-table">
        <tbody>
          {rows.map(({ label, value }) => (
            <tr key={label}>
              <td>{label}</td>
              <td className="num highlight">{value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Growth Dynamics Panel ─────────────────────────────────────────────────────

function GrowthDynamicsPanel({ gd, year }) {
  if (!gd) return null
  const isWin = gd.win_vs_lapse === 'WIN'
  const net = gd.net_win_loss_revenue

  return (
    <div className="card animate-in">
      <div className="section-header">
        <h3 className="section-title">Growth Dynamics</h3>
        <span className={`badge ${isWin ? 'badge-win' : 'badge-lapse'}`}>
          {isWin ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
          {gd.win_vs_lapse}
        </span>
      </div>

      {/* Visual bar */}
      <div style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', height: 40, borderRadius: 'var(--radius-md)', overflow: 'hidden', gap: 2 }}>
          {[
            { label: 'Retained', val: gd.retained_donors.current_year_revenue, color: 'var(--teal-600)' },
            { label: 'New + Reactive', val: gd.total_added.revenue, color: 'var(--amber-500)' },
            { label: 'Lapsed', val: -(gd.lapsed_donors.prior_year_revenue_lost), color: '#ef4444' },
          ].map(({ label, val, color }) => (
            <div key={label} title={`${label}: ${fmt(Math.abs(val))}`}
              style={{ flex: Math.abs(val), background: color, display: 'flex', alignItems: 'center', justifyContent: 'center', minWidth: 4 }}
            />
          ))}
        </div>
        <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
          {[
            { label: 'Retained', color: 'var(--teal-600)' },
            { label: 'New + Reactivated', color: 'var(--amber-500)' },
            { label: 'Lapsed', color: '#ef4444' },
          ].map(({ label, color }) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.72rem', color: 'var(--stone-400)' }}>
              <div style={{ width: 8, height: 8, borderRadius: 2, background: color }} />
              {label}
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: '0.75rem' }}>
        {[
          { label: 'Retained Donors', count: gd.retained_donors.count, rev: gd.retained_donors.current_year_revenue, color: 'var(--teal-50)' },
          { label: 'Upgraded', count: gd.retained_donors.upgraded_count, rev: gd.retained_donors.upgraded_revenue_gain, color: 'var(--teal-50)', prefix: '+' },
          { label: 'Downgraded', count: gd.retained_donors.downgraded_count, rev: Math.abs(gd.retained_donors.downgraded_revenue_loss), color: '#fef2f2', prefix: '-' },
          { label: 'Lapsed', count: gd.lapsed_donors.count, rev: gd.lapsed_donors.prior_year_revenue_lost, color: '#fef2f2', prefix: '-' },
          { label: 'New Acquired', count: gd.new_donors_acquired.count, rev: gd.new_donors_acquired.revenue, color: 'var(--amber-50)', prefix: '+' },
          { label: 'Reactivated', count: gd.reactivated_donors.count, rev: gd.reactivated_donors.revenue, color: 'var(--amber-50)', prefix: '+' },
        ].map(({ label, count, rev, color, prefix }) => (
          <div key={label} style={{ padding: '0.75rem', background: color, borderRadius: 'var(--radius-md)' }}>
            <p className="label" style={{ marginBottom: '0.25rem' }}>{label}</p>
            <p style={{ fontFamily: 'var(--font-display)', fontSize: '1.1rem', fontWeight: 600, color: 'var(--slate-900)' }}>{fmtNum(count)}</p>
            <p style={{ fontSize: '0.75rem', color: 'var(--stone-400)' }}>{prefix}{fmt(rev)}</p>
          </div>
        ))}
      </div>

      <div style={{ marginTop: '1rem', padding: '1rem', background: isWin ? 'var(--teal-50)' : '#fef2f2', borderRadius: 'var(--radius-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <p style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--slate-700)' }}>Net Revenue Change FY{year}</p>
        <p style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 600, color: isWin ? 'var(--teal-800)' : '#dc2626' }}>
          {net >= 0 ? '+' : ''}{fmt(net)}
        </p>
      </div>
      {(gd.retained_donors?.coverage_ratio || gd.coverage_ratio_acquisition) && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginTop: '0.75rem' }}>
          {gd.retained_donors?.coverage_ratio && (
            <div style={{ padding: '0.65rem', background: 'var(--teal-50)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
              <p className="label" style={{ marginBottom: '0.2rem', fontSize: '0.58rem' }}>Coverage Ratio (Upgrade/Downgrade)</p>
              <p style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', fontWeight: 600, color: 'var(--teal-800)' }}>{(gd.retained_donors.coverage_ratio * 100).toFixed(0)}%</p>
            </div>
          )}
          {gd.coverage_ratio_acquisition && (
            <div style={{ padding: '0.65rem', background: 'var(--amber-50)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
              <p className="label" style={{ marginBottom: '0.2rem', fontSize: '0.58rem' }}>Coverage Ratio (New+Reactive/Lapsed)</p>
              <p style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', fontWeight: 600, color: 'var(--amber-600)' }}>{(gd.coverage_ratio_acquisition * 100).toFixed(0)}%</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── LTV Panel ─────────────────────────────────────────────────────────────────

function LTVPanel({ ltv }) {
  if (!ltv || ltv.error) return null
  const data = ltv.projections?.map(p => ({
    year: `Year ${p.year}`,
    revenue: p.cumulative_revenue_per_donor,
    roi: p.lt_roi,
  })) ?? []

  return (
    <div className="card animate-in">
      <div className="section-header">
        <h3 className="section-title">Long-Term Value</h3>
        <span className="badge badge-amber">New Donor Cohort</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '0.75rem', marginBottom: '1.5rem' }}>
        {[
          { label: 'New Donors', value: fmtNum(ltv.new_donor_count) },
          { label: 'Yr 1 Rev / Donor', value: fmt(ltv.first_year_revenue_per_donor) },
          { label: '5-Year LTV', value: fmt(ltv.five_year_ltv) },
        ].map(({ label, value }) => (
          <div key={label} style={{ textAlign: 'center', padding: '0.75rem', background: 'var(--amber-50)', borderRadius: 'var(--radius-md)', border: '1px solid var(--amber-100)' }}>
            <p className="label" style={{ marginBottom: '0.25rem' }}>{label}</p>
            <p style={{ fontFamily: 'var(--font-display)', fontSize: '1.3rem', fontWeight: 600, color: 'var(--amber-600)' }}>{value}</p>
          </div>
        ))}
      </div>
      <div className="chart-container" style={{ height: 180 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
            <defs>
              <linearGradient id="ltvGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#E8924A" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#E8924A" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--cream-dark)" />
            <XAxis dataKey="year" tick={{ fontSize: 11, fill: 'var(--stone-400)', fontFamily: 'var(--font-body)' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: 'var(--stone-400)', fontFamily: 'var(--font-body)' }} tickFormatter={v => `$${v}`} axisLine={false} tickLine={false} />
            <Tooltip formatter={v => [`$${v.toFixed(2)}`, 'Cumulative Rev/Donor']} contentStyle={{ fontFamily: 'var(--font-body)', fontSize: 12, borderRadius: 8, border: '1px solid var(--cream-dark)' }} />
            <Area type="monotone" dataKey="revenue" stroke="var(--amber-500)" strokeWidth={2} fill="url(#ltvGrad)" dot={{ fill: 'var(--amber-500)', r: 4, strokeWidth: 0 }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// ── Roadmap Panel ─────────────────────────────────────────────────────────────

function RoadmapPanel({ clientName, year, metrics }) {
  const [roadmap, setRoadmap] = useState(null)
  const [loading, setLoading] = useState(false)
  const [tone, setTone] = useState('strategic')

  const generate = async () => {
    setLoading(true)
    try {
      const res = await apiCall('/api/roadmap', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ metrics: metrics || {}, segment: 'all', tone })
      })
      const data = await res.json()
      setRoadmap(data.roadmap)
    } catch (e) {
      setRoadmap('Error generating roadmap. Check that ANTHROPIC_API_KEY is set.')
    }
    setLoading(false)
  }

  // Simple markdown renderer
  const renderMd = (text) => {
    const html = text
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
      .replace(/^### (.+)$/gm, '<h3>$1</h3>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/^- (.+)$/gm, '<li>$1</li>')
      .replace(/(<li>.*<\/li>\n?)+/g, m => `<ul>${m}</ul>`)
      .replace(/\n\n/g, '</p><p>')
      .replace(/^(?!<[hul])/gm, '')
    return `<p>${html}</p>`
  }

  return (
    <div className="card animate-in">
      <div className="section-header">
        <h3 className="section-title">Donor Road Map</h3>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <select
            value={tone}
            onChange={e => setTone(e.target.value)}
            style={{ padding: '0.3rem 0.6rem', border: '1.5px solid var(--cream-dark)', borderRadius: 'var(--radius-sm)', fontFamily: 'var(--font-body)', fontSize: '0.78rem', color: 'var(--slate-700)', background: 'white', outline: 'none' }}
          >
            <option value="strategic">Strategic</option>
            <option value="conversational">Conversational</option>
            <option value="executive">Executive</option>
          </select>
          <button className="btn btn-amber btn-sm" onClick={generate} disabled={loading}>
            {loading ? <><RefreshCw size={12} style={{ animation: 'spin 1s linear infinite' }} /> Generating…</> : <><Sparkles size={12} /> Generate</>}
          </button>
        </div>
      </div>

      {!roadmap && !loading && (
        <div className="empty-state">
          <div className="empty-icon"><Map size={24} /></div>
          <p style={{ fontWeight: 500 }}>Generate AI-powered recommendations</p>
          <p style={{ fontSize: '0.82rem' }}>
            StoryCause intelligence will analyze each lifecycle segment and
            recommend engagement strategies grounded in your data.
          </p>
        </div>
      )}
      {loading && (
        <div className="empty-state">
          <div style={{ width: 40, height: 40, border: '3px solid var(--cream-dark)', borderTopColor: 'var(--teal-600)', borderRadius: '50%', animation: 'spin 800ms linear infinite' }} />
          <p style={{ fontSize: '0.85rem', color: 'var(--stone-400)' }}>Analyzing {clientName}'s donor file…</p>
        </div>
      )}
      {roadmap && (
        <div className="roadmap-content" dangerouslySetInnerHTML={{ __html: renderMd(roadmap) }} />
      )}
    </div>
  )
}

// ── Revenue Bar Chart ─────────────────────────────────────────────────────────

function RevenueBySegment({ metrics }) {
  if (!metrics?.segments) return null
  const data = SEGMENT_ORDER.map(key => ({
    name: SEGMENT_META[key]?.label ?? key,
    revenue: metrics.segments[key]?.revenue ?? 0,
    active: metrics.segments[key]?.active ?? 0,
    color: SEGMENT_META[key]?.color ?? '#ccc',
  })).filter(d => d.revenue > 0)

  return (
    <div className="card animate-in">
      <div className="section-header">
        <h3 className="section-title">Revenue by Segment</h3>
      </div>
      <div className="chart-container" style={{ height: 220 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 20 }} barSize={32}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--cream-dark)" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'var(--stone-400)', fontFamily: 'var(--font-body)' }} axisLine={false} tickLine={false} angle={-15} textAnchor="end" />
            <YAxis tickFormatter={v => v >= 1000000 ? `$${(v/1000000).toFixed(1)}M` : v >= 1000 ? `$${(v/1000).toFixed(0)}K` : `$${v}`} tick={{ fontSize: 10, fill: 'var(--stone-400)', fontFamily: 'var(--font-body)' }} axisLine={false} tickLine={false} />
            <Tooltip formatter={v => [fmt(v), 'Revenue']} contentStyle={{ fontFamily: 'var(--font-body)', fontSize: 12, borderRadius: 8, border: '1px solid var(--cream-dark)' }} />
            <Bar dataKey="revenue" radius={[4, 4, 0, 0]}>
              {data.map((d, i) => <Cell key={i} fill={d.color} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// ── Full Metrics Table ────────────────────────────────────────────────────────

function FullMetricsTable({ metrics }) {
  if (!metrics?.segments) return null
  return (
    <div className="card animate-in" style={{ overflowX: 'auto' }}>
      <div className="section-header">
        <h3 className="section-title">Lifecycle Metrics — FY{metrics.analysis_year}</h3>
      </div>
      <table className="dhc-table" style={{ minWidth: 700 }}>
        <thead>
          <tr>
            <th>Segment</th>
            <th className="num">Available</th>
            <th className="num">Active</th>
            <th className="num">Retention</th>
            <th className="num">Revenue</th>
            <th className="num">Avg Gift</th>
            <th className="num">Rev/Active</th>
          </tr>
        </thead>
        <tbody>
          {SEGMENT_ORDER.map(key => {
            const seg = metrics.segments[key]
            if (!seg) return null
            return (
              <tr key={key}>
                <td style={{ fontWeight: 500, color: SEGMENT_META[key]?.color }}>
                  {SEGMENT_META[key]?.emoji} {SEGMENT_META[key]?.label}
                </td>
                <td className="num">{fmtNum(seg.available)}</td>
                <td className="num">{fmtNum(seg.active)}</td>
                <td className="num">{key === 'new_donors' ? <span className="muted">—</span> : fmtPct(seg.pct_donors_giving)}</td>
                <td className="num highlight">{fmt(seg.revenue)}</td>
                <td className="num">{fmt(seg.average_gift)}</td>
                <td className="num">{fmt(seg.revenue_per_active)}</td>
              </tr>
            )
          })}
          <tr style={{ fontWeight: 700, borderTop: '2px solid var(--cream-dark)' }}>
            <td style={{ fontWeight: 700 }}>Totals</td>
            <td className="num">{fmtNum(metrics.totals.available_donors)}</td>
            <td className="num">{fmtNum(metrics.totals.active_donors)}</td>
            <td className="num">{fmtPct(metrics.totals.overall_retention_pct)}</td>
            <td className="num highlight">{fmt(metrics.totals.total_revenue)}</td>
            <td className="num">{fmt(metrics.totals.average_gift)}</td>
            <td className="num">{fmt(metrics.totals.revenue_per_active)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

// ── Auth Gate ─────────────────────────────────────────────────────────────────

function AuthGate({ onAuth }) {
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [error, setError] = useState(null)
  const [checking, setChecking] = useState(false)

  const attempt = async () => {
    setChecking(true)
    setError(null)
    sessionStorage.setItem('dhc_key', password)
    try {
      const res = await apiCall('/api/health')
      if (res.ok) {
        onAuth(password)
      } else {
        sessionStorage.removeItem('dhc_key')
        setError('Incorrect password. Try again.')
      }
    } catch {
      setError('Could not connect to server.')
    }
    setChecking(false)
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--cream)' }}>
      <div className="card animate-in" style={{ maxWidth: 400, width: '100%', textAlign: 'center' }}>
        <div style={{ width: 56, height: 56, borderRadius: 16, background: 'var(--teal-800)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.25rem' }}>
          <Lock size={24} color="white" />
        </div>
        <p className="label" style={{ marginBottom: '0.3rem', color: 'var(--teal-600)' }}>StoryCause</p>
        <h2 className="display-md" style={{ marginBottom: '0.5rem' }}>Donor Health Check™</h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--stone-400)', marginBottom: '1.5rem' }}>
          Enter your dashboard password to continue.
        </p>
        <div style={{ position: 'relative', marginBottom: '1rem' }}>
          <input
            type={show ? 'text' : 'password'}
            value={password}
            onChange={e => setPassword(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && attempt()}
            placeholder="Dashboard password"
            style={{ width: '100%', padding: '0.65rem 2.5rem 0.65rem 0.9rem', border: `1.5px solid ${error ? '#fca5a5' : 'var(--cream-dark)'}`, borderRadius: 'var(--radius-md)', fontFamily: 'var(--font-body)', fontSize: '0.9rem', outline: 'none', background: 'white' }}
          />
          <button onClick={() => setShow(s => !s)}
            style={{ position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--stone-400)', padding: 0 }}>
            {show ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
        {error && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.6rem 0.75rem', background: '#fee2e2', borderRadius: 'var(--radius-sm)', marginBottom: '1rem', fontSize: '0.82rem', color: '#991b1b' }}>
            <AlertCircle size={14} /> {error}
          </div>
        )}
        <button className="btn btn-primary" onClick={attempt} disabled={!password || checking}
          style={{ width: '100%', justifyContent: 'center' }}>
          {checking ? <><RefreshCw size={14} style={{ animation: 'spin 1s linear infinite' }} /> Checking…</> : 'Continue →'}
        </button>
      </div>
    </div>
  )
}

// ── Session Warning Banner ────────────────────────────────────────────────────

function SessionWarning({ onDismiss }) {
  return (
    <div style={{ background: 'var(--amber-100)', border: '1px solid var(--amber-400)', borderRadius: 'var(--radius-md)', padding: '0.75rem 1rem', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
      <AlertCircle size={16} color="var(--amber-600)" style={{ flexShrink: 0 }} />
      <div style={{ flex: 1, fontSize: '0.83rem', color: 'var(--amber-600)' }}>
        <strong>Session data was lost</strong> — the server restarted since your last analysis.
        Please upload your files and run the analysis again.
      </div>
      <button onClick={onDismiss}
        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--amber-600)', fontSize: '1rem', lineHeight: 1, padding: '0 0.25rem' }}>×</button>
    </div>
  )
}

// ── SOW Panel ─────────────────────────────────────────────────────────────────

function SOWPanel() {
  const [prospect, setProspect] = useState('')
  const [contact, setContact] = useState('')
  const [ohpDone, setOhpDone] = useState(true)
  const [years, setYears] = useState(10)
  const [sow, setSow] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const generate = async () => {
    if (!prospect.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await apiCall('/api/sow', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prospect_name: prospect,
          ohp_completed: ohpDone,
          years_requested: years,
          ...(contact ? { contact_name: contact } : {}),
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Generation failed')
      setSow(data.sow)
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  const download = () => {
    const safe = prospect.replace(/[^a-zA-Z0-9 _-]/g, '_')
    const blob = new Blob([sow], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `StoryCause_SOW_${safe}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  const renderMd = (text) => text
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, m => `<ul>${m}</ul>`)
    .replace(/\n\n/g, '</p><p>')

  return (
    <div>
      <div className="card animate-in" style={{ marginBottom: '1.25rem' }}>
        <div className="section-header">
          <h3 className="section-title">Generate Statement of Work</h3>
        </div>
        <div style={{ display: 'grid', gap: '0.75rem' }}>
          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-500)', display: 'block', marginBottom: '0.35rem', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
              Prospect Institution <span style={{ color: 'var(--amber-500)' }}>*</span>
            </label>
            <input value={prospect} onChange={e => setProspect(e.target.value)}
              placeholder="e.g. Missouri Western State University"
              style={{ width: '100%', padding: '0.6rem 0.85rem', border: '1.5px solid var(--cream-dark)', borderRadius: 'var(--radius-md)', fontFamily: 'var(--font-body)', fontSize: '0.88rem', outline: 'none' }}
              onFocus={e => e.target.style.borderColor = 'var(--teal-600)'}
              onBlur={e => e.target.style.borderColor = 'var(--cream-dark)'}
            />
          </div>
          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-500)', display: 'block', marginBottom: '0.35rem', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
              Primary Contact <span style={{ color: 'var(--stone-400)', fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>— optional</span>
            </label>
            <input value={contact} onChange={e => setContact(e.target.value)}
              placeholder="e.g. Dr. Sarah Johnson, VP of Advancement"
              style={{ width: '100%', padding: '0.6rem 0.85rem', border: '1.5px solid var(--cream-dark)', borderRadius: 'var(--radius-md)', fontFamily: 'var(--font-body)', fontSize: '0.88rem', outline: 'none' }}
              onFocus={e => e.target.style.borderColor = 'var(--teal-600)'}
              onBlur={e => e.target.style.borderColor = 'var(--cream-dark)'}
            />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-500)', display: 'block', marginBottom: '0.35rem', letterSpacing: '0.04em', textTransform: 'uppercase' }}>OHP Status</label>
              <select value={ohpDone} onChange={e => setOhpDone(e.target.value === 'true')}
                style={{ width: '100%', padding: '0.6rem 0.85rem', border: '1.5px solid var(--cream-dark)', borderRadius: 'var(--radius-md)', fontFamily: 'var(--font-body)', fontSize: '0.88rem', outline: 'none', background: 'white' }}>
                <option value="true">OHP Already Completed</option>
                <option value="false">Prospective Partner</option>
              </select>
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-500)', display: 'block', marginBottom: '0.35rem', letterSpacing: '0.04em', textTransform: 'uppercase' }}>Years of Data</label>
              <select value={years} onChange={e => setYears(Number(e.target.value))}
                style={{ width: '100%', padding: '0.6rem 0.85rem', border: '1.5px solid var(--cream-dark)', borderRadius: 'var(--radius-md)', fontFamily: 'var(--font-body)', fontSize: '0.88rem', outline: 'none', background: 'white' }}>
                {[5, 7, 10, 12, 15].map(y => <option key={y} value={y}>{y} years</option>)}
              </select>
            </div>
          </div>
        </div>
        {error && (
          <div style={{ display: 'flex', gap: '0.5rem', padding: '0.6rem 0.75rem', background: '#fee2e2', borderRadius: 'var(--radius-sm)', marginTop: '0.75rem', fontSize: '0.82rem', color: '#991b1b' }}>
            <AlertCircle size={14} style={{ flexShrink: 0, marginTop: 1 }} /> {error}
          </div>
        )}
        <button className="btn btn-amber" onClick={generate} disabled={!prospect.trim() || loading}
          style={{ width: '100%', justifyContent: 'center', marginTop: '1rem' }}>
          {loading ? <><RefreshCw size={14} style={{ animation: 'spin 1s linear infinite' }} /> Generating SOW…</> : <><FileText size={14} /> Generate SOW</>}
        </button>
      </div>

      {sow && (
        <div className="card animate-in">
          <div className="section-header">
            <h3 className="section-title">Statement of Work — {prospect}</h3>
            <button className="btn btn-ghost btn-sm" onClick={download}>
              <Download size={13} /> Download .md
            </button>
          </div>
          <div className="roadmap-content" dangerouslySetInnerHTML={{ __html: `<p>${renderMd(sow)}</p>` }} />
        </div>
      )}
    </div>
  )
}

// ── Dashboard Screen ──────────────────────────────────────────────────────────

function DashboardScreen({ data, onReset, sessionWarning, onDismissWarning }) {
  const [activeTab, setActiveTab] = useState('overview')
  const [selectedSegment, setSelectedSegment] = useState(null)
  const [downloading, setDownloading] = useState(false)
  const { metrics, growth_dynamics: gd, ltv, file_growth: fg, large_gift: lg, summary_kpis: kpis } = data
  const totals = metrics?.totals ?? {}
  const year = data.analysis_year

  const tabs = [
    { id: 'overview',   label: 'Overview' },
    { id: 'lifecycle',  label: 'Lifecycle' },
    { id: 'dynamics',   label: 'Growth' },
    { id: 'roadmap',    label: 'Road Map' },
    { id: 'sow',        label: 'SOW' },
  ]

  // Download report from pre-computed data
  const handleDownload = async () => {
    setDownloading(true)
    try {
      const stored = JSON.parse(sessionStorage.getItem('dhc_analysis') || '{}')
      const cn = encodeURIComponent(stored.client_name || 'Client')
      const yr = stored.analysis_year || new Date().getFullYear()
      const res = await apiCall(`/api/report/download?client_name=${cn}&analysis_year=${yr}`)
      if (!res.ok) throw new Error('Download failed')
      const blob = await res.blob()
      const cd = res.headers.get('Content-Disposition') || ''
      const match = cd.match(/filename="(.+)"/)
      const filename = match ? match[1] : `StoryCause_DHC_FY${year}.md`
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = filename; a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      alert('Download failed: ' + e.message)
    }
    setDownloading(false)
  }

  return (
    <div>
      {sessionWarning && <SessionWarning onDismiss={onDismissWarning} />}

      {/* Tab nav */}
      <div style={{ display: 'flex', gap: '0.25rem', marginBottom: '1.75rem', borderBottom: '1px solid var(--cream-dark)', paddingBottom: '0' }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            style={{ padding: '0.6rem 1.1rem', border: 'none', background: 'transparent', cursor: 'pointer', fontFamily: 'var(--font-body)', fontSize: '0.85rem', fontWeight: activeTab === t.id ? 600 : 400, color: activeTab === t.id ? 'var(--teal-800)' : 'var(--stone-400)', borderBottom: `2px solid ${activeTab === t.id ? 'var(--teal-800)' : 'transparent'}`, marginBottom: -1, transition: 'var(--transition-fast)', letterSpacing: '0.01em' }}>
            {t.label}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', paddingBottom: '0.5rem' }}>
          <button className="btn btn-ghost btn-sm" onClick={handleDownload} disabled={downloading}>
            {downloading
              ? <><RefreshCw size={12} style={{ animation: 'spin 1s linear infinite' }} /> Downloading…</>
              : <><Download size={12} /> Report</>}
          </button>
          <button className="btn btn-ghost btn-sm" onClick={onReset}>
            <Upload size={12} /> New Analysis
          </button>
        </div>
      </div>

      {/* Overview */}
      {activeTab === 'overview' && (
        <>
          {/* Page header */}
          <div className="animate-in" style={{ marginBottom: '1.75rem' }}>
            <p className="label" style={{ marginBottom: '0.3rem', color: 'var(--teal-600)' }}>
              Donor Health Check™ · FY{year}
            </p>
            <h1 className="display-lg" style={{ color: 'var(--slate-900)' }}>{data.client_name}</h1>
          </div>

          {/* KPI row */}
          <div className="metric-grid">
            <KPICard label="Active Donors" value={totals.active_donors} icon={Users} delay={1} />
            <KPICard label="General Revenue" value={kpis?.general_revenue ?? totals.total_revenue} prefix="$" icon={DollarSign} delay={2} decimals={0} />
            <KPICard label="Overall Retention" value={kpis?.overall_retention_pct ?? totals.overall_retention_pct} suffix="%" icon={Heart} delay={3} decimals={1} />
            <KPICard label="Renewal (13–24 Mo)" value={kpis?.renewal_13_24_pct} suffix="%" icon={TrendingUp} delay={4} decimals={1} />
          </div>

          {/* File growth */}
          {fg && (
            <div className="card animate-in" style={{ marginBottom: '1.25rem' }}>
              <p className="label" style={{ marginBottom: '1rem' }}>Donor File Growth</p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.5rem', textAlign: 'center' }}>
                {[
                  { label: 'Active Last Year', value: fg.donors_active_last_year, color: 'var(--slate-300)' },
                  { label: 'New Acquired', value: fg.new_donors_acquired, color: 'var(--teal-600)' },
                  { label: 'Reactivated', value: fg.reactivated_donors, color: 'var(--amber-500)' },
                  { label: 'Retained', value: fg.retained_donors, color: 'var(--teal-800)' },
                  { label: 'Active This Year', value: fg.donors_active_this_year, color: 'var(--teal-800)' },
                ].map(({ label, value, color }) => (
                  <div key={label} style={{ padding: '0.75rem 0.5rem' }}>
                    <p className="label" style={{ marginBottom: '0.3rem', fontSize: '0.6rem' }}>{label}</p>
                    <p style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', fontWeight: 600, color, lineHeight: 1 }}>{fmtNum(value)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Large Gift Donors ($10k+) — per DHC methodology, tracked separately from lifecycle */}
          {lg && (
            <div className="card animate-in" style={{ marginBottom: '1.25rem', borderTop: '3px solid var(--amber-500)' }}>
              <p className="label" style={{ marginBottom: '1rem' }}>Revenue Summary</p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.75rem' }}>
                {[
                  { label: 'General Revenue', value: kpis?.general_revenue, color: 'var(--teal-800)' },
                  { label: `Large Gift ($${(lg.threshold/1000).toFixed(0)}k+)`, value: lg.revenue, color: 'var(--amber-600)' },
                  { label: 'Total Revenue', value: lg.total_revenue, color: 'var(--teal-800)', bold: true },
                  { label: 'Large Gift %', value: lg.pct_of_total, suffix: '%', color: 'var(--amber-600)' },
                ].map(({ label, value, color, bold, suffix }) => (
                  <div key={label} style={{ textAlign: 'center', padding: '0.75rem', background: 'var(--cream)', borderRadius: 'var(--radius-md)' }}>
                    <p className="label" style={{ marginBottom: '0.3rem', fontSize: '0.58rem' }}>{label}</p>
                    <p style={{ fontFamily: 'var(--font-display)', fontSize: bold ? '1.5rem' : '1.3rem', fontWeight: bold ? 700 : 600, color, lineHeight: 1 }}>
                      {suffix ? `${value?.toFixed(1)}${suffix}` : `$${value?.toLocaleString('en-US', { maximumFractionDigits: 0 }) ?? '—'}`}
                    </p>
                    {label === `Large Gift ($${(lg.threshold/1000).toFixed(0)}k+)` && (
                      <p style={{ fontSize: '0.65rem', color: 'var(--stone-400)', marginTop: 2 }}>{lg.donor_count?.toLocaleString()} donors</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="grid-2" style={{ marginBottom: '1.25rem' }}>
            <RevenueBySegment metrics={metrics} />
            {gd && <GrowthDynamicsPanel gd={gd} year={year} />}
          </div>
          {ltv && <LTVPanel ltv={ltv} />}
        </>
      )}

      {/* Lifecycle */}
      {activeTab === 'lifecycle' && (
        <>
          <div className="animate-in" style={{ marginBottom: '1.5rem' }}>
            <p className="label" style={{ marginBottom: '0.3rem', color: 'var(--teal-600)' }}>Lifecycle Explorer</p>
            <h2 className="display-md">Select a segment to explore</h2>
          </div>
          <SegmentArc metrics={metrics} selected={selectedSegment} onSelect={setSelectedSegment} />
          {selectedSegment
            ? <SegmentPanel segKey={selectedSegment} metrics={metrics} />
            : <FullMetricsTable metrics={metrics} />}
        </>
      )}

      {/* Growth */}
      {activeTab === 'dynamics' && (
        <>
          <div className="animate-in" style={{ marginBottom: '1.5rem' }}>
            <p className="label" style={{ marginBottom: '0.3rem', color: 'var(--teal-600)' }}>Growth Dynamics</p>
            <h2 className="display-md">Win vs. Lapse Analysis</h2>
          </div>
          <div style={{ display: 'grid', gap: '1.25rem' }}>
            {gd && <GrowthDynamicsPanel gd={gd} year={year} />}
            {ltv && <LTVPanel ltv={ltv} />}
          </div>
        </>
      )}

      {/* Roadmap */}
      {activeTab === 'roadmap' && (
        <>
          <div className="animate-in" style={{ marginBottom: '1.5rem' }}>
            <p className="label" style={{ marginBottom: '0.3rem', color: 'var(--teal-600)' }}>Donor Road Map</p>
            <h2 className="display-md">AI-powered segment recommendations</h2>
          </div>
          <RoadmapPanel clientName={data.client_name} year={year} metrics={metrics} />
        </>
      )}

      {/* SOW */}
      {activeTab === 'sow' && (
        <>
          <div className="animate-in" style={{ marginBottom: '1.5rem' }}>
            <p className="label" style={{ marginBottom: '0.3rem', color: 'var(--teal-600)' }}>Statement of Work</p>
            <h2 className="display-md">Generate a client SOW document</h2>
          </div>
          <SOWPanel />
        </>
      )}
    </div>
  )
}

// ── App Root ──────────────────────────────────────────────────────────────────

export default function App() {
  const [authRequired, setAuthRequired] = useState(false)
  const [authed, setAuthed]             = useState(false)
  const [analysisData, setAnalysisData] = useState(null)
  const [booting, setBooting]           = useState(true)

  // On mount: check if password protection is active
  useEffect(() => {
    const init = async () => {
      try {
        const res = await apiCall('/api/health')
        if (res.status === 401) {
          setAuthRequired(true)
          setBooting(false)
          return
        }
        setAuthed(true)
      } catch {
        setAuthed(true)
      }
      setBooting(false)
    }
    init()
  }, [])

  const handleAuth = (key) => {
    sessionStorage.setItem('dhc_key', key)
    setAuthed(true)
    setAuthRequired(false)
    setBooting(false)
  }

  const handleComplete = (data) => {
    setAnalysisData(data)
    sessionStorage.setItem('dhc_analysis', JSON.stringify({
      client_name: data.client_name,
      analysis_year: data.analysis_year,
    }))
  }

  const handleReset = () => {
    setAnalysisData(null)
  }

  // ── Render ──

  if (booting) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--cream)' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ width: 40, height: 40, border: '3px solid var(--teal-200)', borderTopColor: 'var(--teal-800)', borderRadius: '50%', animation: 'spin 700ms linear infinite', margin: '0 auto 1rem' }} />
          <p style={{ fontSize: '0.82rem', color: 'var(--stone-400)' }}>Loading StoryCause DHC…</p>
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    )
  }

  if (authRequired && !authed) {
    return (
      <>
        <AuthGate onAuth={handleAuth} />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </>
    )
  }

  return (
    <div className="app-shell">
      <nav className="topnav">
        <a className="nav-brand" href="https://www.storycause.com" target="_blank" rel="noopener noreferrer">
          <div className="nav-brand-mark">S</div>
          <div className="nav-brand-text">
            <span className="nav-brand-name">StoryCause</span>
            <span className="nav-brand-sub">Donor Health Check™</span>
          </div>
        </a>
        {analysisData && (
          <div className="nav-tabs">
            <span style={{ fontSize: '0.72rem', color: 'var(--teal-200)' }}>
              FY{analysisData.analysis_year}
            </span>
          </div>
        )}
        {analysisData?.client_name && (
          <span className="nav-client-badge">{analysisData.client_name}</span>
        )}
      </nav>

      <main className="main-content">
        {!analysisData ? (
          <>
            {sessionWarning && (
              <SessionWarning onDismiss={() => setSessionWarning(false)} />
            )}
            <UploadScreen onAnalysisComplete={handleComplete} />
          </>
        ) : (
          <DashboardScreen
            data={analysisData}
            onReset={handleReset}
            sessionWarning={false}
            onDismissWarning={() => {}}
          />
        )}
      </main>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
