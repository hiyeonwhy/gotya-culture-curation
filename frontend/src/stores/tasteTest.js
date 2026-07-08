import { ref } from 'vue'
import { defineStore } from 'pinia'

import api from '../api'


const ANSWERS_KEY = 'todayWhatTasteAnswers'
const RESULT_KEY = 'todayWhatTasteResult'

function readSessionJson(key, fallback) {
  try {
    const value = sessionStorage.getItem(key)
    return value ? JSON.parse(value) : fallback
  } catch {
    return fallback
  }
}

export const useTasteTestStore = defineStore('tasteTest', () => {
  const config = ref(null)
  const answers = ref(readSessionJson(ANSWERS_KEY, {}))
  const result = ref(readSessionJson(RESULT_KEY, null))
  const latestResult = ref(null)
  const loading = ref(false)
  const submitting = ref(false)
  const error = ref('')

  function extractError(requestError) {
    const data = requestError.response?.data
    if (data?.detail) return String(data.detail)
    if (data && typeof data === 'object') {
      const first = Object.values(data).flat()[0]
      if (first) return String(first)
    }
    return '취향 테스트 정보를 불러오지 못했습니다.'
  }

  async function fetchConfig() {
    if (config.value) return config.value
    loading.value = true
    error.value = ''
    try {
      const { data } = await api.get('/tastes/test/config/')
      config.value = data
      return data
    } catch (requestError) {
      error.value = extractError(requestError)
      throw requestError
    } finally {
      loading.value = false
    }
  }

  async function fetchLatestResult() {
    try {
      const { data } = await api.get('/tastes/test/results/latest/')
      latestResult.value = data.result
      return data.result
    } catch (requestError) {
      error.value = extractError(requestError)
      throw requestError
    }
  }

  function startNewTest() {
    answers.value = {}
    result.value = null
    error.value = ''
    sessionStorage.removeItem(ANSWERS_KEY)
    sessionStorage.removeItem(RESULT_KEY)
  }

  function clearResultData() {
    result.value = null
    latestResult.value = null
    sessionStorage.removeItem(RESULT_KEY)
  }

  function setAnswer(questionId, value) {
    answers.value = { ...answers.value, [questionId]: value }
    sessionStorage.setItem(ANSWERS_KEY, JSON.stringify(answers.value))
  }

  function hasAnswer(questionId) {
    return Object.prototype.hasOwnProperty.call(answers.value, questionId)
  }

  async function submitTest() {
    if (!config.value) await fetchConfig()
    const payload = {
      answers: config.value.questions.map((question) => ({
        question_id: question.question_id,
        answer: answers.value[question.question_id],
      })),
    }
    submitting.value = true
    error.value = ''
    try {
      const { data } = await api.post('/tastes/test/results/', payload)
      result.value = data
      if (data.saved) latestResult.value = data
      sessionStorage.setItem(RESULT_KEY, JSON.stringify(data))
      return data
    } catch (requestError) {
      error.value = extractError(requestError)
      throw requestError
    } finally {
      submitting.value = false
    }
  }

  return {
    config,
    answers,
    result,
    latestResult,
    loading,
    submitting,
    error,
    fetchConfig,
    fetchLatestResult,
    startNewTest,
    clearResultData,
    setAnswer,
    hasAnswer,
    submitTest,
  }
})
