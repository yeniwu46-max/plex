<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NIcon, NInput, useMessage } from 'naive-ui'
import { ArrowBackOutline, PersonAddOutline } from '@vicons/ionicons5'
import { useAuthStore } from '../stores/auth'
import { passwordValid, safeAuthRedirect } from '../utils/authValidation'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const auth = useAuthStore()

const username = ref('')
const email = ref('')
const nickname = ref('')
const password = ref('')
const confirmation = ref('')
const loading = ref(false)

async function onSubmit(e: Event) {
  e.preventDefault()
  if (loading.value) return
  if (!/^[A-Za-z0-9][A-Za-z0-9_-]{2,29}$/.test(username.value.trim())) {
    message.warning('用户名需为 3–30 位字母、数字、下划线或短横线，以字母或数字开头'); return
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim()) || email.value.trim().endsWith('.local')) {
    message.warning('请输入可接收邮件的邮箱地址'); return
  }
  if (!nickname.value.trim()) { message.warning('请填写昵称'); return }
  if (!passwordValid(password.value)) { message.warning('密码需为 8–128 位，至少包含字母和数字'); return }
  if (password.value !== confirmation.value) { message.warning('两次输入的密码不一致'); return }

  loading.value = true
  try {
    const session = await auth.register({
      username: username.value.trim(), email: email.value.trim(), real_name: nickname.value.trim(),
      password: password.value,
      role: 'student',
    })
    message.success('注册成功')
    const redirect = safeAuthRedirect(route.query.redirect, auth.homePathForRole(session.role))
    await router.replace(redirect)
  } catch (err) {
    message.error(err instanceof Error ? err.message : '注册失败')
  } finally {
    loading.value = false
  }
}

function backToLogin() {
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : undefined
  void router.push({
    name: 'login',
    query: redirect ? { redirect } : undefined,
  })
}
</script>

<template>
  <div class="register-page">
    <section class="register-card">
      <button type="button" class="back" aria-label="返回登录" @click="backToLogin">
        <n-icon :component="ArrowBackOutline" />
      </button>

      <header class="head">
        <div class="emblem" aria-hidden="true">
          <n-icon :component="PersonAddOutline" />
        </div>
        <h1>创建 Explorer 账号</h1>
        <p>加入 PLEX 探索网络</p>
      </header>

      <form class="form" @submit="onSubmit">
        <label>用户名
          <n-input v-model:value="username" size="large" :maxlength="30" placeholder="3–30 位字母、数字、下划线或短横线" :input-props="{ autocomplete: 'username', 'aria-label': '用户名' }" />
        </label>
        <label>昵称
          <n-input v-model:value="nickname" size="large" :maxlength="50" placeholder="希望小E怎样称呼你" :input-props="{ autocomplete: 'nickname', 'aria-label': '昵称' }" />
        </label>
        <label>邮箱
          <n-input v-model:value="email" size="large" :maxlength="100" placeholder="用于找回密码，请填写真实邮箱" :input-props="{ type: 'email', autocomplete: 'email', 'aria-label': '邮箱' }" />
        </label>
        <label>登录密码
          <n-input v-model:value="password" size="large" type="password" show-password-on="click" :maxlength="128" placeholder="8–128 位，至少包含字母和数字" :input-props="{ autocomplete: 'new-password', 'aria-label': '登录密码' }" />
        </label>
        <label>确认密码
          <n-input v-model:value="confirmation" size="large" type="password" :maxlength="128" placeholder="再次输入密码" :input-props="{ autocomplete: 'new-password', 'aria-label': '确认密码' }" />
        </label>
        <p class="registration-note">注册的是学生账号。加入班级后，可使用老师发布的练习与学习资源。</p>
        <button type="submit" class="submit" :disabled="loading">
          {{ loading ? '注册中...' : '注册并进入' }}
        </button>
      </form>

      <n-button quaternary class="login-link" @click="backToLogin">已有账号，返回登录</n-button>
    </section>
  </div>
</template>

<style scoped>
.form label { display: grid; gap: 8px; font-size: 14px; }
.registration-note { margin: 0; font-size: 13px; color: #b6c5d4; line-height: 1.6; }
.register-page {
  min-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(1.5rem, 5vw, 3rem);
  color: #f8fafc;
  background:
    radial-gradient(circle at 50% 0%, rgba(0, 245, 212, 0.18), transparent 32rem),
    linear-gradient(180deg, #020617 0%, #030712 100%);
  font-family:
    'Outfit',
    'Noto Sans SC',
    system-ui,
    -apple-system,
    sans-serif;
}

.register-card {
  position: relative;
  width: min(100%, 410px);
  padding: clamp(1.75rem, 5vw, 2.5rem);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 1.25rem;
  background: rgba(15, 23, 42, 0.62);
  box-shadow:
    0 0 0 1px rgba(0, 245, 212, 0.05) inset,
    0 24px 80px rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(20px);
}

.back {
  position: absolute;
  top: 1rem;
  left: 1rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 999px;
  color: #cbd5e1;
  background: rgba(15, 23, 42, 0.7);
  cursor: pointer;
}

.back:hover {
  color: #00f5d4;
  border-color: rgba(0, 245, 212, 0.35);
}

.head {
  text-align: center;
  margin-bottom: 1.75rem;
}

.emblem {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 4.5rem;
  height: 4.5rem;
  margin-bottom: 1rem;
  border-radius: 50%;
  color: #00f5d4;
  background: rgba(0, 245, 212, 0.08);
  border: 1px solid rgba(0, 245, 212, 0.24);
  font-size: 2rem;
  box-shadow: 0 0 30px rgba(0, 245, 212, 0.18);
}

.head h1 {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 700;
  letter-spacing: 0;
}

.head p {
  margin: 0.5rem 0 0;
  color: rgba(226, 232, 240, 0.58);
}

.form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form :deep(.n-input) {
  --n-border: 1px solid rgba(255, 255, 255, 0.1) !important;
  --n-border-hover: 1px solid rgba(0, 245, 212, 0.35) !important;
  --n-border-focus: 1px solid rgba(0, 245, 212, 0.55) !important;
  --n-color: rgba(15, 23, 42, 0.65) !important;
  --n-color-focus: rgba(15, 23, 42, 0.85) !important;
  --n-text-color: #e2e8f0 !important;
  --n-placeholder-color: rgba(148, 163, 184, 0.75) !important;
}

.field-icon {
  color: rgba(148, 163, 184, 0.85);
}

.submit {
  width: 100%;
  margin-top: 0.25rem;
  padding: 0.85rem 1.25rem;
  border: none;
  border-radius: 999px;
  color: #020617;
  cursor: pointer;
  font: inherit;
  font-weight: 700;
  background: linear-gradient(90deg, #00f5d4 0%, #00c9ae 55%, #0a6b5c 100%);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.35);
}

.submit:hover {
  transform: translateY(-1px);
}

.submit:disabled {
  opacity: 0.65;
  cursor: not-allowed;
  transform: none;
}

.login-link {
  width: 100%;
  margin-top: 1rem;
}
</style>
