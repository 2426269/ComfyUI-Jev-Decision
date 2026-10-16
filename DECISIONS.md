# 重要设计决定

本文件按决定追加。改变既有决定时新增条目，写明替代哪个 ID；原条目保留。讨论中的想法标为 proposed，不与 accepted 混淆。用户当前明确要求优先，必要时补记替代关系。

## DEC-001 / accepted / 2026-09-21

主题：核心保持通用判断能力。

来源：本任务用户明确认可轻量、基础、可扩展的节点设计。

决定：Context、Questions、Result 为核心对象；业务用途通过数据与连线组合。模型说明、LoRA 卡、Skill 发现、文本生成不进入核心。

影响：约束 DESIGN 第 1、3、7、11 节，新增功能先判断能否由现有组合表达。

验证：新需求能通过修改输入、问题和接线完成；无需添加业务名称节点。

## DEC-002 / accepted / 2026-09-21

主题：评估与行动分离。

决定：Evaluate 保留完整判断；阈值、映射和路由独立于模型请求。上下文显式传递且采用值语义。

影响：修改策略不失效模型评估缓存；不把不确定或网络错误转换成 false。

验证：按 ACCEPTANCE 第 2–4 节，以字段校验、调用次数及分支执行次数验证。

## DEC-003 / accepted / 2026-09-21

主题：文档优先与行为留痕。

来源：用户要求“建个任务日志让 agent 记录自己的行为，写下 agent.md 约束 agent 行为和约定基本准则。文档优先”。

决定：采用标准 AGENTS.md；TASK_LOG 只追加事件；STATUS 维护当前快照；DESIGN/ACCEPTANCE 在行为变更前修订；重大变更记录到本文件。

影响：每项实质工作都具有目标、依据、操作与验证记录。常规实现选择不引入重复审批；超出已接受产品边界的改变先写具体提案。

验证：每次交付检查任务日志与实际修改对应，未运行检查不得称通过。

## DEC-004 / accepted / 2026-09-21

主题：公开接口收缩为单个 Semantic Judge。

依据或触发证据：用户提供 `E:\QQ下载\对话记录.txt` 汇总与 GPT、DeepSeek、Gemini 的讨论，并明确批准第五个 `details_json` 输出以及先冻结成功成果、再重设计文档。

决定：第一版只公开 `JevSemanticJudge`。输入以运行时 STRING 为核心，模式为 Noul、Choice、Score；固定输出 BOOLEAN、FLOAT、INT、STRING、details_json。执行、路由、图扫描、动作节点和本地模型不进入第一版。现有 provider、校验、凭证和测试成果作为内部基础复用。

理由：一个节点即可把语义不确定性转换为 ComfyUI 原生信号，使用成本更低；完整结果通过第五个 JSON 输出保留，不需要把自定义协议暴露给普通工作流。

影响：替代 DEC-001 中“Context、Questions、Result 为公开核心对象”的部分；保留 DEC-001 的通用性目标。DEC-002 的评估与行动分离继续有效，但阈值派生集中在同一节点的本地输出映射中，改变 threshold 不触发模型请求。

兼容性与迁移：这是对尚未发布实验节点的不兼容重构。P0 Noul 切片已归档，重写完成后不保留两套并列公开节点。

验证：按新版 ACCEPTANCE 的 SJ01–SJ16；冻结证据见 `records/REDESIGN-20260921-001-baseline.json`。

替代的决定 ID：部分替代 DEC-001；细化但不替代 DEC-002。

## DEC-005 / accepted / 2026-09-21

主题：单一 context socket 扩展为严格多类型输入。

依据或触发证据：用户指出 STRING-only 输入无法直接覆盖结构化状态和基础标量，并明确要求继续实现。目标 ComfyUI V3 提供 MultiType、DICT、ARRAY 与基础标量类型；TypeSafe provider 边界已经接受 string、object、array。

决定：保留一个 `JevSemanticJudge` 和一个 `context` socket，允许 STRING、DICT、ARRAY、BOOLEAN、INT、FLOAT。DICT/ARRAY 作为原生 JSON state；标量包装为 object；不使用无限制 ANY。IMAGE、LATENT、MODEL、VAE、tensor 与自定义运行时对象必须先由上游转换为可说明的文字或 JSON 元数据。

理由：覆盖文本、结构化档案和基础控制值，同时不引入业务节点、隐式工作流扫描或任意对象序列化。严格白名单能在网络调用前阻止巨大张量、不可重复对象和敏感内部状态进入云请求。

影响：细化 DEC-004 的“运行时 STRING 为核心”为“单一显式 JSON 基础状态接口”，继续保持固定八输入、五输出和单节点边界。STRING 工作流兼容；context socket 的公开类型从 STRING 改为多类型联合。

兼容性与迁移：原有 STRING 连线、请求和 STRING 指纹保持兼容。依赖 context socket 精确等于 STRING 的第三方前端假设需要按联合类型重新验证。

验证：ACCEPTANCE SJ19–SJ22。

替代的决定 ID：部分细化并替代 DEC-004 的 STRING-only 输入约束；不替代其单节点和五输出决定。

## DEC-006 / accepted / 2026-09-22

主题：供应方响应采用“已知语义严格、未知字段兼容”的验证策略。

依据或触发证据：外部评审指出当前 exact-field 校验会在供应方仅增加 `request_id` 等字段时令工作流失败。随后各执行一次真实 Choice 与 Score 请求；`jev-1.13.0` 的字段与当前契约完全一致，严格校验均通过，但这只能证明当前版本，不能保证未来只增加字段时仍兼容。

决定：`model`、`answers.decision` 及各模式必需字段必须存在；type、概率范围与归一化、Choice ID、Score 坐标及 legend 继续严格校验。供应方新增的未知字段不单独导致失败。`decision` answer 内未知字段作为原始 answer 的一部分保留到 `details_json.answer`；供应方顶层和 `answers` 中其他未知字段不属于公开结果契约，允许但不传播。缺失必需字段或已知字段语义错误仍立即失败。

理由：新增元数据不应中断判断；已知坐标或分布异常则会影响下游控制，必须继续 fail closed。当前 details_json v1 已能保存完整 answer，无需为尚未出现的额外字段破坏公开 schema 或伪造 warnings。

影响：细化 DESIGN 第 5、6、8 节与 ACCEPTANCE SJ12；新增 SJ23、SJ24。不会改变固定五输出位置、现有合法响应映射或错误不等于 false 的原则。

兼容性与迁移：所有既有合法响应保持相同输出。过去因未知字段失败的响应可能开始成功；这属于供应方前向兼容修复。依赖“任意额外字段必须报错”的测试应改为验证未知字段保留与已知字段仍严格。

验证：真实 Choice/Score 各一次；fixture 覆盖顶层、answers 和 answer 额外字段，确认 answer extras 保留；继续覆盖缺字段、错误 type、概率、choice、score 与 legend 拒绝。

替代的决定 ID：无；细化 DEC-004 的严格响应边界。

## 新条目模板

复制以下字段追加到文件末尾，不替换旧决定：

- ID / 状态 / 时间：
- 主题：
- 依据或触发证据：
- 决定及简短理由：
- 影响的 DESIGN 章节、节点、协议版本：
- 兼容性与迁移：
- 验证方式及 ACCEPTANCE 编号：
- 替代的决定 ID（如有）：
