<script setup lang="ts">
import type { CostEstimate } from '../../api/aiUsage'
defineProps<{ estimate?: CostEstimate }>()

const reasons: Record<string, string> = {
  historical_unpriced: '旧记录没有价格快照', in_progress: '调用尚未结束',
  call_not_succeeded: '调用失败或中断，费用待核对', model_not_reported: '未报告实际模型',
  missing_usage: '输入或输出用量缺失', inconsistent_usage: '用量字段不一致',
  unsupported_usage: '包含尚未支持的计费项目', unsupported_billing: '当前调用方式尚未匹配价格',
  unsupported_tier: '服务档位尚未匹配价格', rate_not_found: '模型或渠道没有已核实价格',
  rate_outside_validity: '价格未生效或已过复核期限', ambiguous_rate: '价格规则重叠',
  rate_card_unavailable: '价格文件暂不可用', invalid_rate_card: '价格文件需要修正',
}
function amount(value: string) {
  // Preserve sub-cent amounts; rounding to two decimals would look free.
  return value.includes('.') ? value.replace(/0+$/, '').replace(/\.$/, '') : value
}
</script>

<template>
  <div class="ai-cost">
    <p v-if="!estimate">费用估算暂不可用。</p>
    <p v-else-if="estimate.status === 'no_calls'">本周期暂无已记录的模型调用。</p>
    <template v-else>
      <p><strong>{{ estimate.status === 'partial' ? '部分调用的费用估算' : '费用估算' }}</strong>：已估算 {{ estimate.estimated_calls }} 次，未估算 {{ estimate.unpriced_calls }} 次。</p>
      <ul v-if="estimate.by_currency.length" aria-label="按币种列出的估算费用">
        <li v-for="entry in estimate.by_currency" :key="entry.currency">
          {{ entry.currency }} <strong>{{ amount(entry.min) }}<template v-if="entry.min !== entry.max"> – {{ amount(entry.max) }}</template></strong>
          <span>（{{ entry.calls }} 次调用）</span>
        </li>
      </ul>
      <p v-if="estimate.unpriced_calls">未估算部分未计入上述金额，不代表免费；不同币种分别统计。</p>
      <details v-if="Object.keys(estimate.unpriced_reasons).length">
        <summary>查看未估算原因</summary>
        <ul><li v-for="(count, key) in estimate.unpriced_reasons" :key="key">{{ reasons[key] || '计费信息待核对' }}：{{ count }} 次</li></ul>
      </details>
      <p class="ai-cost__note">这是平台模型调用成本，不是你的应付费用。依据已核对的公开价格和已报告用量估算，区间可能来自峰谷价或缓存用量不完整。金额未经供应商账单核对，不是实际扣费；不含税费、协议折扣和其他基础设施费用。</p>
    </template>
  </div>
</template>

<style scoped>
.ai-cost { margin-block: 12px; padding-block: 10px; border-top: 1px solid var(--plex-border, #526378); overflow-wrap: anywhere; }
.ai-cost p { margin: 6px 0; }
.ai-cost ul { margin: 6px 0; padding-left: 20px; }
.ai-cost summary { cursor: pointer; }
.ai-cost summary:focus-visible { outline: 2px solid currentColor; outline-offset: 3px; }
.ai-cost__note { opacity: .8; }
</style>
