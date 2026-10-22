<script setup lang="ts">
import { computed, onActivated, onDeactivated, onMounted, onBeforeUnmount, ref } from 'vue'
import { NButton, NSelect, NAlert, NTag, useMessage, useDialog } from 'naive-ui'
import PlexCodeEditor from './PlexCodeEditor.vue'
import { onBeforeRouteLeave, useRouter } from 'vue-router'
import { practiceRequest, type Exam } from '../../api/studentPractice'
import { fetchStudentArenaTrials, type StudentTrial } from '../../api/studentTrials'
import { STAR_PATH_DOMAINS } from '../../data/starPathDomains'
const router = useRouter(), message = useMessage(), dialog = useDialog()
const trialTypes:Record<string,string>={acm:'编程竞赛',exam:'模拟考试',practice:'专项练习',homework:'课堂作业',challenge:'挑战试炼'}
const trialStatuses:Record<string,string>={published:'已发布',active:'进行中',running:'进行中',ongoing:'进行中',ended:'已结束',completed:'已完成',not_started:'未开始',scheduled:'即将开始',joined:'已参与',in_progress:'作答中'}
const keys = ref<string[]>([]), exam = ref<Exam | null>(null), teachers = ref<StudentTrial[]>([])
const selected = ref(0), busy = ref(false), error = ref(''), saveStatus = ref(''), now = ref(Date.now())
const drafts = ref<Record<string,string>>({}), dirty = ref(false)
let active = true, epoch = 0, offset = 0, timer: ReturnType<typeof setInterval> | undefined, saving: Promise<void> | null = null
const options = STAR_PATH_DOMAINS.flatMap(d => d.knowledgePoints.map(k => ({label:`${d.title} · ${k.title}`,value:k.id})))
const question = computed(() => exam.value?.questions[selected.value])
const remaining = computed(() => Math.max(0, Math.ceil((Date.parse(exam.value?.deadline || '')-now.value-offset)/1000)))
const clock = computed(() => `${Math.floor(remaining.value/60)}:${String(remaining.value%60).padStart(2,'0')}`)
function apply(value: Exam) { exam.value=value; offset=Date.parse(value.server_time)-Date.now(); if(!dirty.value) drafts.value={...value.answers} }
async function load() {
 const ticket=epoch
 try { const [papers,list] = await Promise.all([practiceRequest<{items:Exam[]}>('get','/mock-exams'), fetchStudentArenaTrials()]); if(!active || ticket!==epoch)return
 teachers.value=list.trials; const current=papers.items.find(e=>e.status!=='completed')||papers.items[0]; if(current)apply(current); error.value=''
 } catch(e) { if(active) error.value=e instanceof Error?e.message:'考试加载失败' }
}
async function start() { busy.value=true; try { dirty.value=false; apply(await practiceRequest<Exam>('post','/mock-exams',{knowledge_keys:keys.value})); selected.value=0; saveStatus.value='试卷已保存' } catch(e){message.error(e instanceof Error?e.message:'组卷失败')} finally{busy.value=false} }
function edit(value:string) { if(question.value){drafts.value={...drafts.value,[question.value.id]:value};dirty.value=true;saveStatus.value='待保存'} }
async function save() {
 if(saving) return saving
 if(!exam.value || exam.value.status!=='active' || !dirty.value)return
 const id=exam.value.id, snapshot={...drafts.value}, revision=exam.value.revision, ticket=epoch
 saving=(async()=>{try { const value=await practiceRequest<Exam>('patch',`/mock-exams/${id}/answers`,{answers:snapshot,revision}); if(ticket!==epoch)return
 dirty.value=JSON.stringify(drafts.value)!==JSON.stringify(snapshot);apply(value);saveStatus.value=dirty.value?'待保存':'已保存'
 }catch(e){saveStatus.value=e instanceof Error?e.message:'保存失败，请重试'; throw e}finally{saving=null}})()
 return saving
}
async function submit() { if(!exam.value)return; busy.value=true;try { await save(); if(dirty.value)throw new Error('仍有未保存的修改，请稍后重试');apply(await practiceRequest<Exam>('post',`/mock-exams/${exam.value.id}/submit`,{}));saveStatus.value='已交卷，等待判定' }catch(e){message.error(e instanceof Error?e.message:'交卷失败')}finally{busy.value=false} }
function confirmSubmit(){dialog.warning({title:'确认交卷',content:'交卷后不能修改答案，系统将按六道题的通过情况评分。',positiveText:'交卷',negativeText:'继续作答',onPositiveClick:submit})}
function begin(){active=true;clearInterval(timer);void load();timer=setInterval(()=>{now.value=Date.now();if(!active||busy.value)return;if(exam.value?.status==='active'&&remaining.value>0){void save().catch(()=>undefined)}else if(exam.value&&exam.value.status!=='completed'){void practiceRequest<Exam>('get',`/mock-exams/${exam.value.id}`).then(v=>{if(active){dirty.value=false;apply(v)}}).catch(()=>{error.value='判定状态加载失败，请重试'})}},3000)}
async function reloadDraft(){dialog.warning({title:'载入已保存的草稿',content:'这会替换当前尚未保存的修改。',positiveText:'载入',negativeText:'保留本页',onPositiveClick:async()=>{dirty.value=false;await load();saveStatus.value='已重新载入'}})}
function beforeUnload(event:BeforeUnloadEvent){if(dirty.value){event.preventDefault();event.returnValue=''}}
onBeforeRouteLeave(async()=>{if(!dirty.value)return true;try{await save();return !dirty.value}catch{message.warning('答案尚未保存，请重试保存后再离开');return false}})
onMounted(()=>window.addEventListener('beforeunload',beforeUnload))
onBeforeUnmount(()=>window.removeEventListener('beforeunload',beforeUnload))
function stop(){active=false;++epoch;clearInterval(timer)}
onMounted(begin);onActivated(begin);onDeactivated(stop);onBeforeUnmount(stop)
</script>
<template>
 <section class="exam-paper" data-tour="student-exam">
  <header><div><h3>自主组卷</h3><p>6 道编程题 · 120 分钟 · 交卷后开放小E辅导</p></div><n-tag>自动保存进度</n-tag></header>
  <n-alert v-if="error" type="warning">{{error}} <n-button text @click="load">重试</n-button></n-alert>
  <template v-if="!exam || exam.status==='completed'">
   <div class="exam-generate-controls"><n-select v-model:value="keys" multiple filterable :max="6" :options="options" placeholder="选择最多六个知识点；留空从题库随机抽取" />
   <n-button type="primary" :loading="busy" @click="start">随机生成六题试卷</n-button></div>
  </template>
  <template v-if="exam">
   <div class="paper-bar"><strong>{{exam.status==='active'?`剩余 ${clock}`:exam.status==='completed'?`得分 ${exam.score} / 100`:'已交卷 · 待判定'}}</strong><span role="status">{{saveStatus}}</span><n-button v-if="exam.status==='active'" :loading="busy" @click="confirmSubmit">交卷</n-button></div>
   <nav aria-label="试卷题目"><n-button v-for="(q,i) in exam.questions" :key="q.id" :type="i===selected?'primary':'default'" @click="selected=i">{{i+1}}{{drafts[q.id]?.trim()?' ·':''}}</n-button></nav>
   <article v-if="question"><h4>{{question.title}}</h4><p class="statement">{{question.description}}</p><pre v-for="(example,i) in question.examples" :key="i">输入：{{example.input}}
输出：{{example.output}}</pre>
    <PlexCodeEditor :model-value="drafts[question.id] ?? question.starter_code" :readonly="exam.status!=='active'" height="360px" @update:model-value="edit" />
    <div v-if="exam.status==='active'" class="paper-bar"><n-button @click="save().catch(()=>undefined)">立即保存</n-button><n-button @click="reloadDraft">重新载入草稿</n-button><span>切题自动保留草稿；离开前请确认已保存。</span></div>
    <div v-if="exam.status==='completed'" class="paper-bar"><n-tag>{{exam.results[question.id]?.all_passed?'通过':'未通过'}}</n-tag><n-button @click="router.push({path:'/student/messenger',query:{submission:exam.results[question.id]?.attempt_id}})">关联本次作答问小E</n-button></div>
   </article>
  </template>
  <section class="teacher-papers"><h3>教师发布</h3><p v-if="!teachers.length">暂无向你开放的教师试卷</p><article v-for="paper in teachers" :key="paper.id"><div><strong>{{paper.title}}</strong><p>{{trialTypes[paper.trial_type]||paper.trial_type}} · {{paper.duration_minutes}} 分钟 · {{trialStatuses[paper.effective_status||paper.status]||paper.effective_status||paper.status}} · {{trialStatuses[paper.my_status||'']||'尚未参与'}}<br v-if="paper.starts_at"/><span v-if="paper.starts_at">{{new Date(paper.starts_at).toLocaleString()}} 开始</span></p></div><n-button @click="router.push({path:'/student/trials',query:{trialId:paper.id}})">查看试卷</n-button></article></section>
 </section>
</template>
<style scoped>
.exam-paper{display:grid;gap:20px;min-width:0;color:var(--plex-text)}header,.paper-bar,.teacher-papers article{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}h3,h4,p{margin:0}p{line-height:1.7;opacity:.8}nav{display:flex;gap:8px;flex-wrap:wrap}article{min-width:0}article>h4{margin:16px 0}.statement,pre{white-space:pre-wrap;overflow-wrap:anywhere}.paper-bar{margin:12px 0}.teacher-papers{border-top:1px solid var(--plex-border);padding-top:24px}.teacher-papers article{padding:16px 0;border-bottom:1px solid var(--plex-border)}:global(html[data-plex-style="comic"] .exam-paper){border:2px solid var(--plex-border);padding:20px;box-shadow:4px 4px 0 #07131f;border-radius:14px}
.exam-generate-controls{display:flex;align-items:flex-start;gap:12px;min-width:0}.exam-generate-controls :deep(.n-select){flex:1;min-width:0}.exam-generate-controls>.n-button{flex:none;max-width:220px}
@media(max-width:600px){.exam-generate-controls{flex-wrap:wrap;justify-content:flex-end}.exam-generate-controls :deep(.n-select){flex-basis:100%}}
</style>
