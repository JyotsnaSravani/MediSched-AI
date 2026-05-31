/**
 * Analytics service.
 * Handles all analytics-related API calls.
 * Sprint 4 - Analytics & Reporting
 */

import api from './api'

export interface DashboardStats {
  date_range: {
    start_date: string
    end_date: string
  }
  appointments: {
    total: number
    confirmed: number
    completed: number
    cancelled: number
    no_shows: number
    no_show_rate: number
  }
  slots: {
    total: number
    booked: number
    available: number
    blocked: number
    utilization_rate: number
  }
  calls: {
    total: number
    completed: number
    answered: number
    no_answer: number
    failed: number
    success_rate: number
  }
  reminders: {
    total: number
    sent: number
    delivered: number
    failed: number
  }
  doctors: DoctorStats[]
}

export interface DoctorStats {
  doctor_id: number
  doctor_name: string
  total_slots: number
  booked_slots: number
  total_appointments: number
  completed_appointments: number
  no_shows: number
  utilization_rate: number
}

export interface TrendsData {
  appointments: Array<{ date: string; count: number }>
  calls: Array<{ date: string; count: number }>
}

// Dashboard Stats
export const getDashboardStats = async (params?: any): Promise<DashboardStats> => {
  const response = await api.get<DashboardStats>('/analytics/dashboard/', { params })
  return response.data
}

// Trends Data
export const getTrendsData = async (): Promise<TrendsData> => {
  const response = await api.get<TrendsData>('/analytics/trends/')
  return response.data
}

// CSV Exports
export const exportAppointmentsCSV = async (params?: any): Promise<Blob> => {
  const response = await api.get('/analytics/export/appointments/', {
    params,
    responseType: 'blob'
  })
  return response.data
}

export const exportCallLogsCSV = async (params?: any): Promise<Blob> => {
  const response = await api.get('/analytics/export/call-logs/', {
    params,
    responseType: 'blob'
  })
  return response.data
}

export const analyticsService = {
  getDashboardStats,
  getTrendsData,
  exportAppointmentsCSV,
  exportCallLogsCSV
}
