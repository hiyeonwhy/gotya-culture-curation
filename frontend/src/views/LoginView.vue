<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'


const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const loginId = ref('')
const password = ref('')
const errorMessage = ref('')
const submitting = ref(false)

function formatError(error) {
  const data = error.response?.data
  if (!data) return '서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.'

  return Object.values(data)
    .flatMap((value) => (Array.isArray(value) ? value : [value]))
    .join(' ')
}

async function handleSubmit() {
  errorMessage.value = ''
  submitting.value = true

  try {
    await authStore.login({ login_id: loginId.value, password: password.value })
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.push(redirect)
  } catch (error) {
    errorMessage.value = formatError(error)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="auth-page">
    <form class="auth-card" @submit.prevent="handleSubmit">
      <h1>로그인</h1>

      <label>
        아이디
        <input v-model.trim="loginId" type="text" autocomplete="username" maxlength="50" required />
      </label>

      <label>
        비밀번호
        <input v-model="password" type="password" autocomplete="current-password" required />
      </label>

      <p v-if="errorMessage" class="error" role="alert">{{ errorMessage }}</p>

      <button type="submit" :disabled="submitting">
        {{ submitting ? '로그인 중...' : '로그인' }}
      </button>

      <p>아직 회원이 아니신가요? <RouterLink to="/signup">회원가입</RouterLink></p>
    </form>
  </main>
</template>

<style scoped src="../assets/auth.css"></style>
