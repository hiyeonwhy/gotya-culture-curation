<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useCommunityStore } from '../stores/community'
import '../assets/community.css'


const communityStore = useCommunityStore()
const route = useRoute()
const router = useRouter()
const submitting = ref(false)
const formError = ref('')
const isEdit = computed(() => route.name === 'community-edit')

const form = reactive({
  category: 'recommendation',
  title: '',
  content: '',
})

const categories = [
  { value: 'recommendation', label: '추천' },
  { value: 'review', label: '후기' },
  { value: 'question', label: '질문' },
  { value: 'free', label: '자유' },
]

function extractError(error) {
  const data = error.response?.data
  if (data?.detail) return data.detail
  if (data && typeof data === 'object') return String(Object.values(data).flat()[0])
  return '게시글을 저장하지 못했습니다.'
}

async function submit() {
  formError.value = ''
  submitting.value = true
  try {
    const payload = { ...form }
    const post = isEdit.value
      ? await communityStore.updatePost(route.params.id, payload)
      : await communityStore.createPost(payload)
    await router.push({ name: 'community-detail', params: { id: post.id } })
  } catch (error) {
    formError.value = extractError(error)
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  if (!isEdit.value) return
  try {
    const post = await communityStore.fetchPost(route.params.id, false)
    if (!post.is_owner) {
      await router.replace({ name: 'community-detail', params: { id: post.id } })
      return
    }
    form.category = post.category
    form.title = post.title
    form.content = post.content
  } catch {
    formError.value = communityStore.error
  }
})
</script>

<template>
  <main class="community-page">
    <section class="community-container">
      <div class="community-heading">
        <h1>{{ isEdit ? '게시글 수정' : '새 게시글' }}</h1>
        <RouterLink class="secondary-button" to="/community">목록으로</RouterLink>
      </div>

      <div class="post-form-card">
        <form class="post-form" @submit.prevent="submit">
          <label>
            카테고리
            <select v-model="form.category" required>
              <option v-for="item in categories" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
          </label>

          <label>
            제목
            <input v-model="form.title" maxlength="255" required placeholder="제목을 입력하세요" />
          </label>

          <label>
            내용
            <textarea v-model="form.content" required placeholder="내용을 입력하세요"></textarea>
          </label>

          <p v-if="formError" class="community-error">{{ formError }}</p>

          <div class="post-actions">
            <button class="secondary-button" type="button" @click="router.back()">취소</button>
            <button class="primary-button" type="submit" :disabled="submitting">
              {{ submitting ? '저장 중...' : '저장' }}
            </button>
          </div>
        </form>
      </div>
    </section>
  </main>
</template>
