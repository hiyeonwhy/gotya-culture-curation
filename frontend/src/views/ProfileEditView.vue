<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import '../assets/mypage.css'


const router = useRouter()
const authStore = useAuthStore()
const saving = ref(false)
const error = ref('')

const form = reactive({
  login_id: '',
  nickname: '',
  email: '',
  password: '',
  password_confirm: '',
})

const profileInitial = computed(() => (
  authStore.user?.nickname?.trim()?.[0] || authStore.user?.login_id?.trim()?.[0] || '나'
))

function fillForm(user) {
  form.login_id = user?.login_id || ''
  form.nickname = user?.nickname || ''
  form.email = user?.email || ''
  form.password = ''
  form.password_confirm = ''
}

function extractError(requestError) {
  const data = requestError.response?.data
  if (data?.detail) return String(data.detail)
  if (data && typeof data === 'object') {
    const [field, messages] = Object.entries(data)[0] || []
    const message = Array.isArray(messages) ? messages[0] : messages
    if (message) return `${field}: ${message}`
  }
  return '회원정보를 수정하지 못했습니다.'
}

async function handleSubmit() {
  saving.value = true
  error.value = ''
  try {
    const payload = {
      login_id: form.login_id.trim(),
      nickname: form.nickname.trim(),
      email: form.email.trim() || null,
    }
    if (form.password || form.password_confirm) {
      payload.password = form.password
      payload.password_confirm = form.password_confirm
    }
    await authStore.updateProfile(payload)
    await router.push('/mypage')
  } catch (requestError) {
    error.value = extractError(requestError)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  if (!authStore.user && authStore.token) {
    await authStore.fetchCurrentUser().catch(() => {})
  }
  fillForm(authStore.user)
})
</script>

<template>
  <main class="mypage profile-edit-page">
    <section class="profile-edit-shell">
      <div class="profile-edit-header">
        <div class="profile-edit-avatar">
          <img
            v-if="authStore.user?.profile_image"
            :src="authStore.user.profile_image"
            :alt="`${authStore.user.nickname} 프로필`"
          >
          <span v-else>{{ profileInitial }}</span>
        </div>
        <div>
          <p class="eyebrow">ACCOUNT SETTINGS</p>
          <h1>회원정보 수정</h1>
          <p>아이디, 닉네임, 이메일, 비밀번호를 수정할 수 있습니다.</p>
        </div>
      </div>

      <form class="profile-edit-form" @submit.prevent="handleSubmit">
        <label>
          <span>아이디</span>
          <input
            v-model="form.login_id"
            type="text"
            maxlength="50"
            autocomplete="username"
            required
          >
        </label>

        <label>
          <span>닉네임</span>
          <input
            v-model="form.nickname"
            type="text"
            maxlength="50"
            required
          >
        </label>

        <label>
          <span>이메일</span>
          <input
            v-model="form.email"
            type="email"
            placeholder="example@email.com"
          >
        </label>

        <label>
          <span>새 비밀번호</span>
          <input
            v-model="form.password"
            type="password"
            autocomplete="new-password"
            placeholder="변경하지 않으려면 비워두세요"
          >
        </label>

        <label>
          <span>새 비밀번호 확인</span>
          <input
            v-model="form.password_confirm"
            type="password"
            autocomplete="new-password"
            placeholder="새 비밀번호를 한 번 더 입력하세요"
          >
        </label>

        <p v-if="error" class="mypage-error">{{ error }}</p>

        <div class="profile-edit-actions">
          <button type="button" class="secondary-button" @click="router.push('/mypage')">
            취소
          </button>
          <button type="submit" class="primary-button" :disabled="saving">
            {{ saving ? '저장 중...' : '저장하기' }}
          </button>
        </div>
      </form>
    </section>
  </main>
</template>
