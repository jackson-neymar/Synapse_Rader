import json


def build_analysis_prompt(item: dict, rag_context: list[dict]) -> str:
    """Build a complete analysis prompt for a single intelligence item."""

    prompt = f"""你是一个资深AI技术分析师。对以下技术情报进行深度分析，输出严格JSON格式。

## 评分标准（1-5分锚定）

### 商业潜力（权重默认0.45）
- 5: 解决明确商业痛点，市场热度极高（GitHub 3天5k+ star，行业广泛关注）
- 4: 市场热度高，应用场景清晰
- 3: 有一定应用前景
- 2: 应用场景模糊
- 1: 偏学术研究，暂无商业场景

### 落地难度（权重默认0.20）
- 5: 开源完整，文档齐全含详细README，pip/brew即装即用
- 4: 有代码文档较全，部署成本低
- 3: 有代码但文档不足
- 2: 仅有部分代码或demo
- 1: 无代码/仅论文

### 性能指标（权重默认0.20）
- 5: 多项benchmark SOTA，经第三方验证
- 4: 部分指标SOTA
- 3: 与现有方案持平
- 2: 弱于现有方案
- 1: 无性能数据

### 业务兼容性（权重默认0.15）
- 5: 与公司现有技术栈和业务方向高度匹配
- 4: 大部分匹配
- 3: 部分匹配
- 2: 需要较大适配
- 1: 不匹配

## 上下文自适应权重调整

先判断情报类型，自动调整权重：
- 开源工具/框架 → 落地难度+0.10，商业潜力-0.05
- 学术论文 → 性能指标+0.10，商业潜力-0.05
- 产品/商业动态 → 商业潜力+0.10，性能指标-0.10
- 其他 → 使用默认权重

## 评分公式
总分 = 商业潜力×W_business + 落地难度×W_deploy + 性能指标×W_perf + 业务兼容性×W_compat

## 推荐等级
- >=4.0: 强烈推荐
- 3.0-3.9: 值得关注
- 2.0-2.9: 暂不跟进
- <2.0: 不推荐

## Few-shot 示例

高分示例：
{{
  "summary_one_liner": "轻量级Multi-Agent协作框架，3天5k star",
  "summary_highlights": ["10+ Agent并行协作延迟<100ms", "内置记忆共享模块", "社区活跃度高"],
  "summary_comparison": "相比AutoGen的对话驱动，采用共享内存机制，延迟降低40%",
  "weight_adjustment": "open_source_tool",
  "scores": {{
    "business": {{"value": 5, "confidence": 0.9, "reason": "GitHub 3天5k star，解决Agent协作痛点"}},
    "deploy": {{"value": 4, "confidence": 0.85, "reason": "pip install即用，文档完善"}},
    "performance": {{"value": 4, "confidence": 0.7, "reason": "延迟<100ms优秀，但缺大规模benchmark"}},
    "compatibility": {{"value": 4, "confidence": 0.9, "reason": "与Agent业务方向匹配，Python技术栈兼容"}}
  }},
  "score_total": 4.35,
  "confidence_overall": 0.84,
  "recommend_level": "强烈推荐"
}}

## RAG 历史上下文（相似历史情报）

{json.dumps(rag_context[:5], ensure_ascii=False, indent=2) if rag_context else "（无历史数据）"}

## 当前待分析情报

- 标题: {item.get('title', '')}
- URL: {item.get('url', '')}
- 描述: {item.get('description', '')}

## 输出要求

严格JSON，包含所有以下字段：
summary_one_liner, summary_highlights(3), summary_comparison, weight_adjustment,
scores(business/deploy/performance/compatibility 每维含 value/confidence/reason),
score_total, confidence_overall, recommend_level, rag_context_used"""

    return prompt
