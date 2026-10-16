# Semantic Judge 完整设计

日期：2026-09-22。设计状态：Semantic Judge P0.3 契约与三态配方加固已实现；Noul、Choice、Score 均已取得真实 `jev-1.13.0` 响应。旧四节点实现仅保留在冻结归档中。

## 1. 产品定义

> Turn semantic uncertainty into native ComfyUI signals.

本插件只负责一件事：把运行时上下文中的模糊语义判断转换为 ComfyUI 原生基础类型。公开接口只有一个 `Semantic Judge` 节点，不负责修改 prompt、加载模型或 LoRA、选择工作流分支，也不扫描工作流图。

适合的问题包括动作是否复杂、提示词更偏人像还是场景、多个已描述候选项中哪个更合适，以及程度位于哪一级。不适合确定性字符串查找、数值比较、固定 tag 替换、路径选择等普通代码能可靠完成的任务。

## 2. 设计准则

- 核心轻量、通用、可组合，不加入模型档案、LoRA 卡或特定业务规则。
- 输入是上游已经求值完成的 STRING、DICT、ARRAY、BOOLEAN、INT 或 FLOAT；不从静态 prompt 图猜测最终运行时内容。
- 模型只判断，后续动作由 ComfyUI 数据流和现有节点完成。
- 五个输出的位置与类型固定，工作流保存恢复后不因 mode 改变。
- 保留 API 原始判断和完整分布，不把 confidence 称为准确率。
- 阈值是本地策略；修改 threshold 不应增加 API 调用。
- 缺凭证、网络错误、响应异常与低置信度是不同状态，不能统一变成 false。
- 第一版只做 TypeSafe Jev；未来 backend 通过内部接口增加，不提前实现本地模型。

## 3. 唯一公开节点

节点 ID：`JevSemanticJudge`

显示名：`Semantic Judge`

分类：`Jev Decision`

### 3.1 输入

| 输入 | 类型 | 默认值 | 语义 |
| --- | --- | --- | --- |
| `context` | 必接多类型 socket | 无 | 当前要判断的运行时状态；接受 STRING、DICT、ARRAY、BOOLEAN、INT、FLOAT |
| `instructions` | STRING，多行 | 空 | 完整、独立、可判定的任务描述 |
| `mode` | COMBO | `Noul` | `Noul / Choice / Score` |
| `options` | STRING，多行 | 空 | Choice/Score 的有序选项；Noul 必须为空 |
| `threshold` | FLOAT | `0.5` | 0～1 的本地 BOOLEAN 派生阈值 |
| `model` | STRING，高级 | `jev-latest` | TypeSafe 请求模型 |
| `connection_profile` | STRING，高级 | `default` | 选择环境变量凭证 |
| `refresh` | INT，高级 | `0` | backend 缓存命名空间盐；换成未用值可请求新评估 |

`instructions` 去除首尾空白后不得为空。`context` 按以下规则规范化：

- STRING 去除首尾空白后不得为空，仍以字符串发送。
- DICT 的键必须全部是字符串；DICT 与 ARRAY 必须非空，递归内容只能是 JSON 的 null、boolean、number、string、array、object，浮点数必须有限，循环结构失败。
- BOOLEAN、INT、FLOAT 包装为 `{"value": value}` 后作为 object state 发送；false 与 0 是合法值，FLOAT 必须有限。
- 顶层 null、IMAGE、MASK、LATENT、MODEL、VAE、CONDITIONING、tensor 和其他 Python 对象在 provider 调用前失败。

节点只接收显式连线传来的值，不扫描工作流，也不读取运行时资源对象的内部表示。图像、模型与 LoRA 相关判断应由上游先提取文字、标签、尺寸、名称或其他 JSON 元数据，再连接到 context。

### 3.2 options 文法

每个非空行定义一个选项：

```text
stable_id | human-readable description
```

只写 `stable_id` 也合法，此时描述为空。以第一个 `|` 分隔，后续 `|` 属于描述。ID 去除首尾空白后必须非空、唯一，且不能包含控制字符。空行忽略，不支持注释或转义语法。

Choice 需要 2～255 个选项。声明顺序决定 0 基索引，发送给 API 时使用 ID 作为 criteria 键。

Score 需要 2～10 个有序等级。声明顺序决定等级坐标 0～N-1；发送给 API 的等级描述优先使用 description，为空时使用 ID。

Noul 的 options 必须为空。真假含义应写进 instructions，避免一个字段在不同模式下具有隐藏语法。

## 4. 固定输出契约

节点始终按以下顺序输出：

1. `BOOLEAN decision`
2. `FLOAT value`，范围 0～1
3. `INT index`
4. `STRING label`
5. `STRING details_json`

### 4.1 映射矩阵

| mode | BOOLEAN | FLOAT | INT | STRING |
| --- | --- | --- | --- | --- |
| Noul | `p >= threshold` | `p(true)` | false=0，true=1 | `"false"` 或 `"true"` |
| Choice | `confidence >= threshold` | API `confidence` | 胜出 ID 的声明顺序索引 | 胜出选项 ID |
| Score | `normalized_score >= threshold` | `score / (N-1)` | 最近等级索引 | 最近等级 ID |

比较统一使用 `>=`。Noul 的 0.5 表示真假概率接近，不表示“中等程度”。

Choice 的 `confidence` 是 TypeSafe 响应中与 `probabilities` 分开的供应方字段，不定义为获胜概率或准确率。FLOAT 明确定义为该 API confidence；胜出选项概率和完整概率分布在 details_json 中。低于 threshold 时仍输出真实胜出项，不把它改成空字符串或 -1；BOOLEAN 只表示是否达到本地自动采用门槛。需要保守门控时，下游应读取 details_json 并自行采用胜出概率、confidence 或二者较小值；插件不擅自改写供应方坐标。

Score 原始值位于 0～N-1，允许落在等级之间。FLOAT 输出归一化值。最近等级用 `floor(score + 0.5)` 并限制在合法范围；details_json 保留原始 score、confidence、legend 和概率分布。

## 5. details_json v1

details_json 是规范化 JSON 字符串，顶层结构固定：

```json
{
  "schema_version": 1,
  "kind": "semantic_judge_result",
  "backend": "typesafe",
  "requested_model": "jev-latest",
  "model": "jev-1.13.0",
  "mode": "choice",
  "input_fingerprints": {
    "context_sha256": "...",
    "instructions_sha256": "...",
    "options_sha256": "..."
  },
  "options": [
    {"id": "portrait", "description": "...", "index": 0}
  ],
  "threshold": 0.8,
  "outputs": {
    "boolean": true,
    "float": 0.91,
    "int": 0,
    "string": "portrait"
  },
  "answer": {},
  "usage": {},
  "elapsed_ms": 120,
  "cache": {
    "hit": false,
    "key_sha256": "..."
  }
}
```

`answer` 保存该模式完整、经过校验的 API answer。usage 缺失时为 null，不伪造 token 数。默认不保存 context、instructions 原文，不保存 API key、Authorization header 或未脱敏 HTTP body。STRING context 延续 P0 的原文字节 SHA-256；结构化 context 使用带类型前缀的规范 JSON 计算 SHA-256，避免文本 `{"a":1}` 与对象 `{"a":1}` 发生指纹碰撞。

响应验证对已知语义严格、对新增字段兼容：必需字段必须存在，已知类型、概率、Choice ID、Score 坐标和 legend 必须正确；未知字段本身不导致失败。`answers.decision` 内未知字段随完整 answer 保留，顶层和其他 question 的未知字段不进入 details_json。缺字段与已知字段错误仍在派生输出前失败。

details_json 是检查与互操作出口，不是第二套隐式控制协议。下游若只需控制信号，应直接使用前四个输出。

## 6. 内部请求与 backend 边界

节点把 UI 输入转换为内部 `DecisionRequest`：

- context
- instructions
- mode
- parsed options
- requested model
- connection profile
- refresh

threshold 不属于模型问题，只参与本地输出映射。

内部 backend 接口接收已验证请求，返回：

- provider 名称
- 实际模型
- 完整 answer
- usage
- 可用的 request metadata

第一版只注册 TypeSafe backend。测试可注入 fake backend，但 UI 不提供 Mock、Local Qwen、OpenAI-compatible 等未交付选项。

TypeSafe 每个节点执行只发送一个固定问题 ID `decision`。Noul、Choice、Score 的 wire schema 与官方 Python SDK保持一致。实现可继续使用已验证的 aiohttp transport，不为了抽象而新增 SDK 依赖。

## 7. 缓存与 ComfyUI 执行

缓存分两层：

1. ComfyUI 按节点输入和输出进行图执行缓存。
2. 插件提供进程内、有界的 backend 响应 LRU，默认最多 256 项。

backend 缓存键由 backend、connection profile、请求模型、mode、类型保持的规范化 context、instructions、规范化 options 与 refresh 的规范序列化计算。文本、对象、数组及标量包装后的 state 不会因相同显示文本而错误共用缓存。threshold 不进入 backend 键，因此改变阈值只重新派生输出，不发送请求。错误、超时和校验失败不缓存。

缓存不写磁盘，重启 ComfyUI 后清空。`refresh` 不是删除或失效命令，而是缓存键的一部分：换成未使用的新值会请求新评估，切回旧值仍可能命中旧缓存。details_json 必须报告本次是否命中插件 LRU。当前缓存没有 TTL；生产工作流应优先填写固定模型版本，并在需要重新判断时单调增加 refresh。`jev-latest` 与无 TTL 进程缓存的组合不适合作为跨模型升级的强一致保证。

节点不能通过可变实例字段保存结果。唯一允许的共享状态是受锁保护、容量受限、内容寻址的基础设施缓存；它不包含业务规则。

## 8. 凭证、网络和错误

`default` profile 读取 `TYPESAFE_API_KEY`。命名 profile 只允许字母、数字、下划线和连字符，并映射为 `TYPESAFE_API_KEY_<PROFILE>`。

- API key 不成为节点输入，不进入 workflow JSON、details_json、日志或异常。
- 默认总超时 60 秒，禁止重定向。
- 第一版不自动重试不明确的超时，也不静默 provider 降级。
- 400、401、402、403、404、422、429、529 分别给出可操作但不泄密的错误。
- API 或校验错误默认抛出，停止当前执行；不返回默认判断、不把错误视为 false、不自动使用陈旧缓存。
- 文档明确说明 context 和 instructions 会发送到 TypeSafe 云服务。
- 请求已经发出后，即使用户取消等待，受共享请求合并保护的后台 task 仍可能完成并产生费用；不能把取消队列视为撤销云请求。
- 不自动重试 429、超时或 5xx，也没有内置批量限速。批量工作流应控制并发，收到 429 后由用户调整节奏或 refresh，而不是立即并发重放。

## 9. 与 ComfyUI 生态的连接

插件不重造 Router。第一版文档与样例应验证至少以下组合：

- BOOLEAN → 已安装的条件分支节点。
- FLOAT → 比较或数学节点。
- INT → 索引选择节点。
- STRING → 文本拼接、命名或显示节点。
- details_json → Preview/Show Text 或 JSON 处理节点。

社区节点接口并不统一，所以只记录在目标 ComfyUI 环境中实际验证过的组合，不笼统承诺所有 Switch 或 ANY 节点兼容。没有可用社区节点时，原生 STRING/FLOAT 仍是基本互操作出口。

## 10. 示例用途

### 提示词优化是否保持原义

context 包含原文和候选改写，Noul instructions 要求所有主体、数量、场景、构图、风格和禁止项保持一致。FLOAT 是保持概率，BOOLEAN 是本地阈值结果。

目标环境没有通用的 DICT/JSON 构造节点。提示词配方因此用内置 `StringConcatenate` 和固定边界连接两个动态 STRING，避免手工 JSON 模板对引号、反斜杠和换行转义失败；`instructions` 明确边界前后分别是原文和候选。示例把 `p >= 0.80` 归为 adopt，`0.50 <= p < 0.80` 归为 review，`p < 0.50` 归为 reject，并在 review/reject 的自动路径回退原文。该区间只演示如何把已观察到的 0.76 deletion 假阳性送入复核，不是生产阈值校准。

### 选择生成模型类别

Choice options 使用稳定 ID 和用户写入的能力描述。STRING 输出 ID，INT 输出声明索引。节点不知道该 ID 对应哪个 checkpoint；下游工作流负责解释。

### 动作复杂度

Score 使用从“静态简单姿势”到“多人严重交叠”的有序等级。FLOAT 输出归一化复杂度，可连接参数映射；INT/STRING 给出最近等级。

## 11. 明确不做

第一版不包含：

- Context Builder、Ask Noul/Choice/Score、Evaluate、Read、Inspect 等公开组合节点。
- 多问题单请求、批量 state、动态数量端口。
- 工作流 AST、上下游遍历、MODEL/VAE/LoRA 元数据适配。
- Router、Lazy Select、条件文本动作或动态资源加载。
- 内置模型档案、LoRA 卡、预设市场或 Skill 扫描。
- 本地 decision model、普通 LLM logits 校准或温度缩放。
- 默认评测日志、原文持久化或下游路径追踪。

这些能力只有在单节点真实使用证明需要后，才以独立提案进入设计。

## 12. 兼容性与迁移

旧实验节点 ID：

- `JevDecisionAskNoul`
- `JevDecisionEvaluateText`
- `JevDecisionReadNoul`
- `JevDecisionInspectResult`

它们属于冻结的 P0 探针，不是新版本兼容承诺。重写完成后 entrypoint 只注册 `JevSemanticJudge`。旧源码与证据保存在只读归档中，不在生产入口维持双体系。

保留并重用的内部成果：

- TypeSafe endpoint 与环境凭证边界。
- 严格 JSON 与 answer 校验。
- 错误分类和超时策略。
- ComfyUI V3 注册、PromptExecutor 与缓存计数测试方法。
- 本地密钥文件和安全启动器。

## 13. 分期

### SJ-P0：单节点完整闭环

实现三种 mode、五个固定输出、options parser、details_json、TypeSafe backend、内存 LRU、严格失败和真实 ComfyUI 执行器测试。

### SJ-P1：互操作样例

在目标环境验证实际存在的条件、比较、索引和文本节点，发布少量可打开的 workflow 样例。不新增执行节点。

### SJ-P0.2：多类型 context

保持单节点和单 context socket，将可发送给 Jev 的 JSON 基础状态直接接入；严格拒绝资源对象，验证规范化、缓存、PromptExecutor 和前端保存恢复。现有 STRING 工作流无需迁移。

### 延后评估

持久缓存、批量、多问题、其他 backend 与评测日志只在真实使用证据支持时讨论。

## 14. 当前证据边界

已经确认 TypeSafe endpoint 与 `jev-latest`。真实 Noul 评测、一次 Choice 和一次 Score 烟雾均返回 `jev-1.13.0`；Choice/Score 字段与本地严格契约一致，Score legend 与请求描述逐字一致。真实烟雾只证明当前版本的单次响应形状，不证明未来版本不会增加字段或改变行为。

当前官方客户端依据：[TypeSafe Python SDK](https://github.com/typesafe-ai/typesafe-sdk-python)。外部接口可能变化，实施时仍以固定版本源码、实际响应与本地测试共同校验。

本设计已由 `JevSemanticJudge` P0.2 实现。验收事实以 STATUS、TASK_LOG 和 records 下对应任务记录为准。SJ18-v1 与 v2 已完成明确英文基础集及中英文成对难例评测；v2 独立 validation 通过，但实测发现删除一条禁止要求可能仍得到 0.76。人工小样本不构成通用准确率或生产阈值结论，硬约束遗漏不能完全交给单次语义概率。
