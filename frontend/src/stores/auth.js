import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import api, { AUTH_TOKEN_STORAGE_KEY } from '../api'


export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(AUTH_TOKEN_STORAGE_KEY))
  const user = ref(null)
  const loading = ref(false)

  const isAuthenticated = computed(() => Boolean(token.value && user.value))

  function setAuthentication(data) {
    token.value = data.token
    user.value = data.user
    localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, data.token)
  }

  function clearAuthentication() {
    token.value = null
    user.value = null
    localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY)
  }

  async function signup(payload) {
    const { data } = await api.post('/accounts/signup/', payload)
    setAuthentication(data)
    return data.user
  }

  async function login(payload) {
    const { data } = await api.post('/accounts/login/', payload)
    setAuthentication(data)
    return data.user
  }

  async function logout() {
    try {
      if (token.value) {
        await api.post('/accounts/logout/')
      }
    } catch {
      // 서버가 내려갔거나 토큰이 이미 만료됐어도 로컬 로그인 상태는 종료한다.
    } finally {
      clearAuthentication()
    }
  }

  async function fetchCurrentUser() {
    if (!token.value) {
      clearAuthentication()
      return null
    }

    const { data } = await api.get('/accounts/me/')
    user.value = data
    return data
  }

  async function uploadProfileImage(file) {
    const formData = new FormData()
    formData.append('profile_image', file)

    const { data } = await api.patch('/accounts/me/profile-image/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    user.value = data
    return data
  }

  async function updateProfile(payload) {
    const { data } = await api.patch('/accounts/me/', payload)
    user.value = data
    return data
  }

  async function initializeAuth() {
    if (!token.value || loading.value) return

    loading.value = true
    try {
      await fetchCurrentUser()
    } catch {
      clearAuthentication()
    } finally {
      loading.value = false
    }
  }

  window.addEventListener('auth:unauthorized', clearAuthentication)

  return {
    token,
    user,
    loading,
    isAuthenticated,
    signup,
    login,
    logout,
    fetchCurrentUser,
    uploadProfileImage,
    updateProfile,
    initializeAuth,
    clearAuthentication,
  }
})
