<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import api from '../api'
import { useAuthStore } from '../stores/auth'
import { useContentsStore } from '../stores/contents'
import { useRecommendationStore } from '../stores/recommendations'
import { useTasteTestStore } from '../stores/tasteTest'
import { loadKakaoMap } from '../utils/loadKakaoMap'
import CultureMap from '../components/CultureMap.vue'
import loungeBackground from '../assets/images/lounge/lounge-background.png'
import '../assets/contents.css'

const props = defineProps({
  contentType: {
    type: String,
    required: true,
    validator: (value) => ['movies', 'books', 'cultures'].includes(value),
  },
})

const authStore = useAuthStore()
const contentStore = useContentsStore()
const recommendationStore = useRecommendationStore()
const tasteTestStore = useTasteTestStore()
const route = useRoute()

const search = ref('')
const appliedSearch = ref('')
const searchScope = ref('all')
const sort = ref('popular')
const selectedCategory = ref('')
const selectedMapArea = ref('')
const selectedMapSigungu = ref('')
const page = ref(1)
const sentinel = ref(null)
const catalogSection = ref(null)
const modalOpen = ref(false)
const bookmarked = ref(false)
const bookmarkLoading = ref(false)
const bookmarkError = ref('')
const feedbackType = ref(null)
const likeCount = ref(0)
const feedbackLoading = ref(false)
const feedbackError = ref('')
const likedContentIds = ref(new Set())
const cardFeedbackLoadingIds = ref(new Set())
const hydratedContentStatusIds = ref(new Set())
const selectedPickType = ref('')
const pickStartIndex = ref(0)
const userTasteType = ref('')
const userTasteLabel = ref('')
let observer = null

const tasteTypeOptions = [
  { value: 'TREND', label: '유행 탑승형' },
  { value: 'MONGLE', label: '마음 몽글형' },
  { value: 'WORLD', label: '세계관 과몰입형' },
  { value: 'KNOWLEDGE', label: '지식 냠냠형' },
  { value: 'FESTIVAL', label: '축제 팔랑귀형' },
  { value: 'TOGETHER', label: '같이보기 찰떡형' },
]

const bookSearchScopes = [
  { value: 'all', label: '전체' },
  { value: 'title', label: '제목' },
  { value: 'summary', label: '내용' },
  { value: 'author', label: '저자' },
]

const cultureSearchScopes = [
  { value: 'all', label: '전체' },
  { value: 'title', label: '이름' },
  { value: 'summary', label: '내용' },
  { value: 'place', label: '장소' },
]
const pageConfigs = {
  movies: {
    label: '영화',
    description: '지금 내 마음에 맞는 영화를 찾아보세요.',
    icon: '🎬',
    recommendationKey: 'movie',
    categoryParam: 'genre',
    categories: [
      [28, '액션'], [12, '모험'], [16, '애니메이션'], [35, '코미디'], [80, '범죄'],
      [99, '다큐멘터리'], [18, '드라마'], [10751, '가족'], [14, '판타지'], [36, '역사'],
      [27, '공포'], [10402, '음악'], [9648, '미스터리'], [10749, '로맨스'], [878, 'SF'],
      [53, '스릴러'], [10752, '전쟁'], [37, '서부'],
    ],
  },
  books: {
    label: '도서',
    description: '읽고 싶은 책을 한눈에 골라보세요.',
    icon: '📚',
    recommendationKey: 'book',
    categoryParam: 'category',
    categories: [
      [55890, '건강/취미'], [170, '경제경영'], [987, '과학'], [2551, '만화/라이트노벨'],
      [798, '사회과학'], [1, '소설/시/희곡'], [13789, '에세이'], [55889, '여행에세이'],
      [1196, '인문'], [74, '자기계발'], [1322, '외국어'],
      [1230, '유아/어린이'], [7600, '요리'], [656, '예술/대중문화'],
      [1238, '종교/역학'], [351, '컴퓨터/모바일'],
    ],
  },
  cultures: {
    label: '문화행사',
    description: '오늘 즐길 수 있는 문화행사를 찾아보세요.',
    icon: '🎭',
    recommendationKey: 'culture',
    categoryParam: 'main_category',
    categories: [
      ['공연', '공연'], ['전시', '전시'], ['교육·체험', '교육·체험'],
      ['축제·행사', '축제·행사'], ['가족·아동', '가족·아동'], ['스포츠·레저기타', '스포츠·레저기타'],
    ],
  },
}

const config = computed(() => pageConfigs[props.contentType])
const cultureAreaOrder = ['서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종', '경기', '강원', '전남', '전북', '경북', '경남', '충남', '충북', '제주']
const cultureAreaLabels = {
  서울: '서울',
  부산: '부산',
  대구: '대구',
  인천: '인천',
  광주: '광주',
  대전: '대전',
  울산: '울산',
  세종: '세종',
  경기: '경기도',
  강원: '강원도',
  충북: '충북',
  충남: '충남',
  전북: '전북',
  전남: '전남',
  경북: '경북',
  경남: '경남',
  제주: '제주도',
}
const cultureAreaAliases = Object.fromEntries(
  Object.entries(cultureAreaLabels).map(([area, label]) => [label, area]),
)
const normalizeCultureArea = (area) => cultureAreaAliases[area] || area
const categoryOptions = computed(() => (
  props.contentType === 'books'
    ? [['__ebook', 'Ebook'], ...config.value.categories]
    : config.value.categories
))
const searchScopeOptions = computed(() => {
  if (props.contentType === 'books') return bookSearchScopes
  if (props.contentType === 'cultures') return cultureSearchScopes
  return []
})
const cultureRegionOptions = computed(() => {
  if (props.contentType !== 'cultures') return []

  const summaryAreas = contentStore.regionSummaries
    .map((region) => normalizeCultureArea(region.area))
    .filter(Boolean)
  const itemAreas = contentStore.mapItems
    .map((item) => normalizeCultureArea(item.place?.area))
    .filter(Boolean)
  const areas = new Set([...cultureAreaOrder, ...summaryAreas, ...itemAreas])

  return [...areas].sort((a, b) => {
    const aIndex = cultureAreaOrder.indexOf(a)
    const bIndex = cultureAreaOrder.indexOf(b)
    if (aIndex !== -1 || bIndex !== -1) {
      return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex)
    }
    return a.localeCompare(b, 'ko-KR')
  })
})
const cultureAreaLabel = (area) => cultureAreaLabels[area] || area
const hasSavedTasteResult = computed(() => authStore.isAuthenticated && Boolean(tasteTestStore.latestResult))
const shouldUseAnonymousHero = computed(() => !hasSavedTasteResult.value)
const recommendedItems = computed(() => (
  recommendationStore.result?.recommendations?.[config.value.recommendationKey] || []
))
const pickVisibleCount = 5
const activeTasteLabel = computed(() => (
  tasteTypeOptions.find((option) => option.value === selectedPickType.value)?.label
  || recommendationStore.result?.profile?.result_taste_label
  || recommendationStore.result?.profile?.taste_label
  || '내 취향'
))
const myTasteLabel = computed(() => (
  userTasteLabel.value
  || recommendationStore.result?.profile?.result_taste_label
  || recommendationStore.result?.profile?.taste_label
  || '내 취향'
))
const myTasteOption = computed(() => {
  const value = (
    userTasteType.value
    || recommendationStore.result?.profile?.result_taste_type
    || recommendationStore.result?.profile?.taste_type
    || ''
  )
  return value ? { value, label: myTasteLabel.value } : null
})
const heroTasteLabel = computed(() => (
  selectedPickType.value
    ? tasteTypeOptions.find((option) => option.value === selectedPickType.value)?.label || myTasteLabel.value
    : myTasteLabel.value
))
const otherTasteOptions = computed(() => (
  userTasteType.value
    ? tasteTypeOptions.filter((option) => option.value !== userTasteType.value)
    : []
))
const visiblePickItems = computed(() => (
  recommendedItems.value.slice(pickStartIndex.value, pickStartIndex.value + pickVisibleCount)
))
const currentPickIds = computed(() => recommendedItems.value.map((item) => item.content_item_id))
const maxPickStartIndex = computed(() => Math.max(recommendedItems.value.length - pickVisibleCount, 0))
const pickPositionText = computed(() => {
  if (!recommendedItems.value.length) return '0 / 0'
  return `${pickStartIndex.value + 1} / ${maxPickStartIndex.value + 1}`
})
const pickTitle = computed(() => (
  selectedPickType.value ? `${activeTasteLabel.value} PICK` : '내 취향 PICK'
))
const rankingItems = computed(() => contentStore.popularItems[props.contentType] || [])
const sortOptions = computed(() => props.contentType === 'cultures'
  ? [
      { value: 'ending', label: '마감 임박' },
      { value: 'upcoming', label: '시작순' },
      { value: 'latest', label: '최근 등록순' },
    ]
  : [
      { value: 'popular', label: '인기순' },
      { value: 'latest', label: '최신순' },
      { value: 'rating', label: '평점순' },
    ])

function itemId(item) {
  if (props.contentType === 'movies') return item.tmdb_id
  if (props.contentType === 'books') return item.item_id
  return item.seq
}

function itemContentId(item) {
  return item.content_id || item.content_item_id || null
}

function recommendationId(item) {
  if (props.contentType === 'movies') return item.metadata?.tmdb_id
  if (props.contentType === 'books') return item.metadata?.aladin_item_id
  return item.metadata?.seq
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
  if (props.contentType === 'cultures') {
    const startDate = formatCompactDate(item.metadata?.start_date)
    const endDate = formatCompactDate(item.metadata?.end_date)
    if (startDate && endDate) return `${startDate} ~ ${endDate}`
    return startDate || endDate || '기간 미정'
  }

  const labels = props.contentType === 'movies'
    ? item.metadata?.genres
    : item.metadata?.categories

  return labels?.filter(Boolean).slice(0, 2).join(' · ') || config.value.label
}

function recommendationTags(item) {
  if (props.contentType !== 'cultures') return []
  if (item.metadata?.main_category === '공연') return [item.metadata?.sub_category].filter(Boolean)
  return [item.metadata?.main_category || item.metadata?.sub_category].filter(Boolean)
}

function detailContentItemId() {
  if (!contentStore.currentDetail) return null
  return contentStore.currentDetail.content_id || null
}

function markContentLiked(contentItemId, isLiked) {
  if (!contentItemId) return
  const next = new Set(likedContentIds.value)
  if (isLiked) next.add(contentItemId)
  else next.delete(contentItemId)
  likedContentIds.value = next
}

function markContentStatusHydrated(contentItemId) {
  if (!contentItemId) return
  const next = new Set(hydratedContentStatusIds.value)
  next.add(contentItemId)
  hydratedContentStatusIds.value = next
}

function resetCardStatusCache() {
  likedContentIds.value = new Set()
  hydratedContentStatusIds.value = new Set()
}

function isCardLiked(item) {
  const contentItemId = itemContentId(item)
  return contentItemId ? likedContentIds.value.has(contentItemId) : false
}

function isCardFeedbackLoading(item) {
  const contentItemId = itemContentId(item)
  return contentItemId ? cardFeedbackLoadingIds.value.has(contentItemId) : false
}

function setCardFeedbackLoading(contentItemId, isLoading) {
  const next = new Set(cardFeedbackLoadingIds.value)
  if (isLoading) next.add(contentItemId)
  else next.delete(contentItemId)
  cardFeedbackLoadingIds.value = next
}

async function hydrateCardLikeStatus(items) {
  if (!authStore.isAuthenticated) {
    resetCardStatusCache()
    return
  }

  const contentIds = [...new Set(
    items
      .map((item) => itemContentId(item))
      .filter((contentItemId) => contentItemId && !hydratedContentStatusIds.value.has(contentItemId)),
  )]

  await Promise.allSettled(contentIds.map(async (contentItemId) => {
    const [feedbackResponse, bookmarkResponse] = await Promise.allSettled([
      api.get('/tastes/feedback/status/', { params: { content_item_id: contentItemId } }),
      api.get('/tastes/bookmarks/status/', { params: { content_item_id: contentItemId } }),
    ])

    const isLiked = (
      feedbackResponse.status === 'fulfilled'
      && feedbackResponse.value.data.feedback_type === 'like'
    )
    const isBookmarked = (
      bookmarkResponse.status === 'fulfilled'
      && Boolean(bookmarkResponse.value.data.bookmarked)
    )

    markContentLiked(contentItemId, isLiked || isBookmarked)
    markContentStatusHydrated(contentItemId)
  }))
}

function tags(item) {
  if (props.contentType !== 'cultures') return []
  if (item.main_category === '공연') return [item.sub_category].filter(Boolean)
  return [item.main_category || item.sub_category].filter(Boolean)
}

function itemMeta(item) {
  if (props.contentType === 'movies') {
    return [item.release_date?.slice(0, 4), item.vote_average != null ? `★ ${item.vote_average.toFixed(1)}` : null]
  }
  if (props.contentType === 'books') return [item.author, item.publisher]
  return [formatPeriod(item.start_date, item.end_date)]
}

function formatDate(value) {
  if (!value) return '-'
  return new Intl.DateTimeFormat('ko-KR').format(new Date(`${value}T00:00:00`))
}

function formatPeriod(startDate, endDate) {
  const start = startDate ? formatDate(startDate) : ''
  const end = endDate ? formatDate(endDate) : ''
  if (start && end) return `${start} ~ ${end}`
  return start || end || '기간 미정'
}

function queryParams(targetPage = 1) {
  const params = { page: targetPage, page_size: 20, sort: sort.value }
  if (appliedSearch.value) {
    params.search = appliedSearch.value
    if (['books', 'cultures'].includes(props.contentType) && searchScope.value !== 'all') {
      params.search_scope = searchScope.value
    }
  }
  if (selectedCategory.value !== '') {
    if (props.contentType === 'books' && selectedCategory.value === '__ebook') {
      params.has_ebook = 'true'
    } else {
      params[config.value.categoryParam] = selectedCategory.value
    }
  }
  if (props.contentType === 'cultures') {
    if (selectedMapArea.value) params.area = selectedMapArea.value
    if (selectedMapSigungu.value) params.sigungu = selectedMapSigungu.value
  }
  return params
}

async function loadInitial() {
  page.value = 1
  try {
    await contentStore.fetchItems(props.contentType, queryParams(), false)
    await hydrateCardLikeStatus(contentStore.items)
  } catch {
    // 목록 불러오기 실패는 스토어에서 처리합니다.
  }
}

async function loadMore() {
  if (contentStore.loading || !contentStore.next) return
  const nextPage = page.value + 1
  try {
    await contentStore.fetchItems(props.contentType, queryParams(nextPage), true)
    page.value = nextPage
    await hydrateCardLikeStatus(contentStore.items)
  } catch {
    // 목록 불러오기 실패는 스토어에서 처리합니다.
  }
}

async function applySearch() {
  appliedSearch.value = search.value.trim()
  await loadInitial()
}

async function selectCategory(value) {
  if (selectedCategory.value === value) return
  selectedCategory.value = value
  if (props.contentType === 'cultures') {
    selectedMapArea.value = ''
    selectedMapSigungu.value = ''
  }
  await loadInitial()
}

async function selectCultureRegionFilter(area) {
  if (selectedMapArea.value === area && !selectedMapSigungu.value) return
  selectedMapArea.value = area
  selectedMapSigungu.value = ''
  await loadInitial()
}

async function selectMapRegion(area, category = '') {
  try {
    await contentStore.fetchCultureMapItems({
      area,
      ...(category ? { main_category: category } : {}),
    })
  } catch {
    // 지도 영역 조회 실패는 화면 상태에 표시됩니다.
  }
}

async function selectMapCategory(category, area) {
  const params = category ? { main_category: category } : {}
  const tasks = [contentStore.fetchCultureRegionSummaries(params)]
  if (area) tasks.push(selectMapRegion(area, category))
  await Promise.allSettled(tasks)
}

function openMapEventDetail(item) {
  if (item?.seq != null) openDetailById(item.seq)
}

function scrollToCatalogTop() {
  catalogSection.value?.scrollIntoView({ behavior: 'auto', block: 'start' })
}

async function browseMapResults(category, area = '') {
  const available = config.value.categories.some(([value]) => value === category)
  const targetCategory = available ? category : ''
  const shouldReload = (
    selectedCategory.value !== targetCategory
    || selectedMapArea.value !== area
    || selectedMapSigungu.value
  )
  selectedCategory.value = targetCategory
  selectedMapArea.value = area
  selectedMapSigungu.value = ''
  if (shouldReload) await loadInitial()
  await nextTick()
  catalogSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function openDetailById(id) {
  bookmarked.value = false
  bookmarkLoading.value = false
  bookmarkError.value = ''
  feedbackType.value = null
  likeCount.value = 0
  feedbackLoading.value = false
  feedbackError.value = ''
  modalOpen.value = true
  document.body.classList.add('modal-lock')
  try {
    await contentStore.fetchDetail(props.contentType, id)
    const contentItemId = detailContentItemId()
    if (contentItemId) {
      const { data } = await api.get('/tastes/feedback/status/', {
        params: { content_item_id: contentItemId },
      })
      likeCount.value = Number(data.like_count || 0)
      feedbackType.value = data.feedback_type || null
      markContentLiked(contentItemId, feedbackType.value === 'like')
    }
    if (authStore.isAuthenticated) {
      if (contentItemId) {
        const { data } = await api.get('/tastes/bookmarks/status/', {
          params: { content_item_id: contentItemId },
        })
        bookmarked.value = Boolean(data.bookmarked)
        markContentLiked(contentItemId, bookmarked.value || feedbackType.value === 'like')
        markContentStatusHydrated(contentItemId)
      }
    }
  } catch {
    // 상세 정보 조회 실패는 스토어에서 처리합니다.
  }
}

function closeDetail() {
  modalOpen.value = false
  contentStore.clearDetail()
  bookmarked.value = false
  bookmarkLoading.value = false
  bookmarkError.value = ''
  feedbackType.value = null
  likeCount.value = 0
  feedbackLoading.value = false
  feedbackError.value = ''
  document.body.classList.remove('modal-lock')
}

async function setBookmarkStatus(nextBookmarked) {
  if (!authStore.isAuthenticated || bookmarked.value === nextBookmarked) return

  const contentItemId = detailContentItemId()
  if (!contentItemId) return

  bookmarkLoading.value = true
  bookmarkError.value = ''
  try {
    const { data } = await api.post('/tastes/bookmarks/toggle/', {
      content_item_id: contentItemId,
    })
    bookmarked.value = Boolean(data.bookmarked)
    markContentLiked(contentItemId, bookmarked.value || feedbackType.value === 'like')
    markContentStatusHydrated(contentItemId)
  } catch (error) {
    bookmarkError.value = (
      error.response?.data?.content_item_id?.[0]
      || error.response?.data?.detail
      || '좋아요 상태를 저장하지 못했습니다.'
    )
  } finally {
    bookmarkLoading.value = false
  }
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

async function toggleCardLike(item) {
  const contentItemId = itemContentId(item)
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

    if (detailContentItemId() === contentItemId) {
      feedbackType.value = data.feedback_type || null
      likeCount.value = Number(data.like_count || 0)
      bookmarked.value = isLiked
    }
  } catch {
    // 카드 좋아요 실패는 팝업의 상세 오류 안내를 방해하지 않습니다.
  } finally {
    setCardFeedbackLoading(contentItemId, false)
  }
}

async function submitFeedback(nextFeedbackType) {
  if (!authStore.isAuthenticated || feedbackLoading.value) return

  const contentItemId = detailContentItemId()
  if (!contentItemId) return

  const wasDisliked = feedbackType.value === 'dislike'
  feedbackLoading.value = true
  feedbackError.value = ''
  try {
    const { data } = await api.post('/tastes/feedback/', {
      content_item_id: contentItemId,
      feedback_type: nextFeedbackType,
    })
    likeCount.value = Number(data.like_count || 0)
    feedbackType.value = data.feedback_type || null
    markContentLiked(contentItemId, feedbackType.value === 'like')
    await setBookmarkStatus(feedbackType.value === 'like')
    if (nextFeedbackType === 'dislike' || wasDisliked) {
      recommendationStore.resetRecommendations()
    }
  } catch (error) {
    feedbackError.value = (
      error.response?.data?.content_item_id?.[0]
      || error.response?.data?.feedback_type?.[0]
      || error.response?.data?.detail
      || '반응을 저장하지 못했습니다.'
    )
  } finally {
    feedbackLoading.value = false
  }
}

function onKeydown(event) {
  if (event.key === 'Escape' && modalOpen.value) closeDetail()
}

function syncTasteProfileFromRecommendation() {
  const profile = recommendationStore.result?.profile
  if (!profile) return

  userTasteType.value = profile.result_taste_type || profile.taste_type || ''
  userTasteLabel.value = profile.result_taste_label || profile.taste_label || ''
}

async function preparePage() {
  search.value = ''
  appliedSearch.value = ''
  searchScope.value = 'all'
  selectedMapArea.value = ''
  selectedMapSigungu.value = ''
  selectedPickType.value = ''
  pickStartIndex.value = 0
  recommendationStore.resetRecommendations()
  const requestedCategory = typeof route.query.category === 'string' ? route.query.category : ''
  selectedCategory.value = (
            props.contentType === 'cultures'
    && categoryOptions.value.some(([value]) => value === requestedCategory)
  ) ? requestedCategory : ''
  sort.value = props.contentType === 'cultures' ? 'ending' : 'popular'
  closeDetail()
  const tasks = [loadInitial()]
  if (props.contentType !== 'cultures') tasks.push(contentStore.fetchPopular(props.contentType))
  if (props.contentType === 'cultures') {
    tasks.push(contentStore.fetchCultureRegionSummaries())
    loadKakaoMap().catch(() => {
      // 지도 로딩 실패는 문화행사 화면에서 안내됩니다.
    })
  }
  await Promise.allSettled(tasks)
  if (hasSavedTasteResult.value) {
    await loadTasteRecommendations()
  }
}

async function loadTasteRecommendations() {
  if (!hasSavedTasteResult.value || recommendationStore.loading) return
  try {
    const data = await recommendationStore.generateRecommendations({
      tasteType: selectedPickType.value,
      perType: 10,
    })
    if (!selectedPickType.value) {
      userTasteType.value = data.profile?.result_taste_type || ''
      userTasteLabel.value = data.profile?.result_taste_label || data.profile?.taste_label || ''
    }
    syncTasteProfileFromRecommendation()
    pickStartIndex.value = 0
    await hydrateCardLikeStatus(recommendedItems.value)
  } catch {
    // 추천 생성 실패는 추천 영역에서 안내됩니다.
  }
}

async function refreshTasteRecommendations() {
  if (!hasSavedTasteResult.value || recommendationStore.loading) return
  const resolvedTasteType = selectedPickType.value || recommendationStore.result?.profile?.taste_type
  try {
    await recommendationStore.generateRecommendations({
      tasteType: resolvedTasteType,
      perType: 10,
      excludeContentIds: currentPickIds.value,
    })
    pickStartIndex.value = 0
    await hydrateCardLikeStatus(recommendedItems.value)
  } catch {
    // 추천 생성 실패는 추천 영역에서 안내됩니다.
  }
}

async function selectPickType(tasteType) {
  const nextTasteType = selectedPickType.value === tasteType ? '' : tasteType
  if (selectedPickType.value === nextTasteType && recommendationStore.result) return
  selectedPickType.value = nextTasteType
  pickStartIndex.value = 0
  recommendationStore.resetRecommendations()
  await loadTasteRecommendations()
}

async function selectMyTasteType() {
  if (!selectedPickType.value && recommendationStore.result) return
  selectedPickType.value = ''
  pickStartIndex.value = 0
  recommendationStore.resetRecommendations()
  await loadTasteRecommendations()
}

function movePick(direction) {
  if (!recommendedItems.value.length) return
  const nextIndex = pickStartIndex.value + direction
  pickStartIndex.value = Math.min(Math.max(nextIndex, 0), maxPickStartIndex.value)
}

watch(() => props.contentType, preparePage)

watch(
  () => recommendationStore.result?.profile,
  () => {
    syncTasteProfileFromRecommendation()
  },
  { immediate: true },
)

watch(
  () => authStore.isAuthenticated,
  async (isAuthenticated) => {
    if (isAuthenticated) {
      try {
        await tasteTestStore.fetchLatestResult()
      } catch {
        tasteTestStore.latestResult = null
      }
    } else {
      tasteTestStore.latestResult = null
      selectedPickType.value = ''
      userTasteType.value = ''
      userTasteLabel.value = ''
      recommendationStore.resetRecommendations()
    }

    if (!hasSavedTasteResult.value) {
      selectedPickType.value = ''
      userTasteType.value = ''
      userTasteLabel.value = ''
      recommendationStore.resetRecommendations()
      return
    }

    if (recommendationStore.result) {
      syncTasteProfileFromRecommendation()
      await hydrateCardLikeStatus(recommendedItems.value)
      return
    }

    if (!recommendationStore.result && !recommendationStore.loading) {
      await loadTasteRecommendations()
    }
  },
  { immediate: true },
)

onMounted(async () => {
  await preparePage()
  await nextTick()
  observer = new IntersectionObserver((entries) => {
    if (entries[0]?.isIntersecting) loadMore()
  }, { rootMargin: '240px' })
  if (sentinel.value) observer.observe(sentinel.value)
  window.addEventListener('keydown', onKeydown)
  if (route.hash === '#culture-catalog') {
    catalogSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
})

onBeforeUnmount(() => {
  observer?.disconnect()
  window.removeEventListener('keydown', onKeydown)
  document.body.classList.remove('modal-lock')
})
</script>

<template>
  <main
    class="contents-page"
    :style="{ '--lounge-bg-image': `url(${loungeBackground})` }"
  >
    <section v-if="shouldUseAnonymousHero" class="contents-hero lounge-hero">
      <p class="eyebrow">DISCOVER YOUR NEXT FAVORITE</p>
      <h1>너의 취향은 <strong>아직 비밀</strong>이야.</h1>
      <RouterLink class="hero-test-button" to="/taste-test">
        추천 PICK이 궁금하면 취향 테스트하러 가기
      </RouterLink>
    </section>
    <section v-else class="contents-hero taste-pick-hero lounge-hero">
      <p class="eyebrow">DISCOVER YOUR NEXT FAVORITE</p>
      <h1>너의 취향은 <strong>{{ heroTasteLabel }}</strong> 이야.</h1>
      <div class="today-taste-bar" aria-label="오늘의 취향 선택">
        <div v-if="myTasteOption" class="today-my-taste">
          <span>MY PICK</span>
          <button
            type="button"
            :class="{ active: !selectedPickType }"
            @click="selectMyTasteType"
          >
            {{ myTasteOption.label }}
          </button>
        </div>
        <i v-if="myTasteOption && otherTasteOptions.length" class="taste-bar-divider" aria-hidden="true"></i>
        <span>오늘의 PICK</span>
        <button
          v-for="tasteType in otherTasteOptions"
          :key="tasteType.value"
          type="button"
          :class="{ active: selectedPickType === tasteType.value }"
          @click="selectPickType(tasteType.value)"
        >
          {{ tasteType.label }}
        </button>
      </div>
    </section>

    <section class="contents-shell" :class="{ 'contents-shell-with-picks': hasSavedTasteResult }">
      <section v-if="hasSavedTasteResult" class="taste-picks">
        <p v-if="recommendationStore.loading" class="taste-empty">취향에 맞는 콘텐츠를 고르는 중이에요.</p>
        <p v-else-if="recommendationStore.error" class="taste-empty">
          {{ recommendationStore.error }}
        </p>
        <section v-else-if="recommendedItems.length" class="pick-carousel">
          <div class="pick-carousel-heading">
            <div class="pick-heading-main">
              <h3>{{ pickTitle }}</h3>
            </div>
            <div class="pick-heading-actions">
              <button
                type="button"
                class="pick-refresh-button"
                :disabled="recommendationStore.loading"
                aria-label="다시 받기"
                title="다시 받기"
                @click="refreshTasteRecommendations"
              >
                ↻
              </button>
            </div>
          </div>
          <div class="recommendation-strip">
            <article
              v-for="item in visiblePickItems"
              :key="item.content_item_id"
              class="mini-content-card"
              role="button"
              tabindex="0"
              @click="openDetailById(recommendationId(item))"
              @keydown.enter.prevent="openDetailById(recommendationId(item))"
              @keydown.space.prevent="openDetailById(recommendationId(item))"
            >
              <div class="mini-poster-frame">
                <img v-if="item.thumbnail_url" :src="item.thumbnail_url" :alt="`${item.title} 이미지`" />
                <div v-else class="poster-fallback">{{ config.icon }}</div>
                <button
                  v-if="authStore.isAuthenticated"
                  type="button"
                  class="card-like-button"
                  :class="{ active: isCardLiked(item) }"
                  :disabled="isCardFeedbackLoading(item)"
                  :aria-label="isCardLiked(item) ? '좋아요 해제' : '좋아요'"
                  :title="isCardLiked(item) ? '좋아요 해제' : '좋아요'"
                  @click.stop="toggleCardLike(item)"
                >
                  <span aria-hidden="true">{{ isCardLiked(item) ? '♥' : '♡' }}</span>
                </button>
              </div>
              <div class="mini-content-caption">
                <div v-if="recommendationTags(item).length" class="tag-row mini-tags">
                  <span v-for="tag in recommendationTags(item).slice(0, 2)" :key="tag">{{ tag }}</span>
                </div>
                <p>{{ recommendationMetaText(item) }}</p>
                <h3>{{ item.title }}</h3>
              </div>
            </article>
          </div>
          <footer class="pick-carousel-footer">
            <span class="pick-page-indicator">{{ pickPositionText }}</span>
            <div class="pick-carousel-controls">
              <button type="button" :disabled="pickStartIndex === 0" aria-label="이전 PICK" @click="movePick(-1)">&lt;</button>
              <button type="button" :disabled="pickStartIndex >= maxPickStartIndex" aria-label="다음 PICK" @click="movePick(1)">&gt;</button>
            </div>
          </footer>
        </section>
        <p v-else class="taste-empty">취향에 맞는 콘텐츠를 고르는 중이에요.</p>
      </section>

      <section v-if="contentType === 'cultures'" class="culture-map-preview">
        <div class="culture-map-preview-heading">
          <div>
            <p class="section-kicker">EXPLORE NEARBY</p>
            <h2>지역별 문화행사</h2>
          </div>
        </div>

        <p v-if="contentStore.mapLoading && !contentStore.regionSummaries.length" class="culture-map-preview-status">
          지도를 불러오는 중입니다.
        </p>
        <p v-else-if="contentStore.mapError" class="culture-map-preview-status culture-map-preview-error">
          {{ contentStore.mapError }}
          <button type="button" @click="contentStore.fetchCultureRegionSummaries()">다시 시도</button>
        </p>

        <CultureMap
          compact
          :items="contentStore.mapItems"
          :region-summaries="contentStore.regionSummaries"
          @select-region="selectMapRegion"
          @select-category="selectMapCategory"
          @browse-more="browseMapResults"
          @open-event="openMapEventDetail"
        />
      </section>

      <section v-if="contentType !== 'cultures'" class="popular-ranking">
        <div class="section-title-row">
          <div>
            <p class="section-kicker">POPULAR NOW</p>
            <h2>지금 인기 순위</h2>
            <p class="ranking-description">
              {{ contentType === 'movies' ? 'TMDB 인기순' : '알라딘 판매지수' }}를 기준으로 정렬했어요.
            </p>
          </div>
        </div>

        <ol class="ranking-list">
          <li v-for="(item, index) in rankingItems" :key="itemId(item)">
            <button type="button" @click="openDetailById(itemId(item))">
              <strong class="rank-number">{{ index + 1 }}</strong>
              <div class="rank-cover">
                <img v-if="item.thumbnail_url" :src="item.thumbnail_url" :alt="`${item.title} 이미지`" />
                <div v-else class="poster-fallback">{{ config.icon }}</div>
              </div>
              <div class="rank-copy">
                <h3>{{ item.title }}</h3>
                <p>{{ itemMeta(item).filter(Boolean).join(' · ') }}</p>
              </div>
            </button>
          </li>
        </ol>
      </section>

      <section id="culture-catalog" ref="catalogSection" class="catalog-section">
        <div class="contents-heading">
          <div>
            <p class="section-kicker">BROWSE BY CATEGORY</p>
            <h2>{{ config.label }} 둘러보기</h2>
          </div>
          <strong>{{ contentStore.count.toLocaleString() }}개의 콘텐츠</strong>
        </div>

        <div class="category-clickbar" role="group" :aria-label="`${config.label} 분류 선택`">
          <button
            type="button"
            :class="{ active: selectedCategory === '' }"
            @click="selectCategory('')"
          >전체</button>
          <button
            v-for="category in categoryOptions"
            :key="category[0]"
            type="button"
            :class="{ active: selectedCategory === category[0] }"
            @click="selectCategory(category[0])"
          >{{ category[1] }}</button>
        </div>

        <form class="content-toolbar" @submit.prevent="applySearch">
          <label class="search-field">
            <span class="sr-only">콘텐츠 검색</span>
            <select
              v-if="searchScopeOptions.length"
              v-model="searchScope"
              class="search-scope-select"
              :aria-label="`${config.label} 검색 범위`"
            >
              <option v-for="scope in searchScopeOptions" :key="scope.value" :value="scope.value">
                {{ scope.label }}
              </option>
            </select>
            <input v-model="search" type="search" :placeholder="`${config.label} 제목을 검색해 보세요`" />
            <button type="submit">검색</button>
          </label>
          <select v-model="sort" aria-label="정렬 방식" @change="loadInitial">
            <option v-for="option in sortOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </form>

        <div
          class="catalog-results-layout"
          :class="{ 'has-region-filter': contentType === 'cultures' && cultureRegionOptions.length }"
        >
          <aside
            v-if="contentType === 'cultures' && cultureRegionOptions.length"
            class="region-filter-panel"
            aria-label="대표 지역 선택"
          >
            <strong>지역</strong>
            <div role="group" aria-label="대표 지역">
              <button
                type="button"
                :class="{ active: selectedMapArea === '' }"
                @click="selectCultureRegionFilter('')"
              >
                전체
              </button>
              <button
                v-for="region in cultureRegionOptions"
                :key="region"
                type="button"
                :class="{ active: selectedMapArea === region, compact: cultureAreaLabel(region).length <= 3 }"
                @click="selectCultureRegionFilter(region)"
              >
                {{ cultureAreaLabel(region) }}
              </button>
            </div>
          </aside>

          <div class="catalog-results-main">
            <button
              type="button"
              class="catalog-scroll-top-button"
              aria-label="목록 시작점으로 이동"
              title="목록 시작점으로 이동"
              @click="scrollToCatalogTop"
            >
              ↑
            </button>
            <p v-if="contentStore.error && !modalOpen" class="content-state error-state">
              {{ contentStore.error }} <button type="button" @click="loadInitial">다시 시도</button>
            </p>
            <p v-else-if="!contentStore.loading && contentStore.items.length === 0" class="content-state">
              조건에 맞는 콘텐츠가 없습니다.
            </p>

            <section v-else class="content-grid" :aria-busy="contentStore.loading">
              <article
                v-for="item in contentStore.items"
                :key="`${contentType}-${itemId(item)}`"
                class="content-card"
                role="button"
                tabindex="0"
                @click="openDetailById(itemId(item))"
                @keydown.enter.prevent="openDetailById(itemId(item))"
                @keydown.space.prevent="openDetailById(itemId(item))"
              >
                <div class="poster-frame" :class="{ 'book-poster-frame': contentType === 'books' }">
                  <img v-if="item.thumbnail_url" :src="item.thumbnail_url" :alt="`${item.title} 포스터`" loading="lazy" />
                  <div v-else class="poster-fallback">{{ config.icon }}</div>
                  <span v-if="contentType === 'books' && item.has_ebook" class="ebook-badge">Ebook</span>
                  <button
                    v-if="authStore.isAuthenticated"
                    type="button"
                    class="card-like-button"
                    :class="{ active: isCardLiked(item) }"
                    :disabled="isCardFeedbackLoading(item)"
                    :aria-label="isCardLiked(item) ? '좋아요 해제' : '좋아요'"
                    :title="isCardLiked(item) ? '좋아요 해제' : '좋아요'"
                    @click.stop="toggleCardLike(item)"
                  >
                    <span aria-hidden="true">{{ isCardLiked(item) ? '♥' : '♡' }}</span>
                  </button>
                </div>
                <div class="card-body">
                  <div v-if="tags(item).length" class="tag-row"><span v-for="tag in tags(item).slice(0, 2)" :key="tag">{{ tag }}</span></div>
                  <h3>{{ item.title }}</h3>
                  <p class="card-meta"><span v-for="meta in itemMeta(item).filter(Boolean)" :key="meta">{{ meta }}</span></p>
                </div>
              </article>
            </section>

            <div ref="sentinel" class="scroll-sentinel" aria-hidden="true"></div>
            <p v-if="contentStore.loading" class="loading-row">콘텐츠를 불러오는 중이에요.</p>
            <p v-else-if="contentStore.items.length && !contentStore.next" class="end-row">모든 콘텐츠를 확인했습니다.</p>
          </div>
        </div>
      </section>
    </section>

    <Teleport to="body">
      <div v-if="modalOpen" class="detail-overlay" @click.self="closeDetail">
        <section class="detail-modal" role="dialog" aria-modal="true" aria-label="콘텐츠 상세 정보">
          <button class="modal-close" type="button" aria-label="닫기" @click="closeDetail">×</button>
          <p v-if="contentStore.detailLoading" class="content-state">상세 정보를 불러오는 중이에요.</p>
          <p v-else-if="contentStore.error" class="content-state error-state">{{ contentStore.error }}</p>
          <template v-else-if="contentStore.currentDetail">
            <div class="detail-cover">
              <img v-if="contentStore.currentDetail.thumbnail_url" :src="contentStore.currentDetail.thumbnail_url" :alt="`${contentStore.currentDetail.title} 이미지`" />
              <div v-else class="poster-fallback">{{ config.icon }}</div>
            </div>
            <div class="detail-content">
              <p class="detail-kind">{{ config.label }}</p>
              <div class="detail-title-row">
                <div>
                  <h2>{{ contentStore.currentDetail.title }}</h2>
                  <p
                    v-if="contentType === 'movies' && contentStore.currentDetail.original_title"
                    class="detail-original-title"
                  >
                    {{ contentStore.currentDetail.original_title }}
                  </p>
                </div>
                <button
                  v-if="authStore.isAuthenticated"
                  type="button"
                  class="heart-button"
                  :class="{ active: feedbackType === 'like' }"
                  :disabled="feedbackLoading || bookmarkLoading"
                  :aria-label="feedbackType === 'like' ? '좋아요 해제' : '좋아요'"
                  :title="feedbackType === 'like' ? '좋아요 해제' : '좋아요'"
                  @click="submitFeedback('like')"
                >
                  <span aria-hidden="true">{{ feedbackType === 'like' ? '♥' : '♡' }}</span>
                  <strong>{{ likeCount.toLocaleString() }}</strong>
                </button>
              </div>
              <div v-if="tags(contentStore.currentDetail).length" class="tag-row detail-tags"><span v-for="tag in tags(contentStore.currentDetail)" :key="tag">{{ tag }}</span></div>
              <dl v-if="contentType === 'movies'" class="detail-facts">
                <div><dt>개봉일</dt><dd>{{ formatDate(contentStore.currentDetail.release_date) }}</dd></div>
                <div><dt>평점</dt><dd>★ {{ contentStore.currentDetail.vote_average?.toFixed(1) }}</dd></div>
              </dl>
              <dl v-else-if="contentType === 'books'" class="detail-facts">
                <div><dt>저자</dt><dd>{{ contentStore.currentDetail.author || '-' }}</dd></div>
                <div><dt>출판사</dt><dd>{{ contentStore.currentDetail.publisher || '-' }}</dd></div>
                <div><dt>출간일</dt><dd>{{ formatDate(contentStore.currentDetail.pub_date) }}</dd></div>
              </dl>
              <dl v-else class="detail-facts">
                <div><dt>기간</dt><dd>{{ formatPeriod(contentStore.currentDetail.start_date, contentStore.currentDetail.end_date) }}</dd></div>
                <div><dt>장소</dt><dd>{{ contentStore.currentDetail.place?.place_name || '-' }}</dd></div>
              </dl>
              <p v-if="contentStore.currentDetail.summary" class="detail-summary">{{ contentStore.currentDetail.summary }}</p>
              <div class="detail-actions">
                <p v-if="authStore.isAuthenticated && (bookmarkError || feedbackError)" class="detail-action-error">
                  {{ bookmarkError || feedbackError }}
                </p>
              </div>
              <div class="detail-bottom-actions">
                <a v-if="contentStore.currentDetail.source_url" class="source-link" :href="contentStore.currentDetail.source_url" target="_blank" rel="noopener noreferrer">원문 페이지 보기 ↗</a>
                <button
                  v-if="authStore.isAuthenticated"
                  type="button"
                  class="hide-content-button"
                  :class="{ active: feedbackType === 'dislike' }"
                  :disabled="feedbackLoading || bookmarkLoading"
                  @click="submitFeedback('dislike')"
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
