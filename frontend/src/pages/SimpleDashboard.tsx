import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import SimpleLayout from '../components/SimpleLayout'
import Icon from '../components/Icon'
import { Skeleton } from '../components/Skeleton'
import Breadcrumbs from '../components/Breadcrumbs'
import Button from '../components/Button'
import { useAuth } from '../contexts/AuthContext'
import { analyticsService, DashboardStats as Analytics } from '../services/analyticsService'
import { callingService, CallLog } from '../services/callingService'

const formatRelative = (iso: string) => {
  const d = new Date(iso)
  const diff = (Date.now() - d.getTime()) / 1000
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)} h ago`
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

const SimpleDashboard: React.FC = () => {
  const navigate = useNavigate()
  const { user, can } = useAuth()
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [calls, setCalls] = useState<CallLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      setError(false)
      try {
        const [a, c] = await Promise.all([
          analyticsService.getDashboardStats().catch((e) => {
            console.warn('analytics failed', e)
            return null
          }),
          callingService.getCallLogs().catch(() => [] as CallLog[]),
        ])
        if (cancelled) return
        if (!a) setError(true)
        setAnalytics(a)
        setCalls(c.slice(0, 6))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  const greeting = (() => {
    const h = new Date().getHours()
    if (h < 12) return 'Good morning'
    if (h < 17) return 'Good afternoon'
    return 'Good evening'
  })()

  const firstName = (user?.first_name || user?.email?.split('@')[0] || 'there').split('.')[0]
  const displayName = firstName.charAt(0).toUpperCase() + firstName.slice(1)

  const cards = analytics
    ? [
        {
          label: 'Active doctors',
          value: analytics.doctors.length,
          icon: 'stethoscope' as const,
          tint: 'emerald' as const,
        },
        {
          label: 'Appointments',
          value: analytics.appointments.total,
          icon: 'calendar-check' as const,
          tint: 'rose' as const,
          sub: `${analytics.appointments.confirmed} confirmed · ${analytics.appointments.completed} done`,
        },
        {
          label: 'Available slots',
          value: analytics.slots.available,
          icon: 'clock' as const,
          tint: 'amber' as const,
          sub: `${analytics.slots.utilization_rate.toFixed(0)}% utilization`,
        },
        {
          label: 'Calls placed',
          value: analytics.calls.total,
          icon: 'phone' as const,
          tint: 'indigo' as const,
          sub: `${analytics.calls.success_rate.toFixed(0)}% success rate`,
        },
      ]
    : []

  // Build dynamic activity feed from real call logs
  const activity = calls.map((c) => ({
    title:
      c.outcome === 'COMPLETED' || c.outcome === 'ANSWERED'
        ? `Call connected with ${c.patient_name}`
        : c.outcome === 'FAILED'
          ? `Call to ${c.patient_name} failed`
          : `Call to ${c.patient_name} — ${c.outcome.replace('_', ' ').toLowerCase()}`,
    meta: `${formatRelative(c.initiated_at)} · ${c.patient_phone} · ${c.call_type.replace('_', ' ').toLowerCase()}`,
    outcome: c.outcome,
  }))

  const shortcuts = [
    { label: 'New patient', icon: 'plus' as const, path: '/patients?new=1', show: can('manage_patients') },
    { label: 'Generate slots', icon: 'clock' as const, path: '/slots', show: can('manage_slots') },
    { label: 'Open calendar', icon: 'calendar' as const, path: '/calendar', show: true },
    { label: 'Call logs', icon: 'phone' as const, path: '/call-logs', show: true },
    { label: 'My profile', icon: 'user' as const, path: '/profile', show: true },
  ].filter((s) => s.show)

  // Real per-doctor utilization for the chart card
  const utilization = (analytics?.doctors || []).slice(0, 6).map((d) => ({
    label: d.doctor_name.length > 18 ? d.doctor_name.slice(0, 18) + '…' : d.doctor_name,
    pct: Math.round(d.utilization_rate),
  }))

  return (
    <SimpleLayout title="Dashboard">
      <Breadcrumbs />
      <div className="page-heading">
        <div>
          <h1>
            {greeting}, {displayName}
          </h1>
          <p>Here's what's happening across your practice today.</p>
        </div>
        {can('manage_patients') && (
          <Button
            variant="primary"
            onClick={() => navigate('/patients?new=1')}
            leftIcon={<Icon name="plus" size={16} />}
          >
            Add patient
          </Button>
        )}
      </div>

      {/* Stats */}
      <div className="stat-grid">
        {(loading ? Array.from({ length: 4 }) : cards).map((c: any, i) => (
          <div key={i} className="stat">
            <div className="stat-top">
              <span className="stat-label">
                {loading ? <Skeleton width={120} /> : c.label}
              </span>
              {!loading && (
                <span className={`stat-icon ${c.tint}`}>
                  <Icon name={c.icon} size={18} />
                </span>
              )}
            </div>
            <div className="stat-value">
              {loading ? <Skeleton width={80} height={32} /> : c.value}
            </div>
            <div>
              {loading ? (
                <Skeleton width={140} height={12} />
              ) : c.sub ? (
                <span className="stat-trend-note" style={{ marginLeft: 0 }}>
                  {c.sub}
                </span>
              ) : (
                <span className="stat-trend-note" style={{ marginLeft: 0 }}>
                  Last 30 days
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {error && (
        <div className="alert alert-warning" style={{ marginBottom: 20 }}>
          <Icon name="bolt" size={16} />
          <span>
            Live analytics couldn't be loaded. Showing partial data — make sure the analytics service is running.
          </span>
        </div>
      )}

      <div className="row">
        {/* Activity feed */}
        <div className="col-md-8">
          <div className="card">
            <div className="card-head">
              <div>
                <h5>Recent activity</h5>
                <p>Live events from your AI calling pipeline.</p>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => navigate('/call-logs')}
                rightIcon={<Icon name="chevron-right" size={14} />}
              >
                View all
              </Button>
            </div>
            <div className="card-body">
              {loading ? (
                <div style={{ display: 'grid', gap: 12 }}>
                  {Array.from({ length: 4 }).map((_, i) => (
                    <Skeleton key={i} height={36} />
                  ))}
                </div>
              ) : activity.length === 0 ? (
                <div className="empty-state" style={{ padding: 32 }}>
                  <Icon name="inbox" size={32} />
                  <p className="small-muted mt-2">
                    No activity yet — initiate a test call to see it here.
                  </p>
                </div>
              ) : (
                <div className="activity-list">
                  {activity.map((a, i) => (
                    <div key={i} className="activity-item">
                      <span
                        className="activity-dot"
                        style={{
                          background:
                            a.outcome === 'FAILED'
                              ? 'var(--danger)'
                              : a.outcome === 'COMPLETED' || a.outcome === 'ANSWERED'
                                ? 'var(--brand)'
                                : 'var(--warning)',
                        }}
                      />
                      <div className="activity-body">
                        <div className="activity-title">{a.title}</div>
                        <div className="activity-meta">{a.meta}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Utilization */}
          <div className="card mt-4">
            <div className="card-head">
              <div>
                <h5>Doctor utilization</h5>
                <p>Booked vs. total slots over the reporting window.</p>
              </div>
            </div>
            <div className="card-body">
              {loading ? (
                <div style={{ display: 'grid', gap: 10 }}>
                  {Array.from({ length: 4 }).map((_, i) => (
                    <Skeleton key={i} height={20} />
                  ))}
                </div>
              ) : utilization.length === 0 ? (
                <div className="empty-state" style={{ padding: 32 }}>
                  <Icon name="analytics" size={32} />
                  <p className="small-muted mt-2">
                    Utilization will appear once doctors release slots.
                  </p>
                </div>
              ) : (
                utilization.map((r) => (
                  <div key={r.label} className="chart-bar-row">
                    <div className="chart-bar-label">{r.label}</div>
                    <div className="chart-bar-track">
                      <div className="chart-bar-fill" style={{ width: `${r.pct}%` }} />
                    </div>
                    <div className="chart-bar-value">{r.pct}%</div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Quick actions */}
        <div className="col-md-4">
          <div className="card">
            <div className="card-head">
              <h5>Quick actions</h5>
            </div>
            <div className="card-body" style={{ display: 'grid', gap: 8 }}>
              {shortcuts.map((s) => (
                <button
                  key={s.label}
                  className="btn btn-secondary"
                  style={{ justifyContent: 'flex-start' }}
                  onClick={() => navigate(s.path)}
                >
                  <Icon name={s.icon} size={16} />
                  <span style={{ flex: 1, textAlign: 'left' }}>{s.label}</span>
                  <Icon name="chevron-right" size={14} />
                </button>
              ))}
            </div>
          </div>

          {analytics && (
            <div className="card mt-4">
              <div className="card-head">
                <h5>Reminders</h5>
              </div>
              <div className="card-body" style={{ display: 'grid', gap: 10, fontSize: '0.875rem' }}>
                <Row label="Total scheduled" value={analytics.reminders.total} />
                <Row label="Sent" value={analytics.reminders.sent} tone="success" />
                <Row label="Delivered" value={analytics.reminders.delivered} tone="success" />
                <Row label="Failed" value={analytics.reminders.failed} tone="danger" />
              </div>
            </div>
          )}
        </div>
      </div>
    </SimpleLayout>
  )
}

const Row: React.FC<{ label: string; value: number; tone?: 'success' | 'danger' }> = ({
  label,
  value,
  tone,
}) => (
  <div className="d-flex justify-content-between align-items-center">
    <span style={{ color: 'var(--ink-2)' }}>{label}</span>
    <span
      className={`badge ${
        tone === 'success' ? 'badge-success' : tone === 'danger' ? 'badge-danger' : 'badge-secondary'
      }`}
    >
      {value}
    </span>
  </div>
)

export default SimpleDashboard
