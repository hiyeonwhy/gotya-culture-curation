<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import api from '../api'
import { useAuthStore } from '../stores/auth'
import { useContentsStore } from '../stores/contents'
import { useRecommendationStore } from '../stores/recommendations'
import { useTasteTestStore } from '../stores/tasteTest'
import heroBackground from '../assets/images/home-hero/main-background.png'
import gachaImage from '../assets/images/home-hero/gotya-machine.png'

const authStore = useAuthStore()
const contentStore = useContentsStore()
const recommendationStore = useRecommendationStore()
const tasteTestStore = useTasteTestStore()
const selectedTaste = ref('')
const modalOpen = ref(false)
const activeDetailType = ref('')
const activeDetailContentItemId = ref(null)
const feedbackType = ref(null)
const likeCount = ref(0)
const detailFeedbackLoading = ref(false)
const detailFeedbackError = ref('')
const likedContentIds = ref(new Set())
const cardFeedbackLoadingIds = ref(new Set())

const tasteOptions = [
  { value: 'TREND', label: '유행 탑승형' },
  { value: 'MONGLE', label: '마음 몽글형' },
  { value: 'WORLD', label: '세계관 과몰입형' },
  { value: 'KNOWLEDGE', label: '지식 냠냠형' },
  { value: 'FESTIVAL', label: '축제 팔랑귀형' },
  { value: 'TOGETHER', label: '같이보기 찰떡형' },
]
const hiddenCultureMainTags = new Set([
  '공연',
  '전시',
  '교육·체험',
  '축제·행사',
  '가족·아동',
  '아동·가족',
])

const detailConfigs = {
  movie: {
    endpoint: 'movies',
    label: '영화',
    icon: '🎬',
  },
  book: {
    endpoint: 'books',
    label: '도서',
    icon: '📚',
  },
  culture: {
    endpoint: 'cultures',
    label: '문화행사',
    icon: '🎟',
  },
}

const recommendationSections = computed(() => {
  const recommendations = recommendationStore.result?.recommendations || {}

  return [
    {
      key: 'movie',
      title: '영화 콘텐츠 추천',
      eyebrow: 'MOVIE GOTYA',
      moreTo: '/movies',
      items: recommendations.movie || [],
      fallback: '🎬',
    },
    {
      key: 'book',
      title: '도서 콘텐츠 추천',
      eyebrow: 'BOOK GOTYA',
      moreTo: '/books',
      items: recommendations.book || [],
      fallback: '📚',
    },
    {
      key: 'culture',
      title: '문화 콘텐츠 추천',
      eyebrow: 'CULTURE GOTYA',
      moreTo: '/cultures',
      items: recommendations.culture || [],
      fallback: '🎟',
    },
  ]
})

const activeDetailConfig = computed(() => (
  detailConfigs[activeDetailType.value] || detailConfigs.movie
))
const hasSavedTasteResult = computed(() => Boolean(tasteTestStore.latestResult))
const shouldShowTasteFilters = computed(() => authStore.isAuthenticated && hasSavedTasteResult.value)
const myTasteType = computed(() => (
  tasteTestStore.latestResult?.result?.code
  || recommendationStore.result?.profile?.result_taste_type
  || recommendationStore.result?.profile?.taste_type
  || ''
))
const myTasteLabel = computed(() => (
  tasteTestStore.latestResult?.result?.name
  || recommendationStore.result?.profile?.result_taste_label
  || recommendationStore.result?.profile?.taste_label
  || '내 취향'
))
const myTasteOption = computed(() => (
  myTasteType.value ? { value: myTasteType.value, label: myTasteLabel.value } : null
))
const otherTasteOptions = computed(() => (
  myTasteType.value
    ? tasteOptions.filter((option) => option.value !== myTasteType.value)
    : []
))
const detailHeartActive = computed(() => {
  const contentItemId = detailContentItemId()
  return feedbackType.value === 'like' || (contentItemId ? likedContentIds.value.has(contentItemId) : false)
})

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

function itemMetaText(item, type) {
  if (type === 'culture') {
    const startDate = formatCompactDate(item.metadata?.start_date)
    const endDate = formatCompactDate(item.metadata?.end_date)

    if (startDate && endDate) return `${startDate} ~ ${endDate}`
    return startDate || endDate || '기간 미정'
  }

  const labels = type === 'movie'
    ? item.metadata?.genres
    : item.metadata?.categories

  return labels?.filter(Boolean).slice(0, 2).join(' · ') || (type === 'movie' ? '영화' : '도서')
}

function cardTags(item, type) {
  if (type !== 'culture') return []
  return [
    hiddenCultureMainTags.has(item.metadata?.main_category) ? null : item.metadata?.main_category,
    item.metadata?.sub_category,
  ].filter(Boolean)
}

function recommendationDetailId(item, type) {
  if (type === 'movie') return item.metadata?.tmdb_id
  if (type === 'book') return item.metadata?.aladin_item_id
  return item.metadata?.seq
}

function isCardLiked(item) {
  return likedContentIds.value.has(item.content_item_id)
}

function isCardFeedbackLoading(item) {
  return cardFeedbackLoadingIds.value.has(item.content_item_id)
}

function setCardFeedbackLoading(contentItemId, loading) {
  const next = new Set(cardFeedbackLoadingIds.value)
  if (loading) next.add(contentItemId)
  else next.delete(contentItemId)
  cardFeedbackLoadingIds.value = next
}

function markContentLiked(contentItemId, isLiked) {
  const next = new Set(likedContentIds.value)
  if (isLiked) next.add(contentItemId)
  else next.delete(contentItemId)
  likedContentIds.value = next
}

function detailContentItemId() {
  return activeDetailContentItemId.value || contentStore.currentDetail?.content_item_id || null
}

async function syncBookmarkForContent(contentItemId, shouldBookmark) {
  if (!authStore.isAuthenticated || !contentItemId) return

  const { data } = await api.get('/tastes/bookmarks/status/', {
    params: { content_item_id: contentItemId },
  })
  if (Boolean(data.bookmarked) !== shouldBookmark) {
    await api.post('/tastes/bookmarks/toggle/', {
      content_item_id: contentItemId,
    })
  }
}

function detailTags(item) {
  if (!item) return []
  if (activeDetailType.value !== 'culture') return []
  return [
    hiddenCultureMainTags.has(item.main_category) ? null : item.main_category,
    item.sub_category,
  ].filter(Boolean)
}

async function openDetail(item, type) {
  const id = recommendationDetailId(item, type)
  if (!id) return

  activeDetailType.value = type
  activeDetailContentItemId.value = item.content_item_id || null
  feedbackType.value = null
  likeCount.value = 0
  detailFeedbackLoading.value = false
  detailFeedbackError.value = ''
  modalOpen.value = true
  document.body.classList.add('modal-lock')

  try {
    await contentStore.fetchDetail(detailConfigs[type].endpoint, id)
    const contentItemId = detailContentItemId()
    if (contentItemId) {
      const { data } = await api.get('/tastes/feedback/status/', {
        params: { content_item_id: contentItemId },
      })
      likeCount.value = Number(data.like_count || 0)
      feedbackType.value = data.feedback_type || null
      markContentLiked(contentItemId, feedbackType.value === 'like')
    }
    if (authStore.isAuthenticated && contentItemId) {
      const { data } = await api.get('/tastes/bookmarks/status/', {
        params: { content_item_id: contentItemId },
      })
      markContentLiked(contentItemId, Boolean(data.bookmarked) || feedbackType.value === 'like')
    }
  } catch {
    // 상세 조회 실패 메시지는 contentStore.error로 표시한다.
  }
}

async function toggleCardLike(item) {
  const contentItemId = item.content_item_id
  if (!authStore.isAuthenticated || !contentItemId || isCardFeedbackLoading(item)) return

  setCardFeedbackLoading(contentItemId, true)
  try {
    const { data } = await api.post('/tastes/feedback/', {
      content_item_id: contentItemId,
      feedback_type: 'like',
    })
    const isLiked = data.feedback_type === 'like'
    markContentLiked(contentItemId, isLiked)
    await syncBookmarkForContent(contentItemId, isLiked)
  } catch {
    // 홈 카드에서는 좋아요 실패 메시지를 별도로 노출하지 않는다.
  } finally {
    setCardFeedbackLoading(contentItemId, false)
  }
}

async function submitDetailFeedback(nextFeedbackType) {
  if (!authStore.isAuthenticated || detailFeedbackLoading.value) return

  const contentItemId = detailContentItemId()
  if (!contentItemId) return

  detailFeedbackLoading.value = true
  detailFeedbackError.value = ''
  try {
    const { data } = await api.post('/tastes/feedback/', {
      content_item_id: contentItemId,
      feedback_type: nextFeedbackType,
    })
    likeCount.value = Number(data.like_count || 0)
    feedbackType.value = data.feedback_type || null
    const isLiked = feedbackType.value === 'like'
    markContentLiked(contentItemId, isLiked)
    await syncBookmarkForContent(contentItemId, isLiked)
    if (nextFeedbackType === 'dislike') {
      await syncBookmarkForContent(contentItemId, false)
      recommendationStore.resetRecommendations()
    }
  } catch (error) {
    detailFeedbackError.value = (
      error.response?.data?.content_item_id?.[0]
      || error.response?.data?.feedback_type?.[0]
      || error.response?.data?.detail
      || '반응을 저장하지 못했습니다.'
    )
  } finally {
    detailFeedbackLoading.value = false
  }
}

function closeDetail() {
  modalOpen.value = false
  activeDetailType.value = ''
  activeDetailContentItemId.value = null
  feedbackType.value = null
  likeCount.value = 0
  detailFeedbackLoading.value = false
  detailFeedbackError.value = ''
  contentStore.clearDetail()
  document.body.classList.remove('modal-lock')
}

async function loadRecommendations(tasteType = '') {
  selectedTaste.value = tasteType
  likedContentIds.value = new Set()

  try {
    await recommendationStore.generateRecommendations({
      tasteType,
      perType: 10,
      enhance: false,
    })
  } catch {
    // 홈에서는 추천 실패 시 비어있는 섹션으로만 보여준다.
  }
}

function toggleTaste(tasteType) {
  const nextTasteType = selectedTaste.value === tasteType ? '' : tasteType
  void loadRecommendations(nextTasteType)
}

function selectMyTaste() {
  void loadRecommendations('')
}

async function prepareHome() {
  selectedTaste.value = ''
  if (authStore.token) {
    try {
      await tasteTestStore.fetchLatestResult()
    } catch {
      tasteTestStore.latestResult = null
    }
  } else {
    tasteTestStore.latestResult = null
  }
  void loadRecommendations('')
}

onMounted(() => {
  void prepareHome()
})

onBeforeUnmount(() => {
  document.body.classList.remove('modal-lock')
})
</script>

<template>
  <main class="home-page">
    <section
      class="home-hero"
      :style="{ '--home-hero-bg': `url(${heroBackground})` }"
    >
      <div class="home-copy">
        <p class="home-eyebrow">GOT YOUR ACTIVITY</p>
        <h1>
          <span class="home-title-line">무지성 릴스는 그만!</span>
          <span class="home-title-line">오늘의 도파민은</span>
          <span class="home-title-line"><strong>GotYA</strong>가 책임진다.</span>
        </h1>
        <p class="home-description">
          오늘의 도파민,<br>
          GotYA로 뽑아봐!
        </p>
        <div class="home-actions">
          <RouterLink class="home-primary-link" to="/taste-test">
            오늘의 GotYA 뽑기
          </RouterLink>
        </div>
      </div>

      <div class="gacha-stage" aria-hidden="true">
        <img :src="gachaImage" alt="">
      </div>
    </section>

    <section class="home-content-shell">
      <section v-if="shouldShowTasteFilters" class="taste-filter-section" aria-label="취향 추천 선택">
        <div v-if="myTasteOption" class="home-my-taste">
          <span>MY PICK</span>
          <button
            type="button"
            class="taste-filter-button"
            :class="{ active: !selectedTaste }"
            @click="selectMyTaste"
          >
            {{ myTasteOption.label }}
          </button>
        </div>
        <i v-if="myTasteOption && otherTasteOptions.length" class="home-taste-divider" aria-hidden="true"></i>
        <span class="home-taste-label">오늘의 PICK</span>
        <button
          v-for="taste in otherTasteOptions"
          :key="taste.value"
          type="button"
          class="taste-filter-button"
          :class="{ active: selectedTaste === taste.value }"
          @click="toggleTaste(taste.value)"
        >
          {{ taste.label }}
        </button>
      </section>

      <p v-if="recommendationStore.error" class="home-recommendation-state error">
        추천 콘텐츠를 불러오지 못했어요.
      </p>

      <section
        v-for="section in recommendationSections"
        :key="section.key"
        class="home-recommendation-section"
      >
        <div class="home-section-heading">
          <div>
            <p>{{ section.eyebrow }}</p>
            <h2>{{ section.title }}</h2>
          </div>
          <RouterLink :to="section.moreTo">
            더보기 <span aria-hidden="true">›</span>
          </RouterLink>
        </div>

        <div v-if="section.items.length" class="home-card-row">
          <article
            v-for="item in section.items.slice(0, 6)"
            :key="item.content_item_id"
            class="home-content-card"
            role="button"
            tabindex="0"
            @click="openDetail(item, section.key)"
            @keydown.enter.prevent="openDetail(item, section.key)"
          >
            <div class="home-card-poster">
              <img v-if="item.thumbnail_url" :src="item.thumbnail_url" :alt="`${item.title} 이미지`">
              <span v-else>{{ section.fallback }}</span>
              <button
                v-if="authStore.isAuthenticated"
                type="button"
                class="home-card-like"
                :class="{ active: isCardLiked(item) }"
                :disabled="isCardFeedbackLoading(item)"
                aria-label="찜하기"
                @click.stop.prevent="toggleCardLike(item)"
              >
                {{ isCardLiked(item) ? '♥' : '♡' }}
              </button>
            </div>
            <div v-if="cardTags(item, section.key).length" class="home-card-tags">
              <span v-for="tag in cardTags(item, section.key).slice(0, 2)" :key="tag">{{ tag }}</span>
            </div>
            <p>{{ itemMetaText(item, section.key) }}</p>
            <h3>{{ item.title }}</h3>
          </article>
        </div>

        <p v-else class="home-empty-row">
          아직 추천 가능한 콘텐츠가 없어요.
        </p>
      </section>
    </section>

    <Teleport to="body">
      <div v-if="modalOpen" class="home-detail-overlay" @click.self="closeDetail">
        <section class="home-detail-modal" role="dialog" aria-modal="true" aria-label="콘텐츠 상세 정보">
          <button class="home-modal-close" type="button" aria-label="닫기" @click="closeDetail">×</button>
          <p v-if="contentStore.detailLoading" class="home-detail-state">상세 정보를 불러오는 중이에요.</p>
          <p v-else-if="contentStore.error" class="home-detail-state error">{{ contentStore.error }}</p>
          <template v-else-if="contentStore.currentDetail">
            <div class="home-detail-cover">
              <img
                v-if="contentStore.currentDetail.thumbnail_url"
                :src="contentStore.currentDetail.thumbnail_url"
                :alt="`${contentStore.currentDetail.title} 이미지`"
              >
              <div v-else class="home-detail-fallback">{{ activeDetailConfig.icon }}</div>
            </div>
            <div class="home-detail-content">
              <div class="home-detail-title-row">
                <div>
                  <p class="home-detail-kind">{{ activeDetailConfig.label }}</p>
                  <h2>{{ contentStore.currentDetail.title }}</h2>
                </div>
                <button
                  v-if="authStore.isAuthenticated"
                  type="button"
                  class="home-detail-like"
                  :class="{ active: detailHeartActive }"
                  :disabled="detailFeedbackLoading"
                  :aria-label="detailHeartActive ? '찜하기 해제' : '찜하기'"
                  :title="detailHeartActive ? '찜하기 해제' : '찜하기'"
                  @click="submitDetailFeedback('like')"
                >
                  <span aria-hidden="true">{{ detailHeartActive ? '♥' : '♡' }}</span>
                  <strong>{{ likeCount.toLocaleString() }}</strong>
                </button>
              </div>
              <div v-if="detailTags(contentStore.currentDetail).length" class="home-detail-tags">
                <span v-for="tag in detailTags(contentStore.currentDetail)" :key="tag">{{ tag }}</span>
              </div>

              <dl v-if="activeDetailType === 'movie'" class="home-detail-facts">
                <div><dt>개봉일</dt><dd>{{ formatCompactDate(contentStore.currentDetail.release_date) || '-' }}</dd></div>
                <div><dt>평점</dt><dd>★ {{ contentStore.currentDetail.vote_average?.toFixed(1) || '-' }}</dd></div>
                <div><dt>원제</dt><dd>{{ contentStore.currentDetail.original_title || '-' }}</dd></div>
              </dl>
              <dl v-else-if="activeDetailType === 'book'" class="home-detail-facts">
                <div><dt>저자</dt><dd>{{ contentStore.currentDetail.author || '-' }}</dd></div>
                <div><dt>출판사</dt><dd>{{ contentStore.currentDetail.publisher || '-' }}</dd></div>
                <div><dt>출간일</dt><dd>{{ formatCompactDate(contentStore.currentDetail.pub_date) || '-' }}</dd></div>
                <div><dt>Ebook</dt><dd>{{ contentStore.currentDetail.has_ebook ? '있음' : '없음' }}</dd></div>
              </dl>
              <dl v-else class="home-detail-facts">
                <div><dt>기간</dt><dd>{{ formatCompactDate(contentStore.currentDetail.start_date) || '-' }} ~ {{ formatCompactDate(contentStore.currentDetail.end_date) || '-' }}</dd></div>
                <div><dt>장소</dt><dd>{{ contentStore.currentDetail.place?.place_name || '-' }}</dd></div>
                <div><dt>주소</dt><dd>{{ contentStore.currentDetail.place?.address || '-' }}</dd></div>
                <div><dt>가격</dt><dd>{{ contentStore.currentDetail.price || '-' }}</dd></div>
              </dl>

              <p v-if="contentStore.currentDetail.summary" class="home-detail-summary">
                {{ contentStore.currentDetail.summary }}
              </p>
              <div class="home-detail-actions">
                <p v-if="authStore.isAuthenticated && detailFeedbackError" class="home-detail-action-error">
                  {{ detailFeedbackError }}
                </p>
              </div>
              <div class="home-detail-bottom-actions">
                <a
                  v-if="contentStore.currentDetail.source_url"
                  class="home-source-link"
                  :href="contentStore.currentDetail.source_url"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  원문 페이지 보기 ↗
                </a>
                <button
                  v-if="authStore.isAuthenticated"
                  type="button"
                  class="home-hide-content-button"
                  :class="{ active: feedbackType === 'dislike' }"
                  :disabled="detailFeedbackLoading"
                  @click="submitDetailFeedback('dislike')"
                >
                  이 콘텐츠 다시 보지 않기
                </button>
              </div>
            </div>
          </template>
        </section>
      </div>
    </Teleport>
  </main>
</template>

<style scoped>
.home-page {
  min-height: calc(100vh - 96px);
  padding: 0 0 5rem;
  background:
    linear-gradient(180deg, rgba(245, 246, 248, 0.92), rgba(255, 255, 255, 0.98)),
    #fff;
}

.home-hero {
  position: relative;
  overflow: hidden;
  width: 100%;
  min-height: clamp(680px, calc(100vh - 92px), 830px);
  margin: 0;
  border: 0;
  border-radius: 0;
  background:
    var(--home-hero-bg) center center / cover no-repeat,
    #fff;
  box-shadow: none;
}

.home-hero::before,
.home-hero::after {
  content: none;
}

.home-eyebrow {
  margin: 0 0 1rem;
  color: var(--gotya-mint-dark);
  font-size: 0.82rem;
  font-weight: 950;
  letter-spacing: 0.18em;
}

.home-copy {
  position: absolute;
  top: 50%;
  left: clamp(3.2rem, 8vw, 8.5rem);
  display: flex;
  width: min(52vw, 820px);
  flex-direction: column;
  transform: translateY(-43%);
}

.home-copy h1 {
  display: grid;
  max-width: 820px;
  margin: 0;
  color: var(--gotya-navy);
  font-size: clamp(3.25rem, 4.65vw, 5.6rem);
  line-height: 1.06;
  letter-spacing: -0.08em;
}

.home-title-line {
  display: block;
  white-space: nowrap;
}

.home-copy h1 strong {
  color: var(--gotya-mint-dark);
  font: inherit;
}

.home-description {
  margin: 1.7rem 0 0;
  color: #536176;
  font-size: clamp(1.05rem, 1.45vw, 1.3rem);
  font-weight: 820;
  line-height: 1.65;
}

.home-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 2.4rem;
}

.home-primary-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: clamp(250px, 18vw, 310px);
  min-height: 72px;
  border: 0;
  border-radius: 0.8rem;
  padding: 1rem 2.2rem;
  color: #fff;
  background: linear-gradient(180deg, #5ed9ce, #34c7ba);
  box-shadow: 0 18px 35px rgba(40, 190, 177, 0.24);
  font-size: clamp(1.2rem, 1.35vw, 1.55rem);
  font-weight: 950;
  text-decoration: none;
  transition: transform 0.22s ease, background 0.22s ease;
}

.home-primary-link:hover {
  transform: translateY(-3px);
}

.gacha-stage {
  position: absolute;
  top: 53%;
  right: clamp(3rem, 8vw, 9.5rem);
  display: grid;
  width: min(39vw, 620px);
  place-items: center;
  border: 0;
  background: transparent;
  transform: translateY(-50%);
}

.gacha-stage img {
  display: block;
  width: 100%;
  height: auto;
  max-width: 620px;
  max-height: calc(100vh - 150px);
  object-fit: contain;
  border: 0;
  filter: drop-shadow(0 28px 30px rgba(28, 121, 119, 0.12));
}

.home-content-shell {
  display: grid;
  gap: 3.5rem;
  width: min(100% - 3rem, 1480px);
  margin: 2.4rem auto 0;
}

.taste-filter-section {
  display: flex;
  overflow-x: auto;
  align-items: center;
  justify-content: center;
  gap: 0.8rem;
  padding: 0.25rem 0 0.5rem;
}

.home-my-taste {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 0.45rem;
}

.home-my-taste span,
.home-taste-label {
  flex: 0 0 auto;
  color: #667085;
  font-size: 0.9rem;
  font-weight: 900;
  white-space: nowrap;
}

.home-my-taste span {
  color: var(--gotya-mint-dark);
}

.home-taste-divider {
  flex: 0 0 auto;
  width: 2px;
  height: 1.35rem;
  border-radius: 999px;
  background: rgba(102, 112, 133, 0.28);
}

.taste-filter-button {
  flex: 0 0 auto;
  border: 0;
  border-radius: 999px;
  padding: 0.88rem 1.2rem;
  color: var(--gotya-navy);
  background: #fff;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.06);
  font-weight: 900;
  cursor: pointer;
  transition: transform 0.22s ease, background 0.22s ease;
}

.taste-filter-button:hover,
.taste-filter-button.active {
  border-color: transparent;
  background: var(--gotya-mint);
  transform: translateY(-2px);
}

.home-recommendation-state {
  margin: -1.4rem 0 -1.6rem;
  border-radius: 1.1rem;
  padding: 1rem 1.2rem;
  color: #536176;
  background: transparent;
  box-shadow: none;
}

.home-recommendation-state.error {
  color: #b42318;
  background: transparent;
}

.home-recommendation-section {
  position: relative;
  border: 0;
  border-radius: 0;
  padding: 0;
  background: transparent;
  box-shadow: none;
}

.home-recommendation-section + .home-recommendation-section {
  border-top: 1px solid rgba(102, 112, 133, 0.22);
  padding-top: 2.4rem;
}

.home-section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.4rem;
}

.home-section-heading p {
  margin: 0 0 0.35rem;
  color: var(--gotya-mint-dark);
  font-size: 0.72rem;
  font-weight: 950;
  letter-spacing: 0.15em;
}

.home-section-heading h2 {
  margin: 0;
  color: var(--gotya-navy);
  font-size: clamp(1.45rem, 2.5vw, 2.2rem);
  letter-spacing: -0.045em;
}

.home-section-heading a {
  flex: 0 0 auto;
  color: #536176;
  font-weight: 900;
  text-decoration: none;
}

.home-section-heading a:hover {
  color: var(--gotya-mint-dark);
}

.home-card-row {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: clamp(1rem, 1.5vw, 1.35rem);
}

.home-content-card {
  min-width: 0;
  border: 0;
  padding: 0;
  background: transparent;
  cursor: pointer;
  text-align: left;
}

.home-card-poster {
  position: relative;
  display: grid;
  overflow: hidden;
  place-items: center;
  aspect-ratio: 3 / 4;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  transition: transform 0.22s ease;
}

.home-content-card:hover .home-card-poster,
.home-content-card:focus-visible .home-card-poster {
  transform: translateY(-5px) scale(1.015);
  box-shadow: none;
}

.home-card-poster img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain !important;
  object-position: center;
}

.home-card-poster span {
  font-size: 2.4rem;
}

.home-card-like {
  position: absolute;
  top: 0.65rem;
  right: 0.65rem;
  display: inline-grid;
  width: 2.2rem;
  height: 2.2rem;
  place-items: center;
  border: 0;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  color: var(--gotya-navy);
  box-shadow: 0 8px 18px rgba(26, 31, 46, 0.12);
  font-size: 1.35rem;
  font-weight: 900;
  line-height: 1;
  cursor: pointer;
  backdrop-filter: blur(8px);
}

.home-card-like:hover {
  color: #ef4b5f;
  transform: translateY(-1px);
}

.home-card-like.active {
  color: #ef4b5f;
}

.home-card-like:disabled {
  cursor: default;
}

.home-card-tags {
  display: flex;
  overflow: hidden;
  gap: 0.3rem;
  margin: 0.85rem 0 0.35rem;
}

.home-card-tags span {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 0.22rem 0.48rem;
  color: var(--gotya-mint-dark);
  background: rgba(92, 207, 195, 0.16);
  font-size: 0.68rem;
  font-weight: 850;
}

.home-content-card p {
  overflow: hidden;
  margin: 0 0 0.35rem;
  color: #667085;
  font-size: 0.84rem;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.home-content-card h3 {
  display: -webkit-box;
  overflow: hidden;
  margin: 0;
  color: var(--gotya-navy);
  font-size: 1.02rem;
  font-weight: 900;
  line-height: 1.35;
  letter-spacing: -0.025em;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.home-empty-row {
  margin: 0;
  border: 0;
  border-radius: 0;
  padding: 2rem 1rem;
  color: #667085;
  background: transparent;
  box-shadow: none;
  text-align: center;
}

.home-detail-overlay {
  position: fixed;
  z-index: 1000;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 2rem;
  background: rgba(26, 31, 46, 0.68);
  backdrop-filter: blur(6px);
}

.home-detail-modal {
  position: relative;
  display: grid;
  grid-template-columns: 39% minmax(0, 1fr);
  overflow: hidden;
  width: min(1152px, calc((100vh - 4rem) * 4 / 3), calc(100vw - 4rem));
  aspect-ratio: 4 / 3;
  border-radius: 1.6rem;
  background: #fff;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.25);
}

.home-modal-close {
  position: absolute;
  z-index: 2;
  top: 1.2rem;
  right: 1.2rem;
  border: 0;
  background: transparent;
  color: var(--gotya-navy);
  font-size: 1.8rem;
  font-weight: 900;
  cursor: pointer;
}

.home-detail-state {
  grid-column: 1 / -1;
  margin: 0;
  padding: 4rem 2rem;
  color: #536176;
  text-align: center;
}

.home-detail-state.error {
  color: #b42318;
}

.home-detail-cover {
  display: grid;
  min-width: 0;
  min-height: 0;
  place-items: center;
  background: #f5f6f8;
}

.home-detail-cover img {
  display: block;
  width: 100%;
  height: 100%;
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  object-position: center;
}

.home-detail-fallback {
  font-size: 4rem;
}

.home-detail-content {
  display: flex;
  overflow: hidden;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  padding: 3.2rem 3rem 2.6rem;
}

.home-detail-kind {
  margin: 0 0 0.8rem;
  color: var(--gotya-mint-dark);
  font-weight: 900;
}

.home-detail-title-row {
  display: flex;
  flex: 0 0 auto;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.home-detail-title-row > div {
  min-width: 0;
}

.home-detail-content h2 {
  overflow-y: auto;
  max-height: 2.45em;
  margin: 0;
  color: var(--gotya-navy);
  font-size: 1.4rem;
  line-height: 1.2;
  letter-spacing: -0.05em;
}

.home-detail-like {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 0.35rem;
  min-width: 4.6rem;
  border: 1px solid rgba(102, 112, 133, 0.2);
  border-radius: 999px;
  padding: 0.45rem 0.7rem;
  background: #fff;
  color: #667085;
  font-weight: 900;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease, color 0.15s ease;
}

.home-detail-like span {
  font-size: 1.25rem;
  line-height: 1;
}

.home-detail-like strong {
  font-size: 0.92rem;
  line-height: 1;
}

.home-detail-like:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 10px 18px rgba(39, 55, 77, 0.12);
}

.home-detail-like.active {
  border-color: #e25563;
  color: #e25563;
}

.home-detail-like:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.home-detail-tags {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin: 1rem 0 1.4rem;
}

.home-detail-tags span {
  border-radius: 999px;
  padding: 0.35rem 0.65rem;
  color: #1f6f62;
  background: rgba(92, 207, 195, 0.16);
  font-size: 0.8rem;
  font-weight: 850;
}

.home-detail-facts {
  display: grid;
  flex: 0 0 auto;
  gap: 0.65rem;
  margin: 0 0 1.5rem;
  border-radius: 1rem;
  padding: 1rem;
  background: #f8f4ec;
}

.home-detail-facts div {
  display: grid;
  grid-template-columns: 5rem minmax(0, 1fr);
  gap: 1rem;
}

.home-detail-facts dt {
  color: #667085;
  font-weight: 900;
}

.home-detail-facts dd {
  margin: 0;
  color: var(--gotya-navy);
}

.home-detail-summary {
  flex: 1 1 auto;
  overflow-y: auto;
  min-height: 0;
  margin: 0;
  padding-right: 0.55rem;
  color: #3f4858;
  line-height: 1.75;
}

.home-detail-actions {
  display: grid;
  flex: 0 0 auto;
  gap: 0.7rem;
  margin-top: 1rem;
}

.home-detail-action-note,
.home-detail-action-error {
  margin: 0;
  font-size: 0.92rem;
}

.home-detail-action-note {
  color: #667085;
}

.home-detail-action-error {
  color: #c94d4d;
}

.home-detail-bottom-actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 1rem;
}

.home-source-link {
  color: #ff5c35;
  font-weight: 900;
  text-decoration: none;
}

.home-hide-content-button {
  margin-left: auto;
  border: 1px solid transparent;
  border-radius: 0.8rem;
  padding: 0.68rem 0.9rem;
  background: transparent;
  color: #667085;
  font-weight: 900;
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.home-hide-content-button:hover:not(:disabled) {
  background: #f5f6f8;
  color: var(--gotya-navy);
}

.home-hide-content-button.active {
  background: #f5eeee;
  color: #c94d4d;
}

.home-hide-content-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 1200px) {
  .home-hero {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(280px, 0.75fr);
    align-items: center;
    gap: 2rem;
    min-height: auto;
    padding: 4rem 3rem;
    background-position: center center;
  }

  .home-copy,
  .gacha-stage {
    position: static;
    width: auto;
    transform: none;
  }

  .home-copy h1 {
    font-size: clamp(2.7rem, 6vw, 4.4rem);
  }

  .gacha-stage img {
    width: min(100%, 460px);
  }
}

@media (max-width: 1100px) {
  .home-card-row {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .home-page {
    padding-inline: 1rem;
  }

  .home-hero,
  .home-content-shell {
    width: 100%;
  }

  .home-hero {
    grid-template-columns: 1fr;
    padding-inline: 1rem;
    background-position: center bottom;
  }

  .home-title-line {
    white-space: normal;
  }

  .gacha-stage {
    min-height: auto;
  }

  .gacha-stage img {
    width: min(100%, 390px);
  }

  .home-detail-modal {
    grid-template-columns: 39% minmax(0, 1fr);
    width: min(100%, calc((100vh - 2rem) * 4 / 3));
    aspect-ratio: 4 / 3;
  }

  .home-detail-cover {
    min-height: 0;
  }

  .home-detail-title-row {
    align-items: flex-start;
  }

  .home-detail-bottom-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .home-hide-content-button {
    margin-left: 0;
    text-align: center;
  }
}

@media (max-width: 640px) {
  .home-card-row {
    display: flex;
    overflow-x: auto;
    padding-bottom: 0.5rem;
  }

  .home-content-card {
    flex: 0 0 170px;
  }
}

@media (max-width: 560px) {
  .home-page {
    padding-inline: 0.85rem;
  }

  .home-primary-link {
    width: 100%;
  }

  .home-detail-overlay {
    padding: 1rem;
  }
}

@media (min-width: 1101px) {
  .home-hero {
    min-height: 740px;
    background-position: center top, center;
    background-size: max(100%, 1920px) auto, auto;
  }

  .home-copy {
    left: max(5.5rem, calc(50% - 820px));
    width: 820px;
  }

  .home-copy h1 {
    font-size: 5rem;
  }

  .home-description {
    font-size: 1.18rem;
  }

  .home-primary-link {
    min-width: 280px;
    font-size: 1.35rem;
  }

  .gacha-stage {
    right: max(5.5rem, calc(50% - 790px));
    width: 560px;
  }

  .gacha-stage img {
    max-height: 590px;
  }
}
</style>
