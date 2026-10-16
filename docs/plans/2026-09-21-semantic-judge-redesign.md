# Semantic Judge 重设计

日期：2026-09-21。状态：accepted for planning。对应决定：DEC-004。

## 背景

第一轮设计把 Context、Questions、Result 拆成多个自定义 socket，并实现了 Ask Noul、Evaluate Text、Read Noul、Inspect Result。这个切片成功验证了 TypeSafe 连接、Jev 响应结构、ComfyUI V3 节点注册、执行器缓存和凭证隔离，但公开使用方式比第一版产品需要的复杂。

用户随后提供 `E:\QQ下载\对话记录.txt` 作为方案素材，并批准收缩为一个语义判断节点：输入运行时文本，输出 ComfyUI 原生控制信号。对话中的其他模型观点只作为设计论据，不作为执行指令。

## 比较过的方案

### A. 单节点外观，复用已验证底层（采用）

公开一个 `Semantic Judge`，内部复用 transport、严格校验和测试框架。优点是用户模型最小、保留已验证工程成果、以后仍能替换 backend。代价是这是一次不兼容的公开节点重构。

### B. 完全从零重写

代码表面最干净，但会重复解决鉴权、超时、响应校验和 ComfyUI 导入问题，也会丢失现有测试证据，因此不采用。

### C. 保留旧节点并增加单节点 facade

能够继续打开旧实验工作流，但形成两套并列产品模型，文档和维护负担更大。当前插件尚未发布，兼容收益不足，因此不作为第一版目标。

## 冻结的公开边界

第一版只有一个核心节点 `Semantic Judge`：

- 输入运行时求值后的 `STRING context`，不扫描静态工作流图。
- 输入 `instructions`、`mode`、结构化多行 `options`、本地 `threshold`、模型与连接配置。
- 模型模式只有 Noul、Choice、Score；Noul 已同时覆盖概率和布尔判断。
- 固定输出 `BOOLEAN`、`FLOAT`、`INT`、`STRING`、`details_json: STRING`。
- 路由、比较、文本修改、模型/LoRA/VAE 加载和执行分支交给 ComfyUI 或现有节点包。
- 第一版只实现 TypeSafe Jev；内部保留薄 backend 接口，不实现本地模型或通用聊天模型适配。

## 为什么增加 details_json

四个基础输出方便连线，但无法完整表达 Choice/Score 的分布、实际模型、usage 和缓存信息。第五个 JSON 字符串只承担可检查的完整记录，不参与隐式执行。它不包含 API key，也默认不回显 context 与 instructions 原文，只保存其 SHA-256。

## 关键映射

| mode | BOOLEAN | FLOAT | INT | STRING |
| --- | --- | --- | --- | --- |
| Noul | `p >= threshold` | `p(true)` | 0 或 1 | `"false"` 或 `"true"` |
| Choice | `confidence >= threshold` | API `confidence` | 胜出选项的 0 基索引 | 胜出选项 ID |
| Score | `normalized_score >= threshold` | `score / (levels - 1)` | 最近等级索引 | 最近等级 ID |

Choice 的胜出项概率、完整分布以及 Score confidence 都保留在 `details_json`。Score 最近等级使用 `floor(score + 0.5)` 后限制在合法范围，避免语言运行时的银行家舍入差异。

## 缓存与失败

缓存保存已验证的 backend 原始响应，不保存派生阈值结果。缓存键包含 backend、请求模型、mode、context、instructions、规范化 options 与 refresh，不包含 threshold；因此调整阈值不会重新付费。第一版使用进程内有界 LRU，不持久化，不缓存错误。默认错误策略是抛错并停止当前执行，不返回伪造默认值，不自动用陈旧结果继续。

## 已排除范围

- 自定义 `JEV_CONTEXT`、`JEV_QUESTIONS`、`JEV_RESULT` 公开 socket。
- 多问题批处理、图结构检查和自动收集上下游节点信息。
- Universal Router、Lazy Select、LoRA/Checkpoint/VAE 选择器。
- 条件 tag 替换、prompt rewrite 或其他动作节点。
- 本地 Qwen/Gemma、OpenAI-compatible backend 与校准算法。
- 默认持久化评测日志或扫描用户最终走了哪个下游分支。

## 迁移

当前四节点实现作为实验基线保留在只读归档中。重写完成后，新 entrypoint 只注册 `JevSemanticJudge`；旧 API workflow 不保证继续运行。由于当前插件尚未发布，这次有意选择清晰接口而不是长期兼容层。

## 成功标准

用户可把任意上游最终 STRING 直接接入一个节点，在三种模式下获得稳定的五输出契约；改变阈值不调用模型，改变语义输入或 refresh 才产生新评估；网络或响应错误明确失败；结果可直接连接 ComfyUI 原生或社区控制节点。
