<template>
  <div class="history-search">
    <n-space vertical :size="16">
      <n-space>
        <n-date-picker v-model:value="dateRange" type="daterange" clearable :default-value="defaultRange" />
        <n-select v-model:value="category" :options="catOptions" placeholder="分类" clearable style="width:140px" />
        <n-select v-model:value="recommend" :options="recOptions" placeholder="推荐等级" clearable style="width:120px" />
        <n-input v-model:value="keyword" placeholder="搜索关键词" clearable style="width:200px" @keyup.enter="search" />
        <n-button type="primary" @click="search">检索</n-button>
        <n-button @click="reset">重置</n-button>
      </n-space>

      <n-data-table :columns="columns" :data="items" :loading="loading" :pagination="pagination" @update:page="onPage" />

      <n-card v-if="selected" title="详情" size="small">
        <n-descriptions v-if="selected.scores" :columns="2" size="small" bordered>
          <n-descriptions-item v-for="(s, k) in selected.scores" :key="k" :label="dimLabels[k] || k">
            {{ s.value }}/5 | {{ (s.confidence * 100).toFixed(0) }}%
            <n-tag v-if="s.confidence < 0.6" type="warning" size="tiny">低</n-tag>
          </n-descriptions-item>
        </n-descriptions>
      </n-card>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { NDataTable, NDatePicker, NSelect, NInput, NButton, NSpace, NCard, NTag, NDescriptions, NDescriptionsItem } from 'naive-ui'
import { get } from '../api'

const loading = ref(false)
const dateRange = ref<[number, number] | null>(null)
const category = ref<string | null>(null)
const recommend = ref<string | null>(null)
const keyword = ref('')
const items = ref<any[]>([])
const selected = ref<any>(null)
const total = ref(0)
const page = ref(1)

const catOptions = [
  { label: 'AI Agent', value: 'AI Agent' },
  { label: '多模态大模型', value: '多模态大模型' },
  { label: 'NLP', value: 'NLP' },
]
const recOptions = [
  { label: '强烈推荐', value: '强烈推荐' },
  { label: '值得关注', value: '值得关注' },
  { label: '暂不跟进', value: '暂不跟进' },
  { label: '不推荐', value: '不推荐' },
]

const dimLabels: Record<string, string> = {
  business: '商业潜力', deploy: '落地难度',
  performance: '性能指标', compatibility: '业务兼容性',
}

const columns = [
  { title: '评分', key: 'score_total', width: 70, render: (r: any) => r.score_total?.toFixed(1) },
  { title: '推荐', key: 'recommend_level', width: 90 },
  { title: '摘要', key: 'summary_one_liner', ellipsis: { tooltip: true } },
  { title: '时间', key: 'analyzed_at', width: 100, render: (r: any) => r.analyzed_at?.slice(0, 10) },
]

const pagination = computed(() => ({
  page: page.value, pageSize: 20, itemCount: total.value,
}))

const defaultRange = ref<[number, number]>([Date.now() - 30 * 86400000, Date.now()])

async function search() {
  loading.value = true
  const params: Record<string, any> = { page: page.value, page_size: 20 }
  if (dateRange.value) {
    params.date_from = new Date(dateRange.value[0]).toISOString().slice(0, 10)
    params.date_to = new Date(dateRange.value[1]).toISOString().slice(0, 10)
  }
  if (category.value) params.category = category.value
  if (recommend.value) params.recommend_level = recommend.value
  if (keyword.value) params.keyword = keyword.value

  const data = await get<any>('/items?' + new URLSearchParams(params))
  items.value = data.items
  total.value = data.total
  loading.value = false
}

function reset() {
  dateRange.value = null; category.value = null; recommend.value = null
  keyword.value = ''; page.value = 1; search()
}

function onPage(p: number) { page.value = p; search() }
</script>
