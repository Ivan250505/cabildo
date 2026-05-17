import api from "./client"

export const getUsers       = (params)     => api.get("/api/users", { params }).then((r) => r.data)
export const createUser     = (data)       => api.post("/api/users", data).then((r) => r.data)
export const updateUser     = (id, data)   => api.put(`/api/users/${id}`, data).then((r) => r.data)
export const deleteUser     = (id)         => api.delete(`/api/users/${id}`)
export const resetPassword  = (id)         => api.post(`/api/users/${id}/reset-password`).then((r) => r.data)
