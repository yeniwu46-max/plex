<script setup lang="ts">
import { computed, onMounted, onActivated, onDeactivated, ref } from 'vue'
import { NButton, NSelect, NInput, NDrawer, NDrawerContent } from 'naive-ui'
import { useMediaQuery } from '@vueuse/core'
import LearnerKnowledgeDetails from './LearnerKnowledgeDetails.vue'
import PlexKnowledgeGraph from '../shared/PlexKnowledgeGraph.vue'
import { fetchStudentKnowledgeGraph, type KnowledgeGraphPayload } from '../../api/knowledgeGraph'
import { fetchLearnerState, type LearnerStateSnapshot } from '../../api/learnerState'
import { STAR_PATH_DOMAINS } from '../../data/starPathDomains'
import type { KgNode } from '../../data/knowledgeGraphData'
const mobile=useMediaQuery('(max-width: 768px)'), detailOpen=ref(false)
const graph=ref<KnowledgeGraphPayload|null>(null),state=ref<LearnerStateSnapshot|null>(null),domain=ref<string|null>(STAR_PATH_DOMAINS[0]?.key||null),search=ref(''),selected=ref<KgNode|null>(null),error=ref(''),loading=ref(false)
const map=ref<InstanceType<typeof PlexKnowledgeGraph>|null>(null)
let epoch=0
const evidenceCount=computed(()=>state.value?.concepts.filter(c=>c.independent_count+c.assisted_count>0).length||0)
const nodes=computed(()=>{const ids=domain.value?new Set(STAR_PATH_DOMAINS.find(d=>d.key===domain.value)?.knowledgePoints.map(k=>k.id)):null;return (graph.value?.nodes||[]).filter(n=>(!ids||ids.has(n.id))&&(!search.value||n.label.includes(search.value))).map((n,i)=>{const c=state.value?.concepts.find(c=>c.concept_id===n.id);return {...n,...(domain.value?{x:90+(i%4)*180,y:80+Math.floor(i/4)*110}:{}),status:(!c||c.estimate===null?'unlearned':c.estimate>=.8?'mastered':c.estimate<.5?'weak':'learning') as KgNode['status']}})})
const edges=computed(()=>{const ids=new Set(nodes.value.map(n=>n.id));return(graph.value?.edges||[]).filter(e=>ids.has(e.source)&&ids.has(e.target))})
const concept=computed(()=>state.value?.concepts.find(c=>c.concept_id===selected.value?.id))
const misconceptions=computed(()=>state.value?.misconceptions.filter(c=>c.concept_id===selected.value?.id&&c.status!=='dismissed')||[])
async function load(){const ticket=++epoch;loading.value=true;try{const [g,s]=await Promise.all([fetchStudentKnowledgeGraph(),fetchLearnerState()]);if(ticket!==epoch)return;graph.value=g;state.value=s;error.value='';if(!selected.value)selected.value=g.nodes[0]||null}catch(e){if(ticket===epoch)error.value=e instanceof Error?e.message:'地图暂不可用'}finally{if(ticket===epoch)loading.value=false}}
function select(node:KgNode){selected.value=node;if(mobile.value)detailOpen.value=true}
onMounted(load);onActivated(load);onDeactivated(()=>{++epoch})
</script>
<template><section class="exploration-report">
 <header class="map-intro"><div><span class="eyebrow">我的知识宇宙</span><h2>每一次练习，点亮下一程</h2><p>从真实作答中发现进步与薄弱点，让下一步更有方向。</p></div><div class="evidence-number"><strong>{{evidenceCount}}</strong><span>已有作答证据的知识点</span></div></header>
 <p v-if="error" role="alert">{{error}} <n-button @click="load">重试</n-button></p><p v-else-if="loading">正在连接学习地图…</p>
 <div class="map-controls" data-tour="student-profile"><n-select v-model:value="domain" clearable :options="STAR_PATH_DOMAINS.map(d=>({label:d.title,value:d.key}))" placeholder="全部八大学域"/><n-input v-model:value="search" clearable placeholder="搜索知识点"/><n-button @click="map?.zoomMap(1.2)">放大</n-button><n-button @click="map?.zoomMap(.8)">缩小</n-button><n-button @click="map?.resetMap()">全图</n-button></div>
 <div class="map-layout"><div class="map-surface"><PlexKnowledgeGraph v-if="graph" ref="map" :nodes="nodes" :edges="edges" :scroll-zoom="false" height="480px" @node-click="select"/><n-button v-if="mobile&&selected" @click="detailOpen=true">查看 {{selected.label}} 档案</n-button><p v-if="graph&&!nodes.length">没有匹配的知识点</p><details class="accessible-nodes"><summary>知识点列表 · 键盘浏览</summary><div><button v-for="node in nodes" :key="node.id" @click="select(node)">{{node.label}}</button></div></details></div>
 <LearnerKnowledgeDetails v-if="!mobile" :selected="selected" :concept="concept" :misconceptions="misconceptions"/>
 <n-drawer v-model:show="detailOpen" placement="bottom" height="min(76dvh, 620px)" :auto-focus="true"><n-drawer-content title="知识点档案" closable><LearnerKnowledgeDetails :selected="selected" :concept="concept" :misconceptions="misconceptions"/></n-drawer-content></n-drawer></div>
 </section></template>
<style scoped>
.exploration-report{color:var(--plex-text);margin-bottom:24px}.map-intro{display:flex;justify-content:space-between;align-items:center;gap:24px;padding:28px;border:1px solid var(--plex-border);border-radius:20px;background:linear-gradient(130deg,color-mix(in srgb,#55eee9 9%,transparent),transparent)}h2{font-size:clamp(22px,2.3vw,32px);margin:10px 0}p{line-height:1.8;opacity:.8}.eyebrow{letter-spacing:.14em;font-size:12px;color:var(--plex-accent,#30b7ae)}.evidence-number{display:grid;gap:6px;min-width:150px}.evidence-number strong{font-size:44px}.evidence-number span{font-size:12px}.map-controls{display:grid;grid-template-columns:minmax(140px,1fr) minmax(150px,1fr) auto auto auto;gap:10px;margin:20px 0}.map-layout{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:18px}.map-surface,.node-report{min-width:0;border:1px solid var(--plex-border);border-radius:18px;overflow:hidden;background:var(--plex-bg-card)}.node-report{padding:22px}.evidence-value{display:grid;gap:8px;margin:24px 0}.evidence-value strong{font-size:28px}.evidence-value small{opacity:.65}dl>div{display:flex;justify-content:space-between;gap:10px;padding:10px 0;border-bottom:1px solid var(--plex-border)}dd{margin:0}.map-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:24px}.accessible-nodes{padding:16px}.accessible-nodes>div{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.accessible-nodes button{background:transparent;color:inherit;border:1px solid var(--plex-border);border-radius:8px;padding:8px;cursor:pointer}:global(html[data-plex-style="comic"] .map-intro),:global(html[data-plex-style="comic"] .node-report),:global(html[data-plex-style="comic"] .map-surface){border-width:2px;border-radius:6px 20px 6px 20px;box-shadow:4px 4px 0 color-mix(in srgb,currentColor 15%,transparent)}@media(max-width:1024px){.map-layout{grid-template-columns:1fr}.node-report{border-radius:18px}.map-controls{grid-template-columns:1fr 1fr}}@media(max-width:600px){.map-intro{padding:18px;align-items:flex-start;flex-direction:column}.evidence-number{display:flex;align-items:center;gap:15px}.evidence-number strong{font-size:28px}.map-controls{grid-template-columns:repeat(3,1fr)}.map-controls>:first-child,.map-controls>:nth-child(2){grid-column:1/-1}}
</style>
