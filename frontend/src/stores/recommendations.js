import { ref } from 'vue'
import { defineStore } from 'pinia'

import api from '../api'


export const useRecommendationStore = defineStore('recommendations', () => {
  const result = ref(null)
  const loading = ref(false)
  const enhancing = ref(false)
  const error = ref('')
  let requestSequence = 0

  function extractError(requestError) {
    if (requestError.code === 'ECONNABORTED') {
      return '추천 데이터 응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.'
    }
    const data = requestError.response?.data
    if (data?.detail) return data.detail
    if (data && typeof data === 'object') {
      const first = Object.values(data).flat()[0]
      if (first) return String(first)
    }
    return '추천 결과를 생성하지 못했습니다.'
  }

  async function enhanceRecommendations(payload, previewResult, sequence) {
    enhancing.value = true
    try {
      const enhancementPayload = {
        ...payload,
        taste_type: previewResult.profile.taste_type,
      }
      const { data } = await api.post(
        '/tastes/recommendations/generate/',
        enhancementPayload,
        { timeout: 20000 },
      )
      if (sequence === requestSequence && data.source === 'gms') {
        result.value = {
          ...data,
          profile: previewResult.profile,
        }
      }
    } catch {
      // DB 미리보기가 이미 표시되므로 GMS 실패는 사용자 흐름을 막지 않는다.
    } finally {
      if (sequence === requestSequence) enhancing.value = false
    }
  }

  async function generateRecommendations({
    tasteType = '',
    perType = 3,
    enhance = true,
    excludeContentIds = [],
  } = {}) {
    const sequence = ++requestSequence
    loading.value = true
    enhancing.value = false
    error.value = ''
    try {
      const payload = { per_type: perType }
      if (tasteType) payload.taste_type = tasteType
      if (excludeContentIds.length) payload.exclude_content_ids = excludeContentIds
      const { data } = await api.post(
        '/tastes/recommendations/preview/',
        payload,
        { timeout: 10000 },
      )
      if (sequence !== requestSequence) return data
      result.value = data
      if (enhance) void enhanceRecommendations(payload, data, sequence)
      return data
    } catch (requestError) {
      if (sequence === requestSequence) {
        error.value = extractError(requestError)
      }
      throw requestError
    } finally {
      if (sequence === requestSequence) loading.value = false
    }
  }

  function resetRecommendations() {
    requestSequence += 1
    result.value = null
    loading.value = false
    enhancing.value = false
    error.value = ''
  }

  return {
    result,
    loading,
    enhancing,
    error,
    generateRecommendations,
    resetRecommendations,
  }
})
