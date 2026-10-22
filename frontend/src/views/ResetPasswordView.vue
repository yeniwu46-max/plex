<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { NInput, NButton, NAlert } from 'naive-ui'
import { resetPassword } from '../api/auth'
import { formatHttpError } from '../api/http'
import { passwordValid } from '../utils/authValidation'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const token = new URLSearchParams(window.location.hash.slice(1)).get('token') || ''
// Do not leave the recovery token in browser history or copied links.
window.history.replaceState(window.history.state, '', window.location.pathname)
const password = ref('')
const confirm = ref('')
const busy = ref(false)
const done = ref(false)
const error = ref(token ? '' : '链接中没有重置凭证，请回到登录页重新申请')
async function submit() {
  if (busy.value || !token) return
  if (!passwordValid(password.value)) { error.value = '密码需为 8–128 位，至少包含字母和数字'; return }
  if (password.value !== confirm.value) { error.value = '两次输入的密码不一致'; return }
  busy.value = true
  error.value = ''
  try {
    await resetPassword(token, password.value)
    auth.clearSession()
    password.value = confirm.value = ''
    done.value = true
  } catch (e) { error.value = formatHttpError(e, '重置失败，请重新申请链接') }
  finally { busy.value = false }
}
</script>

<template>
  <main class="reset-page">
    <section class="reset-card">
      <h1>{{ done ? '密码已更新' : '设置新密码' }}</h1>
      <p>{{ done ? '所有旧登录状态已失效，请使用新密码登录。' : '重置链接有效期为 15 分钟，只能使用一次。' }}</p>
      <n-alert v-if="error" type="error" role="alert">{{ error }}</n-alert>
      <form v-if="token && !done" @submit.prevent="submit">
        <label>新密码<n-input v-model:value="password" type="password" show-password-on="click" :maxlength="128" placeholder="8–128 位，包含字母和数字" :input-props="{ autocomplete: 'new-password', 'aria-label': '新密码' }" /></label>
        <label>确认新密码<n-input v-model:value="confirm" type="password" :maxlength="128" :input-props="{ autocomplete: 'new-password', 'aria-label': '确认新密码' }" /></label>
        <n-button attr-type="submit" type="primary" block :loading="busy">更新密码</n-button>
      </form>
      <n-button text @click="router.replace('/login')">返回登录</n-button>
    </section>
  </main>
</template>

<style scoped>
.reset-page { min-height: 100vh; display: grid; place-items: center; padding: 24px; background: #07131f; color: #eef7ff; }
.reset-card { width: min(100%, 420px); padding: 28px; border: 1px solid #26465d; border-radius: 20px; background: #11263a; }
h1 { margin-top: 0; } p { color: #bdcedc; line-height: 1.6; } form { display: grid; gap: 20px; margin: 24px 0; } label { display: grid; gap: 8px; }
</style>
