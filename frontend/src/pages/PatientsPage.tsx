/**
 * Patients Management Page
 * Sprint 1 - Patient Management
 */

import React, { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { patientService } from '../services/patientService'
import { Patient } from '../types'
import Icon from '../components/Icon'
import Button from '../components/Button'
import Breadcrumbs from '../components/Breadcrumbs'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import { SkeletonRow } from '../components/Skeleton'
import PatientFormModal from '../components/PatientFormModal'
import PatientDetailModal from '../components/PatientDetailModal'
import { useConfirm } from '../components/ConfirmDialog'
import { useToast } from '../components/Toast'
import { useDebounce } from '../hooks/useDebounce'
import { useAuth } from '../contexts/AuthContext'

const avatarColor = (id: number) => `em-${((id - 1) % 6) + 1}` as const
const initialsOf = (name: string) =>
  name
    .split(' ')
    .map((p) => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

const PatientsPage: React.FC = () => {
  const [params, setParams] = useSearchParams()
  const [patients, setPatients] = useState<Patient[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchTerm, setSearchTerm] = useState(params.get('q') || '')
  const debouncedSearch = useDebounce(searchTerm, 250)

  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Patient | null>(null)
  const [detailPatient, setDetailPatient] = useState<Patient | null>(null)
  const [importing, setImporting] = useState(false)
  const fileInputRef = React.useRef<HTMLInputElement>(null)
  const confirm = useConfirm()
  const toast = useToast()
  const { can } = useAuth()
  const canManage = can('manage_patients')

  const fetchPatients = useCallback(async () => {
    try {
      setLoading(true)
      const data = await patientService.getPatients()
      setPatients(data.results)
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch patients')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchPatients()
  }, [fetchPatients])

  // Auto-open modal when navigated with ?new=1
  useEffect(() => {
    if (params.get('new') === '1') {
      setEditing(null)
      setModalOpen(true)
      const next = new URLSearchParams(params)
      next.delete('new')
      setParams(next, { replace: true })
    }
  }, [params, setParams])

  // Sync search term to URL so the topbar search can pre-filter
  useEffect(() => {
    if (debouncedSearch) setParams({ q: debouncedSearch }, { replace: true })
    else if (params.get('q')) setParams({}, { replace: true })
  }, [debouncedSearch]) // eslint-disable-line react-hooks/exhaustive-deps

  const filteredPatients = patients.filter((patient) => {
    if (!debouncedSearch) return true
    const search = debouncedSearch.toLowerCase()
    return (
      patient.full_name.toLowerCase().includes(search) ||
      (patient.email?.toLowerCase().includes(search) ?? false) ||
      patient.phone_number.includes(search)
    )
  })

  const calculateAge = (dateOfBirth: string) => {
    const today = new Date()
    const birthDate = new Date(dateOfBirth)
    let age = today.getFullYear() - birthDate.getFullYear()
    const monthDiff = today.getMonth() - birthDate.getMonth()
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) age--
    return age
  }

  const handleNew = () => {
    setEditing(null)
    setModalOpen(true)
  }

  const handleEdit = (patient: Patient) => {
    setEditing(patient)
    setModalOpen(true)
  }

  const handleDelete = async (patient: Patient) => {
    const ok = await confirm({
      title: `Delete ${patient.full_name}?`,
      message:
        'This permanently removes the patient record. Past appointments and call logs are kept.',
      confirmLabel: 'Delete',
      variant: 'danger',
    })
    if (!ok) return
    try {
      await patientService.deletePatient(patient.id)
      toast.success('Patient removed', patient.full_name)
      fetchPatients()
    } catch (err: any) {
      toast.error('Delete failed', err.response?.data?.detail || 'Try again later.')
    }
  }

  const handleChangeDoctor = (patient: Patient) => {
    // Open edit modal to change assigned doctor
    setEditing(patient)
    setModalOpen(true)
  }

  const hasSearch = debouncedSearch.length > 0
  const isEmpty = !loading && !error && filteredPatients.length === 0

  const handleExport = () => {
    if (filteredPatients.length === 0) {
      toast.info('No data to export', 'Add patients first or adjust your search.')
      return
    }

    // Prepare CSV data
    const headers = ['ID', 'Name', 'Phone', 'Email', 'Age', 'Gender', 'Date of Birth', 'Assigned Doctor', 'Registered']
    const rows = filteredPatients.map(patient => {
      const assignedName = (patient as any).assigned_doctor_name as string | null
      // Add = prefix to phone numbers to prevent Excel from converting to scientific notation
      const phoneForExcel = `="${patient.phone_number}"`
      return [
        patient.id,
        patient.full_name,
        phoneForExcel,
        patient.email || '',
        calculateAge(patient.date_of_birth),
        patient.gender_display || patient.gender,
        patient.date_of_birth,
        assignedName ? `Dr. ${assignedName}` : '',
        new Date(patient.created_at).toLocaleDateString()
      ]
    })

    // Create CSV content
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map((cell, index) => {
        // Phone column (index 2) already has formula format
        if (index === 2) return cell
        return `"${cell}"`
      }).join(','))
    ].join('\n')

    // Create and download file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `patients_${new Date().toISOString().split('T')[0]}.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    toast.success('Export complete', `${filteredPatients.length} patient${filteredPatients.length === 1 ? '' : 's'} exported`)
  }

  const handleImportClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Validate file type
    if (!file.name.endsWith('.csv')) {
      toast.error('Invalid file', 'Please upload a CSV file')
      return
    }

    setImporting(true)
    try {
      const result = await patientService.importPatients(file)
      
      if (result.error_count > 0) {
        toast.warning(
          'Import completed with errors',
          `${result.success_count} imported, ${result.error_count} failed. Check console for details.`
        )
        console.error('Import errors:', result.errors)
      } else {
        toast.success(
          'Import successful!',
          `${result.success_count} patients imported and welcome calls triggered`
        )
      }
      
      // Refresh patient list
      fetchPatients()
    } catch (err: any) {
      toast.error('Import failed', err.response?.data?.message || 'Try again')
    } finally {
      setImporting(false)
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  return (
    <div className="page-container">
      <Breadcrumbs />
      <div className="page-heading">
        <div>
          <h1>Patients</h1>
          <p>{patients.length} patient{patients.length === 1 ? '' : 's'} in your registry</p>
        </div>
        <div className="d-flex gap-2">
          <Button 
            size="sm" 
            variant="success"
            leftIcon={<Icon name="arrow-up" size={14} />} 
            onClick={handleImportClick}
            loading={importing}
            disabled={importing}
          >
            Import
          </Button>
          <Button size="sm" leftIcon={<Icon name="download" size={14} />} onClick={handleExport}>
            Export
          </Button>
          {canManage && (
            <Button variant="primary" onClick={handleNew} leftIcon={<Icon name="plus" size={16} />}>
              New patient
            </Button>
          )}
        </div>
      </div>

      {/* Hidden file input for import */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />

      {error && (
        <ErrorState
          inline
          title="Couldn't load patients"
          message={error}
          onRetry={fetchPatients}
          retrying={loading}
        />
      )}

      <div className="table-wrap">
        <div className="table-tools">
          <div style={{ position: 'relative', flex: 1, maxWidth: 420 }}>
            <label htmlFor="patient-search" className="visually-hidden">
              Search patients
            </label>
            <input
              id="patient-search"
              type="search"
              className="form-input"
              style={{ paddingLeft: 36 }}
              placeholder="Search by name, email, or phone…"
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
          <span className="small-muted" aria-live="polite">
            {filteredPatients.length} result{filteredPatients.length === 1 ? '' : 's'}
          </span>
        </div>

        {loading ? (
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Contact</th>
                  <th>Age</th>
                  <th>Gender</th>
                  <th>Assigned Dr.</th>
                  <th>Registered</th>
                  <th style={{ width: 90 }}></th>
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: 6 }).map((_, i) => (
                  <SkeletonRow key={i} columns={7} />
                ))}
              </tbody>
            </table>
          </div>
        ) : isEmpty ? (
          <EmptyState
            icon="patients"
            title={hasSearch ? 'No matching patients' : 'No patients yet'}
            description={
              hasSearch
                ? `No results for "${debouncedSearch}". Try a different search.`
                : 'Add your first patient to begin scheduling appointments.'
            }
            action={
              hasSearch ? (
                <Button variant="secondary" onClick={() => setSearchTerm('')}>
                  Clear search
                </Button>
              ) : (
                <Button variant="primary" onClick={handleNew} leftIcon={<Icon name="plus" size={16} />}>
                  New patient
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
                  <th scope="col">Contact</th>
                  <th scope="col">Age</th>
                  <th scope="col">Gender</th>
                  <th scope="col">Assigned Dr.</th>
                  <th scope="col">Registered</th>
                  <th scope="col" style={{ width: 90 }}>
                    <span className="visually-hidden">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredPatients.map((patient) => {
                  const assignedName = (patient as any).assigned_doctor_name as string | null
                  return (
                    <tr
                      key={patient.id}
                      style={{ cursor: 'pointer' }}
                      onClick={() => setDetailPatient(patient)}
                    >
                      <td>
                        <div className="cell-user">
                          <span className={`avatar ${avatarColor(patient.id)}`} aria-hidden="true">
                            {initialsOf(patient.full_name)}
                          </span>
                          <div>
                            <div className="cell-user-name">{patient.full_name}</div>
                            <div className="cell-user-sub">ID #{patient.id}</div>
                          </div>
                        </div>
                      </td>
                      <td>
                        <div>{patient.phone_number}</div>
                        {patient.email && <div className="cell-user-sub">{patient.email}</div>}
                      </td>
                      <td>{calculateAge(patient.date_of_birth)} yrs</td>
                      <td>
                        <span className="badge badge-secondary">
                          {patient.gender_display || patient.gender}
                        </span>
                      </td>
                      <td>
                        {assignedName ? (
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span className="small-muted">Dr. {assignedName}</span>
                            {canManage && (
                              <div style={{ display: 'flex', gap: 4 }}>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  iconOnly
                                  aria-label={`Change doctor for ${patient.full_name}`}
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleChangeDoctor(patient)
                                  }}
                                  leftIcon={<Icon name="edit" size={12} />}
                                  title="Change doctor"
                                />
                              </div>
                            )}
                          </div>
                        ) : (
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span className="small-muted">—</span>
                            {canManage && (
                              <Button
                                size="sm"
                                variant="ghost"
                                iconOnly
                                aria-label={`Assign doctor to ${patient.full_name}`}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleChangeDoctor(patient)
                                }}
                                leftIcon={<Icon name="plus" size={12} />}
                                title="Assign doctor"
                              />
                            )}
                          </div>
                        )}
                      </td>
                      <td className="small-muted">
                        {new Date(patient.created_at).toLocaleDateString(undefined, {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                        })}
                      </td>
                      <td onClick={(e) => e.stopPropagation()}>
                        {canManage ? (
                          <div style={{ display: 'flex', gap: 4 }}>
                            <Button
                              size="sm"
                              variant="ghost"
                              iconOnly
                              aria-label={`Edit ${patient.full_name}`}
                              onClick={() => handleEdit(patient)}
                              leftIcon={<Icon name="edit" size={14} />}
                            />
                            <Button
                              size="sm"
                              variant="ghost"
                              iconOnly
                              aria-label={`Delete ${patient.full_name}`}
                              onClick={() => handleDelete(patient)}
                              leftIcon={<Icon name="trash" size={14} />}
                            />
                          </div>
                        ) : (
                          <span className="small-muted">—</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <PatientFormModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSaved={() => fetchPatients()}
        initial={editing}
      />

      <PatientDetailModal
        open={!!detailPatient}
        patient={detailPatient}
        onClose={() => setDetailPatient(null)}
      />
    </div>
  )
}

export default PatientsPage
