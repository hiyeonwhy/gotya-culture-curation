<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

import api from '../api'
import { useAuthStore } from '../stores/auth'
import { useMyPageStore } from '../stores/mypage'
import { useTasteTestStore } from '../stores/tasteTest'
import '../assets/mypage.css'


const authStore = useAuthStore()
const myPageStore = useMyPageStore()
const tasteTestStore = useTasteTestStore()
const sentinel = ref(null)
const profileImageInput = ref(null)
const profileImageUploading = ref(false)
const profileImageError = ref('')
const modalOpen = ref(false)
const detailLoading = ref(false)
const detailError = ref('')
const currentDetail = ref(null)
const currentListItem = ref(null)
const feedbackType = ref(null)
const likeCount = ref(0)
const actionLoading = ref(false)
const actionError = ref('')
let observer = null

const DETAIL_ENDPOINTS = {
  movie: '/movies/',
  book: '/books/',
  culture: '/cultures/',
}

const collectionTabs = [
  { value: 'bookmarks', label: '\ub098\uc758 \ucc1c \ubaa9\ub85d' },
  { value: 'dislikes', label: '\uc2eb\uc5b4\uc694 \ubaa9\ub85d' },
]

const typeTabs = [
  { value: '', label: '\uc804\uccb4' },
  { value: 'book', label: '\ub3c4\uc11c' },
  { value: 'movie', label: '\uc601\ud654' },
  { value: 'culture', label: '\ubb38\ud654' },
]

const contentTypeLabels = {
  book: '\ub3c4\uc11c',
  movie: '\uc601\ud654',
  culture: '\ubb38\ud654',
}

const selectedCollectionLabel = computed(() => (
  collectionTabs.find((tab) => tab.value === myPageStore.selectedCollection)?.label || '\ub098\uc758 \ucc1c \ubaa9\ub85d'
))
const collectionEyebrow = computed(() => (
  myPageStore.selectedCollection === 'dislikes' ? 'HIDDEN CONTENTS' : 'BOOKMARKS'
))
const collectionDescription = computed(() => (
  myPageStore.selectedCollection === 'dislikes'
    ? 'AI \ucd94\ucc9c\uc5d0\uc11c \uc81c\uc678\ud55c \ucf58\ud150\uce20\ub97c \ud55c \ubc88\uc5d0 \ud655\uc778\ud574\uc694.'
    : '\uad00\uc2ec \uc788\ub294 \ub3c4\uc11c, \uc601\ud654, \ubb38\ud654 \ucf58\ud150\uce20\ub97c \ud55c \ubc88\uc5d0 \ud655\uc778\ud574\uc694.'
))
const emptyTitle = computed(() => (
  myPageStore.selectedCollection === 'dislikes'
    ? '\uc544\uc9c1 \ub2e4\uc2dc \ubcf4\uc9c0 \uc54a\uae30\ub85c \uc124\uc815\ud55c \ucf58\ud150\uce20\uac00 \uc5c6\uc5b4\uc694.'
    : '\uc544\uc9c1 \ucc1c\ud55c \ucf58\ud150\uce20\uac00 \uc5c6\uc5b4\uc694.'
))
const emptyDescription = computed(() => (
  myPageStore.selectedCollection === 'dislikes'
    ? '\ucf58\ud150\uce20 \ud31d\uc5c5\uc5d0\uc11c \ub2e4\uc2dc \ubcf4\uc9c0 \uc54a\uae30\ub97c \ub204\ub974\uba74 \uc774\uacf3\uc5d0 \ubaa8\uc785\ub2c8\ub2e4.'
    : '\ub77c\uc6b4\uc9c0\uc5d0\uc11c \ub9c8\uc74c\uc5d0 \ub4dc\ub294 \ucf58\ud150\uce20\ub97c \ud558\ud2b8\ub85c \ubaa8\uc544\ubcf4\uc138\uc694.'
))
const itemDateSuffix = computed(() => (
  myPageStore.selectedCollection === 'dislikes' ? '\uc124\uc815' : '\ucc1c'
))

const profileInitial = computed(() => (
  authStore.user?.nickname?.trim()?.[0] || authStore.user?.login_id?.trim()?.[0] || '?'
))
const latestTaste = computed(() => tasteTestStore.latestResult)
const tasteName = computed(() => latestTaste.value?.result?.name || '\uc544\uc9c1 \ucde8\ud5a5 \uacb0\uacfc\uac00 \uc5c6\uc5b4\uc694.')
const tasteSummary = computed(() => latestTaste.value?.result?.summary || '\ucde8\ud5a5 \ud14c\uc2a4\ud2b8\ub97c \uc644\ub8cc\ud558\uba74 \ub098\uc758 \ubb38\ud654 \ucde8\ud5a5\uacfc \uc131\ud5a5\ucd95\uc744 \ud655\uc778\ud560 \uc218 \uc788\uc5b4\uc694.')
const tasteKeywords = computed(() => latestTaste.value?.result?.keywords || [])
const tasteAxisRows = computed(() => latestTaste.value?.axis_percentages || [])
const detailHeartActive = computed(() => (
  feedbackType.value === 'like'
  || myPageStore.selectedCollection === 'bookmarks'
))
function formatDate(value) {
  if (!value) return '-'
  return new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(new Date(value))
}

function contentIcon(type) {
  if (type === 'movie') return '\uc601\ud654'
  if (type === 'book') return '\ub3c4\uc11c'
  return '\ubb38\ud654'
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

function listItemMetaText(item) {
  if (item.content_type === 'culture') {
    const startDate = formatCompactDate(item.metadata?.start_date)
    const endDate = formatCompactDate(item.metadata?.end_date)
    if (startDate && endDate) return `${startDate} ~ ${endDate}`
    return startDate || endDate || '기간 미정'
  }

  const labels = item.content_type === 'movie'
    ? item.metadata?.genres
    : item.metadata?.categories

  return labels?.filter(Boolean).slice(0, 2).join(' · ') || contentTypeLabels[item.content_type] || item.content_type
}

function shortSummary(value) {
  return value || '\uc0c1\uc138 \uc124\uba85\uc774 \uc900\ube44\ub418\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4.'
}

function detailContentItemId() {
  return currentDetail.value?.content_id || currentListItem.value?.content_item_id || null
}

function detailTags(item) {
  if (!item) return []
  if (currentListItem.value?.content_type === 'movie') return item.genres?.map((genre) => genre.name) || []
  if (currentListItem.value?.content_type === 'book') return item.categories?.map((category) => category.name) || []
  return [item.main_category, item.sub_category].filter(Boolean)
}

function removeCurrentListItem() {
  if (currentListItem.value) myPageStore.removeItem(currentListItem.value.id)
}

async function syncBookmarkForContent(contentItemId, shouldBookmark) {
  if (!contentItemId) return
  const { data } = await api.get('/tastes/bookmarks/status/', {
    params: { content_item_id: contentItemId },
  })
  if (Boolean(data.bookmarked) !== shouldBookmark) {
    await api.post('/tastes/bookmarks/toggle/', {
      content_item_id: contentItemId,
    })
  }
}

async function openContentModal(item) {
  if (!item.detail_id || !DETAIL_ENDPOINTS[item.content_type]) return
  modalOpen.value = true
  detailLoading.value = true
  detailError.value = ''
  actionError.value = ''
  currentDetail.value = null
  currentListItem.value = item
  feedbackType.value = null
  likeCount.value = 0
  document.body.classList.add('modal-lock')

  try {
    const { data } = await api.get(`${DETAIL_ENDPOINTS[item.content_type]}${item.detail_id}/`)
    currentDetail.value = data
    const status = await api.get('/tastes/feedback/status/', {
      params: { content_item_id: item.content_item_id },
    })
    likeCount.value = Number(status.data.like_count || 0)
    feedbackType.value = status.data.feedback_type || null
  } catch (requestError) {
    detailError.value = requestError.response?.data?.detail || '\uc0c1\uc138 \uc815\ubcf4\ub97c \ubd88\ub7ec\uc624\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.'
  } finally {
    detailLoading.value = false
  }
}

function closeContentModal() {
  modalOpen.value = false
  currentDetail.value = null
  currentListItem.value = null
  feedbackType.value = null
  likeCount.value = 0
  actionError.value = ''
  document.body.classList.remove('modal-lock')
}

async function submitDetailFeedback(nextFeedbackType) {
  const contentItemId = detailContentItemId()
  if (!contentItemId || actionLoading.value) return

  actionLoading.value = true
  actionError.value = ''
  try {
    if (
      nextFeedbackType === 'like'
      && myPageStore.selectedCollection === 'bookmarks'
      && feedbackType.value !== 'like'
    ) {
      await syncBookmarkForContent(contentItemId, false)
      removeCurrentListItem()
      closeContentModal()
      return
    }

    const { data } = await api.post('/tastes/feedback/', {
      content_item_id: contentItemId,
      feedback_type: nextFeedbackType,
    })
    feedbackType.value = data.feedback_type || null
    likeCount.value = Number(data.like_count || 0)

    if (nextFeedbackType === 'like') {
      await syncBookmarkForContent(contentItemId, feedbackType.value === 'like')
      if (
        (myPageStore.selectedCollection === 'bookmarks' && feedbackType.value !== 'like')
        || myPageStore.selectedCollection === 'dislikes'
      ) {
        removeCurrentListItem()
        closeContentModal()
      }
    }

    if (nextFeedbackType === 'dislike') {
      await syncBookmarkForContent(contentItemId, false)
      if (
        myPageStore.selectedCollection === 'bookmarks'
        || (myPageStore.selectedCollection === 'dislikes' && feedbackType.value !== 'dislike')
      ) {
        removeCurrentListItem()
        closeContentModal()
      }
    }
  } catch (requestError) {
    actionError.value = requestError.response?.data?.detail || '\uc0c1\ud0dc\ub97c \ubcc0\uacbd\ud558\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.'
  } finally {
    actionLoading.value = false
  }
}

function openProfileImagePicker() {
  profileImageInput.value?.click()
}

async function handleProfileImageChange(event) {
  const [file] = event.target.files || []
  if (!file) return

  profileImageError.value = ''
  if (!file.type.startsWith('image/')) {
    profileImageError.value = '이미지 파일만 등록할 수 있습니다.'
    event.target.value = ''
    return
  }

  profileImageUploading.value = true
  try {
    await authStore.uploadProfileImage(file)
  } catch (requestError) {
    const data = requestError.response?.data
    profileImageError.value = data?.profile_image?.[0] || data?.detail || '프로필 사진을 등록하지 못했습니다.'
  } finally {
    profileImageUploading.value = false
    event.target.value = ''
  }
}

async function changeCollection(collection) {
  if (myPageStore.selectedCollection === collection && myPageStore.bookmarks.length) return
  await myPageStore.fetchCollection({
    collection,
    contentType: myPageStore.selectedType,
    targetPage: 1,
    append: false,
  })
  await nextTick()
  observeSentinel()
}

async function changeType(type) {
  if (myPageStore.selectedType === type && myPageStore.bookmarks.length) return
  await myPageStore.fetchCollection({
    collection: myPageStore.selectedCollection,
    contentType: type,
    targetPage: 1,
    append: false,
  })
  await nextTick()
  observeSentinel()
}

function observeSentinel() {
  if (!sentinel.value) return
  observer?.disconnect()
  observer = new IntersectionObserver((entries) => {
    if (entries[0]?.isIntersecting) {
      myPageStore.fetchNextBookmarks().catch(() => {})
    }
  }, { rootMargin: '180px' })
  observer.observe(sentinel.value)
}

onMounted(async () => {
  if (!authStore.user && authStore.token) {
    await authStore.fetchCurrentUser().catch(() => {})
  }

  await Promise.allSettled([
    tasteTestStore.fetchLatestResult(),
    myPageStore.fetchCollection({ collection: 'bookmarks', targetPage: 1, append: false }),
  ])
  await nextTick()
  observeSentinel()
})

onBeforeUnmount(() => {
  observer?.disconnect()
  document.body.classList.remove('modal-lock')
  myPageStore.reset()
})
</script>

<template>
  <main class="mypage">
    <section class="mypage-hero">
      <div class="profile-card">
        <div>
          <button
            class="profile-image profile-image-button"
            type="button"
            :disabled="profileImageUploading"
            aria-label="Upload profile image"
            title="Upload profile image"
            @click="openProfileImagePicker"
          >
            <img
              v-if="authStore.user?.profile_image"
              :src="authStore.user.profile_image"
              :alt="`${authStore.user.nickname || 'User'} profile image`"
            >
            <span v-else>{{ profileInitial }}</span>
            <em>{{ profileImageUploading ? 'Uploading...' : 'Change photo' }}</em>
          </button>
          <input
            ref="profileImageInput"
            class="profile-image-input"
            type="file"
            accept="image/*"
            @change="handleProfileImageChange"
          >
          <p v-if="profileImageError" class="profile-image-error">
            {{ profileImageError }}
          </p>
        </div>
        <div>
          <p class="eyebrow">MY PAGE</p>
          <div class="profile-title-row">
            <h1>{{ authStore.user?.nickname || 'User' }}님</h1>
            <RouterLink class="profile-edit-link" to="/mypage/edit">
              회원정보 수정
            </RouterLink>
          </div>
          <p>{{ authStore.user?.login_id }} 계정으로 GotYA을 이용 중입니다.</p>
          <dl>
            <div>
              <dt>가입일</dt>
              <dd>{{ formatDate(authStore.user?.created_at) }}</dd>
            </div>
          </dl>
        </div>
      </div>

      <div class="taste-card">
        <div class="taste-card-header">
          <div>
            <p class="eyebrow">MY CULTURE TASTE</p>
            <h2>나의 취향</h2>
          </div>
          <RouterLink to="/taste-test">다시 테스트하기</RouterLink>
        </div>

        <strong class="taste-name">{{ tasteName }}</strong>
        <p>{{ tasteSummary }}</p>

        <div v-if="tasteKeywords.length" class="keyword-list">
          <span v-for="keyword in tasteKeywords" :key="keyword">#{{ keyword }}</span>
        </div>

        <div v-if="latestTaste" class="score-list" aria-label="취향 성향축">
          <div
            v-for="score in tasteAxisRows"
            :key="score.key"
            class="score-row"
          >
            <span>{{ score.left_label }}</span>
            <div class="score-track">
              <i :style="{ width: `${score.left_percentage}%` }" />
            </div>
            <strong>{{ Number(score.left_percentage).toFixed(1) }}%</strong>
            <span>{{ score.right_label }}</span>
            <strong>{{ Number(score.right_percentage).toFixed(1) }}%</strong>
          </div>
        </div>

        <RouterLink v-else class="taste-start-link" to="/taste-test">
          취향 테스트 시작하기
        </RouterLink>
      </div>
    </section>
    <section class="bookmark-section">
      <div class="section-heading">
        <div>
          <p class="eyebrow">{{ collectionEyebrow }}</p>
          <h2>{{ selectedCollectionLabel }}</h2>
        </div>
      </div>

      <div class="collection-switch" aria-label="마이페이지 콘텐츠 목록 선택">
        <button
          v-for="tab in collectionTabs"
          :key="tab.value"
          type="button"
          :class="{ active: myPageStore.selectedCollection === tab.value }"
          @click="changeCollection(tab.value)"
        >
          {{ tab.label }}
        </button>
      </div>

      <div class="bookmark-tabs" aria-label="콘텐츠 유형 필터">
        <button
          v-for="tab in typeTabs"
          :key="tab.value || 'all'"
          type="button"
          :class="{ active: myPageStore.selectedType === tab.value }"
          @click="changeType(tab.value)"
        >
          {{ tab.label }}
        </button>
      </div>

      <p v-if="myPageStore.error" class="mypage-error">{{ myPageStore.error }}</p>

      <div v-if="myPageStore.bookmarks.length" class="bookmark-grid">
        <article
          v-for="item in myPageStore.bookmarks"
          :key="`${myPageStore.selectedCollection}-${item.id}`"
          class="bookmark-card"
        >
          <div
            class="bookmark-cover bookmark-cover-button"
            role="button"
            tabindex="0"
            @click="openContentModal(item)"
            @keydown.enter.prevent="openContentModal(item)"
            @keydown.space.prevent="openContentModal(item)"
          >
            <img
              v-if="item.thumbnail_url"
              :src="item.thumbnail_url"
              :alt="item.title"
            >
            <span v-else>{{ contentIcon(item.content_type) }}</span>
          </div>
          <div class="bookmark-body">
            <p>{{ listItemMetaText(item) }}</p>
            <h3>{{ item.title }}</h3>
          </div>
        </article>
      </div>

      <div v-else-if="!myPageStore.loading" class="empty-bookmarks">
        <strong>{{ emptyTitle }}</strong>
        <p>{{ emptyDescription }}</p>
        <div>
          <RouterLink to="/books">도서 둘러보기</RouterLink>
          <RouterLink to="/movies">영화 둘러보기</RouterLink>
          <RouterLink to="/cultures">문화 둘러보기</RouterLink>
        </div>
      </div>

      <div ref="sentinel" class="bookmark-sentinel">
        <span v-if="myPageStore.loading">목록을 불러오는 중이에요.</span>
        <span v-else-if="myPageStore.hasMore">아래로 스크롤하면 더 불러와요.</span>
        <span v-else-if="myPageStore.bookmarks.length">모든 목록을 확인했어요.</span>
      </div>
    </section>
    <Teleport to="body">
      <div v-if="modalOpen" class="mypage-detail-overlay" @click.self="closeContentModal">
        <section class="mypage-detail-modal" role="dialog" aria-modal="true" aria-label="Content detail">
          <button class="mypage-modal-close" type="button" aria-label="Close" @click="closeContentModal">x</button>
          <p v-if="detailLoading" class="mypage-detail-state">Loading detail...</p>
          <p v-else-if="detailError" class="mypage-detail-state mypage-detail-error">{{ detailError }}</p>
          <template v-else-if="currentDetail">
            <div class="mypage-detail-cover">
              <img v-if="currentDetail.thumbnail_url" :src="currentDetail.thumbnail_url" :alt="currentDetail.title">
              <span v-else>{{ contentIcon(currentListItem?.content_type) }}</span>
            </div>
            <div class="mypage-detail-content">
              <p class="eyebrow">{{ contentTypeLabels[currentListItem?.content_type] || currentListItem?.content_type }}</p>
              <div class="mypage-detail-title-row">
                <h2>{{ currentDetail.title }}</h2>
                <button
                  v-if="authStore.isAuthenticated"
                  type="button"
                  class="mypage-heart-button"
                  :class="{ active: detailHeartActive }"
                  :disabled="actionLoading"
                  :aria-label="detailHeartActive ? 'Unlike' : 'Like'"
                  :title="detailHeartActive ? 'Unlike' : 'Like'"
                  @click="submitDetailFeedback('like')"
                >
                  <span v-if="detailHeartActive" aria-hidden="true">&hearts;</span>
                  <span v-else aria-hidden="true">&#9825;</span>
                  <strong>{{ likeCount.toLocaleString() }}</strong>
                </button>
              </div>

              <div v-if="detailTags(currentDetail).length" class="mypage-detail-tags">
                <span v-for="tag in detailTags(currentDetail)" :key="tag">{{ tag }}</span>
              </div>

              <dl v-if="currentListItem?.content_type === 'movie'" class="mypage-detail-facts">
                <div><dt>Release</dt><dd>{{ formatDate(currentDetail.release_date) }}</dd></div>
                <div><dt>Rating</dt><dd>{{ currentDetail.vote_average?.toFixed(1) || '-' }}</dd></div>
                <div><dt>Original</dt><dd>{{ currentDetail.original_title || '-' }}</dd></div>
              </dl>
              <dl v-else-if="currentListItem?.content_type === 'book'" class="mypage-detail-facts">
                <div><dt>Author</dt><dd>{{ currentDetail.author || '-' }}</dd></div>
                <div><dt>Publisher</dt><dd>{{ currentDetail.publisher || '-' }}</dd></div>
                <div><dt>Published</dt><dd>{{ formatDate(currentDetail.pub_date) }}</dd></div>
                <div><dt>Ebook</dt><dd>{{ currentDetail.has_ebook ? 'Yes' : 'No' }}</dd></div>
              </dl>
              <dl v-else class="mypage-detail-facts">
                <div><dt>Period</dt><dd>{{ formatDate(currentDetail.start_date) }} - {{ formatDate(currentDetail.end_date) }}</dd></div>
                <div><dt>Place</dt><dd>{{ currentDetail.place?.place_name || '-' }}</dd></div>
                <div><dt>Region</dt><dd>{{ [currentDetail.place?.area, currentDetail.place?.sigungu].filter(Boolean).join(' ') || '-' }}</dd></div>
                <div><dt>Price</dt><dd>{{ currentDetail.price || '-' }}</dd></div>
              </dl>

              <p class="mypage-detail-summary">{{ currentDetail.summary || currentListItem?.summary || '정보 없음' }}</p>
              <p v-if="actionError" class="mypage-detail-error">{{ actionError }}</p>
              <div class="mypage-detail-bottom-actions">
                <a v-if="currentDetail.source_url" :href="currentDetail.source_url" target="_blank" rel="noreferrer">자세히 보기</a>
                <button
                  v-if="authStore.isAuthenticated"
                  type="button"
                  class="mypage-hide-button"
                  :class="{ active: feedbackType === 'dislike' }"
                  :disabled="actionLoading"
                  @click="submitDetailFeedback('dislike')"
                >
                  {{ feedbackType === 'dislike' ? 'Allow again' : '이 콘텐츠 다시보지 않기' }}
                </button>
              </div>
            </div>
          </template>
        </section>
      </div>
    </Teleport>
  </main>
</template>
