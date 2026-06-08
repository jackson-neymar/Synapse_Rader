<template>
  <div class="daily-report">
    <n-spin :show="loading">
      <n-empty v-if="!items.length && !loading" description="今日日报尚未生成" />

      <template v-else>
        <n-space :size="[16, 16]" class="stats-row">
          <n-card size="small" class="stat-card"><n-statistic label="今日情报" :value="displayItems.length" /></n-card>
          <n-card size="small" class="stat-card stat-high"><n-statistic label="强烈推荐" :value="high.length" /></n-card>
          <n-card size="small" class="stat-card stat-mid"><n-statistic label="值得关注" :value="mid.length" /></n-card>
          <n-card size="small" class="stat-card"><n-statistic label="暂不跟进" :value="low.length" /></n-card>
        </n-space>

        <n-divider />

        <template v-if="high.length">
          <h3 class="section-title high">强烈推荐 ({{ high.length }})</h3>
          <n-card v-for="item in high" :key="item.id" size="small" class="item-card">
            <template #header>
              <n-space align="center" :wrap="false">
                <n-tag type="error" size="small" :bordered="false">{{ item.recommend_level }}</n-tag>
                <span class="item-score">{{ item.score_total?.toFixed(1) }}</span>
                <span class="item-title">{{ item.title?.slice(0, 60) || '?' }}</span>
                <span v-if="item.confidence_overall" class="confidence">置信度 {{ Math.round(item.confidence_overall * 100) }}%</span>
              </n-space>
            </template>
            <p v-if="item.summary_one_liner" class="item-summary">📌 {{ item.summary_one_liner }}</p>
            <div v-if="highlights(item).length" class="item-highlights">
              <n-tag v-for="h in highlights(item)" :key="h" size="small" round :bordered="false" class="highlight-tag">{{ h }}</n-tag>
            </div>
            <n-descriptions :columns="2" size="small" bordered class="score-table">
              <n-descriptions-item v-for="(s, k) in item.scores || {}" :key="k" :label="dimLabels[k] || k">
                <n-progress :percentage="(s.value || 0) * 20" :height="18" :color="scoreColors[s.value] || '#999'" :border-radius="4" indicator-placement="inside">
                  {{ s.value }}/5 | {{ Math.round((s.confidence || 0) * 100) }}%
                </n-progress>
                <span class="score-reason">{{ s.reason?.slice(0, 60) || '' }}</span>
                <n-tag v-if="s.confidence < 0.6" type="warning" size="tiny">⚠低置信度</n-tag>
              </n-descriptions-item>
            </n-descriptions>
            <a v-if="item.url" :href="item.url" target="_blank" class="item-link">🔗 {{ item.url }}</a>
          </n-card>
        </template>

        <template v-if="mid.length">
          <h3 class="section-title mid">值得关注 ({{ mid.length }})</h3>
          <n-card v-for="item in mid" :key="item.id" size="small" class="item-card">
            <template #header>
              <n-space align="center" :wrap="false">
                <n-tag type="warning" size="small" :bordered="false">{{ item.recommend_level }}</n-tag>
                <span class="item-score">{{ item.score_total?.toFixed(1) }}</span>
                <span class="item-title">{{ item.title?.slice(0, 60) || '?' }}</span>
                <span v-if="item.confidence_overall" class="confidence">置信度 {{ Math.round(item.confidence_overall * 100) }}%</span>
              </n-space>
            </template>
            <p v-if="item.summary_one_liner" class="item-summary">📌 {{ item.summary_one_liner }}</p>
            <n-descriptions v-if="item.scores" :columns="2" size="small" bordered class="score-table">
              <n-descriptions-item v-for="(s, k) in item.scores" :key="k" :label="dimLabels[k] || k">
                <n-progress :percentage="(s.value || 0) * 20" :height="18" :color="scoreColors[s.value] || '#999'" :border-radius="4" indicator-placement="inside">
                  {{ s.value }}/5 | {{ Math.round((s.confidence || 0) * 100) }}%
                </n-progress>
                <span class="score-reason">{{ s.reason?.slice(0, 50) || '' }}</span>
              </n-descriptions-item>
            </n-descriptions>
            <a v-if="item.url" :href="item.url" target="_blank" class="item-link">🔗 {{ item.url }}</a>
          </n-card>
        </template>

        <template v-if="low.length">
          <n-collapse>
            <n-collapse-item :title="'暂不跟进 (' + low.length + ')'">
              <n-table :single-line="false" size="small">
                <thead><tr><th>标题</th><th>评分</th><th>理由</th></tr></thead>
                <tbody>
                  <tr v-for="item in low" :key="item.id">
                    <td>{{ item.title?.slice(0, 40) || '?' }}</td>
                    <td>{{ item.score_total?.toFixed(1) }}</td>
                    <td class="reason-cell">{{ item.summary_one_liner?.slice(0, 30) || '-' }}</td>
                  </tr>
                </tbody>
              </n-table>
            </n-collapse-item>
          </n-collapse>
        </template>
      </template>
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { NCard, NTag, NStatistic, NSpace, NSpin, NEmpty, NDivider, NCollapse, NCollapseItem, NTable, NDescriptions, NDescriptionsItem, NProgress } from 'naive-ui'
import { get } from '../api'

const loading = ref(true)
const items = ref<any[]>([])
const MAX = 20

const dimLabels: Record<string, string> = { business: '商业潜力', deploy: '落地难度', performance: '性能指标', compatibility: '业务兼容性' }
const scoreColors: Record<number, string> = { 1: '#d03050', 2: '#f0a020', 3: '#f0a020', 4: '#18a058', 5: '#18a058' }

const displayItems = computed(() => items.value.slice(0, MAX))
const high = computed(() => displayItems.value.filter(i => i.recommend_level === '强烈推荐'))
const mid = computed(() => displayItems.value.filter(i => i.recommend_level === '值得关注'))
const low = computed(() => displayItems.value.filter(i => ['暂不跟进', '不推荐'].includes(i.recommend_level)))

function highlights(item: any): string[] {
  let h = item.summary_highlights
  if (!h) return []
  if (typeof h === 'string') { try { h = JSON.parse(h) } catch { return [] } }
  return Array.isArray(h) ? h : []
}

onMounted(async () => {
  try {
    const data = await get<any>('/report/today')
    items.value = data.items || []
  } catch (e) {
    console.error('Failed to load report:', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.stats-row { display: flex; flex-wrap: wrap; }
.stat-card { min-width: 100px; }
.stat-high :deep(.n-statistic__content) { color: #d03050; }
.stat-mid :deep(.n-statistic__content) { color: #f0a020; }
.section-title { margin: 20px 0 12px; font-size: 18px; }
.section-title.high { color: #d03050; }
.section-title.mid { color: #f0a020; }
.item-card { margin-bottom: 14px; }
.item-score { font-size: 20px; font-weight: 700; color: #18a058; }
.item-title { font-weight: 500; }
.confidence { font-size: 12px; color: #999; }
.item-summary { margin: 0 0 8px; color: #333; }
.item-highlights { margin-bottom: 12px; }
.highlight-tag { margin: 2px 4px 2px 0; }
.score-table { margin: 8px 0; }
.score-reason { display: block; color: #888; font-size: 12px; margin-top: 2px; }
.item-link { display: inline-block; margin-top: 8px; color: #2080f0; word-break: break-all; }
.reason-cell { color: #888; font-size: 13px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
