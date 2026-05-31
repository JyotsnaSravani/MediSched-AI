import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Icon from './Icon'
import { useDebounce } from '../hooks/useDebounce'
import { patientService } from '../services/patientService'
import { doctorService } from '../services/doctorService'
import { Doctor, Patient } from '../types'

interface Props {
  open: boolean
  onClose: () => void
  initialQuery?: string
}

type Item = {
  id: string
  label: string
  hint?: string
  icon: Parameters<typeof Icon>[0]['name']
  group: 'Pages' | 'Patients' | 'Doctors' | 'Actions'
  to: string
}

const PAGES: Item[] = [
  { id: 'p-dashboard', label: 'Dashboard', icon: 'dashboard', group: 'Pages', to: '/dashboard' },
  { id: 'p-analytics', label: 'Analytics', icon: 'analytics', group: 'Pages', to: '/analytics' },
  { id: 'p-calendar', label: 'Calendar', icon: 'calendar', group: 'Pages', to: '/calendar' },
  { id: 'p-slots', label: 'Availability', icon: 'clock', group: 'Pages', to: '/slots' },
  { id: 'p-patients', label: 'Patients', icon: 'patients', group: 'Pages', to: '/patients' },
  { id: 'p-doctors', label: 'Doctors', icon: 'stethoscope', group: 'Pages', to: '/doctors' },
  { id: 'p-calls', label: 'Call Logs', icon: 'phone', group: 'Pages', to: '/call-logs' },
  { id: 'p-reminders', label: 'Reminders', icon: 'bell', group: 'Pages', to: '/reminders' },
  { id: 'p-profile', label: 'My profile', icon: 'user', group: 'Pages', to: '/profile' },
]

const ACTIONS: Item[] = [
  { id: 'a-new-patient', label: 'Add new patient', icon: 'user-plus', group: 'Actions', to: '/patients?new=1' },
  { id: 'a-new-doctor', label: 'Add new doctor', icon: 'plus', group: 'Actions', to: '/doctors?new=1' },
  { id: 'a-generate-slots', label: 'Generate availability slots', icon: 'clock', group: 'Actions', to: '/slots' },
]

const CommandPalette: React.FC<Props> = ({ open, onClose, initialQuery = '' }) => {
  const navigate = useNavigate()
  const [query, setQuery] = useState(initialQuery)
  const debounced = useDebounce(query, 200)
  const [patients, setPatients] = useState<Patient[]>([])
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [activeIdx, setActiveIdx] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  // Reset on open
  useEffect(() => {
    if (open) {
      setQuery(initialQuery)
      setActiveIdx(0)
      setTimeout(() => inputRef.current?.focus(), 0)
    }
  }, [open, initialQuery])

  // Load entities once on first open (cheap; could be paginated later)
  useEffect(() => {
    if (!open) return
    if (patients.length === 0) {
      patientService.getPatients().then((d) => setPatients(d.results)).catch(() => {})
    }
    if (doctors.length === 0) {
      doctorService.getDoctors().then(setDoctors).catch(() => {})
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  const items = useMemo<Item[]>(() => {
    const q = debounced.trim().toLowerCase()
    const pageMatches = q
      ? PAGES.filter((p) => p.label.toLowerCase().includes(q))
      : PAGES
    const actionMatches = q
      ? ACTIONS.filter((a) => a.label.toLowerCase().includes(q))
      : ACTIONS

    let patientMatches: Item[] = []
    let doctorMatches: Item[] = []
    if (q) {
      patientMatches = patients
        .filter(
          (p) =>
            p.full_name.toLowerCase().includes(q) ||
            p.phone_number.includes(q) ||
            (p.email && p.email.toLowerCase().includes(q))
        )
        .slice(0, 6)
        .map((p) => ({
          id: `pt-${p.id}`,
          label: p.full_name,
          hint: `${p.phone_number}${p.email ? ' · ' + p.email : ''}`,
          icon: 'user' as const,
          group: 'Patients' as const,
          to: `/patients?q=${encodeURIComponent(p.full_name)}`,
        }))
      doctorMatches = doctors
        .filter(
          (d) =>
            d.full_name.toLowerCase().includes(q) ||
            d.specialization.toLowerCase().includes(q) ||
            d.email.toLowerCase().includes(q)
        )
        .slice(0, 6)
        .map((d) => ({
          id: `dr-${d.id}`,
          label: `Dr. ${d.full_name}`,
          hint: d.specialization,
          icon: 'stethoscope' as const,
          group: 'Doctors' as const,
          to: `/doctors?q=${encodeURIComponent(d.full_name)}`,
        }))
    }

    return [...pageMatches, ...actionMatches, ...patientMatches, ...doctorMatches]
  }, [debounced, patients, doctors])

  // Reset highlight when results change
  useEffect(() => {
    setActiveIdx(0)
  }, [items.length])

  const choose = (item: Item) => {
    onClose()
    navigate(item.to)
  }

  if (!open) return null

  // Group items for rendering, preserving order
  const groups: { name: Item['group']; items: Item[] }[] = []
  for (const item of items) {
    let g = groups.find((x) => x.name === item.group)
    if (!g) {
      g = { name: item.group, items: [] }
      groups.push(g)
    }
    g.items.push(item)
  }

  let runningIdx = 0

  return (
    <div
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
      onClick={(e) => e.target === e.currentTarget && onClose()}
      style={{ alignItems: 'flex-start', paddingTop: 80 }}
    >
      <div className="cmdk" onKeyDown={(e) => {
        if (e.key === 'Escape') {
          e.preventDefault()
          onClose()
        } else if (e.key === 'ArrowDown') {
          e.preventDefault()
          setActiveIdx((i) => Math.min(items.length - 1, i + 1))
        } else if (e.key === 'ArrowUp') {
          e.preventDefault()
          setActiveIdx((i) => Math.max(0, i - 1))
        } else if (e.key === 'Enter') {
          e.preventDefault()
          if (items[activeIdx]) choose(items[activeIdx])
        }
      }}>
        <div className="cmdk-input-wrap">
          <Icon name="search" size={16} />
          <input
            ref={inputRef}
            className="cmdk-input"
            placeholder="Search pages, patients, doctors, actions…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search"
          />
          <kbd className="kbd">Esc</kbd>
        </div>

        <div className="cmdk-list" role="listbox">
          {items.length === 0 ? (
            <div className="empty-state" style={{ padding: 32 }}>
              <Icon name="search" size={32} />
              <p className="small-muted mt-2">No results for "{debounced}"</p>
            </div>
          ) : (
            groups.map((group) => (
              <div key={group.name} className="cmdk-group">
                <div className="cmdk-group-label">{group.name}</div>
                {group.items.map((item) => {
                  const idx = runningIdx++
                  const active = idx === activeIdx
                  return (
                    <button
                      key={item.id}
                      role="option"
                      aria-selected={active}
                      className={`cmdk-item ${active ? 'active' : ''}`}
                      onMouseEnter={() => setActiveIdx(idx)}
                      onClick={() => choose(item)}
                    >
                      <span className="cmdk-icon">
                        <Icon name={item.icon} size={16} />
                      </span>
                      <span className="cmdk-label">{item.label}</span>
                      {item.hint && <span className="cmdk-hint">{item.hint}</span>}
                    </button>
                  )
                })}
              </div>
            ))
          )}
        </div>

        <div className="cmdk-footer">
          <span><kbd className="kbd">↑</kbd><kbd className="kbd">↓</kbd> navigate</span>
          <span><kbd className="kbd">Enter</kbd> select</span>
          <span><kbd className="kbd">Esc</kbd> close</span>
        </div>
      </div>
    </div>
  )
}

export default CommandPalette
