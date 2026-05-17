import { create } from "zustand"
import { getMe, login as apiLogin, logout as apiLogout } from "../api/auth"

const useAuthStore = create((set) => ({
  user: null,
  loading: true,

  init: async () => {
    const token = localStorage.getItem("access_token")
    if (!token) return set({ loading: false })
    try {
      const user = await getMe()
      set({ user, loading: false })
    } catch {
      localStorage.clear()
      set({ user: null, loading: false })
    }
  },

  login: async (email, password) => {
    const data = await apiLogin(email, password)
    localStorage.setItem("access_token", data.access_token)
    localStorage.setItem("refresh_token", data.refresh_token)
    set({ user: data.user })
    return data.user
  },

  logout: async () => {
    try { await apiLogout() } catch { /* token ya inválido */ }
    localStorage.clear()
    set({ user: null })
  },
}))

export default useAuthStore
