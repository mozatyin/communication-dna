# PRD 生成模块 — 接入指南

> 本文档说明 PRD（Product Requirements Document）生成模块的架构、输入输出格式、接入点，
> 以及如何替换或增强现有的生成逻辑。

---

## 1. 整体流程

```
用户多轮对话 → 触发 PRD 生成 → PrdGenerator → prd.txt → 下游消费（Wireframe / 代码生成）
```

详细步骤：

1. 用户在前端与 AI 助手进行多轮对话，讨论游戏设计
2. 用户说"帮我生成 PRD"或类似意图，触发 PRD 生成
3. 系统通过 TaskManager 创建异步任务
4. `GameServiceV3.generate_prd()` 被调用
5. 内部调用 `PrdGenerator.generate()` 完成实际生成
6. 输出保存为 `storage/projects/{uid}/{session_id}/prd.txt`
7. 前端通过轮询接口查询任务完成状态

---

## 2. 核心文件

| 文件 | 职责 |
|------|------|
| `chat_module/core/game/prd/prd_generator.py` | **核心生成逻辑**。构建 prompt → 调用 LLM → 返回 PRD 文档 |
| `api/services/game_service_v3.py` → `generate_prd()` | 加载对话历史和游戏状态，调用 PrdGenerator，将结果写入文件 |
| `api/routes/games_v3.py` → `_execute_prd_generation()` | 异步任务执行器，在后台线程中运行 |
| `shared_tools/file_tools.py` → `create_generate_prd_tool()` | 对话中通过 tool calling 触发 PRD 生成 |

---

## 3. 输入

PrdGenerator 的 `generate()` 方法接收三个参数：

### 3.1 conversation_history（对话历史）

这是最核心的输入。格式为消息列表：

```json
[
  {
    "role": "user",
    "content": "我想做一个塔防游戏，中世纪奇幻风格的"
  },
  {
    "role": "host",
    "content": "听起来很有趣！你想要什么样的防御塔类型？"
  },
  {
    "role": "user",
    "content": "有弓箭塔、魔法塔、炮塔三种，弓箭塔打轻甲快，魔法塔范围伤害，炮塔打重甲"
  },
  {
    "role": "host",
    "content": "这三种塔在面对不同怪物时各有优势，很好的设计！怪物方面你有什么想法？"
  },
  {
    "role": "user",
    "content": "有克制关系，弓箭塔打轻甲快，魔法塔打有护盾的，炮塔打重甲"
  }
]
```

**说明**：
- `role` 只有两种：`"user"`（用户）和 `"host"`（AI 助手）
- `content` 是消息文本
- 通常需要 5-15 轮有实质内容的对话才能生成有质量的 PRD
- 内部会截取最多 50000 字符的对话文本，超长时只保留最近 40 条完整消息

### 3.2 game（Game 实例）

Game 实例中主要使用 `game.facts`，这是从对话中提取的关键事实列表：

```python
game.facts = [
    "游戏类型: 塔防",
    "画面风格: 中世纪奇幻",
    "防御塔: 弓箭塔、魔法塔、炮塔",
    "怪物: 轻甲、护盾、重甲",
    "关卡: 10波怪物",
]
```

### 3.3 session_info（会话信息）

```json
{
  "uid": "game_user_abc123",
  "session_id": "5b7891c6-1606-40ab-89da-ce61403802cf",
  "language": "zh"
}
```

### 3.4 Intention Graph（意图图谱，可选）

如果数据库中存在 IG 数据，PrdGenerator 会自动加载并提取：
- `intentions`：用户表达的意图列表（如"想做一个有策略深度的塔防游戏"）
- `topics`：讨论过的主题（如"防御塔种类"、"怪物设计"）
- `core_intention`：通过蒸馏得到的核心意图

这些信息会作为额外上下文注入到 LLM prompt 中，帮助生成更精准的 PRD。
如果没有 IG 数据，PrdGenerator 仍然可以仅凭对话历史生成 PRD。

---

## 4. 输出

### 4.1 generate() 方法返回值

```python
{
    "prd_document": "## 1. 游戏总览\n- 游戏体验：...",   # Markdown 格式的 PRD 文本
    "prd_summary": "一款中世纪奇幻风格的塔防游戏...",     # 2-3 句话的摘要
    "metadata": {
        "core_intention": "做一个有策略深度的塔防游戏",
        "num_intentions": 5,
        "num_topics": 8,
        "num_facts": 6,
        "ig_available": True,
        "language": "zh",
        "model": "google/gemini-2.5-flash"
    }
}
```

### 4.2 prd.txt 文件格式

最终保存的文件是纯 Markdown 文本，固定章节结构：

```
## 1. 游戏总览
- 游戏体验：...
- 类型与视角：...
- 乐趣与吸引力：...

## 2. 核心游戏循环
- 玩家的即时操作：...
- 胜利/失败/进程条件：...
- 循环的演变、升级与持续吸引力：...

## 3. 游戏系统

### 建造系统
**如何运作**: ...
**为何感觉良好**: ...
**设计考量**: ...
**如何连接**: ...

### 升级系统
...

### [更多系统]
...

## 4. 美术与音效风格
- **视觉风格**: ...
- **色彩调性**: ...
- **动画**: ...
- **打击感与反馈**: ...
- **UI 视觉语言**: ...
- **音效**: ...
- **音乐**: ...
- **占位策略**: ...
```

**关键要求**：
- PRD 只描述**玩家体验和感官层面**，不涉及技术实现
- 每一条都是具体、可执行的设计指令
- 系统章节中如果 LLM 推断出了用户没有明确提到的系统，会标注 `[INFERRED]`
- 整篇文档语言与用户对话语言一致（中文对话 → 中文 PRD）

### 4.3 文件存储位置

```
storage/projects/{uid}/{session_id}/prd.txt
```

---

## 5. 下游消费者

prd.txt 会被以下模块读取：

| 消费者 | 用途 |
|--------|------|
| `InterfacePlanGenerator` | 从 PRD 提取界面列表和导航关系 |
| `AssetTableGenerator` | 从 PRD 推导需要的素材（图片、音频） |
| `WireframeGenerator` | 基于 PRD + Interface Plan + Assets 生成界面布局 |
| `pm_agent_demo`（代码生成） | 基于 PRD + Wireframe 生成游戏代码 |

所以 PRD 的质量直接决定了后续所有环节的质量。

---

## 6. 如何替换/增强生成逻辑

如果要用新的模型或方法替换现有的 PRD 生成：

### 方式 A：替换 PrdGenerator 内部逻辑

修改 `chat_module/core/game/prd/prd_generator.py` 中的 `generate()` 方法。
只要保持输入输出格式不变，上下游不需要任何改动。

```python
async def generate(
    self,
    game: Any,                                    # Game 实例（取 game.facts）
    conversation_history: List[Dict[str, str]],   # 对话历史
    session_info: Dict[str, Any]                  # 会话信息
) -> Dict[str, Any]:
    # 你的新逻辑...
    return {
        "prd_document": "...",   # 必须返回 Markdown 文本
        "prd_summary": "...",    # 可选
        "metadata": {...}        # 可选
    }
```

### 方式 B：提供独立的 API

如果新模型作为独立服务部署（例如 HTTP API），可以在 `generate()` 内部调用：

```python
async def generate(self, game, conversation_history, session_info):
    # 调用外部 API
    response = requests.post("http://your-model-server/generate_prd", json={
        "conversation_history": conversation_history,
        "facts": game.facts if game and hasattr(game, 'facts') else [],
        "language": session_info.get("language", "zh"),
    })
    prd_document = response.json()["prd_document"]
    return {"prd_document": prd_document, "prd_summary": "", "metadata": {}}
```

### 关键约束

1. `prd_document` 必须是 Markdown 纯文本
2. 章节结构建议保持上述 4 个主要章节（游戏总览、核心循环、游戏系统、美术音效），因为下游的 InterfacePlanGenerator 会从中提取结构化信息
3. 如果用中文对话，PRD 必须输出中文
4. 返回值中 `prd_document` 为 `None` 或空字符串时，系统会认为生成失败

---

## 7. 当前 LLM 调用方式

现有实现使用 OpenRouter API（通过 `core.utils.llm.async_chat_completion`）：

- **模型**：`google/gemini-2.5-flash`（默认）
- **Temperature**：0.7
- **Max tokens**：不限制
- **输入 token 估算**：system prompt (~2000) + 对话历史 (~5000-50000) + facts + IG 数据
- **输出 token 估算**：3000-8000（根据游戏复杂度）

---

## 8. 触发方式

PRD 生成可以通过两种方式触发：

### 方式 1：对话触发（推荐）

用户在聊天中说"生成 PRD"、"帮我整理成文档" 等，ToolActionDetector 识别意图后调用 `generate_prd` tool。

### 方式 2：API 直接触发

```
POST /api/v3/games/prd/generate
{
  "uid": "game_user_abc123",
  "session_id": "5b7891c6-...",
  "force_regen": false
}
```

两种方式最终都走到同一个 `GameServiceV3.generate_prd()` → `PrdGenerator.generate()`。
