import api from './api'

export interface Appointment {
  id: number
  slot: number
  patient: number
  patient_name: string
  patient_phone: string
  doctor_name: string
  doctor_specialization: string
  appointment_date: string
  appointment_time: string
  status: 'PENDING' | 'CONFIRMED' | 'COMPLETED' | 'CANCELLED' | 'NO_SHOW'
  status_display: string
  notes: string
  booked_by: number | null
  booked_by_name: string | null
  booked_at: string
  cancelled_at: string | null
  cancelled_by: number | null
  cancellation_reason: string
  updated_at: string
}

export const getAppointments = async (params?: Record<string, any>): Promise<Appointment[]> => {
  const response = await api.get<{ results: Appointment[] } | Appointment[]>('/appointments/', {
    params,
  })
  const data = response.data as any
  return Array.isArray(data) ? data : data.results || []
}

export const getAppointmentsForPatient = (patientId: number) =>
  getAppointments({ patient: patientId })

export const cancelAppointment = async (id: number, reason?: string) => {
  const response = await api.post(`/appointments/${id}/cancel/`, { reason: reason || '' })
  return response.data
}

export const appointmentService = {
  getAppointments,
  getAppointmentsForPatient,
  cancelAppointment,
}
