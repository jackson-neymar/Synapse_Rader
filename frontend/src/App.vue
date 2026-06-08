<template>
  <n-config-provider :locale="zhCN" :date-locale="dateZhCN">
    <div class="app-container">
      <header class="app-header">
        <h1 class="app-title">Synapse_Rader</h1>
        <span class="app-subtitle">AI 技术情报雷达</span>
      </header>

      <n-tabs v-model:value="activeTab" type="line" animated>
        <n-tab-pane name="daily" tab="今日日报">
          <DailyReport />
        </n-tab-pane>
        <n-tab-pane name="history" tab="历史检索">
          <HistorySearch />
        </n-tab-pane>
        <n-tab-pane name="trigger" tab="手动触发">
          <TriggerRun />
        </n-tab-pane>
      </n-tabs>
    </div>
  </n-config-provider>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
  NConfigProvider,
  NTabs,
  NTabPane,
  zhCN,
  dateZhCN,
} from 'naive-ui'
import DailyReport from './views/DailyReport.vue'
import HistorySearch from './views/HistorySearch.vue'
import TriggerRun from './views/TriggerRun.vue'

const activeTab = ref('daily')
</script>

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
    'Helvetica Neue', Arial, sans-serif;
  background: #f5f7fa;
}

.app-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 24px;
}

.app-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding: 20px 0 8px;
}

.app-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: #1a1a2e;
}

.app-subtitle {
  font-size: 14px;
  color: #888;
}
</style>
