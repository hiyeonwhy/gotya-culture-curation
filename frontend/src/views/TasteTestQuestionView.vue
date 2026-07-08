<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useTasteTestStore } from '../stores/tasteTest'
import questionBackground from '../assets/images/taste-test-background.png'
import '../assets/taste-test.css'


const router = useRouter()
const tasteTestStore = useTasteTestStore()
const currentIndex = ref(0)
const emojiModules = import.meta.glob(
  '../assets/images/taste-question-emojis/*.png',
  { eager: true, import: 'default' },
)
const progressCapsuleModules = import.meta.glob(
  '../assets/images/taste-progress-capsules/*.png',
  { eager: true, import: 'default' },
)
const QUESTION_LINE_OVERRIDES = {
  1: [
    '주말 저녁, 볼 콘텐츠를 고르는 순간입니다.',
    '가장 먼저 마음이 가는 기준은 무엇인가요?',
  ],
  5: [
    '마음에 드는 콘텐츠를 발견했을 때',
    '가장 먼저 떠오르는 생각은 무엇인가요?',
  ],
  6: [
    '기간 한정 전시나 축제 소식을 봤습니다.',
    '당신의 반응은 어느 쪽인가요?',
  ],
  7: [
    '낯선 장르의 작품을 만났을 때',
    '도전하게 만드는 요소는 무엇인가요?',
  ],
  9: [
    '같이 볼 콘텐츠를 고르는 상황입니다.',
    '더 중요하게 보는 것은 무엇인가요?',
  ],
  13: [
    '마지막으로 하나를 골라야 한다면,',
    '오늘 당신에게 더 필요한 콘텐츠는 무엇인가요?',
  ],
}
const OPTION_LINE_OVERRIDES = {
  1: {
    A: ['요즘 많이 이야기되는 작품을 골라', '대화에 함께하고 싶다.'],
    B: ['유행보다 지금 내 기분과 취향에', '맞는 작품인지 본다.'],
  },
  2: {
    A: ['인물의 감정선, 분위기,', '장면이 남긴 여운'],
    B: ['새롭게 알게 된 사실,', '해석할 거리, 관점의 변화'],
  },
  3: {
    A: ['규칙과 설정이 탄탄한', '판타지, SF, 모험 세계'],
    B: ['내 주변 사람들과 닮은', '현실적인 관계와 감정 이야기'],
  },
  4: {
    A: ['직접 나가서 공연, 축제, 팝업,', '전시의 현장감을 느낀다.'],
    B: ['조용한 공간에서 책이나 영화를', '보며 천천히 쉰다.'],
  },
  5: {
    A: ['친구나 가족에게 추천해서', '같이 보고 이야기하고 싶다.'],
    B: ['혼자 충분히 감상하고', '내 방식대로 정리하고 싶다.'],
  },
  6: {
    A: ['놓치면 아쉬우니 일정부터 확인하고', '가볼 방법을 찾는다.'],
    B: ['끌리긴 해도 붐비거나 급하면', '나중에 비슷한 콘텐츠를 찾는다.'],
  },
  7: {
    A: ['세계관, 캐릭터, 설정이 독특해서', '파고들 여지가 있다.'],
    B: ['리뷰가 좋고 주변 반응도 좋아서', '실패할 확률이 낮아 보인다.'],
  },
  8: {
    A: ['사진 찍기 좋고', '지금 사람들이 많이 찾는 화제의 전시'],
    B: ['설명을 읽고 나면', '생각할 거리가 많아지는 전시'],
  },
  9: {
    A: ['함께 웃고 바로 이야기할 수 있는', '편한 분위기'],
    B: ['각자 집중해서 감상한 뒤', '깊게 이야기할 수 있는 밀도'],
  },
  10: {
    A: ['몰랐던 분야를 이해하거나', '새로운 관점을 얻었을 때'],
    B: ['감정적으로 위로받거나', '오래 곱씹을 장면이 남았을 때'],
  },
  11: {
    A: ['전시, 공연, 팝업, 산책까지', '묶어서 밖에서 보내기'],
    B: ['서점이나 카페에서', '책과 영화를 천천히 즐기기'],
  },
  12: {
    A: ['원작, 후속작, 설정, 관련 굿즈까지', '이어서 찾아본다.'],
    B: ['좋아할 만한 사람을 떠올리고', '함께 나눌 방법을 찾는다.'],
  },
  13: {
    A: ['지금 바로 즐겁고 부담 없이', '볼 수 있는 콘텐츠'],
    B: ['오래 기억에 남고 내 취향을', '더 선명하게 해주는 콘텐츠'],
  },
}

const questions = computed(() => tasteTestStore.config?.questions || [])
const currentQuestion = computed(() => questions.value[currentIndex.value] || null)
const totalQuestions = computed(() => questions.value.length || 13)
const currentQuestionNumber = computed(() => currentIndex.value + 1)
const selectedAnswer = computed(() => {
  if (!currentQuestion.value || !tasteTestStore.hasAnswer(currentQuestion.value.question_id)) {
    return null
  }
  return tasteTestStore.answers[currentQuestion.value.question_id]
})
const progress = computed(() => {
  if (totalQuestions.value <= 1) return 0
  return (currentIndex.value / (totalQuestions.value - 1)) * 100
})
const progressSteps = computed(() => (
  Array.from({ length: totalQuestions.value }, (_, index) => index + 1)
))
const isLastQuestion = computed(() => currentIndex.value === questions.value.length - 1)
const questionTitleLines = computed(() => {
  const override = QUESTION_LINE_OVERRIDES[currentQuestionNumber.value]
  if (override) return override

  const text = currentQuestion.value?.question_text || ''
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
})

function splitDisplayLines(value) {
  return String(value || '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
}

function getOptionLines(option) {
  const optionKey = getOptionKey(option)
  return OPTION_LINE_OVERRIDES[currentQuestionNumber.value]?.[optionKey]
    || splitDisplayLines(option.text)
}

function padNumber(value) {
  return String(value).padStart(2, '0')
}

function getOptionKey(option) {
  return String(option.label || option.value || '').trim().toUpperCase()
}

function getEmojiSrc(option) {
  const optionKey = getOptionKey(option)
  const fileName = `${currentQuestionNumber.value}-${optionKey}_이모지.png`
  const entry = Object.entries(emojiModules).find(([path]) => path.endsWith(fileName))
  return entry?.[1] || ''
}

function getProgressCapsuleSrc(step) {
  const state = step < currentQuestionNumber.value ? 'open' : 'closed'
  const entry = Object.entries(progressCapsuleModules).find(([path]) => (
    path.endsWith(`${state}-${step}.png`)
  ))
  return entry?.[1] || ''
}

function chooseAnswer(value) {
  tasteTestStore.setAnswer(currentQuestion.value.question_id, value)
}

async function goBack() {
  if (currentIndex.value === 0) {
    await router.push({ name: 'taste-test-start' })
    return
  }
  currentIndex.value -= 1
}

async function goNext() {
  if (selectedAnswer.value === null) return
  if (!isLastQuestion.value) {
    currentIndex.value += 1
    return
  }

  try {
    await tasteTestStore.submitTest()
    await router.push({ name: 'taste-test-recommendations' })
  } catch {
    // Submit errors are shown from the store state.
  }
}

onMounted(async () => {
  try {
    await tasteTestStore.fetchConfig()
    const unansweredIndex = questions.value.findIndex(
      (question) => !tasteTestStore.hasAnswer(question.question_id),
    )
    currentIndex.value = unansweredIndex === -1
      ? Math.max(questions.value.length - 1, 0)
      : unansweredIndex
  } catch {
    // Config errors are shown from the store state.
  }
})
</script>

<template>
  <main
    class="taste-test-page taste-question-page"
    :style="{ '--question-bg-image': `url(${questionBackground})` }"
  >
    <section class="taste-shell taste-question-shell">
      <div class="question-capsule-floor" aria-hidden="true"></div>

      <div v-if="tasteTestStore.loading" class="question-skeleton">
        <div></div>
        <div></div>
        <div></div>
        <p>질문 캡슐을 불러오고 있어요</p>
      </div>

      <p v-else-if="tasteTestStore.error && !currentQuestion" class="taste-error">
        {{ tasteTestStore.error }}
      </p>

      <template v-else-if="currentQuestion">
        <header class="question-progress-panel">
          <div class="question-step-track" aria-label="취향 테스트 진행 단계">
            <span class="question-step-line" aria-hidden="true"></span>
            <span
              class="question-step-line-fill"
              :style="{ width: `${progress}%` }"
              aria-hidden="true"
            ></span>
            <span
              v-for="step in progressSteps"
              :key="step"
              class="question-step"
              :class="{
                active: step === currentQuestionNumber,
                complete: step < currentQuestionNumber,
              }"
            >
              <img :src="getProgressCapsuleSrc(step)" alt="" aria-hidden="true">
              <b>{{ padNumber(step) }}</b>
            </span>
          </div>

          <strong class="question-count">
            {{ padNumber(currentQuestionNumber) }} / {{ padNumber(totalQuestions) }}
          </strong>
        </header>

        <article class="question-card">
          <span class="question-number">CAPSULE {{ padNumber(currentQuestionNumber) }}</span>
          <h1>
            <span
              v-for="line in questionTitleLines"
              :key="line"
            >
              {{ line }}
            </span>
          </h1>
          <p>오늘의 나와 더 가까운 장면을 하나 골라주세요.</p>

          <div class="answer-options">
            <button
              v-for="option in currentQuestion.options || []"
              :key="option.value"
              type="button"
              class="answer-card"
              :class="{ selected: selectedAnswer === option.value }"
              @click="chooseAnswer(option.value)"
            >
              <span class="answer-check" aria-hidden="true">✓</span>
              <span class="answer-emoji-wrap">
                <img
                  v-if="getEmojiSrc(option)"
                  :src="getEmojiSrc(option)"
                  :alt="`${getOptionKey(option)} 선택지 이미지`"
                >
                <span v-else class="choice-token">{{ getOptionKey(option) }}</span>
              </span>
              <strong>
                <span
                  v-for="line in getOptionLines(option)"
                  :key="line"
                >
                  {{ line }}
                </span>
              </strong>
            </button>
          </div>
        </article>

        <footer class="question-actions">
          <button type="button" class="taste-secondary-button" @click="goBack">
            이전 질문
          </button>
          <button
            type="button"
            class="taste-primary-button"
            :disabled="selectedAnswer === null || tasteTestStore.submitting"
            @click="goNext"
          >
            <template v-if="tasteTestStore.submitting">결과 캡슐 여는 중</template>
            <template v-else-if="isLastQuestion">결과 확인하기</template>
            <template v-else>다음 질문</template>
          </button>
        </footer>

        <p v-if="tasteTestStore.error" class="taste-error">
          {{ tasteTestStore.error }}
        </p>
      </template>
    </section>
  </main>
</template>
