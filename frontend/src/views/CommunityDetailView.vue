<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import { useCommunityStore } from '../stores/community'
import '../assets/community.css'


const authStore = useAuthStore()
const communityStore = useCommunityStore()
const route = useRoute()
const router = useRouter()
const commentContent = ref('')
const editingCommentId = ref(null)
const editingContent = ref('')
const actionError = ref('')
const submitting = ref(false)

function formatDate(value) {
  return new Intl.DateTimeFormat('ko-KR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function extractError(error, fallback) {
  return error.response?.data?.detail || fallback
}

async function loadPost() {
  try {
    await communityStore.fetchPost(route.params.id)
  } catch {
    // 스토어의 error 메시지를 화면에 표시한다.
  }
}

async function removePost() {
  if (!window.confirm('게시글을 삭제할까요?')) return
  actionError.value = ''
  try {
    await communityStore.deletePost(route.params.id)
    await router.push({ name: 'community' })
  } catch (error) {
    actionError.value = extractError(error, '게시글을 삭제하지 못했습니다.')
  }
}

async function addComment() {
  if (!commentContent.value.trim()) return
  submitting.value = true
  actionError.value = ''
  try {
    await communityStore.createComment(route.params.id, commentContent.value)
    commentContent.value = ''
  } catch (error) {
    actionError.value = extractError(error, '댓글을 등록하지 못했습니다.')
  } finally {
    submitting.value = false
  }
}

function startEditComment(comment) {
  editingCommentId.value = comment.id
  editingContent.value = comment.content
}

async function saveComment(commentId) {
  if (!editingContent.value.trim()) return
  actionError.value = ''
  try {
    await communityStore.updateComment(route.params.id, commentId, editingContent.value)
    editingCommentId.value = null
    editingContent.value = ''
  } catch (error) {
    actionError.value = extractError(error, '댓글을 수정하지 못했습니다.')
  }
}

async function removeComment(commentId) {
  if (!window.confirm('댓글을 삭제할까요?')) return
  actionError.value = ''
  try {
    await communityStore.deleteComment(route.params.id, commentId)
  } catch (error) {
    actionError.value = extractError(error, '댓글을 삭제하지 못했습니다.')
  }
}

onMounted(loadPost)
</script>

<template>
  <main class="community-page">
    <section class="community-container">
      <p v-if="communityStore.loading && !communityStore.currentPost" class="loading-state">
        게시글을 불러오는 중입니다.
      </p>
      <p v-else-if="communityStore.error && !communityStore.currentPost" class="community-error">
        {{ communityStore.error }}
      </p>

      <template v-if="communityStore.currentPost">
        <article class="post-detail">
          <span class="category-badge">{{ communityStore.currentPost.category_display }}</span>
          <h1>{{ communityStore.currentPost.title }}</h1>
          <div class="post-meta">
            <span>{{ communityStore.currentPost.author.nickname }}</span>
            <span>{{ formatDate(communityStore.currentPost.created_at) }}</span>
            <span>조회 {{ communityStore.currentPost.view_count }}</span>
          </div>

          <div class="post-content">{{ communityStore.currentPost.content }}</div>

          <div class="post-actions">
            <RouterLink class="secondary-button" to="/community">목록</RouterLink>
            <template v-if="communityStore.currentPost.is_owner">
              <RouterLink
                class="secondary-button"
                :to="{ name: 'community-edit', params: { id: communityStore.currentPost.id } }"
              >
                수정
              </RouterLink>
              <button class="danger-button" type="button" @click="removePost">삭제</button>
            </template>
          </div>
        </article>

        <section class="comments-section">
          <h2>댓글 {{ communityStore.currentPost.comment_count }}</h2>

          <form v-if="authStore.isAuthenticated" class="comment-form" @submit.prevent="addComment">
            <textarea v-model="commentContent" required placeholder="댓글을 입력하세요"></textarea>
            <button class="primary-button" type="submit" :disabled="submitting">
              {{ submitting ? '등록 중...' : '댓글 등록' }}
            </button>
          </form>
          <p v-else>
            댓글을 작성하려면
            <RouterLink :to="{ name: 'login', query: { redirect: route.fullPath } }">로그인</RouterLink>해 주세요.
          </p>

          <p v-if="actionError" class="community-error">{{ actionError }}</p>
          <p v-if="communityStore.currentPost.comments.length === 0" class="empty-state">첫 댓글을 남겨보세요.</p>

          <div v-else class="comment-list">
            <article v-for="comment in communityStore.currentPost.comments" :key="comment.id" class="comment-item">
              <div class="comment-header">
                <span><strong>{{ comment.author.nickname }}</strong> · {{ formatDate(comment.created_at) }}</span>
                <div v-if="comment.is_owner" class="comment-actions">
                  <button class="text-button" type="button" @click="startEditComment(comment)">수정</button>
                  <button class="text-button" type="button" @click="removeComment(comment.id)">삭제</button>
                </div>
              </div>

              <form v-if="editingCommentId === comment.id" class="comment-edit" @submit.prevent="saveComment(comment.id)">
                <textarea v-model="editingContent" required></textarea>
                <div class="comment-actions">
                  <button class="text-button" type="button" @click="editingCommentId = null">취소</button>
                  <button class="secondary-button" type="submit">저장</button>
                </div>
              </form>
              <p v-else>{{ comment.content }}</p>
            </article>
          </div>
        </section>
      </template>
    </section>
  </main>
</template>
