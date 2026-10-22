import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import ts from 'typescript'

const source=readFileSync(new URL('../src/data/teacherStarfield.ts',import.meta.url),'utf8')
const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText
const exports={}
vm.runInNewContext(code,{exports,require(name){
  if(name==='./starPathDomains')return {STAR_PATH_TABS:[]}
  if(name==='./teacherKnowledgeCatalog')return {TEACHER_KNOWLEDGE_UNIVERSE:[]}
  throw new Error(name)
}})
const {buildStarfieldKpis,buildRiskTrend}=exports

test('missing metrics do not manufacture rates, gains or a historical trend',()=>{
  const cards=buildStarfieldKpis(null)
  assert.ok(cards.every(c=>c.value==='暂无统计' && c.delta==='' && c.points.length===0))
  assert.equal(buildRiskTrend(null).length,0)
})

test('cards use their own server measure; activity cannot imply repair or trial success',()=>{
  const overview={metrics:{avg_today_completion:0,reviewed_today_students:2,intervention_count:4,intervention_completion_rate:25},heatmap:{rows:[],days:[]}}
  const cards=buildStarfieldKpis(overview)
  assert.deepEqual(Array.from(cards,c=>c.value),['0%','2 人','25%'])
  overview.metrics.avg_today_completion=90
  assert.deepEqual(Array.from(buildStarfieldKpis(overview),c=>c.value),['90%','2 人','25%'])
  overview.metrics.intervention_count=0
  assert.equal(buildStarfieldKpis(overview)[2].value,'暂无工单')
})
