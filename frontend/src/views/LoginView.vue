<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NInput, NCheckbox, NIcon, useMessage } from 'naive-ui'
import { PersonOutline, LockClosedOutline, EyeOutline, EyeOffOutline } from '@vicons/ionicons5'
import { useAuthStore } from '../stores/auth'
import { useNotificationStore } from '../stores/notifications'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const auth = useAuthStore()
const notifications = useNotificationStore()

const username = ref('')
const password = ref('')
const remember = ref(false)
const showPassword = ref(false)
const loading = ref(false)

function togglePassword() {
  showPassword.value = !showPassword.value
}

async function onSubmit(e: Event) {
  e.preventDefault()
  if (!username.value.trim() || !password.value) {
    message.warning('请填写用户名和密码')
    return
  }
  loading.value = true
  try {
    const session = await auth.login(username.value.trim(), password.value)
    message.success('登录成功')
    if (session.role === 'student' && session.id) {
      notifications.hydrate(session.id)
      notifications.push(session.id, 'welcome')
    }
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    const fallback = auth.homePathForRole(auth.profile?.role)
    await router.replace(redirect || fallback)
  } catch (err) {
    message.error(err instanceof Error ? err.message : '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <section class="hero" aria-label="品牌与视觉">
      <div class="hero__bg" />
      <div class="hero__glow hero__glow--planet" />
      <div class="hero__glow hero__glow--ring" />

      <header class="hero__top">
        <div class="brand" aria-label="PLEX Universe">
          <svg class="brand__mark" viewBox="0 0 48 48" width="36" height="36" aria-hidden="true">
            <path
              fill="currentColor"
              d="M24 4l5.2 14.8L44 24l-14.8 5.2L24 44l-5.2-14.8L4 24l14.8-5.2L24 4z"
            />
          </svg>
          <span class="brand__text">PLEX</span>
        </div>
      </header>

      <div class="hero__copy">
        <h1 class="hero__title">
          探索编程<span class="hero__accent">知识宇宙</span>
        </h1>
        <p class="hero__subtitle">点亮属于你的能力星图</p>
        <p class="hero__desc">每一次探索，都是成长的轨迹。</p>
      </div>

      <div class="hero__robot-wrap" aria-hidden="true">
        <svg class="hero__robot" viewBox="0 0 120 140" width="120" height="140">
          <ellipse cx="60" cy="128" rx="40" ry="8" fill="rgba(0,245,212,0.15)" />
          <rect x="28" y="72" width="64" height="48" rx="16" fill="#f8fafc" />
          <circle cx="44" cy="92" r="5" fill="#0f172a" />
          <circle cx="76" cy="92" r="5" fill="#0f172a" />
          <path d="M52 102h16" stroke="#0f172a" stroke-width="3" stroke-linecap="round" />
          <rect x="48" y="48" width="24" height="28" rx="8" fill="#e2e8f0" />
          <circle cx="60" cy="58" r="6" fill="#00f5d4" opacity="0.9" />
          <path
            d="M24 78 Q12 56 20 40 Q28 24 44 20"
            fill="none"
            stroke="#00f5d4"
            stroke-width="4"
            stroke-linecap="round"
          />
          <path
            d="M96 78 Q108 56 100 40 Q92 24 76 20"
            fill="none"
            stroke="#00f5d4"
            stroke-width="4"
            stroke-linecap="round"
          />
        </svg>
      </div>

      <footer class="hero__footer">
        <div class="hero__welcome">
          <div class="hero__progress" />
          <span>欢迎来到 PLEX 宇宙</span>
        </div>
        <p class="hero__copyright">© {{ new Date().getFullYear() }} PLEX Universe. All rights reserved.</p>
      </footer>
    </section>

    <section class="panel" aria-label="登录">
      <div class="card glass">
        <header class="card__head">
          <h2 class="card__title">欢迎回来，<span class="card__accent">Explorer</span></h2>
          <p class="card__sub">继续你的探索之旅</p>
        </header>

        <div class="card__emblem" aria-hidden="true">
          <div class="card__orbit card__orbit--outer" />
          <div class="card__orbit card__orbit--inner" />
          <svg class="card__star" viewBox="0 0 64 64" width="72" height="72">
            <defs>
              <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="4" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            <path
              fill="#00f5d4"
              filter="url(#glow)"
              d="M32 6l6.8 19.2L58 32l-19.2 6.8L32 58l-6.8-19.2L6 32l19.2-6.8L32 6z"
            />
          </svg>
        </div>

        <form class="form" @submit="onSubmit">
          <n-input
            v-model:value="username"
            size="large"
            round
            placeholder="邮箱 / 用户名"
            :input-props="{ autocomplete: 'username' }"
            class="form__field"
          >
            <template #prefix>
              <n-icon :component="PersonOutline" class="form__icon" />
            </template>
          </n-input>

          <n-input
            v-model:value="password"
            size="large"
            round
            placeholder="密码"
            :type="showPassword ? 'text' : 'password'"
            :input-props="{ autocomplete: 'current-password' }"
            class="form__field"
          >
            <template #prefix>
              <n-icon :component="LockClosedOutline" class="form__icon" />
            </template>
            <template #suffix>
              <button
                type="button"
                class="form__eye"
                tabindex="-1"
                aria-label="显示或隐藏密码"
                @click="togglePassword"
              >
                <n-icon :component="showPassword ? EyeOffOutline : EyeOutline" />
              </button>
            </template>
          </n-input>

          <button type="submit" class="form__submit" :disabled="loading">
            <span>{{ loading ? '登录中…' : '进入探索' }}</span>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M5 12h14M13 6l6 6-6 6"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </button>
        </form>

        <div class="social">
          <div class="social__divider">
            <span>或使用以下方式登录</span>
          </div>
          <div class="social__row">
            <button type="button" class="social__btn" aria-label="使用 Google 登录">
              <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
                <path
                  fill="#EA4335"
                  d="M12 10.2v3.75h5.29c-.23 1.18-.93 2.18-1.98 2.85l3.2 2.48c1.86-1.72 2.93-4.25 2.93-7.26 0-.7-.07-1.38-.19-2.04H12z"
                />
                <path
                  fill="#34A853"
                  d="M12 21c2.7 0 4.96-.89 6.61-2.41l-3.2-2.48c-.89.6-2.03.95-3.41.95-2.62 0-4.84-1.77-5.64-4.15H3.07v2.52C4.7 18.98 8.09 21 12 21z"
                />
                <path
                  fill="#4A90E2"
                  d="M6.36 14.91c-.2-.6-.31-1.24-.31-1.91s.11-1.31.31-1.91V8.57H3.07A11.99 11.99 0 0 0 1 12c0 1.93.47 3.75 1.3 5.36l3.36-2.45z"
                />
                <path
                  fill="#FBBC05"
                  d="M12 5.38c1.48 0 2.79.51 3.83 1.5l2.88-2.88C16.95 2.09 14.69 1 12 1 8.09 1 4.7 3.02 3.07 6.64l3.29 2.55C7.16 7.15 9.38 5.38 12 5.38z"
                />
              </svg>
            </button>
            <button type="button" class="social__btn" aria-label="使用 GitHub 登录">
              <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true">
                <path
                  d="M12 1C5.92 1 1 5.92 1 12c0 4.86 3.15 8.98 7.52 10.43.55.1.75-.24.75-.53 0-.26-.01-1.13-.01-2.05-3.06.67-3.71-1.47-3.71-1.47-.5-1.27-1.22-1.61-1.22-1.61-1-.68.08-.67.08-.67 1.1.08 1.68 1.13 1.68 1.13.98 1.68 2.56 1.2 3.19.92.1-.71.39-1.2.71-1.47-2.44-.28-5-1.22-5-5.45 0-1.2.43-2.19 1.13-2.96-.11-.28-.49-1.41.11-2.94 0 0 .92-.3 3.03 1.13a10.5 10.5 0 0 1 5.5 0c2.1-1.43 3.02-1.13 3.02-1.13.6 1.53.22 2.66.11 2.94.7.77 1.13 1.76 1.13 2.96 0 5.24-3.56 6.16-6.97 6.49.55.47 1.03 1.4 1.03 2.83 0 2.04-.02 3.69-.02 4.19 0 .41.28.89 1.05.74C19.85 20.98 23 16.86 23 12 23 5.92 18.08 1 12 1z"
                />
              </svg>
            </button>
            <button type="button" class="social__btn social__btn--brand" aria-label="使用 PLEX 账号登录">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true">
                <path
                  d="M12 2l2.2 6.3L20 12l-5.8 2.1L12 20l-2.2-6.9L4 12l5.8-3.7L12 2z"
                />
              </svg>
            </button>
          </div>
        </div>

        <div class="card__meta">
          <n-checkbox v-model:checked="remember" class="remember">记住我</n-checkbox>
          <a href="#" class="forgot" @click.prevent>忘记密码？</a>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  min-height: 100%;
  font-family:
    'Outfit',
    'Noto Sans SC',
    system-ui,
    -apple-system,
    sans-serif;
  color: #f1f5f9;
  background: #030712;
}

/* —— 左侧 Hero —— */
.hero {
  position: relative;
  flex: 1.45;
  min-height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: clamp(1.25rem, 3vw, 2.5rem);
}

.hero__bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 120% 80% at 85% 45%, rgba(0, 180, 170, 0.22), transparent 55%),
    radial-gradient(circle at 20% 20%, rgba(0, 245, 212, 0.08), transparent 40%),
    radial-gradient(circle at 70% 80%, rgba(59, 130, 246, 0.06), transparent 45%),
    linear-gradient(165deg, #020617 0%, #0a1628 45%, #030712 100%);
}

.hero__bg::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(1.5px 1.5px at 10% 20%, rgba(255, 255, 255, 0.35), transparent),
    radial-gradient(1px 1px at 30% 65%, rgba(255, 255, 255, 0.25), transparent),
    radial-gradient(1px 1px at 70% 30%, rgba(255, 255, 255, 0.2), transparent),
    radial-gradient(1.5px 1.5px at 85% 75%, rgba(255, 255, 255, 0.3), transparent),
    radial-gradient(1px 1px at 50% 50%, rgba(255, 255, 255, 0.15), transparent);
  background-size:
    280px 280px,
    320px 320px,
    260px 260px,
    300px 300px,
    400px 400px;
  opacity: 0.85;
}

.hero__glow {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
}

.hero__glow--planet {
  width: min(72vw, 520px);
  height: min(72vw, 520px);
  right: -18%;
  top: 18%;
  background: radial-gradient(circle at 35% 35%, #1e3a5f 0%, #0c1929 45%, transparent 70%);
  box-shadow:
    inset -20px -20px 80px rgba(0, 245, 212, 0.12),
    0 0 120px rgba(0, 245, 212, 0.08);
}

.hero__glow--ring {
  width: min(90vw, 640px);
  height: min(90vw, 640px);
  right: -28%;
  top: 8%;
  border: 1px solid rgba(0, 245, 212, 0.12);
  opacity: 0.6;
}

.hero__top {
  position: relative;
  z-index: 1;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
  color: #00f5d4;
}

.brand__text {
  font-size: 1.35rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  color: #f8fafc;
}

.hero__copy {
  position: relative;
  z-index: 1;
  margin-top: clamp(2rem, 8vh, 5rem);
  max-width: 28rem;
}

.hero__title {
  margin: 0;
  font-size: clamp(1.75rem, 3.2vw, 2.65rem);
  font-weight: 700;
  line-height: 1.25;
  letter-spacing: 0.02em;
}

.hero__accent {
  color: #00f5d4;
  text-shadow: 0 0 40px rgba(0, 245, 212, 0.35);
}

.hero__subtitle {
  margin: 1rem 0 0;
  font-size: clamp(1.05rem, 1.6vw, 1.25rem);
  color: rgba(241, 245, 249, 0.88);
  font-weight: 500;
}

.hero__desc {
  margin: 0.75rem 0 0;
  font-size: 0.95rem;
  color: rgba(226, 232, 240, 0.55);
  line-height: 1.6;
}

.hero__robot-wrap {
  position: relative;
  z-index: 1;
  margin-top: auto;
  margin-bottom: 1rem;
  filter: drop-shadow(0 12px 24px rgba(0, 245, 212, 0.15));
}

.hero__footer {
  position: relative;
  z-index: 1;
  margin-top: auto;
  padding-top: 1rem;
}

.hero__welcome {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: rgba(226, 232, 240, 0.45);
}

.hero__progress {
  height: 2px;
  width: 140px;
  border-radius: 2px;
  background: linear-gradient(90deg, #00f5d4, rgba(0, 245, 212, 0.15));
  box-shadow: 0 0 12px rgba(0, 245, 212, 0.4);
}

.hero__copyright {
  margin: 1.25rem 0 0;
  font-size: 0.75rem;
  color: rgba(148, 163, 184, 0.45);
}

/* —— 右侧表单 —— */
.panel {
  flex: 1;
  min-width: min(100%, 420px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(1.5rem, 4vw, 3rem);
  background: linear-gradient(180deg, #020617 0%, #030712 100%);
}

.glass {
  background: rgba(15, 23, 42, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 1.25rem;
  box-shadow:
    0 0 0 1px rgba(0, 245, 212, 0.04) inset,
    0 24px 80px rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

.card {
  width: 100%;
  max-width: 400px;
  padding: clamp(1.75rem, 4vw, 2.5rem) clamp(1.5rem, 4vw, 2.25rem);
}

.card__head {
  text-align: center;
}

.card__title {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 600;
  color: #f8fafc;
}

.card__accent {
  color: #00f5d4;
}

.card__sub {
  margin: 0.5rem 0 0;
  font-size: 0.9rem;
  color: rgba(226, 232, 240, 0.55);
}

.card__emblem {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 1.75rem 0 1.5rem;
  min-height: 100px;
}

.card__orbit {
  position: absolute;
  border: 1px solid rgba(0, 245, 212, 0.15);
  border-radius: 50%;
}

.card__orbit--outer {
  width: 100px;
  height: 100px;
}

.card__orbit--inner {
  width: 72px;
  height: 72px;
  border-color: rgba(0, 245, 212, 0.25);
}

.card__star {
  position: relative;
  z-index: 1;
  filter: drop-shadow(0 0 16px rgba(0, 245, 212, 0.55));
}

.form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form__field :deep(.n-input) {
  --n-border: 1px solid rgba(255, 255, 255, 0.1) !important;
  --n-border-hover: 1px solid rgba(0, 245, 212, 0.35) !important;
  --n-border-focus: 1px solid rgba(0, 245, 212, 0.55) !important;
  --n-color: rgba(15, 23, 42, 0.65) !important;
  --n-color-focus: rgba(15, 23, 42, 0.85) !important;
  --n-text-color: #e2e8f0 !important;
  --n-placeholder-color: rgba(148, 163, 184, 0.75) !important;
}

.form__icon {
  color: rgba(148, 163, 184, 0.85);
  font-size: 1.1rem;
}

.form__eye {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.25rem;
  margin: 0 -0.25rem 0 0;
  border: none;
  background: transparent;
  color: rgba(148, 163, 184, 0.9);
  cursor: pointer;
  border-radius: 0.35rem;
}

.form__eye:hover {
  color: #00f5d4;
}

.form__submit {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  width: 100%;
  margin-top: 0.25rem;
  padding: 0.85rem 1.25rem;
  border: none;
  border-radius: 999px;
  font-size: 1rem;
  font-weight: 600;
  font-family: inherit;
  color: #020617;
  cursor: pointer;
  background: linear-gradient(90deg, #00f5d4 0%, #00c9ae 50%, #0a6b5c 100%);
  box-shadow:
    0 0 24px rgba(0, 245, 212, 0.25),
    0 8px 24px rgba(0, 0, 0, 0.35);
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease;
}

.form__submit:hover {
  transform: translateY(-1px);
  box-shadow:
    0 0 32px rgba(0, 245, 212, 0.35),
    0 12px 28px rgba(0, 0, 0, 0.4);
}

.form__submit:active {
  transform: translateY(0);
}

.form__submit:disabled {
  opacity: 0.65;
  cursor: not-allowed;
  transform: none;
}

.social {
  margin-top: 1.75rem;
}

.social__divider {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.25rem;
  font-size: 0.75rem;
  color: rgba(148, 163, 184, 0.65);
}

.social__divider::before,
.social__divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: rgba(255, 255, 255, 0.08);
}

.social__row {
  display: flex;
  justify-content: center;
  gap: 1rem;
}

.social__btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(15, 23, 42, 0.5);
  color: #e2e8f0;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease,
    transform 0.15s ease;
}

.social__btn:hover {
  border-color: rgba(0, 245, 212, 0.35);
  background: rgba(0, 245, 212, 0.08);
  transform: translateY(-2px);
}

.social__btn--brand {
  color: #00f5d4;
  border-color: rgba(0, 245, 212, 0.25);
}

.card__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 1.5rem;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.remember :deep(.n-checkbox-box) {
  border-color: rgba(0, 245, 212, 0.45);
}

.remember :deep(.n-checkbox-box--checked) {
  background-color: #00f5d4 !important;
  border-color: #00f5d4 !important;
}

.forgot {
  font-size: 0.85rem;
  color: #00f5d4;
  text-decoration: none;
  opacity: 0.9;
}

.forgot:hover {
  text-decoration: underline;
}

@media (max-width: 960px) {
  .login-page {
    flex-direction: column;
  }

  .hero {
    min-height: auto;
    flex: none;
    padding-bottom: 2rem;
  }

  .hero__robot-wrap {
    margin-top: 2rem;
  }

  .panel {
    flex: 1;
    padding-top: 0;
  }
}
</style>
