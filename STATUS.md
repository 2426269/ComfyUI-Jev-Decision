# 当前状态

## 2026-10-16 公开源码准备

- 用户明确授权公开至 GitHub 2426269，并为第一方代码选择 MIT；根目录及 nodepack LICENSE 已添加。
- 公开范围为经过筛选的开发源码、文档、样例与脱敏证据；排除 local-runtime 私人配置、research 第三方副本、旧归档、缓存与浏览器状态。
- 本次不改变运行时逻辑、不提交付费请求、不重启用户实例；不将公开快照等同稳定版发布，以下历史实现/验证状态保持原口径。

更新日期：2026-09-22。当前阶段：Semantic Judge P0.3 契约与三态配方加固已实现；SJ18-v1 基础集与 SJ18-v2 中英文成对难例评测均已完成。

## 已实现

公开节点只有 `JevSemanticJudge`：

- 八个固定输入：context、instructions、Noul/Choice/Score、options、threshold、model、connection profile、refresh。
- `context` 是一个必接联合类型 socket，接受 STRING、DICT、ARRAY、BOOLEAN、INT、FLOAT。DICT/ARRAY 以原生 JSON state 发送；标量包装为 object；资源对象在网络调用前拒绝。
- 五个固定输出：BOOLEAN、FLOAT、INT、STRING、details_json。
- Choice 2～255 项；Score 2～10 个有序等级；稳定 ID 与显示说明分离。
- 严格校验 TypeSafe JSON 的必需字段和三种 answer 语义；供应方新增字段兼容，decision answer 的新增字段保留；错误不会被解释成否。
- 进程内有界 LRU 缓存，合并并发相同请求；threshold 不进入缓存键，refresh 是缓存键盐值，不是删除命令。
- details_json 保存完整 answer、实际模型、usage、耗时、缓存信息和输入哈希，不保存 context/instructions 原文。

目标 ComfyUI 的 junction 指向当前源码：

```text
E:\comfyui\ComfyUI-NAI\custom_nodes\ComfyUI-Jev-Decision
```

注册探针确认唯一节点 ID 为 `JevSemanticJudge`。旧四节点只存在于冻结归档和历史文档，不再注册。

## 验证状态

- SJ01–SJ14：通过。既有行为保持。
- SJ15：通过。以隔离的实际 8190 前端加载 API workflow，保存为 UI workflow，清空后重新载入；context STRING 输入 socket、多行 Unicode、options 顺序、threshold、model、connection profile、refresh、五输出类型和连线数量均保持。工作流为 11 个节点、14 条连线；仅 workflow UUID 与前端版本元数据被正常重写。8190 验证后已关闭，用户的 8188 实例未重启。
- SJ16：通过。实际 `/object_info` 确认本地 easy-use schema；真实 PromptExecutor 使用这些安装类消费五个输出。`easy ifElse` 的计数探针结果为选中分支 1 次、未选分支 0 次。
- SJ17：通过一次 Noul 真实烟雾。请求 `jev-latest`，返回 `jev-1.13.0`、Noul `0.94`、347 输入 token、20 输出 token、992 ms。
- SJ18-v1：基础可行性通过。固定 18 个英文人工样本、18 次无重试 Noul 请求全部成功，`jev-latest` 实际返回 `jev-1.13.0`。固定阈值 0.50 和探索阈值 0.60/0.70/0.80/0.90 均为 TP=3、TN=15、FP=0、FN=0；Brier score 0.0013389，使用量合计 7054 input / 360 output tokens。正例概率均为 0.96，反例范围 0.01～0.10。
- SJ18-v2：成对难例完成。12 组、24 个较长样本，中英文各半；calibration 和 validation 各为 6 正/6 负。24 次无重试请求全部返回 `jev-1.13.0`，用量 13561 input / 480 output tokens。calibration 选择阈值 0.50；全体 TP=12、TN=11、FP=1、FN=0，balanced accuracy 0.9583、Brier 0.05599、AUROC 0.98958；独立 validation TP=6、TN=6、无误判，balanced accuracy 与 AUROC 均为 1.0。12/12 pair 排序正确，平均 margin 0.6758，最小 0.16。
- SJ18-v2 失败边界：`c01-negative` 删除“前景不得出现成品陶器”但不主动违反，模型给出 0.76，被 0.50 阈值误判为保义。两例 deletion 的平均概率 0.59，显著高于其他错误类型；遗漏型硬约束应结合确定性检查、逐项问题或人工复核。
- SJ19–SJ22：通过。45 项 unittest 覆盖六种允许类型、拒绝类型、结构化 provider state、缓存和指纹；实际 `/object_info` 返回 `STRING,DICT,ARRAY,BOOLEAN,INT,FLOAT`。BOOLEAN 连线的 7 节点、6 连线 workflow 在隔离前端保存恢复后保持。
- SJ23：通过。Choice 与 Score 各一次真实请求，均返回 `jev-1.13.0` 且通过本地严格语义校验。Choice 为 347 input / 31 output token、859 ms；Score 为 333 input / 17 output token、826 ms；共 2 次请求、0 自动重试。
- SJ24：通过。响应验证改为已知语义严格、未知字段兼容；47 项完整协议/执行测试继续通过，decision answer 额外字段进入 details_json，顶层额外字段不传播，缺失必需字段仍失败。
- SJ25：通过。目标环境没有通用 JSON/DICT 构造器，配方改用内置 `StringConcatenate` 安全组合两个动态 STRING。三态为 `p >= 0.80` adopt、`0.50 <= p < 0.80` review、`p < 0.50` reject；review/reject 的自动路径回退原文。真实 PromptExecutor 对 0.90/0.65/0.20 三种 fixture 路由正确，高概率时未执行内部 review/reject lazy 分支。隔离 8190 前端的 18 节点、20 连线 workflow 保存、清空、重载后保持，用户 8188 未重启。

因此当前可称为 **Semantic Judge P0.3 工程与组合配方可用，并在 SJ18-v1/v2 上证明提示词保义判断具有基础可行性**。仍不能称为通用语义准确率或真实工作负载上的阈值已经验证；删除型约束是已经实测到的风险。

## 互操作记录

本地运行实例和 `comfyui-easy-use` 实际执行类中已确认：

| 输出 | class_type | 目标输入 |
| --- | --- | --- |
| BOOLEAN | `easy ifElse` | `boolean` |
| FLOAT | `easy compare` | `a` 或 `b` |
| INT | `easy anythingIndexSwitch` | `index` |
| STRING / details_json | `easy showAnything` | `anything` |

FLOAT 比较基准使用 `easy float` 输出连接到 `easy compare.b`；直接在通配输入中填写裸浮点值会被目标 ComfyUI 校验器误当成枚举值。插件不内置 Router。真正避免未选分支执行，需要下游消费者自身支持 lazy input；`easy ifElse` 的 `check_lazy_status` 已由真实执行器验证。

可复现互操作工作流：

- `plugin/ComfyUI-Jev-Decision/examples/semantic-judge-interop.api.json`
- `plugin/ComfyUI-Jev-Decision/examples/semantic-judge-interop.workflow.json`
- `output/playwright/semantic-judge-interop.png`
- `plugin/ComfyUI-Jev-Decision/examples/semantic-judge-multitype.api.json`
- `plugin/ComfyUI-Jev-Decision/examples/semantic-judge-multitype.workflow.json`
- `output/playwright/semantic-judge-multitype.png`
- `plugin/ComfyUI-Jev-Decision/examples/prompt-preservation-tristate.api.json`
- `plugin/ComfyUI-Jev-Decision/examples/prompt-preservation-tristate.workflow.json`
- `output/playwright/prompt-preservation-tristate.png`

## 已冻结成果

- 只读归档：`records/artifacts/ComfyUI-Jev-Decision-P0-baseline-20260921T0854+0800.zip`
- SHA-256：`a9c71a714566f64a653dcfe6c0dde534645872a1f5625747d918267638bec370`
- Git 重写前基线：`ecfe40b`

## 下一步

下一阶段若进入对外发布，应先由权利人选择 LICENSE，再决定公开节点 ID、最低兼容矩阵、发布物/证据清单分离、缓存 TTL/模型版本策略、供应方错误码白名单提取和批量限速边界。当前不因尚未发布而破坏已经验证的 `JevSemanticJudge` 工作流。
