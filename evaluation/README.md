# SJ18 提示词保义评测

这套评测回答一个窄问题：给定原提示词 `original` 和经过处理的 `candidate`，Jev 的 Noul 概率能否区分“全部显式要求仍被保留”和“至少一项要求被改变或丢失”。它验证 `Semantic Judge` 能否作为这类工作流的判断器，不把结果推广成 Jev 的通用准确率。

## 固定任务

每个样本把以下原生 DICT 作为 `context` 发送给 TypeSafe：

```json
{"original":"...","candidate":"..."}
```

所有请求使用同一条 Noul instructions：

> Decide whether candidate preserves every explicit requirement in original, including subjects, counts, attributes, actions, setting, time, composition, visual style, and prohibitions. Rewording and compatible added detail are allowed only when no requirement is removed, contradicted, weakened, or changed. Return true only when all explicit requirements are preserved.

`true` 表示完全保义。兼容原要求的补充细节可以存在；删减、矛盾、数量变化、禁止项失效或风格变化均为 `false`。

## 数据集

`prompt-preservation-v1.jsonl` 固定包含 18 个手工构造、无私人内容的明确样本，每类 3 个：

| category | expected | 含义 |
| --- | --- | --- |
| `preserved` | true | 改写保留全部显式要求 |
| `deletion` | false | 删除一项要求 |
| `contradiction` | false | 与一项要求直接冲突 |
| `count_change` | false | 显式数量发生变化 |
| `prohibition_dropped` | false | 禁止项被违反或失效 |
| `style_change` | false | 显式视觉风格被替换 |

每行必须精确包含 `id`、`category`、`expected`、`original`、`candidate` 和 `rationale`。ID 唯一；文本字段非空；`expected` 必须是 JSON boolean。数据集有 3 个正例和 15 个反例，类别覆盖优先于类别平衡，因此不能只看普通 accuracy。

## 运行与输出

先做不联网校验：

```powershell
Set-Location -LiteralPath 'E:\comfyui\Jev-Decision-Design'
& 'E:\comfyui\ComfyUI-NAI\.venv\Scripts\python.exe' '.\tools\evaluate_prompt_preservation.py' --dry-run
```

真实评测从被 Git 忽略的 `local-runtime/.env.local` 读取 `TYPESAFE_API_KEY`：

```powershell
& 'E:\comfyui\ComfyUI-NAI\.venv\Scripts\python.exe' '.\tools\evaluate_prompt_preservation.py' --max-requests 18
```

工具顺序执行，每例最多一次请求，不自动重试。认证、额度、限流、网络或响应校验错误会立即停止；已经完成的脱敏结果保留在 `evaluation/runs/<run-id>/`。逐例记录只包含样本 ID、标签、Noul 概率、模型、usage、耗时和错误，不复制 prompt，也不记录密钥或请求头。

固定主阈值为 `0.50`，在看到结果之前确定。另报告 `0.50 / 0.60 / 0.70 / 0.80 / 0.90` 的混淆矩阵、accuracy、balanced accuracy、precision、recall、specificity 和 F1；“best observed threshold”只用于描述这 18 例，不能称为生产阈值。Brier score 使用原始 Noul 概率计算。

## 解释边界

- 人工小样本适合发现明显失败模式，不足以估计真实提示词分布上的泛化误差。
- 正反例不平衡；以 balanced accuracy、正例 recall 和反例 specificity 一起解释。
- Jev 服务的实际模型版本可能由 `jev-latest` 指向不同版本，报告必须保存 requested model 与 returned model。
- 这次评测只覆盖 Noul 和英文明确样本，不证明中文、长提示词、Choice 或 Score 的效果。
- 首轮结果原样保留。若以后修改 instructions 或数据集，应提升版本并创建新 run，不能覆盖本次证据。

## v2

v1 冻结后新增了独立的 [SJ18-v2 成对难例协议](V2-PROTOCOL.md)和 `prompt-preservation-v2.jsonl`。v2 使用 12 组中英文最小差异对，将 calibration 与 validation 分离，并增加 AUROC 与 pair margin。首轮真实结果位于 `runs/v2/20260921T213420+0800/`；它没有覆盖或重算 v1。
