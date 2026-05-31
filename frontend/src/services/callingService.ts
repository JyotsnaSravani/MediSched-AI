/**
 * Calling service.
 * Handles all calling-related API calls.
 * Sprint 3 - AI Calling System
 */

import api from './api'

export interface CallLog {
  id: number
  patient: number
  patient_name: string
  patient_phone: string
  appointment: number | null
  appointment_id: number | null
  call_type: string
  attempt_number: number
  outcome: string
  twilio_call_sid: string | null
  twilio_recording_url: string | null
  duration: number | null
  transcription_status: string
  has_transcription: boolean
  transcription_id: number | null
  initiated_at: string
  completed_at: string | null
  notes: string
}

export interface ManualCallbackTask {
  id: number
  patient: number
  patient_name: string
  patient_phone: string
  appointment: number | null
  appointment_id: number | null
  status: string
  reason: string
  notes: string
  assigned_to: number | null
  assigned_to_name: string | null
  created_at: string
  completed_at: string | null
  completed_by: number | null
  completed_by_name: string | null
}

export interface InitiateCallData {
  patient_id: number
  appointment_id?: number
  call_type?: string
  notes?: string
}

// Call Logs
export const getCallLogs = async (params?: any): Promise<CallLog[]> => {
  const response = await api.get<{ results: CallLog[] }>('/calling/logs/', { params })
  return response.data.results
}

export const getCallLog = async (id: number): Promise<CallLog> => {
  const response = await api.get<CallLog>(`/calling/logs/${id}/`)
  return response.data
}

export const initiateCall = async (data: InitiateCallData) => {
  const response = await api.post('/calling/logs/initiate/', data)
  return response.data
}

// Manual Callback Tasks
export const getManualCallbackTasks = async (params?: any): Promise<ManualCallbackTask[]> => {
  const response = await api.get<{ results: ManualCallbackTask[] }>('/calling/manual-tasks/', { params })
  return response.data.results
}

export const getManualCallbackTask = async (id: number): Promise<ManualCallbackTask> => {
  const response = await api.get<ManualCallbackTask>(`/calling/manual-tasks/${id}/`)
  return response.data
}

export const updateManualCallbackTask = async (id: number, data: Partial<ManualCallbackTask>): Promise<ManualCallbackTask> => {
  const response = await api.patch<ManualCallbackTask>(`/calling/manual-tasks/${id}/`, data)
  return response.data
}

export const completeManualCallbackTask = async (id: number, notes?: string) => {
  const response = await api.post(`/calling/manual-tasks/${id}/complete/`, { notes })
  return response.data
}

export const callingService = {
  getCallLogs,
  getCallLog,
  initiateCall,
  getManualCallbackTasks,
  getManualCallbackTask,
  updateManualCallbackTask,
  completeManualCallbackTask
}
