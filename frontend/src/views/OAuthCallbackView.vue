<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NIcon } from 'naive-ui'
import { AlertCircleOutline, CheckmarkCircleOutline } from '@vicons/ionicons5'
import { useAuthStore, type LoginPayload } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const status = ref<'loading' | 'success' | 'error'>('loading')
const errorMessage = ref('')

function parseHash() {
  const raw = window.location.hash.startsWith('#') ? window.location.hash.slice(1) : window.location.hash
  return new URLSearchParams(raw)
}

onMounted(async () => {
  const params = parseHash()
  const error = params.get('error')
  if (error) {
    status.value = 'error'
    errorMessage.value = error
    return
  }

  const rawSession = params.get('session')
  if (!rawSession) {
    status.value = 'error'
    errorMessage.value = '第三方登录回调缺少会话信息'
    return
  }

  try {
    const session = JSON.parse(rawSession) as LoginPayload
    auth.acceptSession(session)
    status.value = 'success'
    const redirect = params.get('redirect') || auth.homePathForRole(session.role)
    await router.replace(redirect)
  } catch (err) {
    status.value = 'error'
    errorMessage.value = err instanceof Error ? err.message : '第三方登录失败'
  }
})

function backToLogin() {
  void router.replace({ name: 'login' })
}
</script>

<template>
  <main class="callback-page">
    <section class="callback-card">
      <n-icon
        class="status-icon"
        :class="status"
        :component="status === 'error' ? AlertCircleOutline : CheckmarkCircleOutline"
      />
      <h1>{{ status === 'error' ? '登录失败' : '正在进入 PLEX' }}</h1>
      <p>{{ status === 'error' ? errorMessage : '正在同步第三方登录会话...' }}</p>
      <n-button v-if="status === 'error'" type="primary" @click="backToLogin">返回登录</n-button>
    </section>
  </main>
</template>

<style scoped>
.callback-page {
  min-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  color: #f8fafc;
  background: linear-gradient(180deg, #020617 0%, #030712 100%);
}

.callback-card {
  width: min(100%, 360px);
  padding: 2rem;
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 1.25rem;
  background: rgba(15, 23, 42, 0.62);
}

.status-icon {
  font-size: 3rem;
  color: #00f5d4;
}

.status-icon.error {
  color: #f97316;
}

h1 {
  margin: 1rem 0 0.5rem;
  font-size: 1.25rem;
}

p {
  margin: 0 0 1.25rem;
  color: rgba(226, 232, 240, 0.68);
}
</style>
