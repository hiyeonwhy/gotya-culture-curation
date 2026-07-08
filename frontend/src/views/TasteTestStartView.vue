<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useTasteTestStore } from '../stores/tasteTest'
import tasteBackground from '../assets/images/taste-test-background.png'
import tasteMachine from '../assets/images/taste-gotya-machine.png'
import lastResultBackground from '../assets/images/taste-result/last-result-background.png'
import lastResultMachine from '../assets/images/taste-result/result-machine.png'
import '../assets/taste-test.css'


const router = useRouter()
const route = useRoute()
const tasteTestStore = useTasteTestStore()
const showFreshStart = ref(route.query.restart === '1')
const previousResult = computed(() => (
  showFreshStart.value ? null : tasteTestStore.latestResult
))
const previousAxisRows = computed(() => previousResult.value?.axis_percentages || [])

function showStartPage() {
  tasteTestStore.startNewTest()
  showFreshStart.value = true
}

async function beginTest() {
  try {
    tasteTestStore.startNewTest()
    await router.push({ name: 'taste-test-questions' })
  } catch {
    // Route failures are surfaced by the current page state.
  }
}

onMounted(() => {
  Promise.all([
    tasteTestStore.fetchConfig(),
    tasteTestStore.fetchLatestResult(),
  ]).catch(() => {})
})
</script>

<template>
  <main
    class="taste-test-page taste-start-page"
    :class="{ 'taste-main-page': !previousResult, 'taste-last-result-page': previousResult }"
    :style="previousResult ? { '--last-result-bg-image': `url(${lastResultBackground})` } : {}"
  >
    <section class="taste-shell" :class="{ 'taste-main-shell': !previousResult }">
      <div v-if="previousResult" class="previous-taste-card">
        <img
          class="previous-result-machine"
          :src="lastResultMachine"
          alt=""
          aria-hidden="true"
        >
        <div class="result-capsule-visual" aria-hidden="true">
          <span class="gotya-capsule movie"></span>
          <span class="gotya-capsule book"></span>
        </div>

        <div class="previous-taste-copy">
          <span class="taste-kicker">MY LAST GOTYA</span>
          <p>이전에 뽑은 나의 문화 취향</p>
          <h1>{{ previousResult.result.name }}</h1>
          <strong>{{ previousResult.result.subtitle }}</strong>
          <p>{{ previousResult.result.summary }}</p>
          <div class="result-keywords">
            <span
              v-for="keyword in previousResult.result.keywords.slice(0, 8)"
              :key="keyword"
            >
              #{{ keyword }}
            </span>
          </div>
        </div>

        <div class="previous-taste-scores">
          <h2>나의 취향 구성</h2>
          <div v-for="row in previousAxisRows" :key="row.key" class="result-score-row">
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

        <button
          type="button"
          class="taste-primary-button previous-retest-button"
          @click="showStartPage"
        >
          다시 테스트하기
        </button>
      </div>

      <div
        v-else
        class="taste-start-hero"
        :style="{ '--taste-bg-image': `url(${tasteBackground})` }"
      >
        <h1>GotYA World</h1>

        <img
          class="taste-machine-image"
          :src="tasteMachine"
          alt=""
          aria-hidden="true"
        >

        <div v-if="tasteTestStore.loading" class="taste-loading-card">
          취향 캡슐을 준비하고 있어요
        </div>
        <p v-else-if="tasteTestStore.error" class="taste-error">
          {{ tasteTestStore.error }}
        </p>

        <button
          type="button"
          class="taste-primary-button taste-gacha-start-button"
          :disabled="tasteTestStore.loading"
          @click="beginTest"
        >
          Start! <span aria-hidden="true"></span>
        </button>
      </div>
    </section>
  </main>
</template>
