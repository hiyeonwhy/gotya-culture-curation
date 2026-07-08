<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'


const authStore = useAuthStore()
const router = useRouter()

const loginId = ref('')
const nickname = ref('')
const password = ref('')
const passwordConfirm = ref('')
const errorMessage = ref('')
const submitting = ref(false)

function formatError(error) {
  const data = error.response?.data
  if (!data) return '서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.'

  return Object.entries(data)
    .flatMap(([field, value]) => {
      const messages = Array.isArray(value) ? value : [value]
      return messages.map((message) => `${field}: ${message}`)
    })
    .join(' ')
}

async function handleSubmit() {
  errorMessage.value = ''

  if (password.value !== passwordConfirm.value) {
    errorMessage.value = '비밀번호가 일치하지 않습니다.'
    return
  }

  submitting.value = true
  try {
    await authStore.signup({
      login_id: loginId.value,
      nickname: nickname.value,
      password: password.value,
      password_confirm: passwordConfirm.value,
    })
    await router.push('/')
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
      <h1>회원가입</h1>

      <label>
        아이디
        <input v-model.trim="loginId" type="text" autocomplete="username" maxlength="50" required />
      </label>

      <label>
        닉네임
        <input v-model.trim="nickname" type="text" autocomplete="nickname" maxlength="50" required />
      </label>

      <label>
        비밀번호
        <input v-model="password" type="password" autocomplete="new-password" required />
      </label>

      <label>
        비밀번호 확인
        <input v-model="passwordConfirm" type="password" autocomplete="new-password" required />
      </label>

      <p v-if="errorMessage" class="error" role="alert">{{ errorMessage }}</p>

      <button type="submit" :disabled="submitting">
        {{ submitting ? '가입 중...' : '회원가입' }}
      </button>

      <p>이미 회원이신가요? <RouterLink to="/login">로그인</RouterLink></p>
    </form>
  </main>
</template>

<style scoped src="../assets/auth.css"></style>
