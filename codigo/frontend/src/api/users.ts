import client from './client'
import type { BackendUser, UserListResponse } from '../types'

export async function getUsers(params?: { page?: number; limit?: number }): Promise<UserListResponse> {
  const { data } = await client.get<UserListResponse>('users', { params })
  return data
}

export async function createUser(payload: {
  nombre_completo: string
  email: string
  password: string
  rol: 'admin' | 'tecnico' | 'campo' | 'supervisor'
}): Promise<BackendUser> {
  const { data } = await client.post<BackendUser>('users', payload)
  return data
}

export async function updateUser(
  id: string,
  payload: { nombre_completo?: string; rol?: string; estado?: string }
): Promise<BackendUser> {
  const { data } = await client.put<BackendUser>(`users/${id}`, payload)
  return data
}

export async function deactivateUser(id: string): Promise<void> {
  await client.put(`users/${id}`, { estado: 'suspendido' })
}
