# Semantic Judge 验收与验证计划

日期：2026-09-21。适用于 DESIGN 的单节点架构。SJ01–SJ18 记录 P0/P0.1，SJ19–SJ22 验证 P0.2 多类型 context。

## 1. 验收原则

- 分别证明协议、节点 schema、ComfyUI 执行、缓存、真实 provider 和语义效果。
- mock 结果不称为 Jev 实测；一次真实请求不称为准确率验证。
- 五个输出的类型、顺序和语义是公开契约。
- 测试必须证明不该调用 provider 时调用次数为零。
- 凭证、context 原文和 Authorization header 不进入证据记录。

## 2. Schema 与输入

### SJ01 固定节点表面

entrypoint 只注册 `JevSemanticJudge`。schema 在 Noul、Choice、Score 下始终有相同八个输入和五个输出，输出顺序为 BOOLEAN、FLOAT、INT、STRING、STRING。P0.1 的 `context` 是必接 STRING socket；P0.2 由 SJ19 替代其 socket 类型，其余七项仍是节点内控件。

### SJ02 基础输入校验

空 context、空 instructions、非法 threshold、空 model、非法 connection profile 在网络调用前失败。Noul 的非空 options 失败。

### SJ03 options parser

验证：

- 空行忽略。
- `id` 和 `id | description` 均可解析。
- 只按第一个 `|` 分隔。
- 重复、空 ID 和控制字符失败。
- Choice 只接受 2～255 项。
- Score 只接受 2～10 项。
- 顺序和 Unicode 往返不变。

## 3. 五输出数据契约

### SJ04 Noul 映射

用边界 fixture 验证 `p >= threshold`、FLOAT 原概率、INT 0/1、STRING 小写 true/false。覆盖 p=0、p=threshold、p=1。

### SJ05 Choice 映射

验证 BOOLEAN 基于 API confidence；FLOAT 等于 confidence；INT 是胜出 ID 的 0 基声明索引；STRING 是胜出 ID。胜出 ID 不存在、概率键不匹配、分布不归一或 confidence 越界必须失败。

### SJ06 Score 映射

验证 FLOAT 为 `score/(N-1)`；BOOLEAN 对归一化分数使用 `>= threshold`；INT 使用 half-up 最近等级并限界；STRING 是对应等级 ID。覆盖 0、半级、最高级和非法 legend/分布。

### SJ07 details_json v1

解析输出并验证精确顶层字段、schema_version、实际模型、完整 answer、usage、elapsed_ms、cache 信息和五输出镜像。确认没有 key、Authorization header、context 原文或 instructions 原文。

### SJ08 保留信息

Choice 的完整 probabilities、胜出概率与 confidence 同时存在；Score 的 raw score、legend、probabilities 与 confidence 同时存在；缺失 usage 保持 null。

## 4. Provider 与错误

### SJ09 请求形状

三个 mode 分别发送单个 `decision` question，state 等于 context。threshold 不进入 payload。options 按 DESIGN 转换为 Choice map 或 Score ordered list。

### SJ10 凭证和脱敏

default 与命名 profile 映射正确；缺 key 的错误只报告变量名。对已配置真实 key 做内容扫描，除本地 env 文件外匹配数为零。

### SJ11 网络边界

验证 60 秒总超时、禁止重定向、不自动重试不明确超时；400、401、402、403、404、422、429、529 分类正确。错误响应不进入缓存。

### SJ12 严格响应

拒绝非对象、重复 JSON 键、非有限数、错误 answer type、未知/缺失字段、越界概率和不匹配选项。错误在产生任何派生输出前发生。

## 5. 缓存与执行器

### SJ13 backend LRU 计数

注入计数 fake backend：

1. 相同请求连续执行，provider 计数保持 1。
2. 只改变 threshold，计数保持 1，但 BOOLEAN 可变化。
3. 改变 context、instructions、mode、options、model、connection profile 或 refresh，计数各增加 1。
4. 异常请求再次执行仍调用 provider，证明错误未缓存。
5. 超过容量后最旧项被逐出。

### SJ14 ComfyUI PromptExecutor

使用目标 ComfyUI 的真实 `validate_prompt` 与 `PromptExecutor` 执行每种 mode 的 API graph。验证五个输出可消费、同图缓存正确、改变 threshold 不触发 backend 请求。

### SJ15 保存恢复

用前端生成并重新载入 workflow/API JSON，确认 context 输入 socket 的连线、multiline、Unicode、options 顺序、threshold、高级字段和五个输出连线保持不变。没有浏览器时不得宣称该项通过。

## 6. 互操作

### SJ16 原生类型连接

在本地已安装节点中选择并记录实际 class_type，至少验证：

- BOOLEAN 接一个条件消费者。
- FLOAT 接一个比较或数学消费者。
- INT 接一个索引消费者。
- STRING 与 details_json 接文本显示消费者。

若本地缺少某类消费者，记录为未验证，不临时把 Router 加进插件。

## 7. 真实 API 与效果边界

### SJ17 真实 TypeSafe 烟雾

在用户授权和本地凭证存在时，以最小输入执行至少一次新 `JevSemanticJudge` Noul 请求，记录请求次数、requested/returned model、值、usage、延迟和响应字段。默认不重复调用已验证场景。

Choice/Score 可用小额烟雾测试补充，但不是自动测试的前置条件；如果未运行，明确写未验证。

### SJ18 语义评估

“提示词优化是否保义”等效果结论需要独立标注样本，至少包含正例、删减、矛盾、数量变化、否定项丢失和风格变化。报告阈值、模型版本、样本数与错误，不用单个演示替代评估。

执行状态：SJ18-v1 与 v2 已完成。v1 的 18 个样本覆盖上述六类；v2 使用 12 组中英文最小差异对，并把 calibration 与 validation 分开。两轮均报告混淆矩阵、balanced accuracy、Brier、实际模型、usage 和逐例概率；v2 另报告 AUROC、成对 margin 与按语言/错误类型结果。证据见 `evaluation/runs/20260921T212008+0800/` 和 `evaluation/runs/v2/20260921T213420+0800/`。这满足人工诊断集上的可行性证据，不等同于生产校准。

## 8. P0.2 多类型 context

### SJ19 单一多类型 socket

`context` 仍只有一个左侧必接接口，精确接受 `STRING,DICT,ARRAY,BOOLEAN,INT,FLOAT`。不得改成无限制 ANY，不新增 Context Builder 或六个专用判断节点。原有 STRING API workflow 必须继续通过验证。

### SJ20 context 规范化与拒绝

分别验证 STRING、DICT、ARRAY、false、0、有限 FLOAT。DICT/ARRAY 以原生 JSON state 发送；三个标量包装为 `{"value": ...}`。空字符串、空对象、空数组、顶层 null、非字符串键、NaN/Infinity、循环容器、tuple、自定义对象和 tensor 在 backend 计数仍为零时失败。

### SJ21 缓存与指纹

相同规范 context 共用 backend 缓存；不同类型或不同值不共用。STRING 指纹保持 P0 兼容；DICT/ARRAY/标量包装用类型前缀加规范 JSON 计算。details_json 只记录哈希，不记录 context 原文或完整结构。

### SJ22 ComfyUI 与前端往返

真实 `validate_prompt` / `PromptExecutor` 至少执行 STRING、DICT、ARRAY 和一个标量来源，确认 provider 收到预期 state。隔离前端保存、清空并重载多类型连线，确认 context socket 允许的类型、连线和五输出保持；不得重启用户正在运行的 8188 实例。

### SJ23 Choice / Score 真实响应

在用户授权下各提交一次最小 Choice 与 Score 请求，记录 requested/returned model、原始字段集合、已知 answer、usage、延迟和严格映射结果。脚本不得自动重试或记录 key、prompt、Authorization。真实字段与 fixture 不符时先保留原始形状证据，不修改证据迎合实现。

### SJ24 响应前向兼容

已知必需字段和值保持严格：缺字段、错误 type、概率不归一、未知 Choice ID、不一致 Score/legend 均失败。分别在 provider 顶层、answers 和 decision answer 注入额外字段，确认不会仅因新增字段失败；decision answer 的额外字段保留进 details_json，其他层额外字段允许但不传播。

### SJ25 三态提示词配方

先审计目标环境中的通用结构构造能力。若没有能安全转义任意提示词的 DICT/JSON 构造器，使用内置 `StringConcatenate` 将两个独立 STRING 以固定边界组成一个文本 context；不得靠手工 JSON 模板拼接未经转义的提示词。context 进入 `JevSemanticJudge` 后，下游以 `p >= 0.80` 为 adopt、`0.50 <= p < 0.80` 为 review、`p < 0.50` 为 reject；自动路径只在 adopt 时采用候选，review/reject 均回退原文。验证 API graph、真实 PromptExecutor、前端保存恢复和 lazy 行为；0.50/0.80 只标为暴露已知 deletion 风险的示例策略，不称生产校准。

## 9. 文档和安全检查

交付前必须：

- 所有第一方 JSON 可解析。
- 本地 Markdown 链接无断链。
- manifest 哈希与第一方文件集合一致，并排除 `.env.local`、research、缓存和历史 manifest。
- 归档基线 SHA-256 不变。
- README、DESIGN、ACCEPTANCE、STATUS、DECISIONS 与节点 schema 一致。
- 自动测试不访问真实服务；真实烟雾脚本明确一次请求且无自动重试。

## 10. 完成定义

只有 SJ01–SJ14、文档和安全检查全部通过，且 SJ15–SJ17 的执行边界被如实记录，才能称 Semantic Judge P0 完成。SJ18 未完成时只能声明工程可用，不能声明语义准确率已经验证。

只有 SJ19–SJ22、既有 45 项插件回归和文档安全检查全部通过，才能称 P0.2 多类型 context 完成。SJ18 仍独立决定能否声明语义效果。SJ23–SJ25 与新增测试共 47 项通过后，才能称 P0.3 契约与配方加固完成；它不追溯改变 P0.2 的历史完成状态。
