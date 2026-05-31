/**
 * Patient service.
 * Handles all patient-related API calls.
 */

import api from './api'
import { Patient, PatientFormData, PaginatedResponse } from '../types'

export const getPatients = async (search?: string): Promise<PaginatedResponse<Patient>> => {
  const params = search ? { search } : {}
  const response = await api.get<PaginatedResponse<Patient>>('/patients/', { params })
  return response.data
}

export const getPatient = async (id: number): Promise<Patient> => {
  const response = await api.get<Patient>(`/patients/${id}/`)
  return response.data
}

export const createPatient = async (data: PatientFormData): Promise<Patient> => {
  const response = await api.post<Patient>('/patients/', data)
  return response.data
}

export const updatePatient = async (id: number, data: Partial<PatientFormData>): Promise<Patient> => {
  const response = await api.put<Patient>(`/patients/${id}/`, data)
  return response.data
}

export const deletePatient = async (id: number): Promise<void> => {
  await api.delete(`/patients/${id}/`)
}

export const importPatients = async (file: File): Promise<{
  status: string
  message: string
  success_count: number
  error_count: number
  errors: string[]
  patients: number[]
}> => {
  const formData = new FormData()
  formData.append('file', file)
  
  const response = await api.post('/patients/import/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

export const patientService = {
  getPatients,
  getPatient,
  createPatient,
  updatePatient,
  deletePatient,
  importPatients,
}
