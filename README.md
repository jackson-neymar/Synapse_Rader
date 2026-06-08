# Synapse_Rader

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Vue-3.5-brightgreen?logo=vue.js" alt="Vue">
  <img src="https://img.shields.io/badge/LangGraph-0.3-orange" alt="LangGraph">
  <img src="https://img.shields.io/badge/DeepSeek-v4--pro-purple" alt="DeepSeek">

</p>

<p align="center">
  <b>基于 LangGraph 多智能体协作的 AI 技术情报自动监控与辅助决策系统</b>
</p>

<p align="center">
  每日自动采集 · 智能筛选去噪 · 四维 LLM 评分 · RAG 历史对比 · 飞书推送 · Web 控制台
</p>

2025-2026 年，AI 领域进入技术爆发期。多模态大模型、AI Agent、开源工具链每天都有重大更新——GitHub 每日诞生数百个 AI 项目，arXiv 每日发布数百篇论文，HF Mirror 和 Hacker News 每天涌现新的 AI 项目和讨论。技术迭代速度远超个人追踪能力。

**Synapse_Rader** 是一个 AI 驱动的技术情报雷达系统。它像一个不知疲倦的 AI 分析师团队，每天自动完成：

1. **采集** — 从 GitHub、HF Mirror、Hacker News、arXiv 四大信源并行抓取最新 AI 动态
2. **筛选** — 关键词初筛 + LLM 分类 + LLM 去噪三级过滤，从 80+ 条原始信息中精选 10-20 条高质量情报
3. **分析** — 每条情报由 LLM 进行四维评分（商业潜力、落地难度、性能指标、业务兼容性），附带置信度和详细评分理由
4. **对比** — 基于 ChromaDB 向量检索，自动关联历史相似情报，追踪技术演进脉络
5. **报告** — 自动生成结构化 Markdown 日报，区分"强烈推荐 / 值得关注 / 暂不跟进"
6. **推送** — 每日 8:00 准时推送到飞书群消息（@all）+ 飞书文档完整报告

**目标：让技术决策者每天早上花 5 分钟，就能掌握前一日 AI 圈真正值得关注的一切。**


## 多智能体架构

Synapse_Rader 的核心是一个基于 **LangGraph StateGraph** 编排的多智能体流水线。5 个独立 Agent 各司其职，通过共享 State 串联协作：

```
                     ┌──────────────────────────────────────┐
                     │          Synapse_Rader 多智能体系统     │
                     └──────────────────────────────────────┘

  7:00 定时触发 / 手动触发
          │
          ▼
  ┌───────────────┐     ┌─────────────────────────────────────┐
  │  Collector    │────▶│  5 协程并行调用 5 个 Fetcher          │
  │  采集智能体    │     │  GitHub / HF Mirror / Hacker News    │
  └───────┬───────┘     │  / arXiv                             │
          │             │  → SHA256 去重 → 写入 raw_items 表    │
          │             └─────────────────────────────────────┘
          │  ~80 条原始条目
          ▼
  ┌───────────────┐     ┌─────────────────────────────────────┐
  │  Curator      │────▶│  L1 关键词过滤 (规则引擎, 毫秒级)      │
  │  策展智能体    │     │  L2 LLM 分类 (领域归属 + 打标签)       │
  └───────┬───────┘     │  L3 LLM 去噪 (剔除灌水/营销)          │
          │             │  ~80 → ~45 → ~25 → ~15 条             │
          │ ~15 条精选情报  └─────────────────────────────────────┘
          ▼
  ┌───────────────┐     ┌─────────────────────────────────────┐
  │  Analyst      │────▶│  每条情报: RAG检索历史top-5           │
  │  分析智能体    │     │  → LLM 四维评分 (自适应权重)          │
  └───────┬───────┘     │  → 即时写入 ChromaDB 向量库            │
          │             │  8 并发, 15条 < 3分钟                 │
          │ 每条含评分+置信度  └─────────────────────────────────────┘
          ▼
  ┌───────────────┐     ┌─────────────────────────────────────┐
  │  Editor       │────▶│  按推荐等级分组                       │
  │  主编智能体    │     │  生成结构化 Markdown 日报              │
  └───────┬───────┘     │  概览→强推→关注→暂不跟进→全量列表       │
          │             └─────────────────────────────────────┘
          │ 完整日报 Markdown
          ▼
  ┌───────────────┐     ┌─────────────────────────────────────┐
  │  Dispatcher   │────▶│  飞书 Bot 群消息 (@all, ≤10KB)       │
  │  分发智能体    │     │  飞书文档 (完整日报)                   │
  └───────────────┘     │  写入 daily_reports 表                │
                        └─────────────────────────────────────┘
          │
          ▼
    8:00 飞书推送送达
```


## 核心功能

### 🔍 多信源自动采集

| 信源 | 采集范围 | 数量 | 方式 |
|------|---------|------|------|
| GitHub | Python 语言 Trending + 每日新项目 | Top 20×2 | GitHub REST API |
| HF Mirror | HuggingFace 热门模型 (国内镜像) | Top 20 | hf-mirror.com API |
| Hacker News | AI/LLM/Agent 相关高热度讨论 | Top 20 | HN Algolia API |
| arXiv | cs.AI / cs.CL / cs.CV / cs.LG (近3日) | Top 20 | arXiv API + feedparser |

- 4 源并行采集，总耗时 < 60 秒
- SHA256(URL+title) 去重，准确率 100%
- 单源故障不影响其他信源，失败源自动记录到日志

### 🧠 四维 LLM 评分体系

每条情报由 DeepSeek-v4-pro 进行四维评分，每个维度 1-5 分 + 置信度 + 评分理由：

| 维度 | 默认权重 | 衡量什么 |
|------|---------|---------|
| 商业潜力 | 0.45 | 市场热度、应用前景、解决什么商业痛点 |
| 落地难度 | 0.20 | 代码开源程度、文档质量、部署成本 |
| 性能指标 | 0.20 | Benchmark 表现、是否有 SOTA 声明 |
| 业务兼容性 | 0.15 | 与公司技术栈和业务方向的匹配度 |

**上下文自适应权重** — LLM 先判断情报类型，自动调整权重：
- 开源工具/框架 → 落地难度 +0.10
- 学术论文 → 性能指标 +0.10
- 产品/商业动态 → 商业潜力 +0.10

**评分增强机制：**
- **置信度标注** — 每题附带 0.0-1.0 置信度，< 0.6 标注 ⚠️ 低置信度
- **Few-shot 锚定** — Prompt 含 3 个标准答案示例，防止评分漂移
- **可复现验证** — 同一情报重复评分 3 次，标准差 < 0.5

### 📜 RAG 历史对比增强

- **混合检索**: 向量语义相似度 (0.7) + BM25 关键词匹配 (0.3)
- **即时索引**: 每条分析完成立即写入 ChromaDB，同批次后续条目即刻受益
- **空库降级**: 首次运行 ChromaDB 为空时，系统正常降级不报错

### 📋 结构化日报

日报包含 5 个固定板块，Markdown 格式渲染：

1. **今日概览** — 采集/筛选/推荐数量一览表
2. **强烈推荐** (≥4.0分) — 完整评分明细 + 置信度 + RAG 历史对比 + 原始链接
3. **值得关注** (3.0-3.9分) — 同上结构，默认折叠
4. **暂不跟进** (2.0-2.9分) — 精简表格展示
5. **今日采集全量** — 完整列表，支持筛选/搜索/分页

### 📨 飞书多渠道推送

- **群消息** — 每日 8:00 @all，概览 + 强烈推荐摘要（Card 消息，≤10KB）
- **飞书文档** — 完整日报 Markdown，自动创建，团队可见

### 🌐 Web 控制台

| 页面 | 路径 | 功能 |
|------|------|------|
| 今日日报 | `/` | 概览卡片 + 可展开情报卡片（评分条形图/置信度标记）+ 全量列表 |
| 历史检索 | `/history` | 日期/分类/评分/关键词多条件检索 + 分页 + 详情展开 |
| 手动触发 | `/trigger` | 一键触发日报流程 + 5 节点实时进度条 + 执行历史日志 |


## 技术栈

```
┌────────────────┬──────────────────┬─────────────────────┐
│     前端        │      后端         │      基础设施         │
│                │                  │                     │
│  Vue 3         │  FastAPI         │  SQLite             │
│  Vite 5        │  LangGraph 1.2   │  ChromaDB           │
│  TypeScript    │  DeepSeek-v4-pro │  APScheduler        │
│  Naive UI      │  SQLAlchemy 2.x  │  lark-oapi          │
│                │  httpx           │                     │
└────────────────┴──────────────────┴─────────────────────┘
```

**选型原则：** Python 优先 · 异步优先 · MVP 够用不铺张 · 单仓库可部署 · 预留平滑升级路径

| 组件 | MVP | 升级路径 |
|------|-----|---------|
| 数据库 | SQLite | PostgreSQL |
| 向量库 | ChromaDB (嵌入) | Qdrant |
| LLM | DeepSeek-v4-pro | 多模型混合评估 |
| 调度 | APScheduler (内嵌) | Celery + Redis |
| 部署 | 单机直跑 | Kubernetes |


## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+

### 1. 克隆仓库

```bash
git clone https://github.com/your-org/synapse_rader.git
cd synapse_rader
```

### 2. 配置环境变量

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`，填入必要配置：

```env
# DeepSeek API (必需)
DEEPSEEK_API_KEY=sk-xxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# Embedding 模型（本地 bge-large-zh-v1.5）
EMBEDDING_BACKEND=local
EMBEDDING_MODEL=/path/to/bge-large-zh-v1.5
EMBEDDING_DEVICE=cpu

# 飞书应用 (推送必需，可后配)
FEISHU_APP_ID=cli_xxxxxxxx
FEISHU_APP_SECRET=xxxxxxxx
FEISHU_CHAT_ID=oc_xxxxxxxx

# 数据库 (可选，以下为默认值)
DATABASE_URL=sqlite+aiosqlite:///../data/synapse_rader.db
CHROMA_PERSIST_PATH=../data/chroma
```

### 3. 手动启动 (开发模式)

```bash
# 后端
conda activate aiagent
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 前端 (新终端)
cd frontend
npm install
npm run dev
```


## 项目结构

```
synapse_rader/
├── backend/
│   ├── main.py                    # FastAPI 入口 + lifespan 事件
│   ├── settings.py                # 配置管理 (17 环境变量)
│   ├── scheduler.py               # APScheduler 定时任务 (7:00采集, 8:00推送)
│   ├── api/
│   │   ├── reports.py             # GET /api/report/today, /api/report/{date}
│   │   ├── items.py               # GET /api/items (多条件检索)
│   │   ├── trigger.py             # POST /api/trigger/daily-run + 状态查询
│   │   └── stats.py               # GET /api/stats (趋势统计)
│   ├── graph/
│   │   ├── state.py               # AgentState TypedDict 定义
│   │   ├── graph.py               # LangGraph StateGraph 构建 + 编译
│   │   ├── nodes/
│   │   │   ├── collector.py       # Collector Agent — 4源并行采集
│   │   │   ├── curator.py         # Curator Agent — L1/L2/L3 三级过滤
│   │   │   ├── analyst.py         # Analyst Agent — 四维评分 + RAG 检索
│   │   │   ├── editor.py          # Editor Agent — 日报生成
│   │   │   └── dispatcher.py      # Dispatcher Agent — 飞书推送
│   │   └── tools/
│   │       ├── fetchers.py        # 5 个信源采集器 (GitHub×2/HF Mirror/HN/arXiv)
│   │       ├── feishu.py          # 飞书 Bot 消息 + 文档创建
│   │       ├── llm.py             # DeepSeek LLM 封装 (4 种温度配置)
│   │       ├── rag.py             # ChromaDB 混合检索 + Embedding
│   │       ├── prompts.py         # 分析/分类/日报 Prompt 模板 (含 few-shot)
│   │       ├── storage.py         # 去重 + 批量入库 + 状态更新
│   │       └── embedding/         # 可替换 Embedding 后端 (local/openai)
│   ├── models/
│   │   └── database.py            # SQLAlchemy ORM (4 表: raw_items/analyzed_items/
│   │                               #   daily_reports/execution_logs)
│   └── requirements.txt
│
├── frontend/                       # Vue 3 + Vite + TypeScript SPA
│   └── src/
│       ├── App.vue                 # 顶部导航 + Tab 切换
│       ├── api/index.ts            # API 请求封装 (GET/POST)
│       ├── views/
│       │   ├── DailyReport.vue     # 今日日报页
│       │   ├── HistorySearch.vue   # 历史检索页
│       │   └── TriggerRun.vue      # 手动触发页 + 实时进度
│       └── components/
│           ├── ReportCard.vue      # 情报卡片 (展开/折叠 + 评分条形图)
│           ├── ScoreBar.vue        # 四维评分条形图组件
│           ├── FilterBar.vue       # 多条件筛选栏
│           └── RunStatus.vue       # 5 节点执行进度组件
│
├── config/
│   └── keywords.yaml               # L1 关键词过滤配置 (34 个中英文关键词)
├── data/                           # SQLite + ChromaDB 持久化目录
├── logs/                           # 执行日志
└── README.md
```


## 使用指南

### 日常自动化流程

```
每日 7:00  APScheduler 触发采集分析任务
     ↓     Collector → Curator → Analyst → Editor
     ↓     5源采集 → 三级过滤 → 四维评分 → 日报生成
     ↓     (预期耗时 15-25 分钟)
每日 8:00  APScheduler 触发推送任务
     ↓     Dispatcher → 飞书群 @all + 飞书文档
     ↓
   8:00    团队成员在飞书收到日报
```

### 手动触发

当周会或紧急需要最新情报时，打开 Web 控制台 → 手动触发 → 点击"立即执行日报流程"，实时看到 5 个节点的执行进度：

```
● collector    ████████████████  ✅ 已完成 (45s)
● curator      ████████████████  ✅ 已完成 (12s)
● analyst      ██████████░░░░░░  🔄 运行中 (1m32s)
○ editor                          ⏳ 等待中
○ dispatcher                      ⏳ 等待中
```

### 历史检索

在 `/history` 页面按日期范围、分类、推荐等级、评分范围、关键词组合检索，秒级响应（< 1 秒 / 1000 条数据），支持分页和详情展开。


## 许可证

MIT License


<p align="center">
  <b>Synapse_Rader</b> — 让 AI 帮你追踪 AI 的进化
</p>
