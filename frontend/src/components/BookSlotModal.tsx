import React, { useEffect, useMemo, useState } from 'react'
import Modal from './Modal'
import Button from './Button'
import Icon from './Icon'
import { useToast } from './Toast'
import { useDebounce } from '../hooks/useDebounce'
import { patientService } from '../services/patientService'
import { doctorService } from '../services/doctorService'
import { DoctorSlot, Patient } from '../types'

interface Props {
  open: boolean
  onClose: () => void
  slot: DoctorSlot | null
  onBooked?: (booked: { patient: Patient }) => void
}

const BookSlotModal: React.FC<Props> = ({ open, onClose, slot, onBooked }) => {
  const toast = useToast()
  const [patients, setPatients] = useState<Patient[]>([])
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [notes, setNotes] = useState('')
  const debouncedSearch = useDebounce(search, 250)

  useEffect(() => {
    if (!open) return
    setSelectedId(null)
    setSearch('')
    setNotes('')
    setLoading(true)
    patientService
      .getPatients()
      .then((d) => setPatients(d.results))
      .catch(() => setPatients([]))
      .finally(() => setLoading(false))
  }, [open])

  const filtered = useMemo(() => {
    if (!debouncedSearch) return patients.slice(0, 50)
    const q = debouncedSearch.toLowerCase()
    return patients
      .filter(
        (p) =>
          p.full_name.toLowerCase().includes(q) ||
          p.phone_number.includes(q) ||
          (p.email && p.email.toLowerCase().includes(q))
      )
      .slice(0, 50)
  }, [patients, debouncedSearch])

  const handleBook = async () => {
    if (!slot || !selectedId) return
    const selectedPatient = patients.find((p) => p.id === selectedId)
    if (!selectedPatient) return
    setSubmitting(true)
    try {
      await doctorService.bookSlot(slot.doctor, slot.id, selectedId, notes)
      toast.success(
        'Appointment booked',
        `${selectedPatient.full_name} · ${slot.slot_date} ${slot.start_time}`
      )
      onBooked?.({ patient: selectedPatient })
      onClose()
    } catch (err: any) {
      const data = err.response?.data
      toast.error('Booking failed', data?.message || data?.detail || 'Slot may already be taken')
    } finally {
      setSubmitting(false)
    }
  }

  if (!slot) return null

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="lg"
      title="Book appointment"
      description={`Dr. ${slot.doctor_name} · ${slot.slot_date} · ${slot.start_time} – ${slot.end_time}`}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleBook}
            loading={submitting}
            disabled={!selectedId}
          >
            Confirm booking
          </Button>
        </>
      }
    >
      <div className="form-group">
        <label htmlFor="book-search" className="form-label">
          Search patient
        </label>
        <div style={{ position: 'relative' }}>
          <input
            id="book-search"
            type="search"
            className="form-input"
            style={{ paddingLeft: 36 }}
            placeholder="Name, phone, or email…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            autoFocus
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
      </div>

      <div
        style={{
          maxHeight: 280,
          overflowY: 'auto',
          border: '1px solid var(--border)',
          borderRadius: 'var(--r-md)',
        }}
      >
        {loading ? (
          <div className="loading-center">
            <div className="spinner" />
            <div className="mt-3 small-muted">Loading patients…</div>
          </div>
        ) : filtered.length === 0 ? (
          <div className="empty-state" style={{ padding: 32 }}>
            <Icon name="patients" size={32} />
            <p className="small-muted mt-2">No patients match.</p>
          </div>
        ) : (
          <ul style={{ listStyle: 'none' }}>
            {filtered.map((p) => {
              const active = selectedId === p.id
              return (
                <li key={p.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(p.id)}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      padding: '10px 14px',
                      background: active ? 'var(--brand-soft)' : 'transparent',
                      border: 0,
                      borderBottom: '1px solid var(--border)',
                      cursor: 'pointer',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      gap: 12,
                    }}
                  >
                    <div>
                      <div
                        style={{
                          fontWeight: active ? 600 : 500,
                          color: active ? 'var(--brand-ink)' : 'var(--ink)',
                        }}
                      >
                        {p.full_name}
                      </div>
                      <div className="small-muted">
                        {p.phone_number}
                        {p.email ? ` · ${p.email}` : ''}
                      </div>
                    </div>
                    {active && <Icon name="check" size={16} />}
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      <div className="form-group mt-4">
        <label htmlFor="book-notes" className="form-label">
          Notes (optional)
        </label>
        <textarea
          id="book-notes"
          className="form-textarea"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Reason for visit, special requests…"
        />
      </div>
    </Modal>
  )
}

export default BookSlotModal
