/**
 * Call Logs Page
 * Sprint 3 - View all AI call logs with filtering
 */

import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { callingService, CallLog } from '../services/callingService'
import Icon from '../components/Icon'
import Button from '../components/Button'
import Breadcrumbs from '../components/Breadcrumbs'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import { SkeletonRow } from '../components/Skeleton'
import { useToast } from '../components/Toast'
import { useDebounce } from '../hooks/useDebounce'

const outcomeBadge: Record<string, string> = {
  COMPLETED: 'badge-success',
  ANSWERED: 'badge-success',
  NO_ANSWER: 'badge-warning',
  BUSY: 'badge-warning',
  FAILED: 'badge-danger',
  VOICEMAIL: 'badge-info',
}

const transcriptionBadge: Record<string, string> = {
  COMPLETED: 'badge-success',
  IN_PROGRESS: 'badge-info',
  PENDING: 'badge-warning',
  FAILED: 'badge-danger',
  NO_RECORDING: 'badge-secondary',
}

const CallLogsPage: React.FC = () => {
  const navigate = useNavigate()
  const toast = useToast()
  const [params, setParams] = useSearchParams()

  const [callLogs, setCallLogs] = useState<CallLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [initiating, setInitiating] = useState(false)

  const [outcomeFilter, setOutcomeFilter] = useState('')
  const [transcriptionFilter, setTranscriptionFilter] = useState('')
  const [searchTerm, setSearchTerm] = useState(params.get('q') || '')
  const debouncedSearch = useDebounce(searchTerm, 250)
  const selectedId = Number(params.get('selected') || '0') || null
  const rowRefs = React.useRef<Record<number, HTMLTableRowElement | null>>({})

  useEffect(() => {
    if (debouncedSearch) {
      const next = new URLSearchParams(params)
      next.set('q', debouncedSearch)
      setParams(next, { replace: true })
    } else if (params.get('q')) {
      const next = new URLSearchParams(params)
      next.delete('q')
      setParams(next, { replace: true })
    }
  }, [debouncedSearch]) // eslint-disable-line react-hooks/exhaustive-deps

  // Scroll & highlight selected row when navigated with ?selected=ID
  useEffect(() => {
    if (!selectedId || loading) return
    const el = rowRefs.current[selectedId]
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [selectedId, loading, callLogs])

  const [showTestForm, setShowTestForm] = useState(false)
  const [testPatientId, setTestPatientId] = useState(1)

  const fetchCallLogs = useCallback(async () => {
    try {
      setLoading(true)
      const params: any = {}
      if (outcomeFilter) params.outcome = outcomeFilter
      if (transcriptionFilter) params.transcription_status = transcriptionFilter
      const data = await callingService.getCallLogs(params)
      setCallLogs(data)
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch call logs')
    } finally {
      setLoading(false)
    }
  }, [outcomeFilter, transcriptionFilter])

  useEffect(() => {
    fetchCallLogs()
  }, [fetchCallLogs])

  // Auto-refresh every 30 seconds to show updated call data
  useEffect(() => {
    const interval = setInterval(() => {
      fetchCallLogs()
    }, 30000) // Refresh every 30 seconds

    return () => clearInterval(interval)
  }, [fetchCallLogs])

  const filteredCallLogs = callLogs.filter((log) => {
    if (!debouncedSearch) return true
    const s = debouncedSearch.toLowerCase()
    return log.patient_name.toLowerCase().includes(s) || log.patient_phone.includes(s)
  })

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '—'
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const formatDateTime = (d: string) =>
    new Date(d).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })

  const handleInitiateTestCall = async () => {
    try {
      setInitiating(true)
      await callingService.initiateCall({
        patient_id: testPatientId,
        call_type: 'GENERAL',
      })
      toast.success('Test call initiated', 'A new call log will appear in the table.')
      setShowTestForm(false)
      setTimeout(fetchCallLogs, 2000)
    } catch (err: any) {
      toast.error('Call failed', err.response?.data?.detail || 'Failed to initiate call')
    } finally {
      setInitiating(false)
    }
  }

  const hasFilters = !!debouncedSearch || !!outcomeFilter || !!transcriptionFilter
  const isEmpty = !loading && !error && filteredCallLogs.length === 0

  return (
    <div className="page-container">
      <Breadcrumbs />
      <div className="page-heading">
        <div>
          <h1>Call Logs</h1>
          <p>AI outbound calls and their transcription status</p>
        </div>
        <div className="d-flex gap-2">
          <Button
            variant="secondary"
            onClick={fetchCallLogs}
            disabled={loading}
            leftIcon={<Icon name="refresh-cw" size={16} />}
            title="Refresh call logs"
          >
            Refresh
          </Button>
          <Button
            variant="primary"
            onClick={() => setShowTestForm((s) => !s)}
            leftIcon={<Icon name={showTestForm ? 'x' : 'phone'} size={16} />}
          >
            {showTestForm ? 'Hide test form' : 'Test AI Call'}
          </Button>
        </div>
      </div>

      {error && (
        <ErrorState
          inline
          title="Couldn't load call logs"
          message={error}
          onRetry={fetchCallLogs}
          retrying={loading}
        />
      )}

      {showTestForm && (
        <div className="card mb-4">
          <div className="card-head">
            <div>
              <h5>AI call tester</h5>
              <p>Simulates an outbound call when Twilio credentials are not configured.</p>
            </div>
          </div>
          <div className="card-body">
            <div className="row g-3 align-items-end">
              <div className="col-md-6">
                <label htmlFor="test-patient-id" className="form-label">
                  Patient ID
                </label>
                <input
                  id="test-patient-id"
                  type="number"
                  className="form-input"
                  value={testPatientId}
                  onChange={(e) => setTestPatientId(Number(e.target.value))}
                  min={1}
                />
                <div className="small-muted mt-2">Use IDs 1–5 from demo seed data.</div>
              </div>
              <div className="col-md-6">
                <Button
                  variant="success"
                  onClick={handleInitiateTestCall}
                  loading={initiating}
                  leftIcon={!initiating && <Icon name="phone" size={16} />}
                >
                  {initiating ? 'Initiating…' : 'Initiate test call'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="table-wrap">
        <div className="table-tools">
          <div style={{ position: 'relative', flex: 1, maxWidth: 360 }}>
            <label htmlFor="call-search" className="visually-hidden">
              Search calls
            </label>
            <input
              id="call-search"
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
            <label htmlFor="outcome-filter" className="visually-hidden">
              Outcome
            </label>
            <select
              id="outcome-filter"
              className="form-select"
              style={{ width: 180 }}
              value={outcomeFilter}
              onChange={(e) => setOutcomeFilter(e.target.value)}
            >
              <option value="">All outcomes</option>
              <option value="COMPLETED">Completed</option>
              <option value="ANSWERED">Answered</option>
              <option value="NO_ANSWER">No answer</option>
              <option value="BUSY">Busy</option>
              <option value="FAILED">Failed</option>
              <option value="VOICEMAIL">Voicemail</option>
            </select>

            <label htmlFor="transcription-filter" className="visually-hidden">
              Transcription status
            </label>
            <select
              id="transcription-filter"
              className="form-select"
              style={{ width: 200 }}
              value={transcriptionFilter}
              onChange={(e) => setTranscriptionFilter(e.target.value)}
            >
              <option value="">All transcriptions</option>
              <option value="COMPLETED">Completed</option>
              <option value="IN_PROGRESS">In progress</option>
              <option value="PENDING">Pending</option>
              <option value="FAILED">Failed</option>
              <option value="NO_RECORDING">No recording</option>
            </select>

            <span className="small-muted" aria-live="polite">
              {filteredCallLogs.length} result{filteredCallLogs.length === 1 ? '' : 's'}
            </span>
          </div>
        </div>

        {loading ? (
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Type</th>
                  <th>Attempt</th>
                  <th>Outcome</th>
                  <th>Duration</th>
                  <th>Transcription</th>
                  <th>Date</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: 6 }).map((_, i) => (
                  <SkeletonRow key={i} columns={8} />
                ))}
              </tbody>
            </table>
          </div>
        ) : isEmpty ? (
          <EmptyState
            icon="phone"
            title={hasFilters ? 'No matching calls' : 'No calls yet'}
            description={
              hasFilters
                ? 'Adjust the filters or clear your search to see more results.'
                : 'Once you initiate outbound AI calls, they will appear here.'
            }
            action={
              hasFilters ? (
                <Button
                  variant="secondary"
                  onClick={() => {
                    setSearchTerm('')
                    setOutcomeFilter('')
                    setTranscriptionFilter('')
                  }}
                >
                  Clear filters
                </Button>
              ) : (
                <Button
                  variant="primary"
                  onClick={() => setShowTestForm(true)}
                  leftIcon={<Icon name="phone" size={16} />}
                >
                  Run a test call
                </Button>
              )
            }
          />
        ) : (
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Patient</th>
                  <th scope="col">Type</th>
                  <th scope="col">Attempt</th>
                  <th scope="col">Outcome</th>
                  <th scope="col">Duration</th>
                  <th scope="col">Transcription</th>
                  <th scope="col">Date</th>
                  <th scope="col">
                    <span className="visually-hidden">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredCallLogs.map((log) => (
                  <tr
                    key={log.id}
                    ref={(el) => (rowRefs.current[log.id] = el)}
                    className={selectedId === log.id ? 'row-highlight' : ''}
                  >
                    <td>
                      <div className="cell-user-name">{log.patient_name}</div>
                      <div className="cell-user-sub">{log.patient_phone}</div>
                    </td>
                    <td>
                      <span className="badge badge-info">{log.call_type.replace('_', ' ')}</span>
                    </td>
                    <td>
                      <span className="badge badge-secondary">#{log.attempt_number}</span>
                    </td>
                    <td>
                      <span className={`badge ${outcomeBadge[log.outcome] || 'badge-secondary'}`}>
                        {log.outcome.replace('_', ' ')}
                      </span>
                    </td>
                    <td style={{ fontVariantNumeric: 'tabular-nums' }}>
                      {formatDuration(log.duration)}
                    </td>
                    <td>
                      <span
                        className={`badge ${transcriptionBadge[log.transcription_status] || 'badge-secondary'}`}
                      >
                        {log.transcription_status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="small-muted">{formatDateTime(log.initiated_at)}</td>
                    <td>
                      {log.has_transcription && log.transcription_id ? (
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => navigate(`/transcriptions/${log.transcription_id}`)}
                          leftIcon={<Icon name="mic" size={14} />}
                        >
                          View
                        </Button>
                      ) : (
                        <span className="small-muted">—</span>
                      )}
                    </td>
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

export default CallLogsPage
