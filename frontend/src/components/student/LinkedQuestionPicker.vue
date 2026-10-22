<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { NSelect, NButton, NAlert } from 'naive-ui'
import { fetchPracticeHistory, practiceRequest, type Attempt } from '../../api/studentPractice'
import { fetchTutorContext, type TutorContextRequest } from '../../api/tutorContext'
import { useAuthStore } from '../../stores/auth'
import { takeTutorHandoff } from '../../composables/tutorHandoff'
const emit=defineEmits<{change:[value:TutorContextRequest|null]}>()
const route=useRoute(),auth=useAuthStore(),history=ref<Attempt[]>([]),picked=ref<string|null>(null),title=ref(''),error=ref(''),page=ref(1),total=ref(0)
const linkedCode=ref(''), linkedTime=ref('')
let epoch=0
async function verify(value:TutorContextRequest){const ticket=++epoch;emit('change',null);error.value='';try{const context=await fetchTutorContext(value);if(ticket!==epoch)return;if(!context.task)throw new Error('请选择一条有效题目');if(context.task.tutoring_policy==='disabled')throw new Error('本次考试需独立完成，交卷后可关联提问');title.value=context.task.title;linkedCode.value=value.code||'';emit('change',{...value,question_ref:context.task.ref,question_version:context.task.version})}catch(e){if(ticket===epoch)error.value=e instanceof Error?e.message:'关联失败'}}
async function load(){try{const result=await fetchPracticeHistory(page.value);history.value=result.items;total.value=result.total}catch(e){error.value=e instanceof Error?e.message:'历史记录加载失败'}}
async function choose(id:string|null){picked.value=id;const row=history.value.find(r=>r.id===id);if(row){linkedTime.value=row.created_at;await verify({submission_id:row.id,code:row.code})}else{title.value='';linkedCode.value='';linkedTime.value='';emit('change',null)}}
async function initialize(){if(!auth.profile?.id)return;title.value='';linkedCode.value='';linkedTime.value='';emit('change',null);await load();const value=takeTutorHandoff(auth.profile!.id);if(value){await verify(value);return}if(route.query.submission){try{const row=await practiceRequest<Attempt>('get',`/practice-history/${encodeURIComponent(String(route.query.submission))}`);linkedTime.value=row.created_at;await verify({submission_id:row.id,code:row.code})}catch(e){error.value=e instanceof Error?e.message:'作答不可用'}}else if(route.query.question_ref){await verify({question_ref:String(route.query.question_ref)})}}
watch(page,load);watch(()=>auth.profile?.id,()=>{++epoch;history.value=[];emit('change',null);void initialize()})
onMounted(initialize);onBeforeUnmount(()=>{++epoch})
</script>
<template><section class="linked-picker"><strong>{{title||'关联一道题目或历史作答'}}</strong><n-select :value="picked" filterable clearable :options="history.map(r=>({label:`${r.title} · ${new Date(r.created_at).toLocaleString()}`,value:r.id}))" placeholder="选择我的正式作答" @update:value="choose"/><small v-if="linkedTime">{{new Date(linkedTime).toLocaleString()}} 的正式作答</small><details v-if="linkedCode"><summary>代码附件 · {{linkedCode.split('\n').length}} 行</summary><pre>{{linkedCode}}</pre></details><div v-if="total>20"><n-button size="tiny" :disabled="page<=1" @click="page--">上一页</n-button><n-button size="tiny" :disabled="page*20>=total" @click="page++">下一页</n-button></div><n-alert v-if="error" type="warning">{{error}} <n-button text @click="initialize">重新关联</n-button></n-alert></section></template>
<style scoped>.linked-picker{display:grid;gap:10px;padding:12px;border:1px solid var(--plex-border,#369994);border-radius:12px;margin:12px 0}.linked-picker strong{font-size:14px;overflow-wrap:anywhere}.linked-picker pre{max-height:180px;overflow:auto;white-space:pre;font-size:12px}.linked-picker small{opacity:.7}</style>
