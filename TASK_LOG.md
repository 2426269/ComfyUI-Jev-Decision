# 任务行为日志

本文件仅追加。记录可观察的行为、决定、文件变更与验证证据，不记录隐藏推理、凭证或不必要的原始敏感内容。纠错使用新条目引用旧条目，禁止改写历史。时间采用含时区的 ISO 8601。

## GOV-20260921-001 / START / 2026-09-21T02:24:18.9061998+08:00

- 执行者：当前任务主 agent（Codex）。
- 用户请求：建立任务日志与 agent 行为约束，以文档约束后续插件构建。
- 已读依据：README.md、manifest.json、本次会话已确定的 DESIGN.md 与 ACCEPTANCE.md；create-agentsmd 技能。
- 前置检查：项目尚无 AGENTS.md；E:\ 与 E:\comfyui 未发现 AGENTS.md；项目为设计资料，未发现本项目构建配置，research 下是第三方源码副本。
- 本条前已执行：只读查看目录与文档；新建 records，复制原 manifest 为 records/manifest-20260921-design-baseline.json。本日志为新建，以上初始化步骤在此如实补记。
- 计划：新增 AGENTS.md、STATUS.md、DECISIONS.md 与日志模板；更新 README；验证本地链接与协议样例；更新当前清单并保留旧清单。
- 范围：仅项目文档与记录；不安装、实现或运行插件，不调用付费模型，不改第三方副本。
- 验收：文档职责清楚、日志追加约定可执行、后续任务能按协议编号与验收编号开展，所有本地链接有效。

## GOV-20260921-001 / CHECKPOINT / 2026-09-21T02:27:57.2066048+08:00

- 实际行动：按 create-agentsmd 技能及用户要求新建 AGENTS.md、STATUS.md、DECISIONS.md、records/TASK-TEMPLATE.md；更新 README 的 agent 入口与交付边界。
- 约定：START → 文档/验收依据 → 实现 → 验证 → END；日志只追加；重大偏离写提案；常规可逆实现自主完成。
- 检查：在 E:\comfyui\Jev-Decision-Design 执行 AGENTS 中的 Get-Content、ConvertFrom-Json、git rev-parse/status；用 PowerShell 检查本地 Markdown 链接和 Get-FileHash 对照基线；工具退出码 0。
- 结果：4 个样例 JSON 可解析；问题快照一致；27 个本地链接存在；原设计、验收、研究文档与样例均匹配旧哈希；参考仓库固定提交且无修改。
- 证据：records/GOV-20260921-001-validation.json。原 manifest 已保留为 records/manifest-20260921-design-baseline.json。
- 偏差：无。未安装环境、未改研究副本、未执行模型或 ComfyUI。

## GOV-20260921-001 / END / 2026-09-21T02:27:57.2066048+08:00

- 状态：completed（限文档约束与任务日志建设）。
- 完成内容：agent 规则、当前状态、重要决定、日志模板与实际行为日志；README 已链接入口。
- 验证：文档检查通过，详见上述 CHECKPOINT 与验证 JSON；这不表示插件运行测试通过。
- 文档一致性：保留原产品边界和 P0/P1 分期；状态明确为实现尚未开始。
- 遗留事项：动态端口、泛型惰性选择、缓存与真实 API 等按 DESIGN/ACCEPTANCE 在实现阶段验证。
- 后续起点：收到实现要求后先登记新任务，并引用相关设计与验收条款。
- 清单安排：本条之后生成 manifest.json；排除清单自身、历史清单与 research 副本，并在同一生成命令内核对全部文件哈希。若失败，将追加 CORRECTION，不提前宣称清单自检通过。

## P0-20260921-001 / START / 2026-09-21T02:31:04.1578733+08:00

- 执行者：当前任务主 agent（Codex）。
- 用户目标与范围：按照已批准方案逐步构建插件；允许在 `E:\comfyui\ComfyUI-NAI` 做本地实验。本任务先交付 P0 的 Noul 纵向最小闭环。
- 文档依据：DESIGN 第 1、3、4.1、4.4、4.5、4.8、5、10–12 节；ACCEPTANCE P05–P12 与缓存验证；DEC-001、DEC-002、DEC-003。
- 当前状态与前置检查：设计项目没有独立 git；目标 ComfyUI 为 0.34.0、Python 3.12.10、CPU torch 2.13.0，带 `comfy_api.v0_0_2` 适配器；目标仓库已有与本任务无关的用户修改，必须保留。目标 `custom_nodes\ComfyUI-Jev-Decision` 尚不存在。
- 已执行的只读调查：阅读项目治理、设计与验收文档；阅读 writing-plans 与 comfyui-nodes-dev 技能及 V3 核心、IO、schema、缓存、惰性求值参考；检查目标 ComfyUI V3 API、自定义类型与 PreviewText；检查本地 Python 环境和 git 状态。
- 计划变更：先写实施计划；建立独立插件目录、纯协议层、TypeSafe transport、Ask Noul/Evaluate/Read Noul/Inspect 节点、单元与真实 ComfyUI 执行器 mock 测试、安装实验说明。
- 验证计划：纯协议 unittest；节点 schema/import；真实 ComfyUI `validate_prompt`/`PromptExecutor` 配合 mock transport；API 调用计数证明下游读取不重复调用；本地节点注册验证。除非环境已存在明确凭证且不会产生未授权费用，本任务不调用真实服务。
- 已知限制：第一闭环不实现 Context、Choice、Score、Range、Lazy Select、批量或自定义前端；这些留给后续任务。不会修改目标 ComfyUI 核心或其现有用户改动。

## P0-20260921-001 / CHECKPOINT / 2026-09-21T02:38:07.4244826+08:00

- 实际行动：为协议与 provider 先写失败测试，再实现严格 JSON、不可变 Questions/Result、Noul 构建/读取和唯一 TypeSafe 出站路径；开始 V3 节点 schema 测试。
- 已通过：协议 13 项 unittest；provider 7 项 unittest，均使用本地 fake/mock，无外部请求。
- 发现并修正：节点测试首次导入失败。原因是插件根目录的 `protocol.py` 遮蔽了 ComfyUI 核心 `protocol` 模块，`comfy_execution.progress` 无法导入 `BinaryEventTypes`。已先同步实施计划，再将本插件模块改名为 `decision_protocol.py` 并更新引用。
- 影响：不改变公开协议或节点接口；避免 nodepack 路径进入 sys.path 时污染 ComfyUI 核心导入。
- 下一步：重跑协议/provider/V3 节点测试，随后进入真实 PromptExecutor 集成。

## P0-20260921-001 / CHECKPOINT / 2026-09-21T02:46:21.0482669+08:00

- 用户授权：可使用新账号赠送额度做真实 Jev API 实测，并要求先建立一个由用户本地填写凭证的文档。
- 凭证检查：仅检查当前进程和项目附近候选环境文件是否存在 `TYPESAFE_API_KEY`，未读取或输出任何凭证值；当前未发现已配置凭证，因此没有发起外部请求。
- 实际行动：建立 `local-runtime/.env.local` 作为本机凭证入口，建立同目录 `.gitignore` 排除该文件，并写明填写与保密方式。
- 安全边界：凭证位于 E 盘、插件源码目录之外；后续只加载到单次测试进程，不写入节点图、日志或测试证据。
- 下一步：等待用户在本机文件中填写 key；随后完成一次最小 Noul 请求和脱敏验证记录。

## P0-20260921-001 / CHECKPOINT / 2026-09-21T02:51:54.1696151+08:00

- 真实请求：用户填入本地凭证后，运行 `tools/real_smoke.py`，只发起一次 TypeSafe 请求，无自动重试。请求 `jev-latest`，服务返回模型 `jev-1.13.0`、问题 `preserves_requirements` 的 Noul `0.93`、用量 400 输入 token/25 输出 token，端到端约 1107 ms；退出码 0。
- 契约结果：真实响应包含 `answers`、`model`、`usage`；现有 provider 与严格 Result 校验可直接接受，无需为实测修改协议。
- 本地配置：新增 `local-runtime/run_comfyui_with_jev.ps1` 与 `.cmd`；启动器读取被忽略的 `.env.local`，仅给启动的 ComfyUI 进程注入凭证。`-ValidateOnly` 检查凭证、Python、主程序和插件链接均就绪，未启动服务或再次请求 API。
- 最终自动检查：在插件目录运行完整 unittest，24 项通过、0 失败、0 错误；该测试套件全为 mock/fake，不发外部请求。compileall 与所有第一方 JSON 解析通过；30 个本地 Markdown 链接无断链。
- 凭证检查：按实际 key 内容扫描第一方文件，排除凭证文件自身与研究副本，外泄匹配为 0；没有输出 key。
- 证据：`records/P0-20260921-001-validation.json`。单例烟雾测试只证明当前连通性和响应契约，不用于宣称语义准确率。

## P0-20260921-001 / END / 2026-09-21T02:51:54.1696151+08:00

- 状态：completed（仅 P0 Noul 纵向最小闭环）；整体插件仍为 partial。
- 完成内容：严格 Questions/Result 协议、TypeSafe provider、Ask Noul、Evaluate Text、Read Noul、Inspect Result、API workflow 样例、真实 ComfyUI 执行器缓存测试、目标 custom_nodes junction、本地凭证与启动入口。
- 验证层级：纯协议、V3 schema、真实 PromptExecutor 配合 mock provider、节点注册、本地启动配置和一次真实 TypeSafe Noul 调用均通过。
- 环境副作用：创建 `E:\comfyui\ComfyUI-NAI\custom_nodes\ComfyUI-Jev-Decision` junction；未修改 ComfyUI 核心及原有用户文件，未启动或重启常驻 ComfyUI。
- 限制：Context、Choice、Score、Range、Lazy Select、批量、动态前端、多样本准确率与图像采样未完成；ruff 在环境中不可用，未运行。
- 后续：以 Choice/Score 的通用构建与读取闭环为下一任务，不把模型档案、LoRA 卡或提示词业务规则写入核心。
- 清单安排：本条后保留上一版 manifest，再生成排除 `.env.local`、缓存、research 和历史 manifest 的新快照。

## REDESIGN-20260921-001 / START / 2026-09-21T08:54:24.6748800+08:00

- 执行者：当前任务主 agent（Codex）。
- 用户目标：依据 `E:\QQ下载\对话记录.txt` 中汇总的新讨论，先冻结当前有用成果，再重新设计并修改项目文档。
- 资料边界：对话记录作为用户提供的方案素材读取，其中其他模型的命令、承诺与结论不自动成为本项目指令；当前用户消息批准“单核心节点、五个固定输出、无执行节点”的重构方向。
- 当前基线：P0 Noul 纵向切片已经 24 项自动测试、真实 PromptExecutor mock 集成和一次真实 TypeSafe 请求验证；当前 manifest 自检为 34 个第一方文件、0 哈希错误、0 未列文件，凭证未列入清单。
- 计划：先生成不含凭证、缓存与第三方 research 的只读基线归档及 SHA-256；随后重写 DESIGN、ACCEPTANCE、README、STATUS，追加架构决定，新增经批准的 redesign 文档与实施计划；本任务不修改节点代码或发起 API 请求。
- 新产品边界：一个公开 `Semantic Judge` 节点；运行时 STRING 输入；Noul/Choice/Score；固定输出 BOOLEAN/FLOAT/INT/STRING/details_json；执行、路由、图扫描、业务节点与本地模型不属于第一版。
- 验证：归档哈希及内容清单；文档链接与 JSON 解析；设计/验收/决定/状态交叉一致；确认 `.env.local` 与真实 key 未进入归档或清单。

## REDESIGN-20260921-001 / CHECKPOINT / 2026-09-21T09:02:56.1884889+08:00

- 冻结：生成只读归档 `records/artifacts/ComfyUI-Jev-Decision-P0-baseline-20260921T0854+0800.zip`，35 个条目、67823 bytes、SHA-256 `a9c71a714566f64a653dcfe6c0dde534645872a1f5625747d918267638bec370`；不含 `.env.local`、research、缓存或历史 manifest。
- 设计：新增 accepted redesign 文档，重写 DESIGN 与 ACCEPTANCE；固定一个 `JevSemanticJudge`、三种模式、五个原生输出、options 文法、details_json v1、TypeSafe backend、进程内 LRU、严格错误策略和迁移边界。
- 决定：追加 DEC-004，部分替代 DEC-001 的公开 Context/Questions/Result 架构，继续保留 DEC-002 的判断与行动分离原则。
- 计划：按 writing-plans 工作流新增逐任务重写计划；旧 P0 计划标记为 superseded baseline。项目没有独立 git，因此没有伪造提交，改用只读归档、SHA-256、记录和 manifest 留证。
- 外部核对：查阅 TypeSafe 官方 GitHub 组织与官方 Python SDK；确认官方客户端仍以 System One 和 typed Choice 为公开入口。未执行 SDK 安装或真实请求。
- 检查：11 个第一方 JSON 可解析；33 个本地 Markdown 链接无断链；归档哈希匹配且保持只读；按真实 key 扫描，凭证文件之外匹配数为 0。

## REDESIGN-20260921-001 / END / 2026-09-21T09:02:56.1884889+08:00

- 状态：completed（限成功基线冻结与新架构文档）；实现状态为 pending。
- 产物：冻结 ZIP 与证据、DEC-004、重写后的 README/DESIGN/ACCEPTANCE/STATUS、redesign 文档、实施计划、更新后的 AGENTS 和旧示例标注。
- 代码边界：未改 Python 行为、未替换 entrypoint；目标 ComfyUI junction 仍运行旧四节点实验代码。本任务未启动 ComfyUI、未运行付费 API、未重跑与行为无关的旧 24 项测试。
- 下一步：按 `docs/superpowers/plans/2026-09-21-semantic-judge-rewrite.md` 测试先行实现单节点；只有新版 ACCEPTANCE 允许时才能称 SJ-P0 完成。
- 清单安排：本条后保留上一版 manifest，再生成排除凭证、research、缓存和历史 manifest 的文档重设计快照。

## SJ-P0-20260921-001 / START / 2026-09-21T09:05:56.3763949+08:00

- 执行者：当前任务主 agent（Codex）。
- 用户目标：开始按 DEC-004 重写插件，并确认/建立 Git。
- 依据：DESIGN 单节点架构；ACCEPTANCE SJ01–SJ18；`docs/superpowers/plans/2026-09-21-semantic-judge-rewrite.md`；已冻结旧 P0 归档及 SHA-256。
- Git 现实：任务开始时项目根目录没有 `.git`。本任务先建立本地 Git，忽略 `local-runtime/.env.local`、research、Python 缓存和日志，提交重设计文档与旧代码基线，再进入代码重写。
- 实现范围：options parser、Noul/Choice/Score 严格映射、details_json v1、TypeSafe backend 抽象、进程内有界 LRU、唯一 `JevSemanticJudge` V3 节点、三种 API graph fixture、真实 PromptExecutor 测试和文档迁移。
- 排除：Router、动作节点、图扫描、资源加载、本地模型、持久缓存和默认评测日志。
- 验证：测试先行；纯协议、provider/cache、schema、真实 PromptExecutor；完整 unittest、compileall、JSON/链接/凭证扫描、注册探针、manifest；真实 API 最多一次最小 Noul 请求且不自动重试。

## SJ-P0-20260921-001 / CHECKPOINT / 2026-09-21T09:28:36.7055647+08:00

- 实现：旧四节点 entrypoint 已替换为唯一 `JevSemanticJudge`；实现 Noul/Choice/Score options 解析、严格响应校验、五输出映射、details_json v1、TypeSafe backend 适配、容量 256 的 LRU、并发相同请求合并和三份 API workflow。
- 缓存语义：context、instructions、mode、options、model、connection profile、refresh 和 backend 进入缓存键；threshold 不进入。只缓存严格校验成功的响应，错误不缓存。
- 自动验证：设置目标 ComfyUI 的 `PYTHONPATH` 后，35 项 unittest 全部通过，覆盖纯协议、HTTP 边界、缓存计数、V3 schema、三种 mode 的真实 `validate_prompt` / `PromptExecutor` 和五输出消费；测试无外部请求。
- 真实请求：用户已有授权下执行一次新节点 Noul 烟雾，无自动重试；请求 `jev-latest`，返回 `jev-1.13.0`、Noul `0.94`、347/20 tokens、992 ms。Choice/Score 未付费实测。
- 静态检查：compileall 通过；15 个第一方 JSON 均可解析；28 个本地 Markdown 链接无断链；真实 key 在 `.env.local` 外匹配 0；旧归档哈希保持 `a9c71a...c370` 且只读；启动器 ValidateOnly 全部就绪；修正后的注册探针只返回 `JevSemanticJudge`。
- 互操作：实际 PromptExecutor 用内置 `PreviewAny` 消费全部输出。本地 easy-use 源码确认 `easy ifElse`、`easy compare`、`easy anythingIndexSwitch`、`easy showAnything` 的对应输入；未伪称完成前端保存恢复或社区节点完整连线运行。
- 纠正记录：一次完整测试命令因漏设 `PYTHONPATH` 在收集阶段失败，按文档命令重跑通过；首次注册探针漏 await，修正后通过；不存在的 portable Python 路径在真实脚本启动前失败，改用现有 venv 后只产生一次 API 请求。

## SJ-P0-20260921-001 / END / 2026-09-21T09:28:36.7055647+08:00

- 状态：completed（Semantic Judge P0 工程实现）；语义效果评测仍为未完成的独立阶段。
- 验收：SJ01–SJ14 通过；SJ15 未验证；SJ16 部分验证；SJ17 完成一次 Noul；SJ18 未验证。符合 ACCEPTANCE 的 P0 完成定义，但不得宣称语义准确率已验证。
- 产物：单节点源码、35 项测试、Noul/Choice/Score API workflow、迁移说明、状态与实施计划更新、`records/SJ-P0-20260921-001-validation.json`。
- 安装副作用：保留原有 junction，未修改 ComfyUI 核心或其他用户文件，未启动或重启常驻 ComfyUI。
- 后续：建立 SJ18 标注集评估提示词保义判断；另行补做浏览器保存恢复和社区节点完整连线验证。
- 清单安排：保留当前 redesign manifest 为历史快照，随后生成 SJ-P0 manifest 并自检，再提交实现版本。

## SJ-P0.1-20260921-001 / START / 2026-09-21T09:36:18.5584022+08:00

- 执行者：当前任务主 agent（Codex）。
- 用户目标：继续后续工作；按当前 STATUS 执行 Semantic Judge 前端保存恢复与条件节点互操作验收。
- 依据：ACCEPTANCE SJ15、SJ16；DESIGN 的固定八输入、五输出和“判断与执行分离”边界；已完成的 SJ-P0 工程实现。
- 当前状态：Git 工作区干净；本地 `127.0.0.1:8188` 已有 ComfyUI 响应，8190/8191 未占用。先以只读 HTTP 检查现有实例，不擅自重启用户进程。
- 范围：浏览器加载、保存并恢复包含多行 Unicode/options/高级字段/五输出连线的工作流；验证本地实际 `easy ifElse`、`easy compare`、`easy anythingIndexSwitch`、`easy showAnything` schema 与执行兼容；核对 lazy 分支行为。
- 外部调用边界：本任务不调用 TypeSafe，不消耗 Jev 额度。需要执行 Semantic Judge 的部分使用注入 fake backend 的真实 ComfyUI PromptExecutor；浏览器仅验证 schema、连线与序列化。
- 证据与收尾：保存可复现 workflow、必要截图或序列化摘录、HTTP/object_info 与执行器结果；更新 STATUS、验证记录、manifest 和 Git 提交。若浏览器工具不可用，如实记录并改用可复核的前端序列化测试，不把替代测试称为人工浏览器验证。

## SJ-P0.1-20260921-001 / CHECKPOINT / 2026-09-21T19:20:05.4548276+08:00

- 用户反馈与修正：用户指出当前节点似乎只有输出、没有输入接口。检查确认旧 schema 把八项都渲染成节点内控件，虽然 context 有字段，但没有左侧可连接 socket；这与 DESIGN 的“运行时 STRING、可连接”目标不一致。
- 接口修正：context 改为 ComfyUI V3 force_input=True 的必接 STRING socket；instructions、mode、options、threshold、model、connection profile、refresh 保留为节点内控件。三个基础 API workflow 与互操作 workflow 均增加 PrimitiveStringMultiline 上游。
- 隔离实测：启动 PID 54620 的 127.0.0.1:8190 CPU 实例，/object_info/JevSemanticJudge 返回 context 类型 STRING 且 forceInput=true；实际前端加载、保存、清空并重载后为 11 个节点、14 条连线，context 输入 link 仍存在，五输出类型和连线数保持。
- 前端差异：语义字段全部保持；只出现 workflow UUID 与 ue_properties.version 的正常前端重写。截图与 UI workflow 已刷新。控制台只有目标环境已有的 user.css/userdata 404 与社区扩展弃用警告，没有 Jev/Semantic Judge 错误。
- 互操作执行：目标环境实际 easy-use 类通过 PromptExecutor 消费五输出；easy ifElse 计数为选中分支 1、未选分支 0。完整 36 项 unittest 通过，未发起 TypeSafe 请求。
- 进程边界：验证后只停止隔离 PID 54620，8190 已释放；用户原有 8188 仍由 PID 46220 正常响应，未重启或停止。
- 环境提示：并行启动时隔离实例无法取得用户实例正在使用的默认 comfyui.db 锁，但前端、object_info 与节点加载均完成；该错误未影响本次 schema 与保存恢复验证。

## SJ-P0.1-20260921-001 / END / 2026-09-21T19:21:19.7239211+08:00

- 状态：completed。SJ15 前端保存恢复与 SJ16 easy-use 原生类型/惰性分支互操作均已完成。
- 最终接口：context 是唯一左侧必接 STRING socket；其余七个输入是节点内配置控件；输出仍固定为 BOOLEAN、FLOAT、INT、STRING、details_json。
- 验证：36 项 unittest、compileall、19 个第一方 JSON、33 个本地 Markdown 链接、凭证精确扫描、旧归档哈希和只读属性全部通过；本任务 TypeSafe 请求数为 0。
- 证据：records/SJ-P0.1-20260921-001-validation.json、可复现 API/UI workflow 与 output/playwright/semantic-judge-interop.png。
- Git：互操作基线提交 284474ac1d9f04c6c3a3d97238f8302a6277e2f1；context socket 修正提交 cfc00217d3d218ab898e3e74189c9d3a6c2e92e3。
- 运行边界：用户 8188 进程仍加载任务开始时的旧 schema；当前磁盘代码与 junction 已更新，待用户以后正常重启或重载 ComfyUI 后生效。本任务没有打断该进程。
- 遗留：SJ18 语义效果与阈值校准仍未完成；Choice/Score 未增加付费实测。
- 清单安排：本条之后保留 SJ-P0 manifest 为历史文件，生成新的 P0.1 manifest 并自检；随后提交验证记录与清单。

## SJ-P0.2-20260921-001 / START / 2026-09-21T19:59:03.0695890+08:00

- 执行者：当前任务主 agent（Codex）。
- 用户授权：继续实现更全面的输入能力；保留单核心节点和单 context 接口，不增加模型卡、LoRA 卡或图像专用判断节点。
- 现状：P0.1 的 context 是必接 STRING socket；TypeSafe provider 边界本身已经接受 string、object、array。目标 ComfyUI 0.34.0 的 V3 API 提供 MultiType、DICT、ARRAY、BOOLEAN、INT、FLOAT。
- 目标：把唯一 context socket 扩展为严格的 STRING / DICT / ARRAY / BOOLEAN / INT / FLOAT 多类型输入；STRING 原样发送，DICT/ARRAY 规范化后作为原生结构发送，标量包装为 JSON object。
- 拒绝边界：null 顶层、空 STRING、空 DICT/ARRAY、非字符串对象键、非有限浮点、循环结构、IMAGE/LATENT/MODEL/tensor 和任意自定义 Python 对象在 provider 调用前失败。
- 计划：先更新 AGENTS、DESIGN、ACCEPTANCE、DECISIONS 和 README 的公开契约；再用失败测试驱动 context 规范化、类型区分哈希、缓存键和 V3 MultiType schema；随后运行真实 PromptExecutor 与隔离前端保存恢复。
- 验证：覆盖六种允许输入、拒绝类型、原生 dict/list provider payload、标量包装、缓存区分、details_json 不泄漏原文、API/UI round-trip 和现有 easy-use 回归。使用 fake backend，不发起 TypeSafe 请求，不重启用户 8188 实例。

## SJ-P0.2-20260921-001 / CHECKPOINT / 2026-09-21T20:20:11.0921502+08:00

- 文档先行：新增 DEC-005，DESIGN 与 ACCEPTANCE SJ19–SJ22 固定单一多类型 context、严格 JSON 白名单、资源对象拒绝、类型保持缓存和前端验收；AGENTS 产品准则同步更新。
- 测试先行：新增测试首次按预期失败，证据包括 context_sha256 缺失、DICT 被旧协议拒绝、schema 仍为 STRING、PromptExecutor 报 DICT 与 STRING 不匹配；随后实现规范化与 MultiType schema。
- 实现：context 精确类型为 STRING,DICT,ARRAY,BOOLEAN,INT,FLOAT。字符串保持旧行为；DICT/ARRAY 深复制并校验 JSON；BOOLEAN/INT/FLOAT 包装为 {"value": value}；空状态、非字符串键、循环、非有限数、tuple、自定义对象和 tensor 在 SERVICE 调用前失败。
- 缓存与隐私：原 STRING context SHA-256 保持兼容；结构化值使用 object:/array: 前缀加规范 JSON 计算指纹，文本与对象不碰撞。details_json 不保存结构或原文；缓存键继续使用类型保持的规范 JSON。
- 自动测试：完整 45 项 unittest 已通过；真实 PromptExecutor 执行 STRING、DICT、ARRAY 与 bundled PrimitiveBoolean，fake backend 收到原生 object/array 或标量包装。实际 easy-use 惰性分支回归保持通过，TypeSafe 请求数为 0。
- 隔离实测：8190 的 /object_info 返回联合类型 STRING,DICT,ARRAY,BOOLEAN,INT,FLOAT。BOOLEAN 来源的 7 节点、6 连线工作流保存、清空、重载后类型、false 值、连线和配置保持；原 STRING easy-use 互操作工作流也重新保存恢复为联合 socket，仍为 11 节点、14 连线。
- 运行边界：两次隔离 8190 实例均使用内存数据库和独立 user directory，验证后仅停止各自 PID；用户 8188 仍由 PID 46220 正常运行，未重启。浏览器控制台只有可选 userdata 404 和既有社区扩展弃用警告，没有 Jev 节点错误。

## SJ-P0.2-20260921-001 / END / 2026-09-21T20:24:12.5618765+08:00

- 状态：completed。单一 context socket 已从 STRING 扩展为严格的 STRING、DICT、ARRAY、BOOLEAN、INT、FLOAT 联合类型，没有增加公开节点或无限制 ANY。
- 行为：DICT/ARRAY 作为原生 JSON state；标量包装为 object；资源对象与非法 JSON 在 provider 调用前失败。STRING 请求、指纹与既有 workflow 保持兼容。
- 验证：45 项 unittest、真实 PromptExecutor、多类型 /object_info、两份真实前端保存恢复、compileall、23 个第一方 JSON、36 个本地 Markdown 链接、凭证精确扫描与冻结归档检查全部通过；本任务 TypeSafe 请求数为 0。
- 证据：records/SJ-P0.2-20260921-001-validation.json、semantic-judge-multitype API/UI workflow、浏览器截图和更新后的 STRING easy-use UI workflow。
- Git：实现提交 a7e160f723090f4f07ebf60702e594b4b6f965f6。
- 运行边界：隔离 8190 实例已停止，用户 8188 PID 46220 未重启且仍响应；它需要以后正常重启或节点重载才会显示磁盘上的新联合类型 schema。
- 遗留：没有重复付费实测结构化 state；SJ18 多样本语义准确率与阈值校准仍是下一独立任务。
- 清单安排：本条后保留 P0.1 manifest，生成 P0.2 manifest 并自检，再提交验证记录与清单。

## SJ18-20260921-001 / START / 2026-09-21T21:13:11.6323471+08:00

- 执行者：当前任务主 agent（Codex）。
- 用户目标：继续后续工作；按 STATUS 与 ACCEPTANCE SJ18 建立“提示词优化是否保义”标注集并进行真实 Jev 评测。
- 范围：固定 Noul instructions、18 个独立标注样本、无重试真实评测、阈值扫描、混淆矩阵、Brier score、逐类别结果与错误清单。覆盖保义、删减、矛盾、数量变化、否定项丢失、风格变化，每类 3 例。
- 标注原则：expected=true 仅表示候选保留原文全部主体、数量、场景、构图、风格与禁止项；允许不冲突的措辞优化。明确删除、替换、矛盾、人数变化、禁止项失效或风格变化标为 false。样本采用人工构造的明确边界，不使用真实私人提示词。
- 调用边界：用户此前已授权使用本地 TypeSafe 额度。本任务最多 18 次请求，逐例只调用一次，不自动重试；发生认证、额度、限流或响应错误即停止并保留 partial 结果。凭证仅从被忽略的 local-runtime/.env.local 注入进程。
- 产物：evaluation 数据集、评测工具、脱敏逐例 JSONL、汇总 JSON/Markdown、验证记录与更新后的 STATUS/README。结果必须绑定 requested/returned model、样本数、usage、阈值和失败案例。
- 完成边界：小型人工集只能说明该任务上的初步区分能力，不能推广为通用准确率或生产校准结论。

## SJ18-20260921-001 / CHECKPOINT / 2026-09-21T21:20:56.0586475+08:00

- 文档先行：新增 `evaluation/README.md`，冻结 Noul instructions、18 例数据结构、0.50 主阈值、0.50～0.90 探索阈值、指标、隐私与解释边界。
- 数据与工具：新增六类各 3 例的 `prompt-preservation-v1.jsonl`、无自动重试的顺序评测工具及 5 项离线测试。dry-run 确认 18 例结构有效且请求数为 0。
- 回归：插件既有 45 项 unittest 全部通过；评测工具测试通过，未改变公开节点或运行时协议。
- 真实评测：仅运行一次完整 v1，18 次请求全部成功，无重试、无缓存命中和服务错误。请求模型 `jev-latest`，实际模型均为 `jev-1.13.0`；总用量 7054 input / 360 output tokens，总记录耗时 15329 ms。
- 结果：0.50～0.90 均为 TP=3、TN=15、FP=0、FN=0；Brier score 0.0013388888888888895。正例均为 0.96，反例为 0.01～0.10，没有首轮误判。
- 解释：该集合由明确、短小的英文人工样本组成，类别为 3 正/15 负；结果记为基础可行性通过，不称通用准确率、真实工作负载泛化或生产阈值校准。
- 证据目录：`evaluation/runs/20260921T212008+0800/`；逐例文件只记录 ID、标签、概率、模型、usage、耗时和 context 哈希，不复制提示词或凭证。

## SJ18-20260921-001 / END / 2026-09-21T21:24:03.7333246+08:00

- 状态：completed。完成固定协议、标注数据、可复现工具、真实评测、脱敏逐例结果、汇总报告和验证记录。
- 验收：满足 ACCEPTANCE SJ18 对正例、删减、矛盾、数量变化、否定项丢失、风格变化，以及阈值、模型、样本数和错误报告的要求。主阈值 0.50 无误判，但只称基础可行性通过。
- 验证：5 项评测工具测试、45 项插件回归、compileall、dry-run、26 个 JSON、2 个 JSONL、37 个本地 Markdown 链接、凭证精确扫描、输出原文泄漏扫描和冻结归档哈希检查均通过。
- 安全与副作用：共提交 18 次已授权 TypeSafe 请求，0 自动重试；密钥未写入产物。用户 8188 进程 PID 46220 未重启，插件 junction 目标未改变。
- 证据：`records/SJ18-20260921-001-validation.json` 和 `evaluation/runs/20260921T212008+0800/`。首轮数据、instructions 和结果保持不覆盖。
- 后续：建立独立的 SJ18-v2 难例与真实分布集，并将阈值选择集和最终验证集分开；不在 v1 上继续调参后宣称泛化。

## SJ18-V2-20260921-001 / START / 2026-09-21T21:27:02.2339407+08:00

- 执行者：当前任务主 agent（Codex）。
- 用户目标：继续下一阶段；按 STATUS 建立比 v1 更难、能独立选择和验证阈值的提示词保义评测。
- 数据设计：12 组最小差异对、共 24 例；每组共享一个较长原提示词，一个候选完整保义，另一个候选只改变一项约束。中英文各 12 例，calibration 与 validation 各 12 例且均为 6 正/6 负。
- 负例类型：删减、矛盾、数量或关系变化、否定/排除项失效、风格或媒介变化、属性归属/范围变化；每类在两个 split 各出现一次。
- 协议：沿用 v1 已冻结的 Noul instructions，避免看到结果后改题；0.50 保持参考阈值。另在 calibration 上按预先固定的 0.05～0.95 网格选择 balanced accuracy 最大阈值，平局选择最接近 0.50、再选择较低值，并只在 validation 上报告该阈值的独立结果。
- 指标：两个 split 的混淆矩阵、balanced accuracy、Brier、AUROC；12 组正例概率是否高于配对负例及 margin；逐语言、逐错误类型结果和失败清单。
- 调用边界：用户此前已授权使用本地 TypeSafe 额度。本任务最多 24 次新请求，每例一次、0 自动重试；认证、额度、限流、网络或响应错误立即停止并保留 partial。凭证仍只从被忽略的 `.env.local` 注入。
- 完成边界：v2 仍为人工诊断集，不称真实生产分布；若结果暴露失败，原样保留首轮结果，不修改标签、instructions 或重跑掩盖错误。

## SJ18-V2-20260921-001 / CHECKPOINT / 2026-09-21T21:35:43.4227951+08:00

- 文档与数据：先新增 `evaluation/V2-PROTOCOL.md`，冻结 12 组最小差异对、两个 split、语言/类别平衡、阈值选择和指标；随后写入 24 例 v2 数据集。数据集 SHA-256 为 `7e42c7cfc3153b6c950242400f518bc62c06d89081bf55a722effdac890c9dd4`。
- 离线验证：10 项评测工具测试与45项插件回归通过；compileall 和 dry-run 通过，dry-run 请求数为0。v1 文件与结果未修改。
- 真实评测：只运行一次完整 v2；24次请求全部成功，0自动重试，实际模型均为 `jev-1.13.0`，合计13561 input / 480 output tokens，记录总耗时20905 ms。
- 阈值：calibration 的0.05～0.95预设网格按既定规则选择0.50。calibration 为TP=6、TN=5、FP=1、FN=0，balanced accuracy 0.9167、Brier 0.08757、AUROC 0.95833；validation 为TP=6、TN=6、FP=0、FN=0，balanced accuracy 1.0、Brier 0.02441、AUROC 1.0。
- 全集与配对：全体TP=12、TN=11、FP=1、FN=0，balanced accuracy 0.9583、AUROC 0.98958。12/12组的正例概率均高于配对负例，平均margin 0.6758，最小margin 0.16。
- 真实失败：`c01-negative` 只删除“前景不得出现成品陶器”而未主动加入成品，模型返回0.76并在0.50下形成唯一假阳性。两条 deletion 负例均值0.59；其他负例类型均无假阳性。该失败保持原样，没有改标签、改 instructions 或重跑。
- 解释：v2 支持“中英文较长提示词上基础可用”的结论，同时证明纯语义判断对遗漏型硬约束存在风险。生产方案应保留概率、设置复核区间，并对可枚举硬约束使用确定性检查或逐项判断。

## SJ18-V2-20260921-001 / CORRECTION / 2026-09-21T21:37:52.8104641+08:00

- CHECKPOINT 中“v1 文件与结果未修改”的精确含义应为：v1 数据集、评测工具、逐例结果、summary、report 和冻结 instructions 未修改。共享的 `evaluation/README.md` 追加了 v2 入口，因此其文件哈希相对 v1 验证记录发生预期变化；历史 v1 manifest 和验证记录未改写。

## SJ18-V2-20260921-001 / END / 2026-09-21T21:38:43.7315696+08:00

- 状态：completed。完成成对难例协议、24例平衡数据、独立 calibration/validation 阈值流程、真实 API 首轮、脱敏结果、报告和验证记录。
- 验收：calibration 只负责选阈值，validation 不参与选择；0.50 被选中并在 validation 上获得TP=6、TN=6、FP=0、FN=0。全体仍保留唯一假阳性，不把成对排序正确替代成分类正确。
- 验证：10项评测测试、45项插件回归、compileall、dry-run、29个JSON、4个JSONL、41个本地Markdown链接、凭证扫描、v2输出原文泄漏扫描和冻结归档哈希检查通过。
- 外部副作用：共24次已授权TypeSafe请求，0重试；凭证未记录。8188仍为PID 46220，未重启或修改用户运行实例。
- 证据：`records/SJ18-V2-20260921-001-validation.json`、`evaluation/runs/v2/20260921T213420+0800/` 和实现提交 `e57772636b0a75bba7a647ad5fcbee3f144b1e94`。
- 后续：构建一个使用现有DICT/JSON构造节点和lazy条件节点的“候选提示词保义则采用，否则回退原文”真实ComfyUI工作流，验证从两个字符串输入到最终选择输出的完整连接体验。

## REVIEW-HARDENING-20260922-001 / START / 2026-09-22T02:20:18.0828412+08:00

- 执行者：当前任务主 agent（Codex）。
- 用户输入：外部评审确认 manifest 与冻结归档无漂移，并指出 Choice/Score 零真实响应、严格字段策略、缓存版本/TTL、旗舰用例门控、首次凭证体验、网络延迟、测试可移植性、LICENSE、命名与文档漂移等问题。
- 核验原则：逐条以当前源码、文档和真实环境为准；评审意见是待验证证据，不直接当作项目事实。确认项与不同意项均留下理由。
- 第一闭环：新增凭证安全的 Choice/Score 真实烟雾工具，各最多请求一次、0自动重试，记录原始字段集合、已知值、requested/returned model、usage、耗时和本地严格校验结果，不记录 key、prompt 或 Authorization。
- 第二闭环：依据真实响应决定未知字段策略并写入 DECISIONS；保持已知字段和值严格校验，评估是否应容忍并保留供应方新增字段，避免未经证据直接改 details_json schema。
- 第三闭环：构建“提示词优化 adopt/review/reject”三态工作流配方，复用现有节点；不把 v2 的 0.50/0.80 直接冒充生产校准，不向插件核心加入业务节点。
- 顺手修复范围：DESIGN/ACCEPTANCE/DECISIONS 的确认漂移、`refresh` 精确语义、凭证/外发/费用/延迟/取消说明、Choice confidence 定义、easy-use 测试缺失时跳过、LICENSE 发布门槛与旧 pycache 污染。TTL、节点命名、错误码提取和限速若不能在本闭环充分设计，则形成明确后续项，不仓促混改。
- 外部调用：用户此前已授权使用本地 TypeSafe 额度；本任务最多2次新请求，Choice与Score各1次。用户8188实例不重启。

## GITHUB-PUBLIC-20261016-001 / START / 2026-10-16

- 授权：用户要求将本项目发布到 GitHub 账号 2426269，并明确选择公开及 MIT 许可证；已通过 GitHub API 确认当前 CLI 身份为 2426269。
- 范围：补充根目录与 nodepack 的 MIT LICENSE；更新发布边界说明；从当前工作区整理不含凭证、运行目录、第三方研究副本和旧归档的公开源码快照。保留原工作区未知修改，不重置、不改行为，不重启 ComfyUI，不调用付费推理。
- 依据：AGENTS 第6/9节、DESIGN 第8/11/14节、ACCEPTANCE 第9节及 PUBLISHING 的许可证门槛。此次为公开开发源码快照，不创建稳定版 Release，不据此宣称最低兼容矩阵、生产阈值或其他未完成发布项已通过。
- 验证计划：工作树与发布清单核验、脱敏凭证候选扫描、离线测试、公开远端所有者/可见性及提交哈希核验。第三方研究代码不上传；历史证据快照与当前发布清单分开。

## GITHUB-PUBLIC-20261016-001 / END / 2026-10-16

- 状态：completed。第一方开发源码以 MIT 公开至 https://github.com/2426269/ComfyUI-Jev-Decision ，首次公开提交为 `1c570cb6307560b24b928db1d3fba5be7ec51c67`，通过 GitHub API 核对所有者 2426269、public 可见性、MIT 识别及远端/本地 SHA 相等。
- 验证：在独立发布副本、现有 Python 3.12 / ComfyUI 环境中运行 nodepack 完整 unittest，47 项通过；使用 fake backend，0 次外部 TypeSafe 请求。源码候选凭证扫描无未解释命中，没有上传 research、私人运行目录、密钥、缓存或旧归档。
- 变更：仅添加授权的 MIT 许可证和发布边界/状态记录；未修改运行时逻辑，未重置本地未知修改，未更改原仓库远程，未重启用户实例。公开仓库由隔离副本生成，不提交原工作树。
- 解释：这是源码公开展示，不是稳定版 Release；原有最低兼容矩阵、生产阈值等待办仍未因此完成。当前快照另有 PUBLICATION-MANIFEST.json，历史清单不冒充当前哈希。
- 收尾：本条和 STATUS 完成后备份旧 manifest，刷新原工作区与公开副本清单，再推送文档收尾提交；实际最终远端 SHA 记入本轮交付核验，不反复把 SHA 写进清单造成自引用。
