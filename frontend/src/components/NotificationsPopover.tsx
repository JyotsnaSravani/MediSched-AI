import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Icon from './Icon'
import { callingService, CallLog } from '../services/callingService'

interface Props {
  open: boolean
  onClose: () => void
}

const formatTime = (iso: string) => {
  const d = new Date(iso)
  const diff = (Date.now() - d.getTime()) / 1000
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)} h ago`
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

const outcomeText = (o: string) => o.replace('_', ' ').toLowerCase()

const outcomeIcon = (o: string): Parameters<typeof Icon>[0]['name'] => {
  if (o === 'COMPLETED' || o === 'ANSWERED') return 'check'
  if (o === 'FAILED') return 'x'
  return 'phone'
}

const NotificationsPopover: React.FC<Props> = ({ open, onClose }) => {
  const navigate = useNavigate()
  const [logs, setLogs] = useState<CallLog[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    callingService
      .getCallLogs()
      .then((d) => setLogs(d.slice(0, 8)))
      .catch(() => setLogs([]))
      .finally(() => setLoading(false))
  }, [open])

  const goToCall = (id?: number) => {
    onClose()
    navigate(id ? `/call-logs?selected=${id}` : '/call-logs')
  }

  return (
    <>
      <div className="popover-head">
        <strong>Notifications</strong>
        <button
          type="button"
          className="small-muted"
          style={{ background: 'transparent', border: 0, cursor: 'pointer', padding: 4 }}
          onClick={() => goToCall()}
        >
          View all
        </button>
      </div>

      {loading ? (
        <div className="loading-center" style={{ padding: 32 }}>
          <div className="spinner" />
          <div className="mt-2 small-muted">Loading…</div>
        </div>
      ) : logs.length === 0 ? (
        <div className="empty-state" style={{ padding: 32 }}>
          <Icon name="bell" size={28} />
          <p className="small-muted mt-2">You're all caught up.</p>
        </div>
      ) : (
        <ul className="popover-list">
          {logs.map((log) => (
            <li key={log.id}>
              <button
                type="button"
                className="popover-item"
                style={{ width: '100%', background: 'transparent', border: 0, font: 'inherit', textAlign: 'left', cursor: 'pointer' }}
                onClick={() => goToCall(log.id)}
              >
                <span
                  className={`stat-icon ${
                    log.outcome === 'FAILED' ? 'rose' : 'emerald'
                  }`}
                  style={{ width: 28, height: 28 }}
                >
                  <Icon name={outcomeIcon(log.outcome)} size={14} />
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="popover-item-title">
                    Call {outcomeText(log.outcome)} · {log.patient_name}
                  </div>
                  <div className="popover-item-sub">
                    {log.patient_phone} · {formatTime(log.initiated_at)}
                  </div>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

export default NotificationsPopover
