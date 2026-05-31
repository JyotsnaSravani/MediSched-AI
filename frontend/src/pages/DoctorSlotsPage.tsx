/**
 * Doctor Slots Management Page
 * Sprint 2 - Doctor Availability Management
 */

import React, { useCallback, useEffect, useState } from 'react'
import { doctorService } from '../services/doctorService'
import { Doctor, DoctorSlot } from '../types'
import Icon from '../components/Icon'
import Button from '../components/Button'
import Breadcrumbs from '../components/Breadcrumbs'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import { SkeletonRow } from '../components/Skeleton'
import BookSlotModal from '../components/BookSlotModal'
import PatientDetailModal from '../components/PatientDetailModal'
import { useToast } from '../components/Toast'
import { useConfirm } from '../components/ConfirmDialog'
import { Patient } from '../types'

const formatTime = (t: string) => {
  if (!t) return ''
  const [h, m] = t.split(':').map(Number)
  const d = new Date()
  d.setHours(h, m, 0)
  return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

const statusBadge = (s: string) =>
  s === 'AVAILABLE'
    ? 'badge-success'
    : s === 'BOOKED'
      ? 'badge-info'
      : 'badge-secondary'

const DoctorSlotsPage: React.FC = () => {
  const toast = useToast()
  const confirm = useConfirm()

  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [selectedDoctor, setSelectedDoctor] = useState<number | null>(null)
  const [slots, setSlots] = useState<DoctorSlot[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [generating, setGenerating] = useState(false)

  // Slot generation form
  const [slotDate, setSlotDate] = useState(new Date().toISOString().split('T')[0])
  const [startTime, setStartTime] = useState('09:00')
  const [endTime, setEndTime] = useState('17:00')
  const [duration, setDuration] = useState<30 | 60>(30)

  const [bookingSlot, setBookingSlot] = useState<DoctorSlot | null>(null)
  const [justBookedPatient, setJustBookedPatient] = useState<Patient | null>(null)

  useEffect(() => {
    doctorService
      .getDoctors('ACTIVE')
      .then((data) => {
        setDoctors(data)
        if (data.length > 0) setSelectedDoctor((curr) => curr ?? data[0].id)
      })
      .catch(() => setError('Failed to fetch doctors'))
  }, [])

  const fetchSlots = useCallback(async () => {
    if (!selectedDoctor) return
    try {
      setLoading(true)
      const data = await doctorService.getDoctorSlots(selectedDoctor, slotDate)
      setSlots(data)
      setError('')
    } catch {
      setError('Failed to fetch slots')
    } finally {
      setLoading(false)
    }
  }, [selectedDoctor, slotDate])

  useEffect(() => {
    fetchSlots()
  }, [fetchSlots])

  const handleGenerateSlots = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedDoctor) return
    if (endTime <= startTime) {
      toast.error('Invalid range', 'End time must be after start time.')
      return
    }
    setGenerating(true)
    try {
      await doctorService.generateSlots(selectedDoctor, {
        slot_date: slotDate,
        start_time: startTime,
        end_time: endTime,
        duration,
      })
      toast.success('Slots generated', `${slotDate} · ${startTime} – ${endTime}`)
      fetchSlots()
    } catch (err: any) {
      toast.error('Generation failed', err.response?.data?.message || 'Try again.')
    } finally {
      setGenerating(false)
    }
  }

  const handleBlock = async (slot: DoctorSlot) => {
    if (!selectedDoctor) return
    try {
      await doctorService.blockSlot(selectedDoctor, slot.id)
      toast.success('Slot blocked', `${formatTime(slot.start_time)}`)
      fetchSlots()
    } catch {
      toast.error('Block failed', 'Could not block this slot.')
    }
  }

  const handleUnblock = async (slot: DoctorSlot) => {
    if (!selectedDoctor) return
    try {
      await doctorService.unblockSlot(selectedDoctor, slot.id)
      toast.success('Slot unblocked', `${formatTime(slot.start_time)}`)
      fetchSlots()
    } catch {
      toast.error('Unblock failed', 'Could not unblock this slot.')
    }
  }

  const stats = {
    available: slots.filter((s) => s.status === 'AVAILABLE').length,
    booked: slots.filter((s) => s.status === 'BOOKED').length,
    blocked: slots.filter((s) => s.status === 'BLOCKED').length,
  }

  return (
    <div className="page-container">
      <Breadcrumbs />
      <div className="page-heading">
        <div>
          <h1>Doctor Availability</h1>
          <p>
            Pick a doctor and date, generate availability in bulk, then book or block each slot.
          </p>
        </div>
      </div>

      {/* Status legend */}
      <div
        className="card mb-4"
        style={{
          background: 'var(--surface-2)',
          padding: '12px 16px',
          display: 'flex',
          gap: 16,
          alignItems: 'center',
          flexWrap: 'wrap',
          fontSize: '0.8125rem',
          color: 'var(--ink-2)',
        }}
      >
        <strong style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--muted)' }}>
          Slot status
        </strong>
        <span>
          <span className="badge badge-success">Available</span>{' '}
          <span className="small-muted">— ready to book</span>
        </span>
        <span>
          <span className="badge badge-info">Booked</span>{' '}
          <span className="small-muted">— assigned to a patient</span>
        </span>
        <span>
          <span className="badge badge-secondary">Blocked</span>{' '}
          <span className="small-muted">— hidden from booking</span>
        </span>
      </div>

      {error && (
        <ErrorState
          inline
          title="Couldn't load availability"
          message={error}
          onRetry={fetchSlots}
          retrying={loading}
        />
      )}

      {/* Step 1 — Doctor + date picker */}
      <div className="card mb-4">
        <div className="card-head">
          <div>
            <h5>
              <span className="step-pill">1</span> Choose doctor & date
            </h5>
            <p>Slots are scoped to a single doctor on a single date.</p>
          </div>
        </div>
        <div className="card-body">
          <div className="row g-3 align-items-end">
            <div className="col-md-6">
              <label htmlFor="slot-doctor" className="form-label">
                Doctor
              </label>
              <select
                id="slot-doctor"
                className="form-select"
                value={selectedDoctor || ''}
                onChange={(e) => setSelectedDoctor(Number(e.target.value))}
              >
                <option value="">Select a doctor…</option>
                {doctors.map((doctor) => (
                  <option key={doctor.id} value={doctor.id}>
                    Dr. {doctor.full_name} · {doctor.specialization}
                  </option>
                ))}
              </select>
            </div>
            <div className="col-md-6">
              <label htmlFor="slot-date-pick" className="form-label">
                Date
              </label>
              <input
                id="slot-date-pick"
                type="date"
                className="form-input"
                value={slotDate}
                onChange={(e) => setSlotDate(e.target.value)}
              />
            </div>
          </div>
        </div>
      </div>

      {selectedDoctor && (
        <>
          {/* Step 2 — Generation form */}
          <div className="card mb-4">
            <div className="card-head">
              <div>
                <h5>
                  <span className="step-pill">2</span> Generate availability
                </h5>
                <p>Auto-create slots in 30 or 60 minute increments. Skips times that already exist.</p>
              </div>
              <div style={{ display: 'flex', gap: 12, fontSize: '0.8125rem', color: 'var(--muted)' }}>
                <span><span className="badge badge-success">{stats.available}</span> available</span>
                <span><span className="badge badge-info">{stats.booked}</span> booked</span>
                <span><span className="badge badge-secondary">{stats.blocked}</span> blocked</span>
              </div>
            </div>
            <div className="card-body">
              <form onSubmit={handleGenerateSlots}>
                <div className="row g-3 align-items-end">
                  <div className="col-md-3">
                    <label htmlFor="g-start" className="form-label">
                      Start time
                    </label>
                    <input
                      id="g-start"
                      type="time"
                      className="form-input"
                      value={startTime}
                      onChange={(e) => setStartTime(e.target.value)}
                      required
                    />
                  </div>
                  <div className="col-md-3">
                    <label htmlFor="g-end" className="form-label">
                      End time
                    </label>
                    <input
                      id="g-end"
                      type="time"
                      className="form-input"
                      value={endTime}
                      onChange={(e) => setEndTime(e.target.value)}
                      required
                    />
                  </div>
                  <div className="col-md-3">
                    <label htmlFor="g-dur" className="form-label">
                      Duration
                    </label>
                    <select
                      id="g-dur"
                      className="form-select"
                      value={duration}
                      onChange={(e) => setDuration(Number(e.target.value) as 30 | 60)}
                    >
                      <option value={30}>30 minutes</option>
                      <option value={60}>60 minutes</option>
                    </select>
                  </div>
                  <div className="col-md-3">
                    <Button
                      type="submit"
                      variant="primary"
                      loading={generating}
                      leftIcon={!generating && <Icon name="plus" size={16} />}
                    >
                      Generate slots
                    </Button>
                  </div>
                </div>
              </form>
            </div>
          </div>

          {/* Step 3 — Slots table */}
          <div className="table-wrap">
            <div className="table-tools">
              <div>
                <strong>
                  <span className="step-pill">3</span> Manage slots
                </strong>{' '}
                <span className="small-muted">
                  · {slots.length} on{' '}
                  {new Date(slotDate).toLocaleDateString(undefined, {
                    weekday: 'short',
                    month: 'short',
                    day: 'numeric',
                  })}
                </span>
              </div>
            </div>
            {loading ? (
              <div className="table-responsive">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Status</th>
                      <th>Patient</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {Array.from({ length: 5 }).map((_, i) => (
                      <SkeletonRow key={i} columns={4} />
                    ))}
                  </tbody>
                </table>
              </div>
            ) : slots.length === 0 ? (
              <EmptyState
                icon="clock"
                title="No slots for this date"
                description="Use the form above to generate availability."
              />
            ) : (
              <div className="table-responsive">
                <table className="table">
                  <thead>
                    <tr>
                      <th scope="col">Time</th>
                      <th scope="col">Status</th>
                      <th scope="col">Patient</th>
                      <th scope="col" style={{ width: 220 }}>
                        <span className="visually-hidden">Actions</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {slots.map((slot) => (
                      <tr key={slot.id}>
                        <td style={{ fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>
                          {formatTime(slot.start_time)} – {formatTime(slot.end_time)}
                        </td>
                        <td>
                          <span className={`badge ${statusBadge(slot.status)}`}>
                            {slot.status_display || slot.status}
                          </span>
                        </td>
                        <td className="small-muted">{slot.patient_name || '—'}</td>
                        <td>
                          <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                            {slot.status === 'AVAILABLE' && (
                              <>
                                <Button
                                  size="sm"
                                  variant="primary"
                                  onClick={() => setBookingSlot(slot)}
                                  leftIcon={<Icon name="calendar-check" size={14} />}
                                >
                                  Book
                                </Button>
                                <Button
                                  size="sm"
                                  variant="secondary"
                                  onClick={async () => {
                                    const ok = await confirm({
                                      title: 'Block this slot?',
                                      message: 'It will be hidden from booking until you unblock it.',
                                      confirmLabel: 'Block',
                                    })
                                    if (ok) handleBlock(slot)
                                  }}
                                >
                                  Block
                                </Button>
                              </>
                            )}
                            {slot.status === 'BLOCKED' && (
                              <Button
                                size="sm"
                                variant="success"
                                onClick={() => handleUnblock(slot)}
                              >
                                Unblock
                              </Button>
                            )}
                            {slot.status === 'BOOKED' && (
                              <span className="small-muted">Booked</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      <BookSlotModal
        open={!!bookingSlot}
        slot={bookingSlot}
        onClose={() => setBookingSlot(null)}
        onBooked={({ patient }) => {
          fetchSlots()
          setJustBookedPatient(patient)
        }}
      />

      <PatientDetailModal
        open={!!justBookedPatient}
        patient={justBookedPatient}
        onClose={() => setJustBookedPatient(null)}
      />
    </div>
  )
}

export default DoctorSlotsPage
