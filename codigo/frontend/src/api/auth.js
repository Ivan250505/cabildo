import api from "./client"

export const login = (email, password) =>
  api.post("/api/auth/login", { email, password }).then((r) => r.data)

export const getMe = () =>
  api.get("/api/auth/me").then((r) => r.data)

export const changePassword = (data) =>
  api.put("/api/auth/change-password", data)

export const logout = () =>
  api.post("/api/auth/logout")
