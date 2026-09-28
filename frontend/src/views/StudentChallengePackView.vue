<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NTag } from 'naive-ui'
import { CheckmarkCircleOutline, LockClosedOutline, RocketOutline } from '@vicons/ionicons5'
import DashboardShell from '../components/layout/DashboardShell.vue'
import { fetchStudentChallengePack, type StoreChallengePack } from '../api/studentStore'

defineOptions({ name: 'StudentChallengePackView' })

const route = useRoute()
const router = useRouter()
const pack = ref<StoreChallengePack | null>(null)
const loading = ref(true)
const error = ref('')

const nextStage = computed(() => pack.value?.questions.find((question) => !question.completed)?.stage ?? null)
const progressStyle = computed(() => ({ '--progress': `${pack.value?.progress.percent ?? 0}%` }))

async function load() {
  loading.value = true
  error.value = ''
  const code = String(route.params.productCode || '')
  try {
    pack.value = await fetchStudentChallengePack(code)
  } catch (cause) {
    pack.value = null
    error.value = cause instanceof Error ? cause.message : '挑战包加载失败'
  } finally {
    loading.value = false
  }
}

function missionTitle(topic: string, stage: number) {
  const name = (topic || '').toLowerCase()
  if (/数组|列表|array/.test(name)) return '校准星图坐标'
  if (/条件|分支|branch/.test(name)) return '选择跃迁航线'
  if (/循环|loop/.test(name)) return '启动轨道推进器'
  if (/函数|function/.test(name)) return '组装导航模块'
  if (/搜索|查找|search/.test(name)) return '搜寻失联信标'
  if (/变量|输出|输入|print/.test(name)) return '恢复舱段通信'
  return ['点亮远航信标', '读取导航数据', '校准跃迁航线', '启动推进器', '整理星图坐标', '修复舱段模块', '解码通讯信号', '追踪失联探测器', '验证自动航线', '完成远航校准'][stage - 1] || '远航任务'
}

function start(questionId: string) {
  const packCode = pack.value?.product_code
  if (!packCode) return
  void router.push({
    path: `/student/trials/practice/${encodeURIComponent(questionId)}`,
    query: { pack_code: packCode },
  })
}

function returnToStore() {
  void router.push('/student/store')
}

onMounted(() => void load())
watch(() => route.params.productCode, () => void load())
</script>

<template>
  <DashboardShell active-nav="store" :page-title="pack?.title || '星际挑战航线'" page-subtitle="完成任务并把通关记录写进个人航行档案" search-placeholder="" hide-search>
    <main class="challenge-page">
      <section v-if="loading" class="challenge-state">正在接收星际任务简报…</section>
      <section v-else-if="error" class="challenge-state challenge-state--error">
        <div class="challenge-state__signal"><LockClosedOutline /></div>
        <span class="challenge-kicker">航线暂不可用</span>
        <h1>还不能进入这条挑战航线</h1>
        <p>{{ error }}</p>
        <n-button type="primary" round @click="returnToStore">返回星港补给站</n-button>
      </section>

      <template v-else-if="pack">
        <header class="campaign-hero">
          <div class="campaign-copy">
            <button type="button" class="back-link" @click="returnToStore">← 返回星港补给站</button>
            <span class="challenge-kicker"><n-icon :component="RocketOutline" /> 星际远航 · 特别任务</span>
            <h1>{{ pack.title }}</h1>
            <p>{{ pack.description }} 十个关卡将带你从基础指令出发，逐步修复沿途的导航系统。</p>
            <div class="campaign-tags"><n-tag round size="small" :bordered="false">编程实战</n-tag><n-tag round size="small" :bordered="false">不限次数练习</n-tag><n-tag round size="small" :bordered="false">进度自动保存</n-tag></div>
          </div>
          <aside class="campaign-progress" :style="progressStyle">
            <div class="progress-orb"><div><strong>{{ pack.progress.completed_count }}</strong><span>/ {{ pack.total }}</span></div></div>
            <span class="progress-caption">已完成任务</span>
            <strong class="progress-percent">{{ pack.progress.percent }}%</strong>
            <small>通过题目全部测试点后<br />自动写入航行档案</small>
          </aside>
        </header>

        <section class="mission-briefing">
          <div class="briefing-mark" aria-hidden="true">PLEX<br /><strong>01</strong></div>
          <div><span class="challenge-kicker">任务简报</span><h2>算法星带 · 信号恢复行动</h2><p>导航站收到一组待修复的程序指令。请逐关完成代码任务；每次通过全部测试后，通关状态会保存到你的账号，可随时回来继续。</p></div>
          <div class="briefing-note"><span>通关规则</span><strong>所有测试点通过</strong><small>不额外发放 XP，不影响班级排名</small></div>
        </section>

        <section class="mission-section">
          <header class="mission-heading">
            <div><span class="challenge-kicker">航线任务</span><h2>按你的节奏完成十个关卡</h2></div>
            <span>{{ pack.progress.completed_count }} / {{ pack.total }} 已通关</span>
          </header>
          <ol class="mission-route">
            <li
              v-for="question in pack.questions"
              :key="question.id"
              class="mission-stage"
              :class="{ 'mission-stage--completed': question.completed, 'mission-stage--current': question.stage === nextStage }"
            >
              <span class="mission-stage__node">
                <n-icon v-if="question.completed" :component="CheckmarkCircleOutline" />
                <span v-else>{{ String(question.stage).padStart(2, '0') }}</span>
              </span>
              <article class="mission-stage__card">
                <div class="stage-meta"><span>任务 {{ String(question.stage).padStart(2, '0') }}</span><span>{{ question.code }} · {{ question.topic || '算法基础' }}</span></div>
                <h3>{{ missionTitle(question.topic, question.stage) }}<small v-if="question.completed">已完成</small></h3>
                <p>{{ question.title }}</p>
                <div class="stage-footer">
                  <div><n-tag size="small" round :bordered="false">{{ question.difficulty }}</n-tag><span>约 {{ question.duration_min }} 分钟</span></div>
                  <n-button size="small" :secondary="question.completed" :type="question.completed ? 'default' : 'primary'" round @click="start(question.id)">
                    {{ question.completed ? '再次练习' : question.stage === nextStage ? '开始本关' : '进入任务' }}
                  </n-button>
                </div>
              </article>
            </li>
          </ol>
        </section>
        <footer class="campaign-footer"><span>完成记录会跨设备同步到你的账号。</span><button type="button" @click="returnToStore">查看其他补给</button></footer>
      </template>
    </main>
  </DashboardShell>
</template>

<style scoped>
.challenge-page { width: min(1120px,100%); margin: 0 auto; padding: 1.8rem clamp(1rem,3vw,2.5rem) 4rem; color: #e8f6fa; }
.campaign-hero { position: relative; display: grid; grid-template-columns: 1fr 220px; gap: 2rem; overflow: hidden; padding: clamp(1.4rem,4vw,2.8rem); border: 1px solid rgba(78,221,211,.19); border-radius: 28px 28px 28px 7px; background: radial-gradient(ellipse at 74% 120%,rgba(51,192,191,.18),transparent 38%),linear-gradient(125deg,#0d2a3f,#0a1828 70%,#121c32); }
.campaign-hero::after { content:''; position:absolute; width:260px;height:260px;right:115px;top:-195px;border:1px solid rgba(129,231,219,.14);border-radius:50%;box-shadow:0 0 0 27px rgba(129,231,219,.025),0 0 0 62px rgba(129,231,219,.02); }
.campaign-copy { position:relative;z-index:1;max-width:720px; }
.back-link { padding:0;border:0;background:none;color:rgba(201,232,237,.58);font:inherit;font-size:.79rem;cursor:pointer; }
.back-link:hover,.campaign-footer button:hover { color:#9aefe1; }
.challenge-kicker { display:flex;align-items:center;gap:.4rem;color:#79e8d9;font-size:.75rem;font-weight:760;letter-spacing:.04em; }
.campaign-copy>.challenge-kicker { margin-top:1.1rem; }
.campaign-copy h1 { margin:.65rem 0;color:#f3fbff;font-size:clamp(1.8rem,4vw,2.65rem);letter-spacing:-.035em; }
.campaign-copy>p { max-width:650px;margin:0;color:rgba(219,235,244,.68);font-size:.92rem;line-height:1.75; }
.campaign-tags { display:flex;flex-wrap:wrap;gap:.45rem;margin-top:1rem; }
.campaign-progress { position:relative;z-index:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:.36rem;padding:1rem;border:1px solid rgba(133,198,209,.16);border-radius:20px 20px 5px 20px;background:rgba(4,17,28,.63); }
.progress-orb { display:grid;place-items:center;width:128px;height:128px;border-radius:50%;background:conic-gradient(#67ddc6 0 var(--progress),rgba(136,178,193,.14) var(--progress) 100%);box-shadow:0 0 35px rgba(57,209,190,.09); }
.progress-orb>div { display:flex;flex-direction:column;align-items:center;justify-content:center;width:104px;height:104px;border-radius:50%;background:#0b1c2b; }
.progress-orb strong { color:#effdfa;font-size:2rem;line-height:1; }
.progress-orb span { margin-top:.25rem;color:rgba(219,235,244,.54);font-size:.75rem; }
.progress-caption { margin-top:.3rem;color:rgba(219,235,244,.56);font-size:.77rem; }
.progress-percent { color:#9af0dc;font-size:1rem; }
.campaign-progress>small { color:rgba(219,235,244,.43);font-size:.68rem;line-height:1.5;text-align:center; }
.mission-briefing { display:grid;grid-template-columns:65px 1fr 220px;align-items:center;gap:1.1rem;margin-top:1rem;padding:1.2rem 1.35rem;border-left:2px solid rgba(226,185,104,.6);background:linear-gradient(100deg,rgba(76,62,36,.24),rgba(12,25,38,.22)); }
.briefing-mark { display:grid;place-items:center;width:55px;height:55px;border:1px solid rgba(226,185,104,.25);border-radius:16px 16px 4px 16px;color:#d3c296;font-size:.53rem;line-height:1.25;text-align:center; }
.briefing-mark strong { color:#f1d88f;font-size:1rem; }
.mission-briefing h2 { margin:.22rem 0;color:#f0f6f6;font-size:1.08rem; }
.mission-briefing p { max-width:690px;margin:0;color:rgba(219,235,244,.53);font-size:.78rem;line-height:1.6; }
.briefing-note { display:grid;gap:.25rem;padding-left:1rem;border-left:1px solid rgba(154,189,199,.14); }
.briefing-note span,.briefing-note small { color:rgba(219,235,244,.44);font-size:.68rem; }
.briefing-note strong { color:#e8d39e;font-size:.78rem; }
.mission-section { margin-top:2.5rem; }
.mission-heading { display:flex;align-items:end;justify-content:space-between;gap:1rem;margin-bottom:1rem; }
.mission-heading h2 { margin:.27rem 0 0;color:#effaff;font-size:1.42rem; }
.mission-heading>span { color:rgba(219,235,244,.52);font-size:.8rem; }
.mission-route { position:relative;display:grid;gap:.7rem;padding:0;margin:0;list-style:none; }
.mission-route::before { content:'';position:absolute;left:19px;top:24px;bottom:24px;width:1px;background:linear-gradient(rgba(103,222,203,.5),rgba(121,176,193,.12)); }
.mission-stage { position:relative;display:grid;grid-template-columns:40px 1fr;gap:.85rem;align-items:stretch; }
.mission-stage__node { position:relative;z-index:1;display:grid;place-items:center;align-self:start;width:39px;height:39px;margin-top:1rem;border:1px solid rgba(126,182,196,.22);border-radius:50%;background:#0c1e2d;color:#9dbcc5;font-size:.72rem; }
.mission-stage--current .mission-stage__node { border-color:#67ddc6;background:#153c45;color:#bdfff0;box-shadow:0 0 18px rgba(61,205,184,.18); }
.mission-stage--completed .mission-stage__node { border-color:rgba(107,223,185,.38);color:#83e4bf; }
.mission-stage__card { padding:.95rem 1.1rem;border:1px solid rgba(124,183,200,.12);border-radius:6px 17px 17px 17px;background:linear-gradient(112deg,rgba(14,33,48,.95),rgba(8,19,31,.93)); }
.mission-stage--current .mission-stage__card { border-color:rgba(99,218,204,.29);background:linear-gradient(112deg,rgba(16,47,56,.92),rgba(9,24,37,.96)); }
.mission-stage--completed .mission-stage__card { border-color:rgba(101,206,171,.13); }
.stage-meta { display:flex;justify-content:space-between;gap:.8rem;color:rgba(219,235,244,.43);font-size:.68rem; }
.stage-meta span:first-child { color:#86daca; }
.mission-stage__card h3 { display:flex;align-items:center;gap:.6rem;margin:.38rem 0 .2rem;color:#eaf6f8;font-size:.98rem; }
.mission-stage__card h3 small { padding:.17rem .42rem;border:1px solid rgba(97,207,165,.2);border-radius:999px;color:#85dfb7;font-size:.62rem;font-weight:550; }
.mission-stage__card p { margin:0;color:rgba(219,235,244,.53);font-size:.78rem;line-height:1.5; }
.stage-footer { display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-top:.7rem; }
.stage-footer>div { display:flex;align-items:center;gap:.55rem;color:rgba(219,235,244,.43);font-size:.69rem; }
.campaign-footer { display:flex;justify-content:space-between;gap:1rem;margin:1.1rem 0 0 55px;padding-top:.9rem;border-top:1px solid rgba(127,172,188,.12);color:rgba(219,235,244,.44);font-size:.75rem; }
.campaign-footer button { padding:0;border:0;background:none;color:rgba(219,235,244,.6);font:inherit;cursor:pointer; }
.challenge-state { display:flex;min-height:360px;flex-direction:column;align-items:center;justify-content:center;gap:.55rem;color:rgba(219,235,244,.62);text-align:center; }
.challenge-state__signal { display:grid;place-items:center;width:52px;height:52px;border:1px solid rgba(231,188,114,.25);border-radius:50%;color:#edca87;font-size:1.25rem; }
.challenge-state h1 { margin:.3rem 0;color:#effaff;font-size:1.4rem; }
.challenge-state p { max-width:470px;margin:0 0 .5rem;color:rgba(219,235,244,.54);font-size:.83rem;line-height:1.55; }
.challenge-state--error .challenge-kicker { color:#e5c27e; }
@media(max-width:760px){.campaign-hero{grid-template-columns:1fr;gap:1.2rem}.campaign-progress{display:grid;grid-template-columns:88px 1fr;justify-items:start;min-height:100px}.progress-orb{grid-row:span 3;width:76px;height:76px}.progress-orb>div{width:62px;height:62px}.progress-orb strong{font-size:1.4rem}.campaign-progress>small{text-align:left}.mission-briefing{grid-template-columns:50px 1fr}.briefing-mark{width:46px;height:46px}.briefing-note{grid-column:2;border:0;padding:0}.stage-meta{flex-direction:column;gap:.2rem}}
@media(max-width:520px){.challenge-page{padding-top:1rem}.campaign-hero{border-radius:22px 22px 22px 6px}.mission-briefing{align-items:start;padding:1rem}.mission-heading{align-items:start;flex-direction:column}.mission-stage{grid-template-columns:30px 1fr;gap:.55rem}.mission-stage__node{width:29px;height:29px;margin-top:1.1rem;font-size:.64rem}.mission-route::before{left:14px}.mission-stage__card{padding:.8rem}.stage-footer{align-items:flex-start;flex-direction:column}.campaign-footer{margin-left:0;flex-direction:column}}
@media(prefers-reduced-motion:reduce){.progress-orb{scroll-behavior:auto}}
</style>
