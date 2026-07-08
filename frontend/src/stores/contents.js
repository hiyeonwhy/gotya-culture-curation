import { ref } from 'vue'
import { defineStore } from 'pinia'

import api from '../api'


const ENDPOINTS = {
  movies: '/movies/',
  books: '/books/',
  cultures: '/cultures/',
}

export const useContentsStore = defineStore('contents', () => {
  const items = ref([])
  const currentDetail = ref(null)
  const popularItems = ref({ movies: [], books: [] })
  const mapItems = ref([])
  const mapCount = ref(0)
  const regionSummaries = ref([])
  const mapLoading = ref(false)
  const mapError = ref('')
  const count = ref(0)
  const next = ref(null)
  const loading = ref(false)
  const detailLoading = ref(false)
  const error = ref('')
  let requestId = 0

  function messageFrom(error, fallback) {
    return error.response?.data?.detail || fallback
  }

  async function fetchItems(type, params = {}, append = false) {
    const currentRequestId = ++requestId
    loading.value = true
    error.value = ''

    try {
      const { data } = await api.get(ENDPOINTS[type], { params })
      if (currentRequestId !== requestId) return data

      items.value = append ? [...items.value, ...data.results] : data.results
      count.value = data.count
      next.value = data.next
      return data
    } catch (requestError) {
      if (currentRequestId === requestId) {
        error.value = messageFrom(requestError, '콘텐츠를 불러오지 못했습니다.')
      }
      throw requestError
    } finally {
      if (currentRequestId === requestId) loading.value = false
    }
  }

  async function fetchDetail(type, id) {
    detailLoading.value = true
    error.value = ''
    currentDetail.value = null
    try {
      const { data } = await api.get(`${ENDPOINTS[type]}${id}/`)
      currentDetail.value = data
      return data
    } catch (requestError) {
      error.value = messageFrom(requestError, '상세 정보를 불러오지 못했습니다.')
      throw requestError
    } finally {
      detailLoading.value = false
    }
  }

  async function fetchPopular(type) {
    if (!['movies', 'books'].includes(type)) return []
    const { data } = await api.get(ENDPOINTS[type], {
      params: { sort: 'popular', page: 1, page_size: 10 },
    })
    popularItems.value[type] = data.results
    return data.results
  }

  async function fetchCultureMapItems(params = {}) {
    mapLoading.value = true
    mapError.value = ''

    try {
      const { data } = await api.get(ENDPOINTS.cultures, {
        params: {
          map_scope: true,
          page: 1,
          page_size: 500,
          ...params,
        },
      })
      mapItems.value = data.results
      mapCount.value = data.count
      return data
    } catch (requestError) {
      mapItems.value = []
      mapCount.value = 0
      mapError.value = messageFrom(
        requestError,
        '지도에 표시할 문화행사를 불러오지 못했습니다.',
      )
      throw requestError
    } finally {
      mapLoading.value = false
    }
  }

  async function fetchCultureRegionSummaries(params = {}) {
    mapLoading.value = true
    mapError.value = ''
    try {
      const { data } = await api.get('/cultures/regions/summary/', { params })
      regionSummaries.value = data
      return data
    } catch (requestError) {
      regionSummaries.value = []
      mapError.value = messageFrom(requestError, '지역별 문화행사 현황을 불러오지 못했습니다.')
      throw requestError
    } finally {
      mapLoading.value = false
    }
  }

  function clearDetail() {
    currentDetail.value = null
  }

  return {
    items,
    currentDetail,
    popularItems,
    mapItems,
    mapCount,
    regionSummaries,
    mapLoading,
    mapError,
    count,
    next,
    loading,
    detailLoading,
    error,
    fetchItems,
    fetchDetail,
    fetchPopular,
    fetchCultureMapItems,
    fetchCultureRegionSummaries,
    clearDetail,
  }
})
