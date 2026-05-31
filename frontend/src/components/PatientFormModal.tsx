import React, { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import Modal from './Modal'
import Button from './Button'
import { useToast } from './Toast'
import { patientService } from '../services/patientService'
import { doctorService } from '../services/doctorService'
import { Doctor, Patient, PatientFormData } from '../types'

interface Props {
  open: boolean
  onClose: () => void
  onSaved: (patient: Patient) => void
  initial?: Patient | null
}

type FormValues = PatientFormData & { assigned_doctor?: number | '' }

const PatientFormModal: React.FC<Props> = ({ open, onClose, onSaved, initial }) => {
  const toast = useToast()
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [submitting, setSubmitting] = useState(false)
  const isEdit = !!initial

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    defaultValues: {
      full_name: '',
      phone_number: '',
      date_of_birth: '',
      gender: 'MALE',
      email: '',
      address: '',
      medical_notes: '',
      referring_doctor: '',
      assigned_doctor: '',
    },
  })

  useEffect(() => {
    if (!open) return
    doctorService.getDoctors('ACTIVE').then(setDoctors).catch(() => setDoctors([]))
    reset(
      initial
        ? {
            full_name: initial.full_name,
            phone_number: initial.phone_number,
            date_of_birth: initial.date_of_birth,
            gender: initial.gender,
            email: initial.email || '',
            address: initial.address || '',
            medical_notes: initial.medical_notes || '',
            referring_doctor: initial.referring_doctor || '',
            assigned_doctor: (initial as any).assigned_doctor ?? '',
          }
        : {
            full_name: '',
            phone_number: '',
            date_of_birth: '',
            gender: 'MALE',
            email: '',
            address: '',
            medical_notes: '',
            referring_doctor: '',
            assigned_doctor: '',
          }
    )
  }, [open, initial, reset])

  const onSubmit = handleSubmit(async (values) => {
    setSubmitting(true)
    try {
      const payload: any = {
        ...values,
        assigned_doctor: values.assigned_doctor === '' ? null : Number(values.assigned_doctor),
        email: values.email || undefined,
      }
      const saved = isEdit
        ? await patientService.updatePatient(initial!.id, payload)
        : await patientService.createPatient(payload)
      toast.success(isEdit ? 'Patient updated' : 'Patient added', saved.full_name)
      onSaved(saved)
      onClose()
    } catch (err: any) {
      const detail =
        err.response?.data?.detail ||
        err.response?.data?.phone_number?.[0] ||
        err.response?.data?.message ||
        'Failed to save patient'
      toast.error('Save failed', detail)
    } finally {
      setSubmitting(false)
    }
  })

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="lg"
      title={isEdit ? 'Edit patient' : 'New patient'}
      description="Required fields are marked with an asterisk."
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button variant="primary" onClick={onSubmit} loading={submitting}>
            {isEdit ? 'Save changes' : 'Add patient'}
          </Button>
        </>
      }
    >
      <form onSubmit={onSubmit}>
        <div className="row g-3">
          <div className="col-md-6">
            <label className="form-label" htmlFor="p-name">
              Full name *
            </label>
            <input
              id="p-name"
              className="form-input"
              {...register('full_name', { required: 'Full name is required' })}
            />
            {errors.full_name && <div className="form-error">{errors.full_name.message}</div>}
          </div>
          <div className="col-md-6">
            <label className="form-label" htmlFor="p-phone">
              Phone number *
            </label>
            <input
              id="p-phone"
              className="form-input"
              placeholder="+919876543210"
              {...register('phone_number', {
                required: 'Phone number is required',
                pattern: {
                  value: /^\+?\d{9,15}$/,
                  message: 'Use 9–15 digits, optional + prefix',
                },
              })}
            />
            {errors.phone_number && (
              <div className="form-error">{errors.phone_number.message}</div>
            )}
          </div>
          <div className="col-md-6">
            <label className="form-label" htmlFor="p-dob">
              Date of birth *
            </label>
            <input
              id="p-dob"
              type="date"
              className="form-input"
              {...register('date_of_birth', { required: 'Date of birth is required' })}
            />
            {errors.date_of_birth && (
              <div className="form-error">{errors.date_of_birth.message}</div>
            )}
          </div>
          <div className="col-md-6">
            <label className="form-label" htmlFor="p-gender">
              Gender *
            </label>
            <select id="p-gender" className="form-select" {...register('gender', { required: true })}>
              <option value="MALE">Male</option>
              <option value="FEMALE">Female</option>
              <option value="OTHER">Other</option>
            </select>
          </div>
          <div className="col-md-6">
            <label className="form-label" htmlFor="p-email">
              Email
            </label>
            <input
              id="p-email"
              type="email"
              className="form-input"
              {...register('email', {
                pattern: { value: /^\S+@\S+\.\S+$/, message: 'Enter a valid email' },
              })}
            />
            {errors.email && <div className="form-error">{errors.email.message}</div>}
          </div>
          <div className="col-md-6">
            <label className="form-label" htmlFor="p-doctor">
              Assigned doctor
            </label>
            <select
              id="p-doctor"
              className="form-select"
              {...register('assigned_doctor')}
            >
              <option value="">— None —</option>
              {doctors.map((d) => (
                <option key={d.id} value={d.id}>
                  Dr. {d.full_name} · {d.specialization}
                </option>
              ))}
            </select>
          </div>
          <div className="col-md-12">
            <label className="form-label" htmlFor="p-address">
              Address
            </label>
            <textarea id="p-address" className="form-textarea" {...register('address')} />
          </div>
          <div className="col-md-12">
            <label className="form-label" htmlFor="p-notes">
              Medical notes
            </label>
            <textarea id="p-notes" className="form-textarea" {...register('medical_notes')} />
          </div>
          <div className="col-md-12">
            <label className="form-label" htmlFor="p-ref">
              Referring doctor
            </label>
            <input id="p-ref" className="form-input" {...register('referring_doctor')} />
          </div>
        </div>
      </form>
    </Modal>
  )
}

export default PatientFormModal
