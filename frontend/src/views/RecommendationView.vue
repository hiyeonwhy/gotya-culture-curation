<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import { useRecommendationStore } from '../stores/recommendations'
import { useTasteTestStore } from '../stores/tasteTest'
import resultBackground from '../assets/images/taste-result/result-background.png'
import '../assets/recommendations.css'
import '../assets/taste-test.css'


const router = useRouter()
const authStore = useAuthStore()
const recommendationStore = useRecommendationStore()
const tasteTestStore = useTasteTestStore()
const tasteType = ref('')
const activeType = ref('book')
const showAll = ref(false)
const visibleCount = ref(5)
const startIndexes = reactive({ book: 0, movie: 0, culture: 0 })

const tastes = [
  { value: 'TREND', label: '유행 탑승형' },
  { value: 'MONGLE', label: '마음 몽글형' },
  { value: 'WORLD', label: '세계관 과몰입형' },
  { value: 'KNOWLEDGE', label: '지식 냠냠형' },
  { value: 'FESTIVAL', label: '축제 팔랑귀형' },
  { value: 'TOGETHER', label: '같이보기 찰떡형' },
]

const profile = computed(() => recommendationStore.result?.profile || null)
const isLoggedIn = computed(
  () => profile.value?.is_authenticated ?? Boolean(authStore.token),
)
const displayedTasteResult = computed(() => (
  isLoggedIn.value ? tasteTestStore.latestResult : tasteTestStore.result
))
const sections = computed(() => {
  const recommendations = recommendationStore.result?.recommendations || {}
  return [
    { key: 'book', title: '도서', items: recommendations.book || [] },
    { key: 'movie', title: '영화', items: recommendations.movie || [] },
    { key: 'culture', title: '문화', items: recommendations.culture || [] },
  ]
})
const activeSection = computed(
  () => sections.value.find((section) => section.key === activeType.value) || sections.value[0],
)
const isRandomRecommendation = computed(
  () => profile.value?.selection_source === 'random' && !displayedTasteResult.value,
)
const maxStartIndex = computed(() => Math.max(
  activeSection.value.items.length - visibleCount.value,
  0,
))
const visibleItems = computed(() => {
  if (showAll.value) return activeSection.value.items
  const start = startIndexes[activeType.value]
  return activeSection.value.items.slice(start, start + visibleCount.value)
})
const axisRows = computed(() => displayedTasteResult.value?.axis_percentages || [])

function updateVisibleCount() {
  if (window.innerWidth <= 640) visibleCount.value = 1
  else if (window.innerWidth <= 900) visibleCount.value = 2
  else if (window.innerWidth <= 1180) visibleCount.value = 3
  else visibleCount.value = 5

  for (const section of sections.value) {
    const max = Math.max(section.items.length - visibleCount.value, 0)
    startIndexes[section.key] = Math.min(startIndexes[section.key], max)
  }
}

function move(direction) {
  startIndexes[activeType.value] = Math.min(
    Math.max(startIndexes[activeType.value] + direction, 0),
    maxStartIndex.value,
  )
}

function selectSection(key) {
  activeType.value = key
  showAll.value = false
}

function formatCompactDate(value) {
  if (!value) return ''
  const date = new Date(`${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
  }).format(date)
}

function recommendationMetaText(item) {
  if (activeType.value === 'culture') {
    const startDate = formatCompactDate(item.metadata?.start_date)
    const endDate = formatCompactDate(item.metadata?.end_date)
    if (startDate && endDate) return `${startDate} ~ ${endDate}`
    return startDate || endDate || '기간 미정'
  }

  const labels = activeType.value === 'movie'
    ? item.metadata?.genres
    : item.metadata?.categories

  return labels?.filter(Boolean).slice(0, 2).join(' · ') || activeSection.value.title
}

async function generate({ useDisplayedResult = false } = {}) {
  const resolvedTasteType = useDisplayedResult
    ? displayedTasteResult.value?.result.code || ''
    : tasteType.value
  try {
    await recommendationStore.generateRecommendations({
      tasteType: resolvedTasteType,
      perType: 10,
      enhance: isLoggedIn.value || Boolean(displayedTasteResult.value),
    })
    Object.keys(startIndexes).forEach((key) => { startIndexes[key] = 0 })
    showAll.value = false
  } catch {
    // 추천 오류 메시지는 스토어 상태로 화면에 표시됩니다.
  }
}

async function restartTest() {
  tasteTestStore.startNewTest()
  recommendationStore.resetRecommendations()
  await router.push({ name: 'taste-test-start', query: { restart: '1' } })
}

function clearAnonymousTasteResult() {
  if (isLoggedIn.value) return
  tasteTestStore.clearResultData()
  recommendationStore.resetRecommendations()
}

watch(visibleCount, () => {
  startIndexes[activeType.value] = Math.min(
    startIndexes[activeType.value],
    maxStartIndex.value,
  )
})

onMounted(async () => {
  updateVisibleCount()
  window.addEventListener('resize', updateVisibleCount)
  try {
    await Promise.all([
      tasteTestStore.fetchConfig(),
      tasteTestStore.fetchLatestResult(),
    ])
  } catch {
    // 취향 결과가 없어도 랜덤 추천은 계속 진행합니다.
  }
  if (displayedTasteResult.value) {
    tasteType.value = displayedTasteResult.value.result.code
  }
  await generate({ useDisplayedResult: true })
})

onBeforeUnmount(() => {
  clearAnonymousTasteResult()
  window.removeEventListener('resize', updateVisibleCount)
})
</script>

<template>
  <main
    class="recommendation-page"
    :style="{ '--result-bg-image': `url(${resultBackground})` }"
  >
    <section class="recommendation-container">
      <header class="recommendation-header">
        <p class="recommendation-eyebrow">GOTYA AI CURATION</p>
        <h1>오늘의 도파민,<br><strong>AI</strong>가 한 번 더 뽑아드려요.</h1>
        <p>취향 결과와 서비스 DB의 실제 콘텐츠를 바탕으로 도서·영화·문화생활을 추천합니다.</p>
      </header>

      <template v-if="displayedTasteResult">
        <section class="result-hero recommendation-result-hero">
          <div class="result-capsule-visual" aria-hidden="true">
            <span class="gotya-capsule movie"></span>
            <span class="gotya-capsule culture"></span>
          </div>

          <div class="result-copy">
            <span class="taste-kicker">MY CULTURE TASTE</span>
            <p>당신의 오늘 취향은</p>
            <h1>{{ displayedTasteResult.result.name }}</h1>
            <strong>{{ displayedTasteResult.result.subtitle }}</strong>
            <p class="result-summary">{{ displayedTasteResult.result.summary }}</p>
            <div class="result-keywords">
              <span
                v-for="keyword in displayedTasteResult.result.keywords.slice(0, 9)"
                :key="keyword"
              >
                #{{ keyword }}
              </span>
            </div>
          </div>

          <div class="result-composition">
            <h2>나의 취향 구성도</h2>
            <div v-for="row in axisRows" :key="row.key" class="result-score-row">
              <div>
                <span>{{ row.left_label }}</span>
                <strong>{{ (Number(row.left_percentage) / 10).toFixed(1) }}</strong>
              </div>
              <div class="result-score-track" aria-hidden="true">
                <span :style="{ width: `${row.left_percentage}%` }"></span>
              </div>
              <div>
                <span>{{ row.right_label }}</span>
                <strong>{{ (Number(row.right_percentage) / 10).toFixed(1) }}</strong>
              </div>
            </div>
          </div>
        </section>

        <section class="recommendation-retest-only">
          <button type="button" class="taste-secondary-button" @click="restartTest">
            다시 테스트하기
          </button>
        </section>
      </template>

      <section v-else class="taste-banner recommendation-test-banner">
        <div class="guest-banner-copy">
          <span class="taste-eyebrow">TRY GOTYA FIRST</span>
          <strong>취향 테스트로 나만의 캡슐을 열어보세요.</strong>
          <p>
            로그인하지 않아도 바로 추천을 볼 수 있어요. 먼저 랜덤 추천을 보여드리고,
            테스트 후에는 당신의 취향에 맞춰 더 정교하게 추천합니다.
          </p>
        </div>
        <div class="guest-capsule-preview" aria-hidden="true">
          <span class="gotya-capsule movie"></span>
          <span class="gotya-capsule book"></span>
          <span class="gotya-capsule culture"></span>
        </div>
        <div class="guest-test-cta">
          <RouterLink to="/taste-test">취향 테스트 시작하기</RouterLink>
        </div>
      </section>

      <p v-if="recommendationStore.error" class="recommendation-error">
        {{ recommendationStore.error }}
      </p>

      <template v-if="recommendationStore.result">
        <div class="recommendation-profile">
          <template v-if="isRandomRecommendation">
            취향 테스트 전이라 <strong>랜덤 GotYA 추천</strong>을 보여드려요.
          </template>
          <template v-else>
            적용 취향: <strong>{{ profile.taste_label }}</strong>
          </template>
          <span v-if="recommendationStore.result.source === 'database_preview'">
            · DB 즉시 추천
          </span>
          <span v-else> · AI 반영 추천</span>
          <span v-if="recommendationStore.enhancing" class="recommendation-enhancing">
            · AI가 추천 순서를 정리하는 중
          </span>
        </div>

        <section class="recommendation-box">
          <div class="recommendation-tabs" role="tablist" aria-label="추천 콘텐츠 유형">
            <button
              v-for="section in sections"
              :key="section.key"
              type="button"
              role="tab"
              :aria-selected="activeType === section.key"
              :class="{ active: activeType === section.key }"
              @click="selectSection(section.key)"
            >
              {{ section.title }}
            </button>
          </div>

          <div class="recommendation-box-content">
            <div class="recommendation-box-heading">
              <div>
                <span>{{ isRandomRecommendation ? '오늘의 랜덤 캡슐' : '취향 맞춤 캡슐' }}</span>
                <h2>{{ activeSection.title }} 추천</h2>
              </div>
              <span>{{ activeSection.items.length }}개</span>
            </div>

            <p v-if="activeSection.items.length === 0" class="recommendation-empty">
              추천 가능한 콘텐츠가 없습니다. 먼저 전체 콘텐츠를 DB에 동기화해 주세요.
            </p>
            <div
              v-else
              class="recommendation-grid"
              :class="{ 'show-all': showAll }"
              :style="{ '--visible-count': visibleCount }"
            >
              <article
                v-for="item in visibleItems"
                :key="item.content_item_id"
                class="recommendation-card"
              >
                <img :src="item.thumbnail_url" :alt="`${item.title} 이미지`" />
                <div class="recommendation-card-body">
                  <p>{{ recommendationMetaText(item) }}</p>
                  <h3>{{ item.title }}</h3>
                </div>
              </article>
            </div>

            <footer v-if="activeSection.items.length" class="recommendation-box-footer">
              <button type="button" class="more-button" @click="showAll = !showAll">
                {{ showAll ? '슬라이드로 보기' : '전체 보기' }}
              </button>
              <div v-if="!showAll" class="carousel-controls">
                <span>{{ startIndexes[activeType] + 1 }} / {{ maxStartIndex + 1 }}</span>
                <button
                  type="button"
                  aria-label="이전 추천 보기"
                  :disabled="startIndexes[activeType] === 0"
                  @click="move(-1)"
                >&lt;</button>
                <button
                  type="button"
                  aria-label="다음 추천 보기"
                  :disabled="startIndexes[activeType] >= maxStartIndex"
                  @click="move(1)"
                >&gt;</button>
              </div>
            </footer>
          </div>
        </section>
      </template>

      <div v-else-if="recommendationStore.loading" class="recommendation-loading">
        추천 캡슐을 준비하고 있어요.
      </div>
    </section>
  </main>
</template>
