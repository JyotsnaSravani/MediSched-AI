/**
 * Doctor service.
 * Handles all doctor-related API calls.
 */

import api from './api'
import { Doctor, DoctorFormData, DoctorSlot, SlotGenerateData } from '../types'

export const getDoctors = async (status?: string): Promise<Doctor[]> => {
  const params = status ? { status } : {}
  const response = await api.get<{ results: Doctor[] }>('/doctors/', { params })
  return response.data.results
}

export const getDoctor = async (id: number): Promise<Doctor> => {
  const response = await api.get<Doctor>(`/doctors/${id}/`)
  return response.data
}

export const createDoctor = async (data: DoctorFormData): Promise<Doctor> => {
  const response = await api.post<Doctor>('/doctors/', data)
  return response.data
}

export const updateDoctor = async (id: number, data: Partial<DoctorFormData>): Promise<Doctor> => {
  const response = await api.put<Doctor>(`/doctors/${id}/`, data)
  return response.data
}

export const deleteDoctor = async (id: number): Promise<void> => {
  await api.delete(`/doctors/${id}/`)
}

export const toggleDoctorStatus = async (id: number, status: 'ACTIVE' | 'INACTIVE'): Promise<Doctor> => {
  const response = await api.patch<Doctor>(`/doctors/${id}/`, { status })
  return response.data
}

// Doctor Slots
export const getDoctorSlots = async (doctorId: number, date?: string): Promise<DoctorSlot[]> => {
  const params = date ? { slot_date: date } : {}
  const response = await api.get<{ results: DoctorSlot[] }>(`/doctors/${doctorId}/slots/`, { params })
  return response.data.results
}

export const generateSlots = async (doctorId: number, data: SlotGenerateData): Promise<DoctorSlot[]> => {
  const response = await api.post<DoctorSlot[]>(`/doctors/${doctorId}/slots/generate/`, data)
  return response.data
}

export const blockSlot = async (doctorId: number, slotId: number): Promise<DoctorSlot> => {
  const response = await api.patch<DoctorSlot>(`/doctors/${doctorId}/slots/${slotId}/block/`)
  return response.data
}

export const unblockSlot = async (doctorId: number, slotId: number): Promise<DoctorSlot> => {
  const response = await api.patch<DoctorSlot>(`/doctors/${doctorId}/slots/${slotId}/unblock/`)
  return response.data
}

export const bookSlot = async (doctorId: number, slotId: number, patientId: number, notes?: string) => {
  const response = await api.post(`/doctors/${doctorId}/slots/${slotId}/book/`, {
    patient: patientId,
    notes: notes || ''
  })
  return response.data
}

export const doctorService = {
  getDoctors,
  getDoctor,
  createDoctor,
  updateDoctor,
  deleteDoctor,
  toggleDoctorStatus,
  getDoctorSlots,
  generateSlots,
  blockSlot,
  unblockSlot,
  bookSlot
}
