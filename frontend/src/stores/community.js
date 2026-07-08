import { ref } from 'vue'
import { defineStore } from 'pinia'

import api from '../api'


export const useCommunityStore = defineStore('community', () => {
  const posts = ref([])
  const currentPost = ref(null)
  const count = ref(0)
  const next = ref(null)
  const previous = ref(null)
  const loading = ref(false)
  const error = ref('')

  function errorMessage(requestError, fallback) {
    const data = requestError.response?.data
    if (typeof data === 'string') return data
    if (data?.detail) return data.detail
    if (data && typeof data === 'object') {
      const first = Object.values(data).flat()[0]
      if (first) return String(first)
    }
    return fallback
  }

  async function fetchPosts(params = {}) {
    loading.value = true
    error.value = ''
    try {
      const { data } = await api.get('/community/posts/', { params })
      posts.value = data.results
      count.value = data.count
      next.value = data.next
      previous.value = data.previous
      return data
    } catch (requestError) {
      error.value = errorMessage(requestError, '게시글을 불러오지 못했습니다.')
      throw requestError
    } finally {
      loading.value = false
    }
  }

  async function fetchPost(postId, trackView = true) {
    loading.value = true
    error.value = ''
    if (currentPost.value?.id !== Number(postId)) currentPost.value = null
    try {
      const { data } = await api.get(`/community/posts/${postId}/`, {
        params: { track_view: trackView },
      })
      currentPost.value = data
      return data
    } catch (requestError) {
      error.value = errorMessage(requestError, '게시글을 불러오지 못했습니다.')
      throw requestError
    } finally {
      loading.value = false
    }
  }

  async function createPost(payload) {
    const { data } = await api.post('/community/posts/', payload)
    return data
  }

  async function updatePost(postId, payload) {
    const { data } = await api.patch(`/community/posts/${postId}/`, payload)
    currentPost.value = data
    return data
  }

  async function deletePost(postId) {
    await api.delete(`/community/posts/${postId}/`)
    if (currentPost.value?.id === Number(postId)) currentPost.value = null
  }

  async function createComment(postId, content) {
    const { data } = await api.post(`/community/posts/${postId}/comments/`, { content })
    if (currentPost.value?.id === Number(postId)) {
      currentPost.value.comments.push(data)
      currentPost.value.comment_count += 1
    }
    return data
  }

  async function updateComment(postId, commentId, content) {
    const { data } = await api.patch(`/community/comments/${commentId}/`, { content })
    if (currentPost.value?.id === Number(postId)) {
      const index = currentPost.value.comments.findIndex((comment) => comment.id === commentId)
      if (index !== -1) currentPost.value.comments[index] = data
    }
    return data
  }

  async function deleteComment(postId, commentId) {
    await api.delete(`/community/comments/${commentId}/`)
    if (currentPost.value?.id === Number(postId)) {
      currentPost.value.comments = currentPost.value.comments.filter((comment) => comment.id !== commentId)
      currentPost.value.comment_count -= 1
    }
  }

  return {
    posts,
    currentPost,
    count,
    next,
    previous,
    loading,
    error,
    fetchPosts,
    fetchPost,
    createPost,
    updatePost,
    deletePost,
    createComment,
    updateComment,
    deleteComment,
  }
})
