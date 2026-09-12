import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '../api'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('tm_token') || '')
  const user = ref(JSON.parse(localStorage.getItem('tm_user') || 'null'))

  async function login(username: string, password: string) {
    const res: any = await authApi.login(username, password)
    token.value = res.token
    user.value = res.user
    localStorage.setItem('tm_token', res.token)
    localStorage.setItem('tm_user', JSON.stringify(res.user))
    return res
  }

  async function register(username: string, password: string, nickname?: string) {
    const res: any = await authApi.register(username, password, nickname)
    token.value = res.token
    user.value = res.user
    localStorage.setItem('tm_token', res.token)
    localStorage.setItem('tm_user', JSON.stringify(res.user))
    return res
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('tm_token')
    localStorage.removeItem('tm_user')
  }

  return { token, user, login, register, logout }
})
