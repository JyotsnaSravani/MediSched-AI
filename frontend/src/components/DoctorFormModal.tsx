import React, { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import Modal from './Modal'
import Button from './Button'
import { useToast } from './Toast'
import { doctorService } from '../services/doctorService'
import { Doctor, DoctorFormData } from '../types'

interface Props {
  open: boolean
  onClose: () => void
  onSaved: (doctor: Doctor) => void
  initial?: Doctor | null
}

const DoctorFormModal: React.FC<Props> = ({ open, onClose, onSaved, initial }) => {
  const toast = useToast()
  const [submitting, setSubmitting] = useState(false)
  const isEdit = !!initial

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<DoctorFormData>({
    defaultValues: {
      full_name: '',
      specialization: '',
      phone_number: '',
      email: '',
      status: 'ACTIVE',
    },
  })

  useEffect(() => {
    if (!open) return
    reset(
      initial
        ? {
            full_name: initial.full_name,
            specialization: initial.specialization,
            phone_number: initial.phone_number,
            email: initial.email,
            status: initial.status,
          }
        : {
            full_name: '',
            specialization: '',
            phone_number: '',
            email: '',
            status: 'ACTIVE',
          }
    )
  }, [open, initial, reset])

  const onSubmit = handleSubmit(async (values) => {
    setSubmitting(true)
    try {
      const saved = isEdit
        ? await doctorService.updateDoctor(initial!.id, values)
        : await doctorService.createDoctor(values)
      toast.success(isEdit ? 'Doctor updated' : 'Doctor added', `Dr. ${saved.full_name}`)
      onSaved(saved)
      onClose()
    } catch (err: any) {
      const data = err.response?.data
      const detail =
        data?.detail ||
        data?.email?.[0] ||
        data?.phone_number?.[0] ||
        data?.message ||
        'Failed to save doctor'
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
      title={isEdit ? 'Edit doctor' : 'Add doctor'}
      description="Doctors can be marked active/inactive to control availability."
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button variant="primary" onClick={onSubmit} loading={submitting}>
            {isEdit ? 'Save changes' : 'Add doctor'}
          </Button>
        </>
      }
    >
      <form onSubmit={onSubmit}>
        <div className="row g-3">
          <div className="col-md-6">
            <label className="form-label" htmlFor="d-name">
              Full name *
            </label>
            <input
              id="d-name"
              className="form-input"
              {...register('full_name', { required: 'Full name is required' })}
            />
            {errors.full_name && <div className="form-error">{errors.full_name.message}</div>}
          </div>
          <div className="col-md-6">
            <label className="form-label" htmlFor="d-spec">
              Specialization *
            </label>
            <input
              id="d-spec"
              className="form-input"
              placeholder="e.g. Cardiology"
              {...register('specialization', { required: 'Specialization is required' })}
            />
            {errors.specialization && (
              <div className="form-error">{errors.specialization.message}</div>
            )}
          </div>
          <div className="col-md-6">
            <label className="form-label" htmlFor="d-phone">
              Phone number *
            </label>
            <input
              id="d-phone"
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
            <label className="form-label" htmlFor="d-email">
              Email *
            </label>
            <input
              id="d-email"
              type="email"
              className="form-input"
              {...register('email', {
                required: 'Email is required',
                pattern: { value: /^\S+@\S+\.\S+$/, message: 'Enter a valid email' },
              })}
            />
            {errors.email && <div className="form-error">{errors.email.message}</div>}
          </div>
          <div className="col-md-6">
            <label className="form-label" htmlFor="d-status">
              Status
            </label>
            <select id="d-status" className="form-select" {...register('status')}>
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
            </select>
          </div>
        </div>
      </form>
    </Modal>
  )
}

export default DoctorFormModal
