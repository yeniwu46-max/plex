import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import ts from 'typescript'
import * as vue from 'vue'

function script(path, names) {
  const source = readFileSync(new URL(path, import.meta.url), 'utf8')
    .match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1]
  return ts.transpileModule(source + `\nexport const api={${names}};`, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText
}
const tick = async () => { await vue.nextTick(); await Promise.resolve() }
const student = id => ({ id, username: `student${id}`, real_name: `Student ${id}`, status: 'active', level: 1, total_points: 0 })
const overview = (classId = 1) => ({ teacher: { id: 10 }, selected_class: { id: classId, name: 'Synthetic class' }, students: [student(4), student(5)], attention_students: [] })

function starfield() {
  const exports = {}, hooks = {}, auth = vue.reactive({ profile: { id: 10, role: 'teacher' } })
  const route = vue.reactive({ name: 'teacher-starfield', path: '/teacher/starfield', query: { studentId: '4', period: 'week' } })
  const context = { overview: vue.ref(null), loading: vue.ref(true), errorMessage: vue.ref(''), hasSelectedClass: vue.ref(true), attentionStudents: vue.ref([]), selectedClassId: vue.ref(1), loadOverview() {} }
  const navigate = args => { route.query = args.query; return Promise.resolve() }
  const scope = vue.effectScope()
  scope.run(() => vm.runInNewContext(script('../src/views/TeacherStarfieldView.vue', 'profileStudent,profileVisible,focusedStudentId,goExplorer'), {
    exports, sessionStorage: { getItem: () => null }, require(name) {
      if (name === 'vue') return { ...vue, onMounted() {}, onActivated: f => { hooks.activate = f }, onDeactivated: f => { hooks.deactivate = f } }
      if (name === 'vue-router') return { useRoute: () => route, useRouter: () => ({ push: navigate, replace: navigate }) }
      if (name === '../stores/auth') return { useAuthStore: () => auth }
      if (name === '../composables/useTeacherOverview') return { useTeacherOverviewInjected: () => context }
      if (name === '../data/starPathDomains') return { STAR_PATH_TABS: [] }
      if (name === '../data/knowledgeGraphData') return { KG_NODES: [], KG_EDGES: [] }
      if (name === '../api/teacherOverview') return { fetchTeacherClassStats: async () => null }
      if (name === '../api/teacherAgents') return { fetchClassDiagnosis: async () => ({}) }
      if (name === '../api/knowledgeGraph') return { fetchClassKnowledgeGraph: async () => ({ nodes: [], edges: [] }) }
      if (name === '../api/http') return { formatHttpError: e => String(e) }
      return {}
    },
  }))
  return { ...exports.api, context, auth, route, hooks, dispose: () => scope.stop() }
}

test('student route waits for authorized overview, opens details and preserves unrelated query on close', async () => {
  const s = starfield()
  try {
    assert.equal(s.profileVisible.value, false)
    s.context.overview.value = overview(); s.context.loading.value = false
    assert.equal(s.profileVisible.value, true); assert.equal(s.profileStudent.value.id, 4)
    s.profileVisible.value = false
    assert.equal(s.route.query.studentId, undefined); assert.equal(s.route.query.period, 'week')
    s.goExplorer(5)
    assert.equal(s.profileVisible.value, true); assert.equal(s.profileStudent.value.id, 5)
  } finally { s.dispose() }
})

test('unknown student, stale class/account and inactive cached page cannot expose a profile', async () => {
  const s = starfield()
  try {
    s.context.overview.value = overview(); s.context.loading.value = false
    s.route.query.studentId = '99'; assert.equal(s.profileStudent.value, null)
    s.route.query.studentId = '4e0'; assert.equal(s.focusedStudentId.value, null)
    s.route.query.studentId = '4'
    s.hooks.deactivate(); assert.equal(s.profileStudent.value, null)
    s.hooks.activate(); assert.equal(s.profileStudent.value.id, 4)
    s.route.name = 'teacher-classes'; assert.equal(s.profileStudent.value, null)
    s.route.name = 'teacher-starfield'
    s.auth.profile.id = 11; assert.equal(s.profileStudent.value, null)
    s.auth.profile.id = 10
    s.context.selectedClassId.value = 2; assert.equal(s.profileStudent.value, null)
    await tick(); assert.equal(s.route.query.studentId, undefined)
  } finally { s.dispose() }
})

function profile() {
  const exports = {}, calls = [], auth = vue.reactive({ profile: { id: 10, role: 'teacher' } })
  const props = vue.reactive({ show: true, student: student(4) })
  let unmount = () => {}
  const scope = vue.effectScope()
  scope.run(() => vm.runInNewContext(script('../src/components/teacher/ExplorerProfileModal.vue', 'history,loading'), {
    exports, defineProps: () => props, defineEmits: () => () => {}, require(name) {
      if (name === 'vue') return { ...vue, onBeforeUnmount: f => { unmount = f } }
      if (name === '../../stores/auth') return { useAuthStore: () => auth }
      if (name === '../../api/teacherTrials') return { fetchStudentTrialHistory: id => new Promise((resolve, reject) => calls.push({ id, resolve, reject })) }
      return {}
    },
  }))
  return { ...exports.api, props, calls, auth, dispose() { unmount(); scope.stop() } }
}

test('initially visible profile loads history, and a late previous student cannot replace current results', async () => {
  const s = profile()
  try {
    assert.equal(s.calls[0].id, 4)
    s.props.student = student(5)
    assert.equal(s.calls[1].id, 5)
    s.calls[1].resolve({ student: 5 }); await tick()
    s.calls[0].resolve({ student: 4 }); await tick()
    assert.equal(s.history.value.student, 5); assert.equal(s.loading.value, false)
  } finally { s.dispose() }
})

test('closing, signing out or unmounting invalidates pending history', async () => {
  const s = profile()
  s.props.show = false
  s.calls[0].resolve({ student: 4 }); await tick(); assert.equal(s.history.value, null)
  s.props.show = true
  s.auth.profile = null
  s.calls[1].resolve({ student: 4 }); await tick(); assert.equal(s.history.value, null)
  s.auth.profile = { id: 11, role: 'teacher' }
  s.dispose(); s.calls[2].resolve({ student: 4 }); await tick()
  assert.equal(s.history.value, null)
})
