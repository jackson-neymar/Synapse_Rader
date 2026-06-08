<template>
  <div class="trigger-run">
    <n-space vertical :size="20">
      <n-card title="手动执行日报流程">
        <n-space vertical :size="12">
          <p>点击按钮将立即触发一次完整的日报流程：采集 → 筛选 → 分析 → RAG → 报告 → 推送</p>
          <n-button type="primary" :disabled="running" @click="trigger">⚡ 立即执行日报流程</n-button>
          <n-alert v-if="message" :type="messageType" closable>{{ message }}</n-alert>
        </n-space>
      </n-card>

      <n-card v-if="runId" title="执行状态">
        <n-space vertical :size="8">
          <n-tag>Run ID: {{ runId }}</n-tag>
          <n-progress v-for="node in nodes" :key="node.name"
            :percentage="node.status === 'success' ? 100 : node.status === 'running' ? 50 : 0"
            :status="node.status === 'failed' ? 'error' : node.status === 'success' ? 'success' : 'default'"
            :indicator-placement="'inside'"
            :height="28"
          >
            {{ node.name }} — {{ statusText(node) }}
          </n-progress>
        </n-space>
      </n-card>

      <n-card title="最近执行记录">
        <n-data-table :columns="logColumns" :data="runHistory" :loading="historyLoading" :pagination="false" />
      </n-card>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { NCard, NButton, NTag, NProgress, NDataTable, NSpace, NAlert } from 'naive-ui'
import { get, post } from '../api'

const running = ref(false)
const runId = ref('')
const message = ref('')
const messageType = ref<'success' | 'error' | 'warning'>('success')
const nodes = ref<any[]>([])
const runHistory = ref<any[]>([])
const historyLoading = ref(false)
let timer: any = null

const logColumns = [
  { title: 'Run ID', key: 'run_id', width: 140 },
  { title: '触发', key: 'trigger', width: 70 },
  { title: '节点状态', key: 'nodes', render: (r: any) => Object.entries(r.nodes).map(([k, v]) => `${k}:${v}`).join(', ') },
]

const statusText = (node: any) => {
  if (node.status === 'success') return '已完成'
  if (node.status === 'running') return '运行中...'
  if (node.status === 'failed') return `失败: ${node.error || ''}`
  return '等待中'
}

async function trigger() {
  if (running.value) return
  running.value = true; message.value = ''
  try {
    const data = await post<any>('/trigger/daily-run')
    runId.value = data.run_id; message.value = data.message; messageType.value = 'success'
    pollStatus()
  } catch (e: any) {
    message.value = e.message || '触发失败'; messageType.value = 'error'
    running.value = false
  }
}

async function pollStatus() {
  if (!runId.value) return
  const data = await get<any>(`/run-status/${runId.value}`)
  nodes.value = data.nodes || []
  if (data.overall_status === 'success' || data.overall_status === 'failed') {
    message.value = data.overall_status === 'success' ? '日报已生成，请查看今日日报' : '执行失败'
    messageType.value = data.overall_status === 'success' ? 'success' : 'error'
    running.value = false
    loadHistory()
    return
  }
  timer = setTimeout(pollStatus, 3000)
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const data = await get<any>('/run-history')
    runHistory.value = data.runs || []
  } finally {
    historyLoading.value = false
  }
}

onMounted(loadHistory)
onUnmounted(() => clearTimeout(timer))
</script>
