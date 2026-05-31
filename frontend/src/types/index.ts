/**
 * TypeScript type definitions for MediSched AI.
 */

// User & Authentication
export interface User {
  id: number
  email: string
  username: string
  first_name: string
  last_name: string
  full_name: string
  role: 'ADMIN' | 'STAFF' | 'DOCTOR' | 'READONLY'
  role_display: string
  is_active: boolean
  date_joined: string
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface LoginResponse {
  access: string
  refresh: string
  user: User
}

// Patient
export interface Patient {
  id: number
  full_name: string
  phone_number: string
  date_of_birth: string
  age: number
  gender: 'MALE' | 'FEMALE' | 'OTHER'
  gender_display: string
  email?: string
  address?: string
  medical_notes?: string
  referring_doctor?: string
  assigned_doctor?: number | null
  assigned_doctor_name?: string | null
  created_at: string
  updated_at?: string
  created_by_name?: string
}

export interface PatientFormData {
  full_name: string
  phone_number: string
  date_of_birth: string
  gender: 'MALE' | 'FEMALE' | 'OTHER'
  email?: string
  address?: string
  medical_notes?: string
  referring_doctor?: string
}

// Doctor
export interface Doctor {
  id: number
  full_name: string
  specialization: string
  phone_number: string
  email: string
  status: 'ACTIVE' | 'INACTIVE'
  status_display: string
  user?: number
  user_email?: string
  created_at: string
  updated_at: string
}

export interface DoctorFormData {
  full_name: string
  specialization: string
  phone_number: string
  email: string
  status: 'ACTIVE' | 'INACTIVE'
  user?: number
}

// Doctor Slot
export interface DoctorSlot {
  id: number
  doctor: number
  doctor_name: string
  doctor_specialization: string
  slot_date: string
  start_time: string
  end_time: string
  duration: 30 | 60
  duration_display: string
  status: 'AVAILABLE' | 'BOOKED' | 'BLOCKED'
  status_display: string
  booked_patient?: number
  patient_name?: string
  booked_at?: string
  created_at: string
  updated_at: string
}

export interface SlotGenerateData {
  slot_date: string
  start_time: string
  end_time: string
  duration: 30 | 60
}

// API Error
export interface ApiError {
  error: string
  message: string
  status_code: number
  details?: Record<string, string[]>
}

// Pagination
export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
