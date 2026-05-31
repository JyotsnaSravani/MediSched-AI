/**
 * Calendar Page
 * Sprint 2 - Calendar & Appointment Booking
 */

import React, { useState, useEffect, useCallback } from 'react'
import { doctorService } from '../services/doctorService'
import { DoctorSlot } from '../types'
import Icon from '../components/Icon'
import Breadcrumbs from '../components/Breadcrumbs'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import BookSlotModal from '../components/BookSlotModal'
import PatientDetailModal from '../components/PatientDetailModal'
import { useAuth } from '../contexts/AuthContext'
import { Patient } from '../types'

const formatTime = (t: string) => {
  if (!t) return ''
  const [h, m] = t.split(':').map(Number)
  const d = new Date()
  d.setHours(h, m, 0)
  return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

const CalendarPage: React.FC = () => {
  const [slots, setSlots] = useState<DoctorSlot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0])
  const [statusFilter, setStatusFilter] = useState('')
  const [bookingSlot, setBookingSlot] = useState<DoctorSlot | null>(null)
  const [justBookedPatient, setJustBookedPatient] = useState<Patient | null>(null)
  const { can } = useAuth()
  const canBook = can('book_slots')

  const fetchSlots = useCallback(async () => {
    try {
      setLoading(true)
      const doctors = await doctorService.getDoctors()
      const all: DoctorSlot[] = []
      for (const d of doctors) {
        try {
          const s = await doctorService.getDoctorSlots(d.id, selectedDate)
          all.push(...s)
        } catch {}
      }
      setSlots(all)
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch calendar data')
    } finally {
      setLoading(false)
    }
  }, [selectedDate])

  useEffect(() => {
    fetchSlots()
  }, [fetchSlots])

  const filtered = slots.filter((s) => (statusFilter ? s.status === statusFilter : true))

  const grouped: Record<string, DoctorSlot[]> = {}
  filtered.forEach((s) => {
    if (!grouped[s.doctor_name]) grouped[s.doctor_name] = []
    grouped[s.doctor_name].push(s)
  })

  const stats = {
    available: slots.filter((s) => s.status === 'AVAILABLE').length,
    booked: slots.filter((s) => s.status === 'BOOKED').length,
    blocked: slots.filter((s) => s.status === 'BLOCKED').length,
  }

  const slotTone = (status: string) => {
    switch (status) {
      case 'AVAILABLE': return { bg: 'var(--brand-soft)', border: 'var(--brand-soft-2)', text: 'var(--brand-ink)' }
      case 'BOOKED':    return { bg: 'var(--info-soft)', border: '#C7D2FE', text: '#3730A3' }
      default:          return { bg: 'var(--surface-2)', border: 'var(--border)', text: 'var(--muted)' }
    }
  }

  return (
    <div className="page-container">
      <Breadcrumbs />
      <div className="page-heading">
        <div>
          <p style={{ margin: 0, fontSize: '0.8125rem', color: 'var(--muted)' }}>
            {canBook
              ? 'Click an available slot to book it for a patient.'
              : 'Browse upcoming availability across the team.'}
          </p>
          <h1>Calendar</h1>
          <p>Availability across your team on {new Date(selectedDate).toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}</p>
        </div>
      </div>

      {/* Controls + legend */}
      <div className="card mb-4">
        <div className="card-body" style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Icon name="calendar" size={16} />
            <input
              type="date"
              className="form-input"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              style={{ width: 180 }}
            />
          </div>
          <div className="v-divider" />
          <div className="pill-filter">
            <button className={statusFilter === '' ? 'active' : ''} onClick={() => setStatusFilter('')}>All</button>
            <button className={statusFilter === 'AVAILABLE' ? 'active' : ''} onClick={() => setStatusFilter('AVAILABLE')}>Available</button>
            <button className={statusFilter === 'BOOKED' ? 'active' : ''} onClick={() => setStatusFilter('BOOKED')}>Booked</button>
            <button className={statusFilter === 'BLOCKED' ? 'active' : ''} onClick={() => setStatusFilter('BLOCKED')}>Blocked</button>
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 16, fontSize: '0.8125rem', color: 'var(--muted)' }}>
            <span><span className="badge badge-success">{stats.available}</span> available</span>
            <span><span className="badge badge-info">{stats.booked}</span> booked</span>
            <span><span className="badge badge-secondary">{stats.blocked}</span> blocked</span>
          </div>
        </div>
      </div>

      {error && (
        <ErrorState
          inline
          title="Couldn't load calendar"
          message={error}
          onRetry={fetchSlots}
          retrying={loading}
        />
      )}

      {loading ? (
        <div className="card"><div className="loading-center"><div className="spinner spinner-lg" /><div className="mt-3">Loading calendar…</div></div></div>
      ) : Object.keys(grouped).length === 0 ? (
        <div className="card">
          <EmptyState
            icon="calendar"
            title="No slots for this date"
            description={`Ask a doctor to release availability for ${selectedDate}, or generate slots in Availability.`}
          />
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {Object.entries(grouped).map(([doctorName, doctorSlots]) => {
            const color = `em-${(doctorName.length % 6) + 1}`
            const initials = doctorName.split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase()
            return (
              <div key={doctorName} className="card">
                <div className="card-head">
                  <div className="cell-user">
                    <span className={`avatar ${color}`}>{initials}</span>
                    <div>
                      <div className="cell-user-name">Dr. {doctorName}</div>
                      <div className="cell-user-sub">{doctorSlots.length} slot{doctorSlots.length === 1 ? '' : 's'} · {doctorSlots.filter((s) => s.status === 'BOOKED').length} booked</div>
                    </div>
                  </div>
                </div>
                <div className="card-body">
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 10 }}>
                    {doctorSlots.map((s) => {
                      const tone = slotTone(s.status)
                      const bookable = s.status === 'AVAILABLE' && canBook
                      return (
                        <button
                          key={s.id}
                          type="button"
                          disabled={!bookable}
                          onClick={() => bookable && setBookingSlot(s)}
                          aria-label={
                            bookable
                              ? `Book ${formatTime(s.start_time)} with Dr. ${s.doctor_name}`
                              : s.status === 'AVAILABLE'
                                ? `Available slot at ${formatTime(s.start_time)} (booking requires staff role)`
                                : `${s.status.toLowerCase()} slot at ${formatTime(s.start_time)}`
                          }
                          style={{
                            padding: '12px 14px',
                            background: tone.bg,
                            border: `1px solid ${tone.border}`,
                            borderRadius: 'var(--r-md)',
                            transition: 'all var(--t-fast)',
                            cursor: bookable ? 'pointer' : 'not-allowed',
                            textAlign: 'left',
                            font: 'inherit',
                            color: 'inherit',
                            opacity: bookable ? 1 : 0.85,
                          }}
                          onMouseEnter={(e) => {
                            if (bookable) {
                              e.currentTarget.style.transform = 'translateY(-1px)'
                              e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
                            }
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.transform = ''
                            e.currentTarget.style.boxShadow = ''
                          }}
                        >
                          <div style={{ fontSize: '0.9375rem', fontWeight: 600, color: tone.text, fontVariantNumeric: 'tabular-nums' }}>
                            {formatTime(s.start_time)}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: 2 }}>
                            {formatTime(s.start_time)} – {formatTime(s.end_time)}
                          </div>
                          <div style={{ marginTop: 8 }}>
                            <span className={`badge ${s.status === 'AVAILABLE' ? 'badge-success' : s.status === 'BOOKED' ? 'badge-info' : 'badge-secondary'}`}>
                              {s.status}
                            </span>
                          </div>
                          {s.patient_name && (
                            <div style={{ marginTop: 8, fontSize: '0.75rem', color: 'var(--ink-2)', fontWeight: 500 }}>
                              <Icon name="user" size={10} /> {s.patient_name}
                            </div>
                          )}
                        </button>
                      )
                    })}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
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

export default CalendarPage
