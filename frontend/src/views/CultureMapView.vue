<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

import CultureMap from '../components/CultureMap.vue'
import { useContentsStore } from '../stores/contents'
import '../assets/culture-map.css'


const contentStore = useContentsStore()
const router = useRouter()

async function loadMapEvents() {
  try {
    await contentStore.fetchCultureRegionSummaries()
  } catch {
    // 스토어의 mapError를 화면에 표시한다.
  }
}


async function loadRegionEvents(area, category = '') {
  try {
    await contentStore.fetchCultureMapItems({
      area,
      ...(category ? { main_category: category } : {}),
    })
  } catch {
    // 스토어의 mapError를 화면에 표시한다.
  }
}


async function loadCategoryEvents(category, area) {
  const params = category ? { main_category: category } : {}
  const tasks = [contentStore.fetchCultureRegionSummaries(params)]
  if (area) tasks.push(loadRegionEvents(area, category))
  await Promise.allSettled(tasks)
}


function browseCultureList(category) {
  router.push({
    name: 'cultures',
    query: category ? { category } : {},
    hash: '#culture-catalog',
  })
}

onMounted(loadMapEvents)
</script>

<template>
  <main class="culture-map-page">
    <header class="culture-map-header">
      <div>
        <p>KOREA CULTURE MAP</p>
        <h1>지역별 문화지도</h1>
        <span>전국의 문화행사를 지역별로 탐색하고 가까운 행사를 찾아보세요.</span>
      </div>
      <RouterLink to="/cultures">문화생활 목록으로</RouterLink>
    </header>

    <section class="culture-map-summary" aria-live="polite">
      <p v-if="contentStore.mapLoading && !contentStore.regionSummaries.length">좌표가 있는 문화행사를 불러오는 중입니다.</p>
      <p v-else-if="contentStore.mapError" class="culture-map-api-error">
        {{ contentStore.mapError }}
        <button type="button" @click="loadMapEvents">다시 시도</button>
      </p>
      <p v-else>
        원하는 시·도를 선택하면 문화행사 위치와 목록을 확인할 수 있습니다.
      </p>
    </section>

    <CultureMap
      :items="contentStore.mapItems"
      :region-summaries="contentStore.regionSummaries"
      @select-region="loadRegionEvents"
      @select-category="loadCategoryEvents"
      @browse-more="browseCultureList"
    />
  </main>
</template>
