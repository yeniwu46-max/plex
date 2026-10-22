<script setup lang="ts">
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePreferredReducedMotion } from '@vueuse/core'
import { useAuthStore } from '../stores/auth'
import { useThemeStore } from '../stores/theme'
import { fetchArrival, saveArrival, completeArrival, acknowledgeArrival, type ArrivalState, type SurveyAnswers, type Appearance } from '../api/onboarding'
import { formatHttpError } from '../api/http'
import { safeAuthRedirect } from '../utils/authValidation'
import littleE from '../assets/xiao-e-comic.svg'

const auth = useAuthStore(), theme = useThemeStore(), route = useRoute(), router = useRouter()
const owner = auth.profile?.id
const reducedMotion = usePreferredReducedMotion()
const editing = computed(() => route.name === 'student-arrival-profile')
const enteredAsEditor = editing.value
const loading = ref(true), busy = ref(false), error = ref(''), draftError = ref('')
const state = ref<ArrivalState | null>(null)
const answers = ref<SurveyAnswers>({})
const step = ref(1)
const style = ref<Appearance['visual_style']>(theme.visualStyle)
const mode = ref<'dark' | 'light'>(theme.resolvedTheme)
const welcome = ref(false), stage = ref(0), ready = ref(false)
let draftTimer: ReturnType<typeof setTimeout> | undefined
let animationTimers: ReturnType<typeof setTimeout>[] = []
let draftQueue = Promise.resolve()
let loaded = false, disposed = false
let originalAppearance = theme.appearance()
let saved = false
const cacheKey = computed(() => `plex-arrival-draft:${auth.profile?.id}`)
const appearance = (): Appearance => ({ visual_style: style.value, color_mode: mode.value })
const labels = { age_range: '你的年龄范围', programming_level: '目前的编程基础', field: '你正在学习或从事的领域' } as const
// JSON object key order is not the questionnaire's presentation order.
const optionOrder = {
  age_range: ['under13', '13_15', '16_18', '19_24', '25_34', '35plus', 'private'],
  programming_level: ['none', 'syntax', 'exercises', 'projects', 'professional', 'unknown'],
  field: ['student', 'software', 'engineering', 'education', 'creative', 'business', 'other', 'private'],
} as const
function orderedOptions(key: keyof typeof labels) {
  const choices = state.value?.options[key] ?? {}
  const known: readonly string[] = optionOrder[key]
  return [...known, ...Object.keys(choices).filter(value => !known.includes(value))]
    .filter(value => Object.hasOwn(choices, value))
    .map(value => ({ value, text: choices[value] }))
}
const target = computed(() => {
  const value = safeAuthRedirect(route.query.redirect, '/student')
  return (value === '/student' || value.startsWith('/student/')) && router.resolve(value).matched.length > 0 && !/^\/student\/(onboarding|arrival-profile)([/?#]|$)/.test(value) ? value : '/student'
})
const valid = computed(() => Boolean(answers.value.age_range && answers.value.programming_level && answers.value.field))
const nickname = computed(() => auth.profile?.real_name || auth.profile?.username || '新冒险家')

function accept(result: ArrivalState) {
  if (disposed || auth.profile?.id !== owner) throw new Error('登录账号已变化，请重新进入')
  state.value = result
  auth.syncProfile({ onboarding: result.onboarding, preferences: result.preferences })
}
async function load() {
  loaded = false; loading.value = true; error.value = ''
  try {
    await auth.ensureAccount()
    const result = await fetchArrival()
    if (disposed) return
    accept(result)
    await nextTick()
    originalAppearance = result.preferences ?? theme.appearance()
    if (!editing.value && !result.onboarding.required) { await router.replace(target.value); return }
    if (editing.value && result.onboarding.required) { await router.replace('/student/onboarding'); return }
    answers.value = { ...(result.onboarding.status === 'pending' ? result.draft : result.answers) }
    step.value = editing.value ? 1 : result.step
    style.value = result.preferences?.visual_style ?? theme.visualStyle
    mode.value = result.preferences?.color_mode === 'auto' ? theme.resolvedTheme : result.preferences?.color_mode ?? theme.resolvedTheme
    if (!editing.value && result.onboarding.status === 'pending') {
      try {
        const cached = JSON.parse(sessionStorage.getItem(cacheKey.value) || 'null')
        if (cached) {
          answers.value = cached.answers; step.value = cached.step === 2 ? 2 : 1
          if (['space', 'comic'].includes(cached.preferences?.visual_style)) style.value = cached.preferences.visual_style
          if (['dark', 'light'].includes(cached.preferences?.color_mode)) mode.value = cached.preferences.color_mode
        }
      } catch { sessionStorage.removeItem(cacheKey.value) }
    }
    theme.previewAppearance(appearance())
    if (result.onboarding.welcome_pending && !editing.value) showWelcome()
  } catch (e) { error.value = formatHttpError(e, '入驻资料加载失败，请重试') }
  finally { loading.value = false; window.setTimeout(() => { loaded = true }, 0) }
}

function queueDraft() {
  if (!loaded || editing.value || welcome.value || busy.value || state.value?.onboarding.status !== 'pending') return
  clearTimeout(draftTimer)
  const payload = { answers: { ...answers.value }, step: step.value, preferences: appearance() }
  const snapshot = JSON.stringify(payload)
  sessionStorage.setItem(cacheKey.value, snapshot)
  draftTimer = setTimeout(() => {
    draftQueue = draftQueue.then(async () => {
      if (disposed || auth.profile?.id !== owner) return
      try {
        await saveArrival(payload.answers, payload.step, payload.preferences, true)
        draftError.value = ''
        if (sessionStorage.getItem(cacheKey.value) === snapshot) sessionStorage.removeItem(cacheKey.value)
      } catch { draftError.value = '草稿暂未同步，仍保留在本页。你可以重试或继续入驻。' }
    })
  }, 500)
}
watch([answers, step, style, mode], () => {
  if (loaded) theme.previewAppearance(appearance())
  queueDraft()
}, { deep: true })
function next() {
  error.value = ''
  if (!valid.value) { error.value = '请选择三个问题的答案，也可以选择“暂不确定”或“暂不透露”。'; return }
  step.value = 2
}
async function submit(action: 'submit' | 'skip') {
  if (busy.value || auth.profile?.id !== owner) return
  if (action === 'submit' && !valid.value) { error.value = '请先完成三个问题。'; step.value = 1; return }
  busy.value = true; error.value = ''; clearTimeout(draftTimer)
  try {
    await draftQueue
    const result = editing.value ? await saveArrival(answers.value, 2, appearance()) : await completeArrival(action, answers.value, appearance())
    accept(result)
    saved = true
    if (result.preferences) {
      style.value = result.preferences.visual_style
      mode.value = result.preferences.color_mode === 'auto' ? theme.resolvedTheme : result.preferences.color_mode
    }
    sessionStorage.removeItem(cacheKey.value)
    if (editing.value) { await router.replace('/student/me/profile'); return }
    if (result.onboarding.welcome_pending) showWelcome()
    else await router.replace(target.value)
  } catch (e) { error.value = formatHttpError(e, '保存未完成，请重试'); }
  finally { busy.value = false }
}
function finishAnimation() {
  animationTimers.forEach(clearTimeout); animationTimers = []
  stage.value = 2; ready.value = true
}
function showWelcome() {
  welcome.value = true; stage.value = 0; ready.value = false
  animationTimers.forEach(clearTimeout)
  if (reducedMotion.value === 'reduce') { finishAnimation(); return }
  animationTimers = [setTimeout(() => { stage.value = 1 }, 2000), setTimeout(() => { stage.value = 2 }, 4000), setTimeout(finishAnimation, 6000)]
}
watch(reducedMotion, value => { if (value === 'reduce' && welcome.value) finishAnimation() })
async function enter() {
  if (busy.value || auth.profile?.id !== owner) return
  busy.value = true; error.value = ''
  try {
    const result = await acknowledgeArrival()
    accept(result)
    await router.replace(target.value)
  } catch (e) { error.value = formatHttpError(e, '请重试进入，入驻编号已为你保留') }
  finally { busy.value = false }
}
onMounted(load)
onBeforeUnmount(() => {
  disposed = true; clearTimeout(draftTimer); animationTimers.forEach(clearTimeout)
  if (enteredAsEditor && !saved && auth.profile?.id === owner) theme.previewAppearance(originalAppearance)
})
</script>

<template>
  <main class="arrival" :class="[{ 'arrival--comic': style === 'comic', 'arrival--light': mode === 'light', 'arrival--welcome': welcome }, `arrival--stage-${stage}`]">
    <div class="arrival-stars" aria-hidden="true"><i v-for="n in 24" :key="n" :style="{ '--i': n }" /></div>
    <header class="arrival-top"><RouterLink to="/student" aria-label="PLEX 首页" class="arrival-brand">PLEX<span>UNIVERSE</span></RouterLink><span>{{ editing ? '你的入驻档案' : '新旅程 · 即将开启' }}</span></header>
    <section v-if="loading" class="arrival-card arrival-loading" aria-live="polite"><img :src="littleE" alt="" /><h1>小E正在准备你的探索舱</h1><p>正在同步入驻资料…</p></section>
    <section v-else-if="!state" class="arrival-card"><h1>暂时无法连接探索舱</h1><p role="alert">{{ error }}</p><button class="arrival-primary" @click="load">重新加载</button><button class="arrival-link" @click="auth.logout().then(() => router.replace('/login'))">返回登录</button></section>

    <section v-else-if="welcome" class="arrival-ceremony" :class="{ 'is-ready': ready }" aria-labelledby="welcome-title">
      <button v-if="!ready" class="arrival-skip-animation" @click="finishAnimation">跳过动画 →</button>
      <div class="arrival-portal" aria-hidden="true"><div class="portal-ring" /><div class="portal-ring portal-ring--inner" /><img :src="littleE" alt="" /></div>
      <div class="arrival-welcome-copy" aria-live="polite">
        <p class="arrival-eyebrow">{{ stage === 0 ? 'FLIGHT 01 · 启航' : stage === 1 ? 'ARRIVAL · 欢迎抵达' : 'EXPLORER ID · 专属入驻徽章' }}</p>
        <h1 id="welcome-title">{{ stage === 0 ? '向你的学习宇宙出发' : stage === 1 ? `${nickname}，欢迎来到 PLEX` : `你是第 ${state.onboarding.adventurer_number} 位入驻的冒险家！` }}</h1>
        <p>{{ stage < 2 ? '小E将陪你发现问题、尝试解答，走出自己的学习路径。' : '每一段成长，都从一次好奇开始。你的旅程，现在开启。' }}</p>
      </div>
      <div v-if="stage === 2" class="arrival-badge"><span>PLEX EXPLORER</span><strong>#{{ state.onboarding.adventurer_number }}</strong><span>{{ nickname }}</span></div>
      <button v-if="ready" class="arrival-primary arrival-enter" :disabled="busy" @click="enter">{{ busy ? '正在进入…' : '开启探索 →' }}</button>
      <p v-if="error" role="alert" class="arrival-error">{{ error }}</p>
    </section>

    <section v-else class="arrival-workspace">
      <aside class="arrival-intro">
        <p class="arrival-eyebrow">YOUR NEXT CHAPTER</p><h1>{{ editing ? '让小E更懂你' : '你好，\n新冒险家。' }}</h1>
        <p>{{ editing ? '学习会进步，兴趣也会变化。随时更新你的入驻资料。' : '花半分钟认识彼此，\n一起找到适合你的学习起点。' }}</p>
        <div class="arrival-mascot"><img :src="littleE" alt="学习伙伴小E" /><span>从你的起点开始，<br />我们一起探索！</span></div>
        <small>基础信息用于个性化指导；年龄不会发送给外部模型。你可以稍后修改。</small>
      </aside>
      <div class="arrival-card">
        <nav class="arrival-steps" aria-label="问卷进度"><span :class="{ active: step === 1 }" :aria-current="step === 1 ? 'step' : undefined">01 了解你</span><span aria-hidden="true">／</span><span :class="{ active: step === 2 }" :aria-current="step === 2 ? 'step' : undefined">02 选择外观</span></nav>
        <form @submit.prevent="step === 1 ? next() : submit('submit')">
          <div v-if="step === 1" class="arrival-questions">
            <fieldset v-for="(label, key) in labels" :key="key"><legend>{{ label }}</legend><div class="arrival-options"><label v-for="{ text, value } in orderedOptions(key)" :key="value" :class="{ selected: answers[key] === value }"><input v-model="answers[key]" type="radio" :name="key" :value="value" /><span>{{ text }}</span></label></div></fieldset>
            <label v-if="answers.field === 'other'" class="arrival-other">补充你的领域 · 选填<input v-model="answers.field_detail" maxlength="50" placeholder="不超过 50 字，如产品设计" /><small>{{ answers.field_detail?.length || 0 }}/50</small></label>
          </div>
          <div v-else class="arrival-appearance">
            <h2>选择你喜欢的探索世界</h2><p>风格与明暗可以自由组合，以后也能随时切换。</p>
            <fieldset><legend>主题风格</legend><div class="arrival-style-options"><label v-for="choice in [{ value: 'space' as const, label: '经典主题', caption: '安静、清晰的太空探索' }, { value: 'comic' as const, label: '太空漫画风', caption: '把每次学习画成新篇章' }]" :key="choice.value" :class="{ selected: style === choice.value }"><input v-model="style" type="radio" name="style" :value="choice.value" /><div class="arrival-mini" :class="`mini-${choice.value}`" aria-hidden="true"><span>PLEX</span><i /><b>探索，从这里开始</b><em>开启新篇章 →</em></div><strong>{{ choice.label }}</strong><small>{{ choice.caption }}</small></label></div></fieldset>
            <fieldset><legend>明暗模式</legend><div class="arrival-options arrival-mode-options"><label :class="{ selected: mode === 'dark' }"><input v-model="mode" type="radio" name="mode" value="dark" /><span>☾ 黑夜</span></label><label :class="{ selected: mode === 'light' }"><input v-model="mode" type="radio" name="mode" value="light" /><span>☀ 白昼</span></label></div></fieldset>
          </div>
          <p v-if="error" role="alert" class="arrival-error">{{ error }}</p>
          <p v-if="draftError" role="status" class="arrival-error">{{ draftError }} <button type="button" class="arrival-link" @click="queueDraft">重试同步</button></p>
          <footer class="arrival-actions"><button v-if="step === 2" type="button" class="arrival-secondary" :disabled="busy" @click="step = 1">上一步</button><button type="submit" class="arrival-primary" :disabled="busy">{{ busy ? '正在保存…' : step === 1 ? '下一步：选择外观 →' : editing ? '保存资料' : '完成入驻 →' }}</button></footer>
          <button v-if="!editing" type="button" class="arrival-link arrival-later" :disabled="busy" @click="submit('skip')">稍后填写，先去看看</button><RouterLink v-else class="arrival-link arrival-later" to="/student/me/profile">返回学习画像</RouterLink>
        </form>
      </div>
    </section>
    <footer class="arrival-bottom">每个人的起点不同，每一步探索都值得被看见。</footer>
  </main>
</template>

<style scoped>
.arrival { --bg:#07131f; --panel:#102436; --ink:#eef7ff; --muted:#a5bfcd; --line:#35526a; --accent:#55eee9; --accent-ink:#06272c; --option:#0b1c2c; --gold:#f6cd68; min-height:100dvh; padding:26px clamp(20px,5vw,88px); background:radial-gradient(ellipse at 14% 45%,#13424d55,transparent 48%),var(--bg); color:var(--ink); position:relative; isolation:isolate; overflow:hidden; font-family:Inter,'Noto Sans SC',system-ui,sans-serif; }
.arrival--light { --bg:#eff6fa; --panel:#fff; --ink:#112b3b; --muted:#4c6678; --line:#a4bdcc; --accent:#087e83; --accent-ink:#fff; --option:#f1f7fa; --gold:#a76a15; }
.arrival * { box-sizing:border-box; text-shadow:none; } .arrival button,.arrival input { font:inherit; } .arrival button { cursor:pointer; } .arrival button:disabled { cursor:wait; opacity:.65; } .arrival button:focus-visible,.arrival a:focus-visible,.arrival input:focus-visible { outline:3px solid var(--gold); outline-offset:4px; }
.arrival-top { display:flex; align-items:center; justify-content:space-between; gap:20px; max-width:1320px; margin:0 auto; font-size:12px; color:var(--muted); letter-spacing:.06em; } .arrival-brand { font-size:27px; letter-spacing:.12em; font-weight:900; color:var(--accent); text-decoration:none; display:flex; align-items:center; gap:12px; } .arrival-brand span { font-size:10px; letter-spacing:.26em; font-weight:500; color:var(--muted); }
.arrival-workspace { display:grid; grid-template-columns:minmax(240px,.8fr) minmax(0,1.2fr); align-items:center; gap:clamp(28px,5vw,80px); max-width:1180px; margin:clamp(32px,5vw,80px) auto 42px; } .arrival-eyebrow { font-size:11px; letter-spacing:.18em; color:var(--accent); font-weight:700; } .arrival-intro h1 { font-size:clamp(38px,4.2vw,62px); line-height:1.15; margin:24px 0; white-space:pre-line; letter-spacing:-.04em; } .arrival-intro>p:not(.arrival-eyebrow) { color:var(--muted); line-height:1.9; white-space:pre-line; } .arrival-intro small { display:block; max-width:340px; line-height:1.8; color:var(--muted); font-size:12px; }
.arrival-mascot { display:flex; align-items:center; margin:32px 0 26px; gap:12px; } .arrival-mascot img { width:116px; height:116px; object-fit:contain; } .arrival-mascot span { padding:16px; border:1px solid var(--line); border-radius:16px 16px 16px 0; line-height:1.7; font-size:13px; background:var(--panel); }
.arrival-card { padding:clamp(22px,3vw,40px); background:var(--panel); border:1px solid var(--line); border-radius:24px; box-shadow:0 24px 80px #0002; min-width:0; } .arrival-steps { display:flex; gap:16px; font-size:12px; color:var(--muted); margin-bottom:32px; } .arrival-steps .active { color:var(--accent); font-weight:800; }
.arrival-questions,.arrival-appearance { display:grid; gap:26px; } fieldset { padding:0; border:0; margin:0; min-width:0; } legend { font-size:15px; font-weight:700; margin-bottom:12px; } .arrival-options { display:flex; gap:8px; flex-wrap:wrap; } .arrival-options label { display:flex; align-items:center; padding:10px 13px; border:1px solid var(--line); border-radius:10px; background:var(--option); color:var(--muted); font-size:13px; cursor:pointer; min-height:42px; } .arrival-options label.selected { border-color:var(--accent); color:var(--ink); background:color-mix(in srgb,var(--accent) 10%,var(--panel)); } input[type=radio] { appearance:none; width:14px; height:14px; border:1px solid var(--muted); border-radius:50%; margin:0 8px 0 0; flex-shrink:0; } input[type=radio]:checked { border:4px solid var(--accent); } label:has(input:focus-visible) { outline:2px solid var(--gold); outline-offset:3px; }
.arrival-other { display:grid; gap:8px; font-size:13px; } .arrival-other input { width:100%; padding:12px; border-radius:8px; border:1px solid var(--line); color:var(--ink); background:var(--option); } .arrival-other small { text-align:right; color:var(--muted); }
.arrival-primary,.arrival-secondary { display:inline-flex; align-items:center; justify-content:center; padding:14px 22px; border-radius:12px; font-weight:750; font-size:14px; border:1px solid transparent; transition:transform .18s,box-shadow .18s; text-decoration:none; } .arrival-primary { color:var(--accent-ink); background:var(--accent); } .arrival-secondary { color:var(--ink); border-color:var(--line); background:transparent; } .arrival-primary:hover:not(:disabled) { transform:translateY(-2px); box-shadow:0 6px 16px #0002; } .arrival-primary:active:not(:disabled) { transform:translateY(0); } .arrival-actions { display:flex; gap:12px; margin-top:32px; } .arrival-actions .arrival-primary { flex:1; } .arrival-link { color:var(--muted); font-size:13px; background:none; border:0; text-decoration:underline; text-underline-offset:4px; line-height:1.7; } .arrival-later { display:block; width:100%; text-align:center; margin-top:20px; } .arrival-error { padding:12px; border-left:3px solid var(--gold); color:var(--ink); background:color-mix(in srgb,var(--gold) 10%,var(--panel)); font-size:13px; line-height:1.7; }
.arrival-appearance h2 { margin:0; font-size:23px; } .arrival-appearance>p { margin:-12px 0 0; font-size:13px; color:var(--muted); line-height:1.7; } .arrival-style-options { display:grid; grid-template-columns:1fr 1fr; gap:12px; } .arrival-style-options>label { position:relative; min-width:0; padding:12px; border:2px solid var(--line); border-radius:14px; cursor:pointer; background:var(--option); } .arrival-style-options>label.selected { border-color:var(--accent); } .arrival-style-options input { position:absolute; top:18px; right:10px; z-index:2; } .arrival-style-options strong,.arrival-style-options small { display:block; margin-top:12px; } .arrival-style-options strong { font-size:14px; } .arrival-style-options small { font-size:11px; color:var(--muted); line-height:1.7; margin-top:6px; }
.arrival-mini { height:140px; border:1px solid var(--line); border-radius:10px; padding:14px; position:relative; overflow:hidden; background:var(--panel); display:flex; flex-direction:column; align-items:flex-start; justify-content:space-between; } .arrival-mini span { font-size:10px; color:var(--accent); font-weight:900; letter-spacing:.1em; } .arrival-mini i { position:absolute; width:64px; height:64px; border:1px solid var(--accent); border-radius:50%; top:36px; right:-8px; opacity:.35; box-shadow:inset 0 0 20px var(--accent); } .arrival-mini b { font-size:12px; z-index:1; } .arrival-mini em { font-style:normal; padding:6px 9px; border-radius:6px; background:var(--accent); color:var(--accent-ink); font-size:9px; z-index:1; } .mini-comic { border:2px solid var(--ink); box-shadow:3px 3px 0 var(--line); border-radius:5px; background:radial-gradient(var(--line) .7px,transparent .8px) right top/6px 6px,var(--panel); } .mini-comic em { border:1px solid var(--ink); border-radius:3px; box-shadow:2px 2px 0 var(--line); } .arrival-mode-options label { flex:1; justify-content:center; }
.arrival--comic .arrival-card { border:2px solid var(--line); border-radius:10px 26px 12px 22px; box-shadow:7px 7px 0 var(--line); } .arrival--comic .arrival-primary { border:2px solid var(--ink); box-shadow:4px 4px 0 var(--line); border-radius:7px; } .arrival--comic .arrival-mascot span { border:2px solid var(--line); box-shadow:3px 3px 0 var(--line); } .arrival--comic .arrival-options label { border-width:2px; border-radius:6px; }
.arrival-stars { position:absolute; inset:0; pointer-events:none; z-index:-1; } .arrival-stars i { position:absolute; left:calc(mod(var(--i) * 37, 100) * 1%); top:calc(mod(var(--i) * 17, 100) * 1%); width:2px; height:2px; border-radius:50%; background:var(--muted); opacity:.35; } .arrival-bottom { color:var(--muted); text-align:center; font-size:11px; line-height:1.8; margin-top:32px; }
.arrival-loading { max-width:580px; margin:80px auto; text-align:center; } .arrival-loading img { width:100px; } .arrival-loading h1 { font-size:24px; }
.arrival-ceremony { position:relative; min-height:720px; max-width:1100px; margin:20px auto; text-align:center; display:flex; align-items:center; flex-direction:column; justify-content:center; gap:20px; padding:40px 0; } .arrival-skip-animation { position:absolute; right:0; top:0; background:var(--panel); color:var(--ink); border:1px solid var(--line); padding:12px 18px; border-radius:8px; } .arrival-portal { width:230px; height:230px; position:relative; display:grid; place-items:center; } .arrival-portal img { width:135px; height:135px; z-index:1; object-fit:contain; } .portal-ring { position:absolute; inset:0; border:2px solid var(--accent); border-radius:50%; box-shadow:0 0 40px color-mix(in srgb,var(--accent) 20%,transparent),inset 0 0 25px color-mix(in srgb,var(--accent) 15%,transparent); } .portal-ring--inner { inset:18px; border-style:dashed; opacity:.5; } .arrival--stage-0 .arrival-portal { animation:arrival-flight 2s ease both; } .arrival--stage-1 .portal-ring { animation:arrival-gate 2s ease both; } .arrival--stage-2 .arrival-portal { width:130px; height:130px; } .arrival--stage-2 .arrival-portal img { width:90px; height:90px; } .arrival-welcome-copy { max-width:850px; } .arrival-welcome-copy h1 { font-size:clamp(25px,3.5vw,44px); line-height:1.5; margin:12px 0; overflow-wrap:anywhere; } .arrival-welcome-copy>p:last-child { color:var(--muted); font-size:14px; line-height:1.9; } .arrival-badge { display:grid; gap:10px; border:2px solid var(--gold); background:var(--panel); padding:22px 48px; border-radius:16px; animation:arrival-badge .7s ease both; max-width:100%; overflow-wrap:anywhere; } .arrival-badge span:first-child { font-size:10px; letter-spacing:.2em; color:var(--gold); } .arrival-badge strong { font-variant-numeric:tabular-nums; font-size:clamp(40px,6vw,64px); color:var(--gold); line-height:1.1; } .arrival-badge span:last-child { font-size:14px; } .arrival--comic .arrival-badge { border-radius:4px 20px 4px 20px; box-shadow:6px 6px 0 var(--line); } .arrival-enter { min-width:220px; margin-top:8px; } .is-ready * { animation:none!important; }
@keyframes arrival-flight { from { transform:translateY(45px) scale(.65); opacity:.2; } to { transform:translateY(0) scale(1); opacity:1; } } @keyframes arrival-gate { 0% { transform:scale(.9); opacity:.4; } 50% { transform:scale(1.15); opacity:1; } 100% { transform:scale(1); opacity:.8; } } @keyframes arrival-badge { from { transform:translateY(18px) scale(.92); opacity:0; } to { transform:none; opacity:1; } }
@media(max-width:900px) { .arrival-workspace { grid-template-columns:1fr; max-width:640px; gap:22px; margin-top:34px; } .arrival-intro { display:grid; grid-template-columns:1fr 150px; column-gap:12px; } .arrival-intro h1 { font-size:34px; margin:10px 0; white-space:normal; } .arrival-intro .arrival-eyebrow,.arrival-intro>p,.arrival-intro small { grid-column:1; } .arrival-mascot { grid-column:2; grid-row:1/5; justify-content:center; margin:0; } .arrival-mascot img { width:120px; } .arrival-mascot span { display:none; } .arrival-intro small { max-width:none; font-size:11px; } .arrival-ceremony { min-height:650px; } }
@media(max-width:480px) { .arrival { padding:20px 16px; } .arrival-top>span { font-size:10px; } .arrival-brand { font-size:23px; } .arrival-brand span { display:none; } .arrival-intro { grid-template-columns:1fr 80px; } .arrival-intro h1 { font-size:30px; } .arrival-mascot img { width:80px; } .arrival-card { padding:24px 18px; } .arrival-options { gap:8px; } .arrival-options label { padding:10px; font-size:12px; } .arrival-style-options { gap:8px; } .arrival-style-options>label { padding:8px; } .arrival-mini { height:120px; padding:10px; } .arrival-mini b { font-size:10px; } .arrival-mini em { font-size:8px; } .arrival-steps { margin-bottom:24px; } .arrival-primary,.arrival-secondary { padding:13px; font-size:13px; } .arrival-ceremony { min-height:650px; padding-top:70px; } }
@media(prefers-reduced-motion:reduce) { .arrival *, .arrival *::before, .arrival *::after { animation:none!important; transition:none!important; scroll-behavior:auto!important; } }
</style>
