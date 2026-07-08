import { createRouter, createWebHistory } from 'vue-router'

import HomeView from '../views/HomeView.vue'
import LoginView from '../views/LoginView.vue'
import MyPageView from '../views/MyPageView.vue'
import ProfileEditView from '../views/ProfileEditView.vue'
import SignupView from '../views/SignupView.vue'
import CommunityDetailView from '../views/CommunityDetailView.vue'
import CommunityFormView from '../views/CommunityFormView.vue'
import CommunityListView from '../views/CommunityListView.vue'
import ContentListView from '../views/ContentListView.vue'
import CultureMapView from '../views/CultureMapView.vue'
import RecommendationView from '../views/RecommendationView.vue'
import TasteTestQuestionView from '../views/TasteTestQuestionView.vue'
import TasteTestStartView from '../views/TasteTestStartView.vue'

import { AUTH_TOKEN_STORAGE_KEY } from '../api'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash, behavior: 'smooth' }
    return { top: 0, left: 0 }
  },
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { guestOnly: true },
    },
    {
      path: '/signup',
      name: 'signup',
      component: SignupView,
      meta: { guestOnly: true },
    },
    {
      path: '/community',
      name: 'community',
      component: CommunityListView,
    },
    { path: '/contents', redirect: '/movies' },
    { path: '/movies', name: 'movies', component: ContentListView, props: { contentType: 'movies' } },
    { path: '/books', name: 'books', component: ContentListView, props: { contentType: 'books' } },
    { path: '/cultures', name: 'cultures', component: ContentListView, props: { contentType: 'cultures' } },
    { path: '/cultures/map', name: 'culture-map', component: CultureMapView },
    {
      path: '/community/write',
      name: 'community-write',
      component: CommunityFormView,
      meta: { requiresAuth: true },
    },
    {
      path: '/community/:id',
      name: 'community-detail',
      component: CommunityDetailView,
    },
    {
      path: '/community/:id/edit',
      name: 'community-edit',
      component: CommunityFormView,
      meta: { requiresAuth: true },
    },
    {
      path: '/recommendations',
      redirect: { name: 'taste-test-recommendations' },
    },
    {
      path: '/mypage',
      name: 'mypage',
      component: MyPageView,
      meta: { requiresAuth: true },
    },
    {
      path: '/mypage/edit',
      name: 'profile-edit',
      component: ProfileEditView,
      meta: { requiresAuth: true },
    },
    {
      path: '/taste-test',
      name: 'taste-test-start',
      component: TasteTestStartView,
    },
    {
      path: '/taste-test/questions',
      name: 'taste-test-questions',
      component: TasteTestQuestionView,
    },
    {
      path: '/taste-test/recommendations',
      name: 'taste-test-recommendations',
      component: RecommendationView,
    },
    {
      path: '/taste-test/result',
      name: 'taste-test-result',
      redirect: { name: 'taste-test-recommendations' },
    },
  ],
})

router.beforeEach((to) => {
  const hasToken = Boolean(localStorage.getItem(AUTH_TOKEN_STORAGE_KEY))

  if (to.meta.requiresAuth && !hasToken) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.meta.guestOnly && hasToken) {
    return { name: 'home' }
  }

  return true
})

export default router
