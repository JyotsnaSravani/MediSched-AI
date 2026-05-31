/**
 * Analytics Dashboard Page
 * Sprint 4 - Analytics & Reporting
 */

import React, { useCallback, useEffect, useState } from 'react'
import { analyticsService, DashboardStats } from '../services/analyticsService'
import Icon from '../components/Icon'
import Button from '../components/Button'
import Breadcrumbs from '../components/Breadcrumbs'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import { Skeleton, SkeletonRow } from '../components/Skeleton'
import { useToast } from '../components/Toast'

const downloadBlob = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

const AnalyticsPage: React.FC = () => {
  const toast = useToast()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [dateRange, setDateRange] = useState({ start_date: '', end_date: '' })
  const [exporting, setExporting] = useState<'appointments' | 'calls' | null>(null)

  const fetchStats = useCallback(async () => {
    try {
      setLoading(true)
      const params = dateRange.start_date ? dateRange : undefined
      const data = await analyticsService.getDashboardStats(params)
      setStats(data)
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch analytics')
    } finally {
      setLoading(false)
    }
  }, [dateRange])

  useEffect(() => {
    fetchStats()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleApply = () => fetchStats()

  const handleReset = () => {
    setDateRange({ start_date: '', end_date: '' })
    setTimeout(fetchStats, 0)
  }

  const handleExport = async (kind: 'appointments' | 'calls') => {
    setExporting(kind)
    try {
      const params = dateRange.start_date ? dateRange : undefined
      const blob =
        kind === 'appointments'
          ? await analyticsService.exportAppointmentsCSV(params)
          : await analyticsService.exportCallLogsCSV(params)
      const today = new Date().toISOString().split('T')[0]
      downloadBlob(blob, `${kind === 'appointments' ? 'appointments' : 'call_logs'}_${today}.csv`)
      toast.success(
        'Export ready',
        `${kind === 'appointments' ? 'Appointments' : 'Call logs'} downloaded`
      )
    } catch {
      toast.error('Export failed', 'Could not download CSV. Try again.')
    } finally {
      setExporting(null)
    }
  }

  const utilTone = (pct: number) =>
    pct >= 80 ? 'badge-success' : pct >= 50 ? 'badge-warning' : 'badge-danger'

  return (
    <div className="page-container">
      <Breadcrumbs />
      <div className="page-heading">
        <div>
          <h1>Analytics</h1>
          <p>Track scheduling, calls, and reminder performance over time.</p>
        </div>
      </div>

      {error && (
        <ErrorState
          inline
          title="Couldn't load analytics"
          message={error}
          onRetry={fetchStats}
          retrying={loading}
        />
      )}

      {/* Filters */}
      <div className="card mb-4">
        <div className="card-head">
          <div>
            <h5>Reporting window</h5>
            <p>Leave empty to use the default last-30-days range.</p>
          </div>
        </div>
        <div className="card-body">
          <div className="row g-3 align-items-end">
            <div className="col-md-4">
              <label htmlFor="a-start" className="form-label">
                Start date
              </label>
              <input
                id="a-start"
                type="date"
                className="form-input"
                value={dateRange.start_date}
                onChange={(e) => setDateRange({ ...dateRange, start_date: e.target.value })}
              />
            </div>
            <div className="col-md-4">
              <label htmlFor="a-end" className="form-label">
                End date
              </label>
              <input
                id="a-end"
                type="date"
                className="form-input"
                value={dateRange.end_date}
                onChange={(e) => setDateRange({ ...dateRange, end_date: e.target.value })}
              />
            </div>
            <div className="col-md-4 d-flex gap-2">
              <Button variant="primary" onClick={handleApply} loading={loading}>
                Apply filter
              </Button>
              <Button variant="ghost" onClick={handleReset} disabled={loading}>
                Reset
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Summary stat cards */}
      <div className="stat-grid">
        {loading || !stats ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="stat">
              <div className="stat-top">
                <Skeleton width={120} />
              </div>
              <Skeleton width={80} height={32} />
              <Skeleton width={140} height={12} />
            </div>
          ))
        ) : (
          <>
            <StatCard
              label="Total appointments"
              value={stats.appointments.total}
              icon="calendar-check"
              tint="rose"
              sub={`${stats.appointments.completed} done · ${stats.appointments.no_shows} no-shows (${stats.appointments.no_show_rate.toFixed(0)}%)`}
            />
            <StatCard
              label="Slot utilization"
              value={`${stats.slots.utilization_rate.toFixed(0)}%`}
              icon="clock"
              tint="amber"
              sub={`${stats.slots.booked} booked · ${stats.slots.available} available`}
            />
            <StatCard
              label="Call success"
              value={`${stats.calls.success_rate.toFixed(0)}%`}
              icon="phone"
              tint="emerald"
              sub={`${stats.calls.completed} of ${stats.calls.total} calls`}
            />
            <StatCard
              label="Reminders"
              value={stats.reminders.total}
              icon="bell"
              tint="indigo"
              sub={`${stats.reminders.delivered} delivered · ${stats.reminders.failed} failed`}
            />
          </>
        )}
      </div>

      {/* Export */}
      <div className="card mb-4">
        <div className="card-head">
          <div>
            <h5>Export data</h5>
            <p>Downloads CSV files using the current reporting window.</p>
          </div>
        </div>
        <div className="card-body d-flex gap-2 flex-wrap">
          <Button
            variant="success"
            onClick={() => handleExport('appointments')}
            loading={exporting === 'appointments'}
            disabled={!!exporting}
            leftIcon={!exporting && <Icon name="download" size={16} />}
          >
            Appointments CSV
          </Button>
          <Button
            variant="success"
            onClick={() => handleExport('calls')}
            loading={exporting === 'calls'}
            disabled={!!exporting}
            leftIcon={!exporting && <Icon name="download" size={16} />}
          >
            Call logs CSV
          </Button>
        </div>
      </div>

      {/* Doctor performance */}
      <div className="table-wrap">
        <div className="table-tools">
          <div>
            <strong>Doctor performance</strong>{' '}
            <span className="small-muted">
              · {stats?.doctors.length || 0} consultant{stats?.doctors.length === 1 ? '' : 's'}
            </span>
          </div>
        </div>

        {loading ? (
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>Doctor</th>
                  <th>Total slots</th>
                  <th>Booked</th>
                  <th>Utilization</th>
                  <th>Appointments</th>
                  <th>Completed</th>
                  <th>No-shows</th>
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: 5 }).map((_, i) => (
                  <SkeletonRow key={i} columns={7} />
                ))}
              </tbody>
            </table>
          </div>
        ) : !stats || stats.doctors.length === 0 ? (
          <EmptyState
            icon="stethoscope"
            title="No doctor data yet"
            description="Performance metrics appear once doctors release availability and book appointments."
          />
        ) : (
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Doctor</th>
                  <th scope="col">Total slots</th>
                  <th scope="col">Booked</th>
                  <th scope="col">Utilization</th>
                  <th scope="col">Appointments</th>
                  <th scope="col">Completed</th>
                  <th scope="col">No-shows</th>
                </tr>
              </thead>
              <tbody>
                {stats.doctors.map((doctor) => (
                  <tr key={doctor.doctor_id}>
                    <td style={{ fontWeight: 500 }}>Dr. {doctor.doctor_name}</td>
                    <td>{doctor.total_slots}</td>
                    <td>{doctor.booked_slots}</td>
                    <td>
                      <span className={`badge ${utilTone(doctor.utilization_rate)}`}>
                        {doctor.utilization_rate.toFixed(1)}%
                      </span>
                    </td>
                    <td>{doctor.total_appointments}</td>
                    <td>{doctor.completed_appointments}</td>
                    <td>{doctor.no_shows}</td>
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

const StatCard: React.FC<{
  label: string
  value: string | number
  icon: Parameters<typeof Icon>[0]['name']
  tint: 'emerald' | 'rose' | 'amber' | 'indigo'
  sub: string
}> = ({ label, value, icon, tint, sub }) => (
  <div className="stat">
    <div className="stat-top">
      <span className="stat-label">{label}</span>
      <span className={`stat-icon ${tint}`}>
        <Icon name={icon} size={18} />
      </span>
    </div>
    <div className="stat-value">{value}</div>
    <span className="stat-trend-note" style={{ marginLeft: 0 }}>
      {sub}
    </span>
  </div>
)

export default AnalyticsPage
