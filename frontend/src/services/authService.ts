/**
 * Authentication service.
 * Handles login, logout, and token management.
 */

import api from './api'
import { LoginCredentials, LoginResponse, User } from '../types'

export const login = async (credentials: LoginCredentials): Promise<LoginResponse> => {
  const response = await api.post<LoginResponse>('/auth/login/', credentials)
  return response.data
}

export const logout = async (refreshToken: string): Promise<void> => {
  await api.post('/auth/logout/', { refresh: refreshToken })
}

export const getCurrentUser = async (): Promise<User> => {
  const response = await api.get<User>('/auth/me/')
  return response.data
}

export const refreshToken = async (refresh: string): Promise<{ access: string }> => {
  const response = await api.post<{ access: string }>('/auth/refresh/', { refresh })
  return response.data
}
