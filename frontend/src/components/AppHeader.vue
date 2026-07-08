<script setup>
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import { useRecommendationStore } from '../stores/recommendations'
import { useTasteTestStore } from '../stores/tasteTest'
import logoImage from '../assets/images/logo.png'


const authStore = useAuthStore()
const recommendationStore = useRecommendationStore()
const tasteTestStore = useTasteTestStore()
const router = useRouter()

async function handleLogout() {
  await authStore.logout()
  recommendationStore.resetRecommendations()
  tasteTestStore.clearResultData()
  tasteTestStore.startNewTest()
  await router.replace('/')
  window.location.reload()
}
</script>

<template>
  <header class="app-header">
    <RouterLink class="brand" to="/" aria-label="GotYA 홈">
      <img :src="logoImage" alt="GotYA">
    </RouterLink>

    <nav class="primary-nav" aria-label="주요 메뉴">
      <RouterLink to="/">홈</RouterLink>
      <RouterLink to="/taste-test">취향 테스트</RouterLink>
      <RouterLink to="/movies">영화</RouterLink>
      <RouterLink to="/books">도서</RouterLink>
      <RouterLink to="/cultures">문화생활</RouterLink>
      <RouterLink to="/community">커뮤니티</RouterLink>
    </nav>

    <div class="header-actions" aria-label="사용자 메뉴">
      <template v-if="authStore.isAuthenticated">
        <span class="user-name">{{ authStore.user.nickname }}님</span>
        <RouterLink class="text-action" to="/mypage">마이페이지</RouterLink>
        <button class="text-action" type="button" @click="handleLogout">로그아웃</button>
      </template>
      <template v-else>
        <RouterLink class="text-action" to="/login">로그인</RouterLink>
        <RouterLink class="text-action" to="/signup">회원가입</RouterLink>
      </template>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  z-index: 50;
  top: 0;
  display: grid;
  grid-template-columns: minmax(170px, 1fr) auto minmax(170px, 1fr);
  align-items: center;
  gap: 2rem;
  min-height: 92px;
  padding: 0 4.5rem;
  border-top: 1px solid #dbe7ef;
  border-bottom: 1px solid rgba(26, 31, 46, 0.08);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 5px 14px rgba(26, 31, 46, 0.08);
  backdrop-filter: blur(14px);
}

.brand {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-self: start;
  text-decoration: none;
}

.brand img {
  display: block;
  width: auto;
  height: 74px;
  object-fit: contain;
}

.primary-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  justify-self: center;
  gap: clamp(1.4rem, 2.5vw, 3.2rem);
  width: auto;
}

.primary-nav a {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 2.1rem 0;
  color: #20242d;
  font-size: 1rem;
  font-weight: 850;
  text-decoration: none;
  white-space: nowrap;
}

.primary-nav a::after {
  position: absolute;
  right: 0;
  bottom: 1.45rem;
  left: 0;
  height: 3px;
  border-radius: 999px;
  background: transparent;
  content: '';
}

.primary-nav a:hover {
  color: #2563eb;
}

.primary-nav a.router-link-active,
.primary-nav a.router-link-exact-active {
  color: var(--gotya-navy);
  font-weight: 900;
}

.primary-nav a.router-link-active::after,
.primary-nav a.router-link-exact-active::after {
  background: #2563eb;
}

.header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  justify-self: end;
  gap: 0.85rem;
  min-width: 0;
}

.user-name {
  flex: none;
  color: #3f4858;
  font-size: 0.9rem;
  font-weight: 760;
  white-space: nowrap;
}

.text-action {
  border: 0;
  border-radius: 999px;
  padding: 0.58rem 0.82rem;
  background: transparent;
  color: #3f4858;
  font-size: 0.9rem;
  font-weight: 800;
  cursor: pointer;
  text-decoration: none;
  white-space: nowrap;
}

.text-action:hover {
  color: #2563eb;
  background: rgba(37, 99, 235, 0.08);
}

.text-action.router-link-active,
.text-action.router-link-exact-active {
  color: #2563eb;
  background: rgba(37, 99, 235, 0.08);
}

@media (max-width: 1180px) {
  .app-header {
    grid-template-columns: auto 1fr;
    gap: 0.9rem 1.25rem;
    min-height: 0;
    padding: 0.85rem 1.5rem 1rem;
  }

  .primary-nav {
    grid-column: 1 / -1;
    grid-row: 2;
    justify-content: flex-start;
    justify-self: stretch;
    overflow-x: auto;
    gap: 1.35rem;
    padding-bottom: 0.1rem;
  }

  .header-actions {
    grid-column: 2;
    justify-self: end;
  }

  .primary-nav a {
    padding: 0.25rem 0 0.65rem;
    font-size: 0.9rem;
  }

  .primary-nav a::after {
    bottom: 0.25rem;
  }
}

@media (max-width: 720px) {
  .app-header {
    padding: 0.75rem 1rem 0.9rem;
  }

  .brand img {
    height: 56px;
  }

  .header-actions {
    gap: 0.35rem;
  }

  .text-action {
    padding: 0.45rem 0.58rem;
    font-size: 0.82rem;
  }
}
</style>
