/**
 * Doctors Management Page
 * Sprint 1 - Doctor Management
 */

import React, { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { doctorService } from '../services/doctorService'
import { Doctor } from '../types'
import Icon from '../components/Icon'
import Button from '../components/Button'
import Breadcrumbs from '../components/Breadcrumbs'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import { SkeletonRow } from '../components/Skeleton'
import DoctorFormModal from '../components/DoctorFormModal'
import { useConfirm } from '../components/ConfirmDialog'
import { useToast } from '../components/Toast'
import { useDebounce } from '../hooks/useDebounce'
import { useAuth } from '../contexts/AuthContext'

const avatarColor = (id: number) => `em-${((id - 1) % 6) + 1}` as const
const initialsOf = (name: string) =>
  name
    .replace(/^Dr\.?\s*/i, '')
    .split(' ')
    .map((p) => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

const DoctorsPage: React.FC = () => {
  const [params, setParams] = useSearchParams()
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchTerm, setSearchTerm] = useState(params.get('q') || '')
  const [statusFilter, setStatusFilter] = useState('')
  const debouncedSearch = useDebounce(searchTerm, 250)

  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Doctor | null>(null)
  const confirm = useConfirm()
  const toast = useToast()
  const { can } = useAuth()
  const canManage = can('manage_doctors')
  const { isDoctor } = useAuth()

  const fetchDoctors = useCallback(async () => {
    try {
      setLoading(true)
      const data = await doctorService.getDoctors(statusFilter || undefined)
      setDoctors(data)
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch doctors')
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => {
    fetchDoctors()
  }, [fetchDoctors])

  // Auto-open modal when navigated with ?new=1
  useEffect(() => {
    if (params.get('new') === '1' && canManage) {
      setEditing(null)
      setModalOpen(true)
      const next = new URLSearchParams(params)
      next.delete('new')
      setParams(next, { replace: true })
    }
  }, [params, setParams, canManage])

  useEffect(() => {
    if (debouncedSearch) setParams({ q: debouncedSearch }, { replace: true })
    else if (params.get('q')) setParams({}, { replace: true })
  }, [debouncedSearch]) // eslint-disable-line react-hooks/exhaustive-deps

  const filteredDoctors = doctors.filter((doctor) => {
    if (!debouncedSearch) return true
    const search = debouncedSearch.toLowerCase()
    return (
      doctor.full_name.toLowerCase().includes(search) ||
      doctor.email.toLowerCase().includes(search) ||
      doctor.phone_number.includes(search) ||
      doctor.specialization.toLowerCase().includes(search)
    )
  })

  const handleNew = () => {
    setEditing(null)
    setModalOpen(true)
  }

  const handleEdit = (doctor: Doctor) => {
    setEditing(doctor)
    setModalOpen(true)
  }

  const handleDelete = async (doctor: Doctor) => {
    const ok = await confirm({
      title: `Remove Dr. ${doctor.full_name}?`,
      message:
        'This deletes the doctor profile. Existing appointments will keep their reference.',
      confirmLabel: 'Delete',
      variant: 'danger',
    })
    if (!ok) return
    try {
      await doctorService.deleteDoctor(doctor.id)
      toast.success('Doctor removed', `Dr. ${doctor.full_name}`)
      fetchDoctors()
    } catch (err: any) {
      toast.error('Delete failed', err.response?.data?.detail || 'Try again later.')
    }
  }

  const handleToggleStatus = async (doctor: Doctor) => {
    const newStatus = doctor.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE'
    const action = newStatus === 'ACTIVE' ? 'activate' : 'deactivate'
    
    const ok = await confirm({
      title: `${action === 'activate' ? 'Activate' : 'Deactivate'} Dr. ${doctor.full_name}?`,
      message: action === 'activate' 
        ? 'This doctor will be available for appointments and slot management.'
        : 'This doctor will not be available for new appointments. Existing appointments remain unchanged.',
      confirmLabel: action === 'activate' ? 'Activate' : 'Deactivate',
      variant: action === 'activate' ? 'primary' : 'warning',
    })
    if (!ok) return
    
    try {
      await doctorService.toggleDoctorStatus(doctor.id, newStatus)
      toast.success(
        `Doctor ${action}d`,
        `Dr. ${doctor.full_name} is now ${newStatus.toLowerCase()}`
      )
      fetchDoctors()
    } catch (err: any) {
      toast.error('Status update failed', err.response?.data?.detail || 'Try again later.')
    }
  }

  const hasFilters = !!debouncedSearch || !!statusFilter
  const isEmpty = !loading && !error && filteredDoctors.length === 0

  const handleExport = () => {
    if (filteredDoctors.length === 0) {
      toast.info('No data to export', 'Add doctors first or adjust your filters.')
      return
    }

    // Prepare CSV data
    const headers = ['ID', 'Name', 'Specialization', 'Phone', 'Email', 'Status', 'Joined']
    const rows = filteredDoctors.map(doctor => {
      // Add = prefix to phone numbers to prevent Excel from converting to scientific notation
      const phoneForExcel = `="${doctor.phone_number}"`
      return [
        doctor.id,
        `Dr. ${doctor.full_name}`,
        doctor.specialization,
        phoneForExcel,
        doctor.email,
        doctor.status_display || doctor.status,
        new Date(doctor.created_at).toLocaleDateString()
      ]
    })

    // Create CSV content
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map((cell, index) => {
        // Phone column (index 3) already has formula format
        if (index === 3) return cell
        return `"${cell}"`
      }).join(','))
    ].join('\n')

    // Create and download file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `doctors_${new Date().toISOString().split('T')[0]}.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    toast.success('Export complete', `${filteredDoctors.length} doctor${filteredDoctors.length === 1 ? '' : 's'} exported`)
  }

  return (
    <div className="page-container">
      <Breadcrumbs />
      <div className="page-heading">
        <div>
          <h1>Doctors</h1>
          <p>{doctors.length} consultant{doctors.length === 1 ? '' : 's'} on your team</p>
        </div>
        <div className="d-flex gap-2">
          <Button size="sm" leftIcon={<Icon name="download" size={14} />} onClick={handleExport}>
            Export
          </Button>
          {canManage && (
            <Button variant="primary" onClick={handleNew} leftIcon={<Icon name="plus" size={16} />}>
              Add doctor
            </Button>
          )}
        </div>
      </div>

      {error && (
        <ErrorState
          inline
          title="Couldn't load doctors"
          message={error}
          onRetry={fetchDoctors}
          retrying={loading}
        />
      )}

      <div className="table-wrap">
        <div className="table-tools">
          <div style={{ position: 'relative', flex: 1, maxWidth: 420 }}>
            <label htmlFor="doctor-search" className="visually-hidden">
              Search doctors
            </label>
            <input
              id="doctor-search"
              type="search"
              className="form-input"
              style={{ paddingLeft: 36 }}
              placeholder="Search by name, specialization, email…"
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
          <div className="pill-filter" role="radiogroup" aria-label="Filter by status">
            <button
              role="radio"
              aria-checked={statusFilter === ''}
              className={statusFilter === '' ? 'active' : ''}
              onClick={() => setStatusFilter('')}
            >
              All
            </button>
            <button
              role="radio"
              aria-checked={statusFilter === 'ACTIVE'}
              className={statusFilter === 'ACTIVE' ? 'active' : ''}
              onClick={() => setStatusFilter('ACTIVE')}
            >
              Active
            </button>
            <button
              role="radio"
              aria-checked={statusFilter === 'INACTIVE'}
              className={statusFilter === 'INACTIVE' ? 'active' : ''}
              onClick={() => setStatusFilter('INACTIVE')}
            >
              Inactive
            </button>
          </div>
        </div>

        {loading ? (
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>Doctor</th>
                  <th>Specialization</th>
                  <th>Contact</th>
                  <th>Status</th>
                  <th>Joined</th>
                  {canManage && <th style={{ width: 130 }}></th>}
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: 6 }).map((_, i) => (
                  <SkeletonRow key={i} columns={canManage ? 6 : 5} />
                ))}
              </tbody>
            </table>
          </div>
        ) : isEmpty ? (
          <EmptyState
            icon="stethoscope"
            title={hasFilters ? 'No matching doctors' : 'No doctors yet'}
            description={
              hasFilters
                ? 'Try broadening your filters or clearing the search.'
                : 'Add your first doctor to start building your team roster.'
            }
            action={
              hasFilters ? (
                <Button
                  variant="secondary"
                  onClick={() => {
                    setSearchTerm('')
                    setStatusFilter('')
                  }}
                >
                  Clear filters
                </Button>
              ) : (
                <Button variant="primary" onClick={handleNew} leftIcon={<Icon name="plus" size={16} />}>
                  Add doctor
                </Button>
              )
            }
          />
        ) : (
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Doctor</th>
                  <th scope="col">Specialization</th>
                  <th scope="col">Contact</th>
                  <th scope="col">Status</th>
                  <th scope="col">Joined</th>
                  {canManage && (
                    <th scope="col" style={{ width: 130 }}>
                      <span className="visually-hidden">Actions</span>
                    </th>
                  )}
                </tr>
              </thead>
              <tbody>
                {filteredDoctors.map((doctor) => (
                  <tr key={doctor.id}>
                    <td>
                      <div className="cell-user">
                        <span className={`avatar ${avatarColor(doctor.id)}`} aria-hidden="true">
                          {initialsOf(doctor.full_name)}
                        </span>
                        <div>
                          <div className="cell-user-name">Dr. {doctor.full_name}</div>
                          <div className="cell-user-sub">{doctor.email}</div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="badge badge-info">{doctor.specialization}</span>
                    </td>
                    <td>{doctor.phone_number}</td>
                    <td>
                      <span
                        className={`badge ${doctor.status === 'ACTIVE' ? 'badge-success' : 'badge-secondary'}`}
                      >
                        {doctor.status_display || doctor.status}
                      </span>
                    </td>
                    <td className="small-muted">
                      {new Date(doctor.created_at).toLocaleDateString(undefined, {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </td>
                    {canManage && (
                      <td>
                        <div style={{ display: 'flex', gap: 4 }}>
                          <Button
                            size="sm"
                            variant={doctor.status === 'ACTIVE' ? 'warning' : 'success'}
                            iconOnly
                            aria-label={`${doctor.status === 'ACTIVE' ? 'Deactivate' : 'Activate'} Dr. ${doctor.full_name}`}
                            onClick={() => handleToggleStatus(doctor)}
                            leftIcon={<Icon name={doctor.status === 'ACTIVE' ? 'x-circle' : 'check-circle'} size={14} />}
                            title={doctor.status === 'ACTIVE' ? 'Deactivate' : 'Activate'}
                          />
                          <Button
                            size="sm"
                            variant="ghost"
                            iconOnly
                            aria-label={`Edit Dr. ${doctor.full_name}`}
                            onClick={() => handleEdit(doctor)}
                            leftIcon={<Icon name="edit" size={14} />}
                            title="Edit"
                          />
                          <Button
                            size="sm"
                            variant="ghost"
                            iconOnly
                            aria-label={`Delete Dr. ${doctor.full_name}`}
                            onClick={() => handleDelete(doctor)}
                            leftIcon={<Icon name="trash" size={14} />}
                            title="Delete"
                          />
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <DoctorFormModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSaved={() => fetchDoctors()}
        initial={editing}
      />
    </div>
  )
}

export default DoctorsPage
