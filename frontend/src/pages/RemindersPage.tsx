/**
 * Reminders Page
 * Sprint 4 - View all automated reminders
 */

import React, { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { reminderService, ReminderLog, ReminderStats } from '../services/reminderService'
import Icon from '../components/Icon'
import Breadcrumbs from '../components/Breadcrumbs'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import { Skeleton, SkeletonRow } from '../components/Skeleton'
import { useDebounce } from '../hooks/useDebounce'

const statusBadge: Record<string, string> = {
  SENT: 'badge-success',
  DELIVERED: 'badge-success',
  PENDING: 'badge-warning',
  FAILED: 'badge-danger',
  RETRY: 'badge-info',
}

const channelBadge: Record<string, string> = {
  SMS: 'badge-info',
  EMAIL: 'badge-primary',
  BOTH: 'badge-success',
}

const formatDateTime = (d: string | null) =>
  d
    ? new Date(d).toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '—'

const RemindersPage: React.FC = () => {
  const [params, setParams] = useSearchParams()
  const [reminders, setReminders] = useState<ReminderLog[]>([])
  const [stats, setStats] = useState<ReminderStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [statusFilter, setStatusFilter] = useState('')
  const [channelFilter, setChannelFilter] = useState('')
  const [searchTerm, setSearchTerm] = useState(params.get('q') || '')
  const debouncedSearch = useDebounce(searchTerm, 250)

  const fetchReminders = useCallback(async () => {
    try {
      setLoading(true)
      const apiParams: any = {}
      if (statusFilter) apiParams.delivery_status = statusFilter
      if (channelFilter) apiParams.channel = channelFilter
      const data = await reminderService.getReminders(apiParams)
      setReminders(data)
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch reminders')
    } finally {
      setLoading(false)
    }
  }, [statusFilter, channelFilter])

  useEffect(() => {
    fetchReminders()
  }, [fetchReminders])

  useEffect(() => {
    reminderService
      .getReminderStats()
      .then(setStats)
      .catch(() => setStats(null))
  }, [])

  useEffect(() => {
    const next = new URLSearchParams(params)
    if (debouncedSearch) next.set('q', debouncedSearch)
    else next.delete('q')
    setParams(next, { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch])

  const filtered = reminders.filter((r) => {
    if (!debouncedSearch) return true
    const s = debouncedSearch.toLowerCase()
    return r.patient_name.toLowerCase().includes(s) || r.patient_phone.includes(s)
  })

  const hasFilters = !!debouncedSearch || !!statusFilter || !!channelFilter
  const isEmpty = !loading && !error && filtered.length === 0

  return (
    <div className="page-container">
      <Breadcrumbs />
      <div className="page-heading">
        <div>
          <h1>Reminders</h1>
          <p>SMS and email reminders sent to patients ahead of appointments.</p>
        </div>
      </div>

      {error && (
        <ErrorState
          inline
          title="Couldn't load reminders"
          message={error}
          onRetry={fetchReminders}
          retrying={loading}
        />
      )}

      {/* Stat strip */}
      <div className="stat-grid">
        {!stats
          ? Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="stat">
                <div className="stat-top">
                  <Skeleton width={100} />
                </div>
                <Skeleton width={60} height={28} />
              </div>
            ))
          : [
              { label: 'Total', value: stats.total, tint: 'indigo' as const, icon: 'bell' as const },
              { label: 'Delivered', value: stats.delivered, tint: 'emerald' as const, icon: 'check' as const },
              { label: 'Failed', value: stats.failed, tint: 'rose' as const, icon: 'x' as const },
              { label: 'SMS / Email', value: `${stats.sms} / ${stats.email}`, tint: 'amber' as const, icon: 'mail' as const },
            ].map((c) => (
              <div key={c.label} className="stat">
                <div className="stat-top">
                  <span className="stat-label">{c.label}</span>
                  <span className={`stat-icon ${c.tint}`}>
                    <Icon name={c.icon} size={18} />
                  </span>
                </div>
                <div className="stat-value">{c.value}</div>
              </div>
            ))}
      </div>

      <div className="table-wrap">
        <div className="table-tools">
          <div style={{ position: 'relative', flex: 1, maxWidth: 360 }}>
            <label htmlFor="rem-search" className="visually-hidden">
              Search reminders
            </label>
            <input
              id="rem-search"
              type="search"
              className="form-input"
              style={{ paddingLeft: 36 }}
              placeholder="Search by patient or phone…"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            <span
              aria-hidden="true"
              style={{
                position: 'absolute',
                left: 10,
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--muted-2)',
              }}
            >
              <Icon name="search" size={16} />
            </span>
          </div>

          <div className="d-flex gap-2 align-items-center flex-wrap">
            <label htmlFor="rem-status" className="visually-hidden">
              Delivery status
            </label>
            <select
              id="rem-status"
              className="form-select"
              style={{ width: 180 }}
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All statuses</option>
              <option value="SENT">Sent</option>
              <option value="DELIVERED">Delivered</option>
              <option value="PENDING">Pending</option>
              <option value="FAILED">Failed</option>
              <option value="RETRY">Retry</option>
            </select>

            <label htmlFor="rem-channel" className="visually-hidden">
              Channel
            </label>
            <select
              id="rem-channel"
              className="form-select"
              style={{ width: 160 }}
              value={channelFilter}
              onChange={(e) => setChannelFilter(e.target.value)}
            >
              <option value="">All channels</option>
              <option value="SMS">SMS</option>
              <option value="EMAIL">Email</option>
              <option value="BOTH">Both</option>
            </select>

            <span className="small-muted" aria-live="polite">
              {filtered.length} result{filtered.length === 1 ? '' : 's'}
            </span>
          </div>
        </div>

        {loading ? (
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Doctor</th>
                  <th>Appointment</th>
                  <th>Type</th>
                  <th>Channel</th>
                  <th>Status</th>
                  <th>Retry</th>
                  <th>Sent at</th>
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: 5 }).map((_, i) => (
                  <SkeletonRow key={i} columns={8} />
                ))}
              </tbody>
            </table>
          </div>
        ) : isEmpty ? (
          <EmptyState
            icon="bell"
            title={hasFilters ? 'No matching reminders' : 'No reminders yet'}
            description={
              hasFilters
                ? 'Adjust your filters or clear the search.'
                : 'Reminders are sent automatically before scheduled appointments.'
            }
          />
        ) : (
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Patient</th>
                  <th scope="col">Doctor</th>
                  <th scope="col">Appointment</th>
                  <th scope="col">Type</th>
                  <th scope="col">Channel</th>
                  <th scope="col">Status</th>
                  <th scope="col">Retry</th>
                  <th scope="col">Sent at</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <div className="cell-user-name">{r.patient_name}</div>
                      <div className="cell-user-sub">{r.patient_phone}</div>
                    </td>
                    <td>{r.doctor_name}</td>
                    <td>
                      <div>{r.appointment_date}</div>
                      <div className="cell-user-sub">{r.appointment_time}</div>
                    </td>
                    <td>
                      <span className="badge badge-info">
                        {r.reminder_type.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${channelBadge[r.channel] || 'badge-secondary'}`}>
                        {r.channel}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`badge ${statusBadge[r.delivery_status] || 'badge-secondary'}`}
                      >
                        {r.delivery_status}
                      </span>
                    </td>
                    <td>
                      {r.retry_count > 0 ? (
                        <span className="badge badge-warning">{r.retry_count}</span>
                      ) : (
                        <span className="small-muted">—</span>
                      )}
                    </td>
                    <td className="small-muted">{formatDateTime(r.sent_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default RemindersPage
