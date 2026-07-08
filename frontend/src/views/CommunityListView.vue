<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import { useCommunityStore } from '../stores/community'
import '../assets/community.css'


const authStore = useAuthStore()
const communityStore = useCommunityStore()
const router = useRouter()

const category = ref('')
const search = ref('')
const page = ref(1)
const pageCount = computed(() => Math.max(1, Math.ceil(communityStore.count / 10)))

const categories = [
  { value: '', label: '전체' },
  { value: 'recommendation', label: '추천' },
  { value: 'review', label: '후기' },
  { value: 'question', label: '질문' },
  { value: 'free', label: '자유' },
]

function formatDate(value) {
  return new Intl.DateTimeFormat('ko-KR', { dateStyle: 'medium' }).format(new Date(value))
}

async function loadPosts() {
  const params = { page: page.value }
  if (category.value) params.category = category.value
  if (search.value.trim()) params.search = search.value.trim()
  try {
    await communityStore.fetchPosts(params)
  } catch {
    // 스토어의 error 메시지를 화면에 표시한다.
  }
}

async function applyFilter() {
  page.value = 1
  await loadPosts()
}

async function selectCategory(value) {
  if (category.value === value) return
  category.value = value
  page.value = 1
  await loadPosts()
}

async function changePage(nextPage) {
  if (nextPage < 1 || nextPage > pageCount.value) return
  page.value = nextPage
  await loadPosts()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function goToWrite() {
  if (!authStore.isAuthenticated) {
    router.push({ name: 'login', query: { redirect: '/community/write' } })
    return
  }
  router.push({ name: 'community-write' })
}

onMounted(loadPosts)
</script>

<template>
  <main class="community-page">
    <section class="community-container">
      <div class="community-heading">
        <div>
          <h1>커뮤니티</h1>
          <p>추천과 후기, 궁금한 이야기를 함께 나눠보세요.</p>
        </div>
        <button class="primary-button" type="button" @click="goToWrite">글쓰기</button>
      </div>

      <section class="community-board">
        <nav class="community-category-tabs" aria-label="게시글 카테고리">
          <button
            v-for="item in categories"
            :key="item.value"
            class="category-tab"
            :class="{ active: category === item.value }"
            type="button"
            :aria-pressed="category === item.value"
            @click="selectCategory(item.value)"
          >
            {{ item.label }}
          </button>
        </nav>

        <div class="community-board-body">
          <form class="community-toolbar" @submit.prevent="applyFilter">
            <input v-model="search" type="search" placeholder="제목 또는 내용 검색" />
            <button class="secondary-button" type="submit">검색</button>
          </form>

          <p v-if="communityStore.loading" class="loading-state">게시글을 불러오는 중입니다.</p>
          <p v-else-if="communityStore.error" class="community-error">{{ communityStore.error }}</p>
          <p v-else-if="communityStore.posts.length === 0" class="empty-state">등록된 게시글이 없습니다.</p>

          <div v-else class="post-list">
            <RouterLink
              v-for="post in communityStore.posts"
              :key="post.id"
              class="post-card"
              :to="{ name: 'community-detail', params: { id: post.id } }"
            >
              <span class="category-badge">{{ post.category_display }}</span>
              <h2>{{ post.title }}</h2>
              <div class="post-meta">
                <span>{{ post.author.nickname }}</span>
                <span>{{ formatDate(post.created_at) }}</span>
                <span>조회 {{ post.view_count }}</span>
                <span>댓글 {{ post.comment_count }}</span>
              </div>
            </RouterLink>
          </div>

          <div v-if="communityStore.count > 0" class="pagination">
            <button class="secondary-button" type="button" :disabled="page <= 1" @click="changePage(page - 1)">
              이전
            </button>
            <span>{{ page }} / {{ pageCount }}</span>
            <button
              class="secondary-button"
              type="button"
              :disabled="page >= pageCount"
              @click="changePage(page + 1)"
            >
              다음
            </button>
          </div>
        </div>
      </section>
    </section>
  </main>
</template>
