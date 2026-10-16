# ComfyUI Semantic Judge

> **公开开发快照 / 2026-10-16**：本项目已由权利人选择 [MIT 许可证](LICENSE)。源码与文档供学习、复现和项目展示；不等同稳定版 Release。本人负责需求、协议/流程设计与验证，代码借助 AI 实现。供应方模型及 ComfyUI 底层框架并非本项目研发，当前限制见 [发布边界](PUBLISHING.md)。

日期：2026-09-21。状态：单节点 P0.2 已完成工程验证；SJ18 小型语义可行性评测已完成。

> Turn semantic uncertainty into native ComfyUI signals.

插件公开一个 `JevSemanticJudge` 节点。它把运行时文本、JSON 状态或基础标量交给 TypeSafe Jev 做 Noul、Choice 或 Score 判断，并固定输出 ComfyUI 原生的 `BOOLEAN / FLOAT / INT / STRING`，外加完整、可审计的 `details_json`。

> 使用前必须配置 TypeSafe API key。连接到 `context` 的内容和完整 `instructions` 会发送到 TypeSafe 云服务，请求可能产生费用；缺少凭证、网络失败或响应异常会让节点报错停止，不会返回默认 `false`。

它只负责“判断并转换为原生信号”。提示词修改、模型和 LoRA 加载、工作流扫描、对象路由与条件执行继续由现有 ComfyUI 节点负责。

## 节点形态

```text
STRING / DICT / ARRAY / BOOLEAN / INT / FLOAT
      │
      ▼
┌──────────────────────────┐
│ Semantic Judge           │
│ Noul / Choice / Score    │
└───┬─────┬─────┬─────┬────┘
   BOOL FLOAT  INT STRING details_json
      │
      ▼
existing ComfyUI nodes
```

输入固定为 `context`、`instructions`、`mode`、`options`、`threshold`、`model`、`connection_profile`、`refresh`。其中 `context` 是左侧必接多类型 socket，接受 `STRING / DICT / ARRAY / BOOLEAN / INT / FLOAT`；其余配置保留为节点控件。五个输出位置始终不变。`threshold` 只在本地派生 BOOLEAN，因此只改阈值不会再次请求 API。`refresh` 是缓存键盐值：换成未使用值会重新判断，切回旧值仍可能命中旧缓存。

DICT/ARRAY 会作为原生 JSON state 发送，基础标量包装为 `{"value": ...}`。IMAGE、LATENT、MODEL、VAE 和 tensor 不会被隐式序列化；先用上游节点提取描述、标签、名称、尺寸或其他 JSON 元数据。

Choice 与 Score 的 `options` 每行一个：

```text
stable_id | optional description
```

`examples` 目录提供 Noul、Choice、Score、多类型 socket、easy-use 互操作和提示词三态审查 workflow。三态配方从两个动态 STRING 构造 context，仅在保义概率达到示例高阈值时采用候选，中间区间提示人工复核并自动回退原文。安装、凭证和输出映射见[插件说明](plugin/ComfyUI-Jev-Decision/README.md)。

## 当前验证

- 47 项自动测试通过，覆盖纯协议、前向兼容响应、多类型 context、缓存、V3 schema、真实 `PromptExecutor`、三态配方与本地 easy-use 互操作；自动测试不访问外部服务。
- 目标 ComfyUI 通过 junction 加载源码，注册表只出现 `JevSemanticJudge`。
- 一次已授权的新节点 Noul 冒烟成功：请求 `jev-latest`，返回 `jev-1.13.0`，Noul `0.94`，347/20 tokens，约 992 ms。
- 五个输出均已在真实执行器中消费；`easy ifElse` 的计数测试证明未选分支不会执行。
- 浏览器已完成互操作工作流的保存与重新载入，context 输入 socket、Unicode、多行文本、options 顺序、高级字段、11 个节点和 14 条连线均保持；差异仅为前端自动生成的 workflow UUID 与版本元数据。
- 隔离前端确认 context schema 为 `STRING,DICT,ARRAY,BOOLEAN,INT,FLOAT`；BOOLEAN 连线的 7 节点、6 连线 workflow 保存、清空和重载后保持。
- 可复现文件：[API workflow](plugin/ComfyUI-Jev-Decision/examples/semantic-judge-interop.api.json)、[UI workflow](plugin/ComfyUI-Jev-Decision/examples/semantic-judge-interop.workflow.json) 和[浏览器截图](output/playwright/semantic-judge-interop.png)。
- 多类型证据：[API workflow](plugin/ComfyUI-Jev-Decision/examples/semantic-judge-multitype.api.json)、[UI workflow](plugin/ComfyUI-Jev-Decision/examples/semantic-judge-multitype.workflow.json) 和[浏览器截图](output/playwright/semantic-judge-multitype.png)。
- SJ18 使用固定 instructions 和 18 个独立标注样本做了一次无重试真实 Noul 评测。请求 `jev-latest`，18 次均返回 `jev-1.13.0`；固定阈值 0.50 得到 TP=3、TN=15、FP=0、FN=0，Brier score 为 0.0013389。完整协议、数据集和限制见[评测说明](evaluation/README.md)，逐例概率与汇总见[首轮报告](evaluation/runs/20260921T212008+0800/report.md)。
- SJ18-v2 使用 12 组中英文最小差异对和独立 calibration/validation split。24 次请求全部返回 `jev-1.13.0`；0.50 下全体为 TP=12、TN=11、FP=1、FN=0，validation 为 6/6 全对，12 组概率排序全部正确。唯一误判是候选漏掉一项禁止要求但没有显式违反，模型给出 0.76。协议见[v2 设计](evaluation/V2-PROTOCOL.md)，完整结果见[v2 报告](evaluation/runs/v2/20260921T213420+0800/report.md)。
- Choice/Score 各一次真实烟雾均返回 `jev-1.13.0` 并通过严格语义校验；字段、usage、耗时和映射见[脱敏证据](records/choice-score-smoke-20260922.json)。
- 三态提示词配方的 [API workflow](plugin/ComfyUI-Jev-Decision/examples/prompt-preservation-tristate.api.json)、[UI workflow](plugin/ComfyUI-Jev-Decision/examples/prompt-preservation-tristate.workflow.json) 与[前端截图](output/playwright/prompt-preservation-tristate.png)已经通过 PromptExecutor 和隔离前端往返。

两轮 SJ18 证明了这个插件形态能在明确样本和较难的中英文最小差异对上判断提示词保义。v2 同时揭示了重要限制：模型可能把“没有复述某条禁止项”当作仍然保义。因此生产工作流不能只依赖一个看似很高的 Noul 概率；对不可丢失的硬约束，仍应配合确定性检查或更保守的人工复核区间。这些人工样本不能解释为通用准确率或生产阈值已经验证。

## 项目文档

1. [Agent 工作约定](AGENTS.md)
2. [当前状态](STATUS.md)
3. [完整设计](DESIGN.md)
4. [验收计划](ACCEPTANCE.md)
5. [重设计说明](docs/plans/2026-09-21-semantic-judge-redesign.md)
6. [重要决定](DECISIONS.md)
7. [任务日志](TASK_LOG.md)
8. [实施记录](docs/superpowers/plans/2026-09-21-semantic-judge-rewrite.md)
9. [SJ18 语义评测](evaluation/README.md)
10. [SJ18-v2 成对难例协议](evaluation/V2-PROTOCOL.md)

## 冻结的旧实验

DEC-004 之前的四节点 P0 已冻结为只读归档：

```text
records/artifacts/ComfyUI-Jev-Decision-P0-baseline-20260921T0854+0800.zip
SHA-256 a9c71a714566f64a653dcfe6c0dde534645872a1f5625747d918267638bec370
```

归档不包含凭证、缓存或第三方 research。旧节点不再注册，也没有兼容别名；旧工作流需手工替换为一个 `JevSemanticJudge`。

## 研究来源

- [TypeSafe 官方 Python SDK](https://github.com/typesafe-ai/typesafe-sdk-python)
- [hndrr/ComfyUI-Jev 固定源码研究](REPOSITORY-REVIEW.md)

API key 只保存在被 Git 忽略的 `local-runtime/.env.local`，不会进入工作流、日志、验证记录或 manifest。
