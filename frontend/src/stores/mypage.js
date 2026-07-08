import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import api from '../api'


export const useMyPageStore = defineStore('mypage', () => {
  const bookmarks = ref([])
  const count = ref(0)
  const next = ref(null)
  const selectedCollection = ref('bookmarks')
  const selectedType = ref('')
  const page = ref(1)
  const loading = ref(false)
  const error = ref('')

  const hasMore = computed(() => Boolean(next.value))

  function messageFrom(requestError, fallback) {
    return requestError.response?.data?.detail || fallback
  }

  function endpointFor(collection) {
    return collection === 'dislikes'
      ? '/tastes/feedback/dislikes/'
      : '/tastes/bookmarks/'
  }

  async function fetchCollection({
    collection = selectedCollection.value,
    contentType = selectedType.value,
    targetPage = 1,
    append = false,
  } = {}) {
    if (loading.value) return null

    loading.value = true
    error.value = ''
    try {
      const params = { page: targetPage, page_size: 12 }
      if (contentType) params.content_type = contentType

      const { data } = await api.get(endpointFor(collection), { params })
      selectedCollection.value = collection
      selectedType.value = contentType
      page.value = targetPage
      bookmarks.value = append ? [...bookmarks.value, ...data.results] : data.results
      count.value = data.count
      next.value = data.next
      return data
    } catch (requestError) {
      error.value = messageFrom(requestError, '목록을 불러오지 못했습니다.')
      throw requestError
    } finally {
      loading.value = false
    }
  }

  async function fetchBookmarks(options = {}) {
    return fetchCollection({ ...options, collection: 'bookmarks' })
  }

  async function fetchDislikes(options = {}) {
    return fetchCollection({ ...options, collection: 'dislikes' })
  }

  async function fetchNextBookmarks() {
    if (!next.value || loading.value) return null
    return fetchCollection({
      collection: selectedCollection.value,
      contentType: selectedType.value,
      targetPage: page.value + 1,
      append: true,
    })
  }

  function reset() {
    bookmarks.value = []
    count.value = 0
    next.value = null
    selectedCollection.value = 'bookmarks'
    selectedType.value = ''
    page.value = 1
    error.value = ''
  }

  function removeItem(id) {
    bookmarks.value = bookmarks.value.filter((item) => item.id !== id)
    count.value = Math.max(count.value - 1, 0)
  }

  return {
    bookmarks,
    count,
    next,
    selectedCollection,
    selectedType,
    page,
    loading,
    error,
    hasMore,
    fetchCollection,
    fetchBookmarks,
    fetchDislikes,
    fetchNextBookmarks,
    removeItem,
    reset,
  }
})
