import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import vm from 'node:vm'
import ts from 'typescript'
import {parse, compileScript} from '@vue/compiler-sfc'
import * as vue from 'vue'
import {renderToString} from '@vue/server-renderer'

const source=readFileSync(new URL('../src/components/shared/AiCostEstimate.vue',import.meta.url),'utf8')
const script=compileScript(parse(source).descriptor,{id:'cost-test',inlineTemplate:true}).content
const compiled=ts.transpileModule(script,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText
const exports={}
vm.runInNewContext(compiled,{exports,require:name=>{assert.equal(name,'vue');return vue}})
const render=estimate=>renderToString(vue.createSSRApp(exports.default,{estimate}))
const base={status:'estimated',basis:'published_rates_estimate',invoice_verified:false,estimated_calls:1,unpriced_calls:0,
  by_currency:[{currency:'USD',min:'0.0000000001',max:'0.0000000002',calls:1,range_calls:1}],unpriced_reasons:{},by_workflow:{}}

test('small nonzero costs are never rounded to free and estimates are not invoices',async()=>{
  const html=await render(base)
  assert.match(html,/0\.0000000001/);assert.match(html,/0\.0000000002/)
  assert.match(html,/未经供应商账单核对/);assert.match(html,/不是实际扣费/)
})

test('partial costs show excluded unknown calls and keep currencies separate',async()=>{
  const html=await render({...base,status:'partial',unpriced_calls:3,unpriced_reasons:{missing_usage:2,rate_not_found:1},
    by_currency:[...base.by_currency,{currency:'CNY',min:'0.3000000000',max:'0.3000000000',calls:1,range_calls:0}]})
  assert.match(html,/部分调用的费用估算/);assert.match(html,/未估算 3 次/)
  assert.match(html,/USD/);assert.match(html,/CNY/);assert.match(html,/>0\.3</)
  assert.match(html,/不代表免费/);assert.match(html,/输入或输出用量缺失：2 次/)
})

test('empty and legacy responses are distinguished from an explicit zero estimate',async()=>{
  assert.match(await render(undefined),/暂不可用/)
  assert.match(await render({...base,status:'no_calls',by_currency:[],estimated_calls:0}),/暂无已记录/)
  const html=await render({...base,by_currency:[{currency:'USD',min:'0.0000000000',max:'0.0000000000',calls:1,range_calls:0}]})
  assert.match(html,/<strong>0</);assert.doesNotMatch(html,/暂无已记录/)
})
