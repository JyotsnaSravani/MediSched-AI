/**
 * Reminder service.
 * Handles all reminder-related API calls.
 * Sprint 4 - Automated Reminder System
 */

import api from './api'

export interface ReminderLog {
  id: number
  appointment: number
  appointment_id: number
  appointment_date: string
  appointment_time: string
  patient: number
  patient_name: string
  patient_phone: string
  patient_email: string
  doctor_name: string
  reminder_type: string
  channel: string
  delivery_status: string
  message_text: string
  sent_at: string | null
  delivered_at: string | null
  twilio_message_sid: string | null
  email_message_id: string | null
  retry_count: number
  last_retry_at: string | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface ReminderStats {
  total: number
  sent: number
  delivered: number
  failed: number
  pending: number
  sms: number
  email: number
}

// Reminder Logs
export const getReminders = async (params?: any): Promise<ReminderLog[]> => {
  const response = await api.get<{ results: ReminderLog[] }>('/reminders/', { params })
  return response.data.results
}

export const getReminder = async (id: number): Promise<ReminderLog> => {
  const response = await api.get<ReminderLog>(`/reminders/${id}/`)
  return response.data
}

export const getReminderStats = async (): Promise<ReminderStats> => {
  const response = await api.get<ReminderStats>('/reminders/stats/')
  return response.data
}

export const reminderService = {
  getReminders,
  getReminder,
  getReminderStats
}
