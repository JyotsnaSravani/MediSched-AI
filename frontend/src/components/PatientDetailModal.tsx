import React, { useEffect, useState } from 'react'
import Modal from './Modal'
import Button from './Button'
import Icon from './Icon'
import EmptyState from './EmptyState'
import { Skeleton } from './Skeleton'
import { useToast } from './Toast'
import { useConfirm } from './ConfirmDialog'
import { useAuth } from '../contexts/AuthContext'
import { Patient } from '../types'
import {
  appointmentService,
  Appointment,
} from '../services/appointmentService'

interface Props {
  open: boolean
  onClose: () => void
  patient: Patient | null
  onChanged?: () => void
}

const statusBadge: Record<string, string> = {
  PENDING: 'badge-warning',
  CONFIRMED: 'badge-info',
  COMPLETED: 'badge-success',
  CANCELLED: 'badge-secondary',
  NO_SHOW: 'badge-danger',
}

const formatDate = (d: string) =>
  new Date(d).toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })

const formatTime = (t: string) => {
  const [h, m] = t.split(':').map(Number)
  const dt = new Date()
  dt.setHours(h, m, 0)
  return dt.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

const PatientDetailModal: React.FC<Props> = ({ open, onClose, patient, onChanged }) => {
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [loading, setLoading] = useState(false)
  const [cancellingId, setCancellingId] = useState<number | null>(null)
  const toast = useToast()
  const confirm = useConfirm()
  const { can } = useAuth()
  const canCancel = can('book_slots')

  useEffect(() => {
    if (!open || !patient) return
    setLoading(true)
    appointmentService
      .getAppointmentsForPatient(patient.id)
      .then(setAppointments)
      .catch(() => setAppointments([]))
      .finally(() => setLoading(false))
  }, [open, patient])

  const handleCancel = async (apt: Appointment) => {
    const ok = await confirm({
      title: 'Cancel this appointment?',
      message: `${apt.doctor_name} · ${formatDate(apt.appointment_date)} at ${formatTime(
        apt.appointment_time
      )}`,
      confirmLabel: 'Cancel appointment',
      cancelLabel: 'Keep it',
      variant: 'danger',
    })
    if (!ok) return
    setCancellingId(apt.id)
    try {
      await appointmentService.cancelAppointment(apt.id, 'Cancelled from patient view')
      toast.success('Appointment cancelled', `${apt.doctor_name} on ${formatDate(apt.appointment_date)}`)
      const updated = await appointmentService.getAppointmentsForPatient(patient!.id)
      setAppointments(updated)
      onChanged?.()
    } catch (err: any) {
      toast.error('Cancel failed', err.response?.data?.message || 'Try again later.')
    } finally {
      setCancellingId(null)
    }
  }

  if (!patient) return null

  const upcoming = appointments.filter(
    (a) => a.status === 'CONFIRMED' || a.status === 'PENDING'
  )
  const past = appointments.filter(
    (a) => a.status === 'COMPLETED' || a.status === 'CANCELLED' || a.status === 'NO_SHOW'
  )

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="lg"
      title={patient.full_name}
      description={`${patient.phone_number}${patient.email ? ' · ' + patient.email : ''}`}
      footer={
        <Button variant="ghost" onClick={onClose}>
          Close
        </Button>
      }
    >
      {/* Patient summary */}
      <div className="row g-3" style={{ marginBottom: 20 }}>
        <SummaryItem label="Date of birth" value={formatDate(patient.date_of_birth)} />
        <SummaryItem label="Age" value={`${patient.age ?? '—'} yrs`} />
        <SummaryItem label="Gender" value={patient.gender_display || patient.gender} />
        <SummaryItem
          label="Assigned doctor"
          value={patient.assigned_doctor_name ? `Dr. ${patient.assigned_doctor_name}` : '—'}
        />
      </div>

      {patient.medical_notes && (
        <div className="alert alert-info" style={{ marginBottom: 20 }}>
          <Icon name="clipboard" size={16} />
          <div>
            <strong>Medical notes</strong>
            <div style={{ marginTop: 2 }}>{patient.medical_notes}</div>
          </div>
        </div>
      )}

      {/* Upcoming appointments */}
      <h5 className="section-title" style={{ marginBottom: 8 }}>
        <span>
          <Icon name="calendar-check" size={14} /> Upcoming appointments
        </span>
        <span className="small-muted">{upcoming.length}</span>
      </h5>

      {loading ? (
        <div style={{ display: 'grid', gap: 8, marginBottom: 20 }}>
          {Array.from({ length: 2 }).map((_, i) => (
            <Skeleton key={i} height={56} />
          ))}
        </div>
      ) : upcoming.length === 0 ? (
        <EmptyState
          icon="calendar"
          title="No upcoming appointments"
          description="Book a slot from the Calendar or Availability page."
        />
      ) : (
        <div style={{ display: 'grid', gap: 8, marginBottom: 20 }}>
          {upcoming.map((a) => (
            <AppointmentRow
              key={a.id}
              apt={a}
              onCancel={canCancel ? () => handleCancel(a) : undefined}
              cancelling={cancellingId === a.id}
            />
          ))}
        </div>
      )}

      {/* Past appointments */}
      {past.length > 0 && (
        <>
          <h5 className="section-title" style={{ marginBottom: 8 }}>
            <span>
              <Icon name="clock" size={14} /> History
            </span>
            <span className="small-muted">{past.length}</span>
          </h5>
          <div style={{ display: 'grid', gap: 8 }}>
            {past.slice(0, 6).map((a) => (
              <AppointmentRow key={a.id} apt={a} />
            ))}
          </div>
        </>
      )}
    </Modal>
  )
}

const SummaryItem: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="col-md-6">
    <div className="small-muted" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
      {label}
    </div>
    <div style={{ fontWeight: 500, marginTop: 2 }}>{value}</div>
  </div>
)

const AppointmentRow: React.FC<{
  apt: Appointment
  onCancel?: () => void
  cancelling?: boolean
}> = ({ apt, onCancel, cancelling }) => (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      padding: '12px 14px',
      border: '1px solid var(--border)',
      borderRadius: 'var(--r-md)',
      background: 'var(--surface)',
    }}
  >
    <div
      style={{
        width: 36,
        height: 36,
        borderRadius: 'var(--r-md)',
        background: 'var(--brand-soft)',
        color: 'var(--brand-hover)',
        display: 'grid',
        placeItems: 'center',
        flexShrink: 0,
      }}
    >
      <Icon name="calendar-check" size={16} />
    </div>
    <div style={{ flex: 1, minWidth: 0 }}>
      <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>
        {formatDate(apt.appointment_date)} · {formatTime(apt.appointment_time)}
      </div>
      <div className="small-muted">
        Dr. {apt.doctor_name} · {apt.doctor_specialization}
      </div>
    </div>
    <span className={`badge ${statusBadge[apt.status] || 'badge-secondary'}`}>
      {apt.status_display || apt.status}
    </span>
    {onCancel && (apt.status === 'CONFIRMED' || apt.status === 'PENDING') && (
      <Button size="sm" variant="ghost" onClick={onCancel} loading={cancelling}>
        Cancel
      </Button>
    )}
  </div>
)

export default PatientDetailModal
