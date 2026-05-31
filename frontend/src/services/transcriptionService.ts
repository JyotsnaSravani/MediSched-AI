/**
 * Transcription service.
 * Handles all transcription-related API calls.
 * Sprint 3 - Call Transcription System
 */

import api from './api'

export interface Transcription {
  id: number
  call_log: number
  call_log_id: number
  patient_name: string
  patient_phone: string
  appointment: number | null
  appointment_id: number | null
  text: string
  status: string
  whisper_model: string
  confidence_score: number | null
  is_edited: boolean
  last_edited_by: number | null
  last_edited_by_name: string | null
  last_edited_at: string | null
  call_date: string
  call_duration: number | null
  recording_url: string | null
  word_count: number
  created_at: string
  updated_at: string
}

export interface TranscriptionUpdateData {
  text: string
}

// Transcriptions
export const getTranscriptions = async (params?: any): Promise<Transcription[]> => {
  const response = await api.get<{ results: Transcription[] }>('/transcriptions/', { params })
  return response.data.results
}

export const getTranscription = async (id: number): Promise<Transcription> => {
  const response = await api.get<Transcription>(`/transcriptions/${id}/`)
  return response.data
}

export const updateTranscriptionText = async (id: number, text: string): Promise<Transcription> => {
  const response = await api.patch<Transcription>(`/transcriptions/${id}/update-text/`, { text })
  return response.data
}

export const transcriptionService = {
  getTranscriptions,
  getTranscription,
  updateTranscriptionText
}
