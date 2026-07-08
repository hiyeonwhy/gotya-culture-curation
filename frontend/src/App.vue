<script setup>
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'

import AppHeader from './components/AppHeader.vue'
import { useAuthStore } from './stores/auth'


const authStore = useAuthStore()

onMounted(() => {
  authStore.initializeAuth()
})
</script>

<template>
  <AppHeader />
  <RouterView />
</template>
