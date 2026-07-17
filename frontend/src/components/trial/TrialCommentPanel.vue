<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { NButton, NInput, useMessage } from 'naive-ui'
import {
  createTrialComment,
  fetchTrialComments,
  toggleTrialCommentLike,
  type TrialCommentItem,
} from '../../api/trialComments'
import { formatHttpError } from '../../api/http'
import { useAuthStore } from '../../stores/auth'

const props = defineProps<{
  questionRef: string
}>()

const message = useMessage()
const auth = useAuthStore()
const loading = ref(false)
const posting = ref(false)
const items = ref<TrialCommentItem[]>([])
const draft = ref('')
const replyDrafts = ref<Record<number, string>>({})
const replyTargetId = ref<number | null>(null)

async function load() {
  if (!props.questionRef) return
  loading.value = true
  try {
    const result = await fetchTrialComments(props.questionRef)
    items.value = result.items
  } catch (error) {
    message.error(formatHttpError(error, '评论加载失败'))
  } finally {
    loading.value = false
  }
}

async function submitComment(parentId: number | null = null) {
  if (!auth.isAuthenticated) {
    message.warning('请先登录后再发表评论')
    return
  }
  if (!props.questionRef?.trim()) {
    message.error('题目标识缺失，请刷新页面后重试')
    return
  }
  const content = (parentId ? replyDrafts.value[parentId] : draft.value).trim()
  if (!content) {
    message.warning('请输入评论内容')
    return
  }
  posting.value = true
  try {
    await createTrialComment({
      question_ref: props.questionRef,
      content,
      parent_id: parentId,
    })
    if (parentId) {
      replyDrafts.value[parentId] = ''
      replyTargetId.value = null
    } else {
      draft.value = ''
    }
    await load()
    message.success(parentId ? '回复已发布' : '评论已发布')
  } catch (error) {
    message.error(formatHttpError(error, '评论发布失败'))
  } finally {
    posting.value = false
  }
}

async function onToggleLike(comment: TrialCommentItem) {
  try {
    const result = await toggleTrialCommentLike(comment.id)
    comment.liked_by_me = result.liked
    comment.like_count = result.like_count
  } catch (error) {
    message.error(error instanceof Error ? error.message : '点赞失败')
  }
}

function formatTime(value: string | null) {
  if (!value) return ''
  return new Date(value).toLocaleString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function avatarFallback(name: string) {
  return (name || '学').trim().charAt(0).toUpperCase()
}

onMounted(() => {
  void load()
})

watch(
  () => props.questionRef,
  () => {
    void load()
  },
)
</script>

<template>
  <div class="trial-comments">
    <div class="trial-comments__composer">
      <n-input
        v-model:value="draft"
        type="textarea"
        :autosize="{ minRows: 2, maxRows: 4 }"
        placeholder="分享你的思路或疑问…"
      />
      <n-button type="primary" size="small" :loading="posting" @click="submitComment()">发布评论</n-button>
    </div>

    <p v-if="loading" class="trial-comments__state">正在加载评论…</p>
    <p v-else-if="!items.length" class="trial-comments__state">还没有评论，来做第一个分享者吧。</p>

    <article v-for="item in items" :key="item.id" class="trial-comments__thread">
      <header>
        <div class="trial-comments__author">
          <img
            v-if="item.author_avatar_url"
            :src="item.author_avatar_url"
            :alt="item.author_name"
            class="trial-comments__avatar"
          />
          <span v-else class="trial-comments__avatar trial-comments__avatar--fallback">{{ avatarFallback(item.author_name) }}</span>
          <strong>{{ item.author_name }}</strong>
        </div>
        <time>{{ formatTime(item.created_at) }}</time>
      </header>
      <p>{{ item.content }}</p>
      <div class="trial-comments__actions">
        <button type="button" :class="{ 'is-active': item.liked_by_me }" @click="onToggleLike(item)">
          👍 {{ item.like_count || '赞' }}
        </button>
        <button type="button" @click="replyTargetId = replyTargetId === item.id ? null : item.id">回复</button>
      </div>

      <div v-if="replyTargetId === item.id" class="trial-comments__reply-box">
        <n-input
          v-model:value="replyDrafts[item.id]"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 3 }"
          placeholder="写下你的回复…"
        />
        <n-button size="small" type="primary" :loading="posting" @click="submitComment(item.id)">发送回复</n-button>
      </div>

      <div v-if="item.replies.length" class="trial-comments__replies">
        <div v-for="reply in item.replies" :key="reply.id" class="trial-comments__reply">
          <header>
            <div class="trial-comments__author">
              <img
                v-if="reply.author_avatar_url"
                :src="reply.author_avatar_url"
                :alt="reply.author_name"
                class="trial-comments__avatar"
              />
              <span v-else class="trial-comments__avatar trial-comments__avatar--fallback">{{ avatarFallback(reply.author_name) }}</span>
              <strong>{{ reply.author_name }}</strong>
            </div>
            <time>{{ formatTime(reply.created_at) }}</time>
          </header>
          <p>{{ reply.content }}</p>
          <button type="button" :class="{ 'is-active': reply.liked_by_me }" @click="onToggleLike(reply)">
            👍 {{ reply.like_count || '赞' }}
          </button>
        </div>
      </div>
    </article>
  </div>
</template>

<style scoped>
.trial-comments{display:grid;gap:.75rem}.trial-comments__composer{display:grid;gap:.5rem}.trial-comments__state{margin:0;color:rgba(221,230,239,.55);font-size:.82rem}.trial-comments__thread{padding:.75rem;border:1px solid rgba(130,212,255,.12);border-radius:10px;background:rgba(8,20,32,.55)}.trial-comments__thread header,.trial-comments__reply header{display:flex;align-items:center;justify-content:space-between;gap:.5rem;margin-bottom:.35rem}.trial-comments__author{display:flex;align-items:center;gap:.45rem}.trial-comments__avatar{width:1.65rem;height:1.65rem;border-radius:999px;object-fit:cover;border:1px solid rgba(130,212,255,.18)}.trial-comments__avatar--fallback{display:inline-grid;place-items:center;background:rgba(52,230,197,.16);color:#34e6c5;font-size:.72rem;font-weight:700}.trial-comments__thread strong,.trial-comments__reply strong{color:#f5fbff;font-size:.84rem}.trial-comments__thread time,.trial-comments__reply time{color:rgba(221,230,239,.45);font-size:.72rem}.trial-comments__thread p,.trial-comments__reply p{margin:0;color:rgba(226,232,240,.86);font-size:.84rem;line-height:1.55;white-space:pre-wrap}.trial-comments__actions,.trial-comments__reply button{display:flex;gap:.65rem;margin-top:.45rem}.trial-comments__actions button,.trial-comments__reply>button{border:0;background:none;color:rgba(221,230,239,.62);cursor:pointer;font-size:.78rem}.trial-comments__actions button.is-active,.trial-comments__reply>button.is-active{color:#34d399}.trial-comments__reply-box{display:grid;gap:.45rem;margin-top:.55rem;padding-top:.55rem;border-top:1px solid rgba(130,212,255,.1)}.trial-comments__replies{display:grid;gap:.55rem;margin-top:.65rem;padding-left:.75rem;border-left:2px solid rgba(52,230,197,.18)}.trial-comments__reply{padding:.55rem;border-radius:8px;background:rgba(255,255,255,.03)}
</style>
