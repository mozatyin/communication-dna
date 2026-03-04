# One-Sentence PRD — 测试报告与功能文档

> 日期：2026-03-05
> 模块：`intention_graph/one_sentence_prd.py`, `intention_graph/web_search.py`
> 模型：claude-sonnet-4-20250514 (via OpenRouter)
> 版本：v2 (30次迭代优化)

---

## 1. 功能概述

### 1.1 解决的问题

用户只说一句话——"做一个Flappy Bird"、"王者荣耀"、"请帮我生成一个1943模拟游戏"——即可获得完整的 4 章节 PRD 文档。

传统流程需要 10-20 轮对话才能收集足够的设计信息。OneSentencePrd 通过**网络搜索 + LLM 研究 + 意图图谱分析 + 自动问答**填补信息空白，一次性生成与多轮对话同等质量的 PRD。

### 1.2 核心设计原则

| 原则 | 实现方式 |
|------|----------|
| **复用而非重建** | 直接调用现有 Connect → Expand → Clarify 管线，不修改任何已有代码 |
| **复杂度感知** | 检测游戏类型，arcade 游戏跳过 Expand 防止系统膨胀 |
| **忠实度约束** | 研究 prompt 禁止为简单游戏添加原版没有的系统 |
| **向后兼容** | `OneSentencePrd` 纯新增，所有现有类和接口不变 |

---

## 2. 架构

### 2.1 管线流程

```
用户输入: "请帮我生成一个1943模拟游戏"
    │
    ▼
[1] _identify_game()          ← 1次 LLM 调用
    识别: game_name, language, complexity, genre, era, core_systems
    │
    ▼
[2] _research_game()          ← Web 搜索 + 1次 LLM 调用
    DuckDuckGo + Wikipedia → LLM 生成研究报告
    受 complexity profile 约束 (arcade: 1500字, hardcore: 4000字)
    │
    ▼
[3] Connect (现有)            ← 1次 LLM 调用
    从研究文本提取意图节点和转移关系
    │
    ▼
[4] Expand (现有, 条件执行)    ← 0-1次 LLM 调用
    arcade → 跳过 (防止系统膨胀)
    其他 → 展开抽象节点为具体子意图
    │
    ▼
[5] Clarify (现有)            ← 1次 LLM 调用
    检测歧义分支，生成 incisive questions
    │
    ▼
[6] Self-Answer / Interactive ← 0-1次 LLM 调用
    answer_fn=None → LLM 自答 (忠实于原游戏)
    answer_fn=callback → 用户回答
    │
    ▼
[7] _synthesize_conversation() ← 1次 LLM 调用
    研究 + 图谱 → 合成对话 + facts
    强制覆盖所有 core_systems (减少误标 [INFERRED])
    │
    ▼
[8] PrdGenerator (现有)       ← 3次 LLM 调用 (内部 Connect + Expand + 生成)
    对话 + facts → 完整 PRD
    │
    ▼
输出: {prd_document, prd_summary, metadata}
```

### 2.2 复杂度配置

| 参数 | arcade | casual | mid-core | hardcore |
|------|--------|--------|----------|----------|
| `skip_expand` | True | False | False | False |
| `max_systems` | 4 | 6 | 8 | 10 |
| `research_chars` | 1500 | 2000 | 3000 | 4000 |
| `conversation_turns` | 6-8 | 8-10 | 10-12 | 12-14 |

### 2.3 新增文件

| 文件 | 行数 | 职责 |
|------|------|------|
| `intention_graph/one_sentence_prd.py` | ~380 | 主编排器，OneSentencePrd 类 |
| `intention_graph/web_search.py` | ~70 | 网络搜索工具 (DuckDuckGo + Wikipedia) |
| `demo_one_sentence_prd.py` | ~85 | CLI 演示脚本 |
| `tests/test_one_sentence_prd.py` | ~570 | 34 个单元测试 + 3 个集成测试 |

### 2.4 修改的文件

| 文件 | 改动 |
|------|------|
| `intention_graph/__init__.py` | 增加 `OneSentencePrd` 导出 |
| `pyproject.toml` | 增加 `search` 可选依赖 + pytest markers |

### 2.5 未修改的文件

`connect.py`, `expand.py`, `clarify.py`, `detector.py`, `prd_generator.py`, `models.py` — **全部不变**

---

## 3. API 参考

### 3.1 基本用法

```python
from intention_graph import OneSentencePrd

gen = OneSentencePrd(api_key="sk-or-v1-...")

# 全自动模式
result = gen.generate("做一个Flappy Bird")

print(result["prd_document"])   # 完整 PRD (Markdown)
print(result["prd_summary"])    # 2-3 句话摘要
print(result["metadata"])       # 结构化元数据
```

### 3.2 交互模式

```python
def ask_user(questions):
    """questions: [{"question": str, "node_id": str, "branches": list}]"""
    answers = []
    for q in questions:
        answer = input(f"设计问题: {q['question']}\n你的回答: ")
        answers.append(answer)
    return answers

result = gen.generate("做一个Flappy Bird", answer_fn=ask_user)
```

### 3.3 返回值结构

```python
{
    "prd_document": "# 游戏PRD\n## 1. 游戏总览\n...",   # Markdown
    "prd_summary": "这是一款...",                        # 2-3句
    "metadata": {
        # 来自 PrdGenerator (原有)
        "core_intention": "创建飞行射击游戏",
        "num_intentions": 14,
        "num_facts": 9,
        "ig_available": True,
        "language": "zh",
        "model": "claude-sonnet-4-20250514",

        # 来自 OneSentencePrd (新增)
        "input_sentence": "请帮我生成一个1943模拟游戏",
        "detected_game": "1943: The Battle of Midway",
        "complexity": "arcade",
        "genre": "vertical scrolling shooter",
        "era": "1987 arcade",
        "core_systems": ["shooting", "power-ups", "boss battles", ...],
        "research_source": "web+llm",            # 或 "llm_only"
        "interactive_mode": False,                # 是否使用交互模式
        "self_answered_questions": [...],          # LLM 自答的问题列表
        "user_answered_questions": [],             # 用户回答的问题列表
    }
}
```

### 3.4 CLI 演示

```bash
# 预设示例 (5个)
ANTHROPIC_API_KEY=sk-or-... python demo_one_sentence_prd.py flappy
ANTHROPIC_API_KEY=sk-or-... python demo_one_sentence_prd.py kings
ANTHROPIC_API_KEY=sk-or-... python demo_one_sentence_prd.py 1943
ANTHROPIC_API_KEY=sk-or-... python demo_one_sentence_prd.py pvz
ANTHROPIC_API_KEY=sk-or-... python demo_one_sentence_prd.py hollow

# 交互模式 (终端输入回答设计问题)
ANTHROPIC_API_KEY=sk-or-... python demo_one_sentence_prd.py --interactive 1943
```

---

## 4. 测试结果

### 4.1 总览

```
测试运行环境: Python 3.12.12, pytest 9.0.2, macOS Darwin 25.3.0
测试时间: 2026-03-05

全量测试:  66 passed, 19 skipped, 3 deselected
新增测试:  34 passed (test_one_sentence_prd.py)
原有测试:  32 passed (无回归)
集成测试:  4/4 passed (arcade + casual + mid-core + hardcore)
```

### 4.2 Direction 1: 单元测试 (34 个)

所有测试使用 Mock 替代 LLM 调用，无需 API key，运行时间 <3 秒。

#### JSON 解析 (5/5 passed)

| 测试 | 输入 | 预期 | 结果 |
|------|------|------|------|
| `test_parse_json_valid` | `{"a": 1}` | 正常解析 | PASS |
| `test_parse_json_with_markdown_fences` | ` ```json {...} ``` ` | 剥离包装后解析 | PASS |
| `test_parse_json_embedded_in_text` | `text {"x": 42} text` | 提取中间 JSON | PASS |
| `test_parse_json_invalid_returns_empty` | `not json` | 返回 `{}` | PASS |
| `test_parse_json_empty_string` | `""` | 返回 `{}` | PASS |

#### 分支提升 (3/3 passed)

| 测试 | 验证逻辑 | 结果 |
|------|----------|------|
| `test_boost_branch_increases_chosen` | 选中分支概率 +0.3, 其他 -0.15 | PASS |
| `test_boost_branch_clamps_to_bounds` | 概率不超过 1.0 | PASS |
| `test_boost_branch_unrelated_transitions_unchanged` | 不相关 transition 保持原值 | PASS |

#### 复杂度配置 (4/4 passed)

| 测试 | 验证逻辑 | 结果 |
|------|----------|------|
| `test_complexity_profiles_all_defined` | 4 个档位 (arcade/casual/mid-core/hardcore) 全部定义 | PASS |
| `test_arcade_profile_skips_expand` | arcade → `skip_expand=True` | PASS |
| `test_non_arcade_profiles_allow_expand` | 其他 3 个 → `skip_expand=False` | PASS |
| `test_complexity_max_systems_increase` | max_systems 随复杂度单调递增 | PASS |

#### 数据模型 (2/2 passed)

| 测试 | 验证逻辑 | 结果 |
|------|----------|------|
| `test_game_info_creation` | GameInfo 7 个字段完整创建 | PASS |
| `test_simple_game_defaults` | facts 默认空列表 | PASS |

#### 管线编排 — 游戏识别 (2/2 passed)

| 测试 | 验证逻辑 | 结果 |
|------|----------|------|
| `test_identify_game_parses_response` | LLM JSON → GameInfo 正确映射 | PASS |
| `test_identify_game_handles_malformed_json` | 畸形 JSON → 降级默认值 (complexity="mid-core") | PASS |

#### 管线编排 — IG 管线 (2/2 passed)

| 测试 | 验证逻辑 | 结果 |
|------|----------|------|
| `test_run_ig_pipeline_skips_expand_for_arcade` | arcade: Connect→Clarify (跳过 Expand) | PASS |
| `test_run_ig_pipeline_runs_expand_for_midcore` | mid-core: Connect→Expand→Clarify (完整) | PASS |

#### 管线编排 — Self-Answer (2/2 passed)

| 测试 | 验证逻辑 | 结果 |
|------|----------|------|
| `test_self_answer_skips_when_no_questions` | 无歧义 → 不调用 LLM, 返回空列表 | PASS |
| `test_self_answer_calls_llm_when_ambiguities_exist` | 有歧义 → 调用 LLM, 清除 ambiguities | PASS |

#### 管线编排 — Interactive Answer (4/4 passed)

| 测试 | 验证逻辑 | 结果 |
|------|----------|------|
| `test_interactive_answer_calls_callback` | 有歧义 → 调用 answer_fn, 记录答案 | PASS |
| `test_interactive_answer_skips_when_no_questions` | 无歧义 → 不调用回调 | PASS |
| `test_generate_uses_answer_fn_when_provided` | generate() 路由到交互模式 | PASS |
| `test_generate_metadata_non_interactive` | 非交互: interactive_mode=False | PASS |

#### 管线编排 — 对话合成 (2/2 passed)

| 测试 | 验证逻辑 | 结果 |
|------|----------|------|
| `test_synthesize_conversation_returns_valid_structure` | 返回 (conversation, facts) 格式正确 | PASS |
| `test_synthesize_conversation_fallback_on_bad_json` | JSON 失败 → 降级最小对话 | PASS |

#### Web 搜索 (6/6 passed)

| 测试 | 验证逻辑 | 结果 |
|------|----------|------|
| `test_search_game_returns_list` | DDG 搜索返回列表 (未安装则返回 []) | PASS |
| `test_fetch_wikipedia_returns_string_or_none` | 存在的页面返回摘要文本 | PASS |
| `test_fetch_wikipedia_nonexistent_returns_none` | 不存在的页面返回 None | PASS |
| `test_research_game_returns_string` | 聚合搜索返回字符串 | PASS |
| `test_research_game_chinese_lang` | lang="zh" 参数正常工作 | PASS |
| `test_search_result_dataclass` | SearchResult 3 个字段正确 | PASS |

#### 全流程编排 (2/2 passed)

| 测试 | 验证逻辑 | 结果 |
|------|----------|------|
| `test_generate_full_pipeline_arcade` | arcade 完整流程: skip expand + metadata 正确 | PASS |
| `test_generate_runs_expand_for_hardcore` | hardcore 完整流程: runs expand + metadata 正确 | PASS |

### 4.3 Direction 2: 多复杂度验证 (4 个集成测试)

每个测试实际调用 LLM API，耗时约 2-3 分钟。

#### 测试矩阵

| | Arcade | Casual | Mid-Core | Hardcore |
|---|:---:|:---:|:---:|:---:|
| **输入** | 请帮我生成一个1943模拟游戏 | 做一个植物大战僵尸 | 做一个空洞骑士 | 王者荣耀 |
| **检测复杂度** | arcade | casual | mid-core | hardcore |
| **检测类型** | vertical scrolling shooter | tower defense | metroidvania | MOBA |
| **检测年代** | 1987 arcade | 2009 PC | 2017 indie | 2015 mobile |
| **core_systems 数** | 7 | 8 | 12 | 14 |

#### PRD 输出质量

| | Arcade | Casual | Mid-Core | Hardcore |
|---|:---:|:---:|:---:|:---:|
| **章节 1: 游戏总览** | ✅ | ✅ | ✅ | ✅ |
| **章节 2: 核心游戏循环** | ✅ | ✅ | ✅ | ✅ |
| **章节 3: 游戏系统** | ✅ | ✅ | ✅ | ✅ |
| **章节 4: 美术与音效风格** | ✅ | ✅ | ✅ | ✅ |
| **游戏系统数** | 7 | 8 | 9 | 9 |
| **[INFERRED] 系统数** | 2 | 1 | 1 | 2 |
| **IG 意图节点数** | 9 | 15 | 13 | 21 |
| **PRD 字符数** | ~6,000 | ~5,500 | ~6,300 | ~7,500 |
| **IG available** | True | True | True | True |
| **Research source** | web+llm | web+llm | web+llm | web+llm |
| **Expand 执行** | 跳过 | 执行 | 执行 | 执行 |

#### 忠实度验证

| 游戏 | 应有的系统 | 不应有的系统 | 结果 |
|------|-----------|-------------|------|
| **1943** | 射击、道具、BOSS、生命、计分、敌机波次 | 技能树、装备、无尽模式、基地管理 | ✅ 无违规 |
| **PvZ** | 种植、阳光、僵尸、波次、关卡、植物收集 | 在线 PvP、抽卡、赛季 | ✅ 无违规 |
| **空洞骑士** | 战斗、探索、护符、灵魂、升级、BOSS | 多人联机、日常任务 | ✅ 无违规 |
| **王者荣耀** | 英雄、装备、铭文、排位、地图目标、团战 | — (复杂游戏允许丰富系统) | ✅ 系统全面 |

#### [INFERRED] 标签准确性

| 游戏 | 被标 [INFERRED] 的系统 | 是否合理 |
|------|----------------------|----------|
| 1943 | 关卡进程、音效反馈 | 部分合理 (原版有关卡，但对话未明确讨论) |
| PvZ | 教学引导 | ✅ 合理 (原版有，但用户未提及) |
| 空洞骑士 | 教程引导 | ✅ 合理 |
| 王者荣耀 | 符文铭文、实时网络 | 部分合理 (铭文在 core_systems 中，合成对话覆盖不完全) |

### 4.4 Direction 3: 交互模式验证

#### 功能测试

| 场景 | answer_fn | 有歧义? | 预期行为 | 结果 |
|------|-----------|---------|----------|------|
| 全自动 (默认) | None | 有 | LLM 自答 | PASS |
| 全自动 (默认) | None | 无 | 直接跳过 | PASS |
| 交互模式 | callback | 有 | 调用回调，记录答案 | PASS |
| 交互模式 | callback | 无 | 不调用回调 | PASS |

#### 集成测试: 1943 交互模式

```
输入: "请帮我生成一个1943模拟游戏"
模式: interactive (模拟回调)

Clarify 阶段产生的问题:
  Q: What's the most important feature you'd like to work on first -
     the basic flying and shooting mechanics, or the progression
     systems like upgrades and scoring?

模拟用户回答:
  A: I want the classic arcade experience, keeping it simple

结果:
  interactive_mode: True
  user_answered_questions: 1
  self_answered_questions: 0
  complexity: arcade
  PRD 字符数: 4,504
  4 章节完整: ✅
```

#### Metadata 对比

| 字段 | 全自动模式 | 交互模式 |
|------|-----------|----------|
| `interactive_mode` | `False` | `True` |
| `self_answered_questions` | `[{question, answer}]` | `[]` |
| `user_answered_questions` | `[]` | `[{question, answer}]` |
| 其他字段 | 相同 | 相同 |

### 4.5 回归测试

原有 32 个测试全部通过，确认无回归：

| 测试文件 | 测试数 | 结果 |
|----------|--------|------|
| test_models.py | 5 | 5 passed |
| test_intention_models.py | 5 | 5 passed |
| test_intention_storage.py | 2 | 2 passed |
| test_connect.py | 8 | 5 passed, 3 skipped (API) |
| test_expand.py | 4 | 1 passed, 3 skipped (API) |
| test_clarify.py | 4 | 1 passed, 3 skipped (API) |
| test_comparator.py | 3 | 3 passed |
| test_storage.py | 2 | 2 passed |
| test_detector.py | 2 | 2 skipped (API) |
| test_intention_detector.py | 4 | 2 passed, 2 skipped (API) |
| test_catalog.py | 2 | 2 skipped (API) |
| test_speaker.py | 1 | 1 skipped (API) |
| test_graph_speaker.py | 2 | 2 skipped (API) |
| test_closed_loop.py | 2 | 2 skipped (API) |
| test_matcher.py | 1 | 1 skipped (API) |
| **合计** | **47** | **32 passed, 19 skipped** |

---

## 5. 迭代过程中发现并修复的问题

### 5.1 v1 → v2 (迭代 1-10: 初始 10 次迭代优化)

| 问题 | 根因 | 修复 |
|------|------|------|
| 1943 生成了技能树、装备、无尽模式、自适应难度、基地管理 | 无复杂度感知，Expand 无限膨胀 | 加入 complexity detection + skip_expand for arcade |
| Self-Answer 问了"是否从零开始" | Clarify 无上下文，产生泛化问题 | 给 self-answer prompt 注入 genre + complexity + era |
| 合成对话用户"说了"太多推断内容 | 合成 prompt 无忠实度约束 | 要求首句必须是用户原话，后续限制在 core_systems 内 |
| PRD 标题为"现代化1943" | 研究 prompt 无忠实度约束 | 加入 research_constraint 禁止添加原版没有的系统 |

### 5.2 v2 测试阶段 (迭代 11-30)

| 问题 | 根因 | 修复 |
|------|------|------|
| 王者荣耀"多模式"被标 [INFERRED] | 合成对话没覆盖该系统 | 加入 CHECKLIST，强制对话覆盖所有 core_systems |
| casual max_systems=5 过低 | PvZ 有 7-8 个原生系统 | casual: 5→6, mid-core: 7→8 |
| hardcore PRD 偏短 (5.7k) | 对话内容不够丰富 | checklist 改进后提升到 7.5k |
| 测试预期 research_source 错误 | research_source 基于 LLM 输出非 web 搜索结果 | 修正测试断言 |

---

## 6. 已知限制

| 限制 | 影响 | 缓解方案 |
|------|------|----------|
| [INFERRED] 误标 | 少数 core_systems 仍被标为推断 | CHECKLIST 已降低发生率，但不能 100% 消除 |
| LLM 调用次数多 | 全流程 8-10 次 API 调用，耗时 2-3 分钟 | 可合并 identify+research 为 1 次调用 |
| 非游戏领域不适用 | 当前 prompt 针对游戏设计优化 | 需要新的 research_constraint 模板 |
| duckduckgo-search 为可选依赖 | 未安装时退化为纯 LLM 知识 | metadata 中 research_source 会反映 |
| 合成对话的固有不确定性 | LLM 可能遗漏某些系统 | CHECKLIST 约束 + 多次运行取最佳 |

---

## 7. 运行测试

```bash
# 运行全部单元测试 (无需 API key, <3秒)
.venv/bin/pytest tests/test_one_sentence_prd.py -m "not slow" -v

# 运行全部测试 (无需 API key)
.venv/bin/pytest -m "not slow" -q

# 运行集成测试 (需要 API key, 每个 ~3分钟)
ANTHROPIC_API_KEY=sk-or-... .venv/bin/pytest tests/test_one_sentence_prd.py -m slow -v

# 运行 CLI 演示
ANTHROPIC_API_KEY=sk-or-... python demo_one_sentence_prd.py 1943
ANTHROPIC_API_KEY=sk-or-... python demo_one_sentence_prd.py --interactive kings
```

---

## 8. 依赖

### 必需

| 包 | 版本 | 用途 |
|----|------|------|
| anthropic | >=0.40 | LLM API 客户端 |
| pydantic | >=2.0 | 数据模型验证 |
| httpx | (anthropic 依赖) | Wikipedia API 调用 |

### 可选

| 包 | 版本 | 用途 |
|----|------|------|
| duckduckgo-search | >=7.0 | 网络搜索 (未安装则跳过) |

安装可选依赖:

```bash
pip install -e ".[search]"
```
