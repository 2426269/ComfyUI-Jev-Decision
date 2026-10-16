# SJ18-v2 成对难例协议

SJ18-v2 在 v1 的基础可行性结果之后冻结。它继续评估同一个问题：候选改写是否保留原提示词的每一项显式要求。v2 不修改插件节点，也不修改 v1 的数据、instructions 或结果。

## 1. 设计目标

v1 的 18 个样本短、明确，而且只有 3 个正例。v2 使用 12 组最小差异对，共 24 个样本：

- 每组共享同一个较长原提示词。
- `positive` 候选通过重排、近义改写或兼容补充保留全部要求。
- `negative` 候选以 positive 为基础，只删除或改变一个受保护约束。
- calibration 和 validation 各 6 组、12 例，均为 6 正例和 6 反例。
- 中文和英文各 6 组、12 例；两个 split 各包含 3 组中文和 3 组英文。

六种负例变化在 calibration 和 validation 中各出现一次：

1. `deletion`
2. `contradiction`
3. `count_or_relation`
4. `prohibition_violation`
5. `style_or_medium`
6. `attribute_scope`

数据集使用 `pair_id` 将同源正反例配对。除了分类指标，还检查每组 `p(positive) > p(negative)` 以及概率 margin。

## 2. 冻结的判断任务

v2 沿用 v1 的英文 Noul instructions，不根据 v1 或 v2 的结果调整：

> Decide whether candidate preserves every explicit requirement in original, including subjects, counts, attributes, actions, setting, time, composition, visual style, and prohibitions. Rewording and compatible added detail are allowed only when no requirement is removed, contradicted, weakened, or changed. Return true only when all explicit requirements are preserved.

每次请求仍发送原生 DICT：

```json
{"original":"...","candidate":"..."}
```

数据集每行精确包含：`id`、`pair_id`、`split`、`language`、`expected`、`change_type`、`original`、`candidate`、`rationale`。原文和理由只存在于公开测试数据集，不复制到运行结果。

## 3. 阈值选择

`0.50` 保留为预先固定的参考阈值。另在 calibration split 上扫描 `0.05, 0.10, …, 0.95`：

1. 选择 balanced accuracy 最大的阈值。
2. 若并列，选择最接近 0.50 的阈值。
3. 若与 0.50 距离也相同，选择较低阈值。

选定规则在看到输出前写定。validation 标签不参与阈值选择；报告同时给出 validation 在 0.50 和 calibration-selected threshold 下的结果。

## 4. 指标与成功边界

分别对 calibration、validation 和全体样本报告：

- 混淆矩阵、accuracy、balanced accuracy、precision、recall、specificity、F1。
- Brier score 与 AUROC。
- 中文/英文结果。
- 六种负例变化的概率和误判。
- 12 个 pair 的正负概率、margin、正确排序数。

这是一套人工诊断集。即使 validation 完全正确，也只说明当前模型在这些成对难例上表现良好；它仍不代表真实用户提示词分布、跨模型版本稳定性或经过独立大样本校准的生产阈值。

## 5. 调用和证据

工具最多提交 24 次 TypeSafe 请求，每例一次，不自动重试。认证、额度、限流、网络或响应校验错误会立即停止，已经完成的结果保留为 partial。结果记录样本 ID、pair、split、语言、标签、Noul 概率、实际模型、usage、耗时和输入哈希，不记录 API key、Authorization header 或提示词原文。

运行前先执行 dry-run；真实首轮结果一旦产生即冻结，不因误判修改标签或重跑。
