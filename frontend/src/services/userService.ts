/**
 * User management service (Admin only).
 */
import api from './api'
import { User } from '../types'

export interface UserCreateData {
  email: string
  username: string
  first_name: string
  last_name: string
  role: 'ADMIN' | 'STAFF' | 'DOCTOR' | 'READONLY'
  password: string
  password_confirm: string
}

export interface UserUpdateData {
  email?: string
  first_name?: string
  last_name?: string
  role?: 'ADMIN' | 'STAFF' | 'DOCTOR' | 'READONLY'
  is_active?: boolean
}

export const listUsers = async (): Promise<User[]> => {
  const response = await api.get<User[] | { results: User[] }>('/auth/users/')
  return Array.isArray(response.data) ? response.data : response.data.results
}

export const createUser = async (data: UserCreateData): Promise<User> => {
  const response = await api.post<User>('/auth/users/', data)
  return response.data
}

export const updateUser = async (id: number, data: UserUpdateData): Promise<User> => {
  const response = await api.patch<User>(`/auth/users/${id}/`, data)
  return response.data
}

export const deleteUser = async (id: number): Promise<void> => {
  await api.delete(`/auth/users/${id}/`)
}

export const userService = { listUsers, createUser, updateUser, deleteUser }
