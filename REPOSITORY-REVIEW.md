# hndrr/ComfyUI-Jev 源码研究

调研日期：2026-09-21。

仓库：[hndrr/ComfyUI-Jev](https://github.com/hndrr/ComfyUI-Jev)。固定提交：`12239dab9f03cd4c3dead4b043028ea602b8d43b`，提交时间 `2026-09-20T15:49:46+09:00`。本地副本在 [research/ComfyUI-Jev](research/ComfyUI-Jev)。下列结论针对这一提交，不代表后续版本。

研究方式：阅读节点、语义层、API 层、推荐流程、节点文档与执行测试源码。没有安装插件、运行其测试、调用 TypeSafe/OpenRouter 或做图像生成。测试文件存在只能证明作者设计了相应覆盖，不能报告为本次测试通过。

## 1. 作者选择的产品形态

该实现以直接处理文本为入口，公开注册三个节点：

| 节点 | 职责 |
| --- | --- |
| Jev Interpret | 一个节点内选择、布尔判断、多选、评分、数值提取、推荐 |
| Jev Skill Choice | 发现本地 SKILL.md，筛选并输出内容和优先级 |
| OpenRouter Text | 文本生成或生成完整候选项 |

证据：[nodes.py 注册列表及类定义](https://github.com/hndrr/ComfyUI-Jev/blob/12239dab9f03cd4c3dead4b043028ea602b8d43b/nodes.py#L179)。项目配置标记版本 0.1.1、Python >=3.10、ComfyUI >=0.36.0，依赖 aiohttp 与 PyYAML，采用 V3 `ComfyExtension`/`io.ComfyNode`。这是它声明的最低版本，不是我们方案已经验证的兼容范围。[pyproject.toml](https://github.com/hndrr/ComfyUI-Jev/blob/12239dab9f03cd4c3dead4b043028ea602b8d43b/pyproject.toml)

这一形态的主要优点是接线少：选中的完整候选文本直接进入后续文本编码节点。它不是毫无结构的 API 包装，内部已经有明确的语义编译与结果映射层。

## 2. 最有价值的内部设计

### 2.1 问题编译、响应校验、结果映射分离

`semantics.py` 中：

| 函数 | 作用 |
| --- | --- |
| `text_task` | 将 UI 任务与候选转成内部 schema 和 bindings |
| `compile_questions` | 将 schema 转成 Jev questions，记录本地解析计划 |
| `collect_judgments` | 校验响应并收集各字段判断 |
| `resolve` | 用阈值、映射、范围、默认值解析为应用值 |

证据：[编译](https://github.com/hndrr/ComfyUI-Jev/blob/12239dab9f03cd4c3dead4b043028ea602b8d43b/semantics.py#L119)、[收集](https://github.com/hndrr/ComfyUI-Jev/blob/12239dab9f03cd4c3dead4b043028ea602b8d43b/semantics.py#L203)、[映射](https://github.com/hndrr/ComfyUI-Jev/blob/12239dab9f03cd4c3dead4b043028ea602b8d43b/semantics.py#L251)。

启发：我们的 Context/Questions/Result 并不是必须写成大型框架，纯函数和薄节点包装就能实现。区别在于我们把这些边界也暴露给用户接线，而不是只在单个节点内部保留。

### 2.2 候选的说明、正文与返回值分离

候选可以是完整字符串，也可以是 `description/content/value` 记录。模型用于判断的描述与真正返回的值可以不同。多行候选不会按换行拆开，候选值不由模型自由改写。

证据：[text_candidates](https://github.com/hndrr/ComfyUI-Jev/blob/12239dab9f03cd4c3dead4b043028ea602b8d43b/semantics.py#L327)、[用户文档](https://github.com/hndrr/ComfyUI-Jev/blob/12239dab9f03cd4c3dead4b043028ea602b8d43b/docs/nodes.md)。

启发：保留“用于判断的说明”和“被执行的值”之间的边界。我们的 Choice 只返回稳定 ID，实际值放下游映射/惰性分支，便于修改执行目标而不改变判断问题。

### 2.3 多选拆成独立 Noul

`multi_choice` 为每个候选编译一个 Noul，再按阈值筛选。它没有假装一次单选 Choice 能表达多个独立选中项。

启发：可以用问题组合表达多选，不必新增 Jev 原语。需要说明各候选的相关性概率并不是总和为 1 的互斥分布。

### 2.4 数字提取采用原文候选

`extract` 先用正则从原文找到数值及周围上下文，再让 Choice 选择候选或 none，最后返回原文片段。本质是“确定性候选提取＋语义选择”，不是 Jev 生成任意数字。

启发：这是很好的外部工作流案例。首版核心不纳入专门 extract 节点，否则很快继续扩张成日期、地址、标签等各种抽取器。

### 2.5 保留细节与严格解析

主输出是 STRING，但同时保留 details DICT 与 response_json。JSON 解析拒绝重复 key 和非有限数字；响应验证类型、概率范围、候选 key 与分数范围。

证据：[严格解析](https://github.com/hndrr/ComfyUI-Jev/blob/12239dab9f03cd4c3dead4b043028ea602b8d43b/semantics.py#L13)、[答案校验](https://github.com/hndrr/ComfyUI-Jev/blob/12239dab9f03cd4c3dead4b043028ea602b8d43b/semantics.py#L176)。

启发：既提供直接可用的类型输出，也保留完整响应；不应只留下 true/false。我们还计划增加概率和、问题快照与版本校验，其具体数值容差需真实 API 样本验证。

## 3. 与本方案的重要差异

| 维度 | 参考仓库在固定提交的行为 | 我们的决定 |
| --- | --- | --- |
| 上下文 | Jev Interpret 的 state 是 STRING；JSON 可作为文本送入 | 公开 Context 对象，简单文本仍可直连 |
| 问题 | 公共 UI 一次配置一个任务；内部可能编译多个问题 | 独立 Questions 对象，可显式组成问题集 |
| 输出 | result 统一 STRING，details/raw 另给 | Result + 稳定的 FLOAT/STRING 读取 |
| 阈值 | Interpret 自身输入，execute 内 resolve | 下游独立节点，不让阈值使 Evaluate 失效 |
| Score | 主输出是归一化 0…1 的数字字符串 | 默认原等级坐标，归一化显式完成 |
| 候选身份 | 内部按位置生成 c0/c1 等 key | 用户稳定 ID，重排不改变本地绑定 |
| 分支 | 文档建议连接现有 Compare Text/Switch | 验证惰性选择，明确独立输出的例外 |
| 范围 | 加入 Skill 发现、推荐、文本生成 | 这些留在核心外 |
| 密钥 | 支持 widget 明文输入或环境变量 | 仅引用服务端配置，不把密钥序列化进 workflow |
| 启动 | entrypoint 加载 OpenRouter 文本模型目录 | 启动不联网，模型 ID 显式填写 |

阈值影响缓存的判断来自其输入结构和执行路径，也与仓库文档的缓存说明一致。本次未在实际 ComfyUI 中测量其调用次数。

源码公开节点中没有自行实现 `check_lazy_status` 或 `ExecutionBlocker`；这并不等于搭配的所有外部 Switch 都不支持惰性求值，只表示该插件没有独立提供、也没有在已读执行测试中证明任意两条昂贵分支只执行一路。

## 4. 两阶段推荐的思想与边界

`suggestions.py` 先对描述排名，并判断任务是否需要专门指导；取 shortlist 后读完整内容，逐候选检查适用性，可以返回空集合。

其中 gate 是 work、procedure、general 三个 Noul 的人工组合 `(work + procedure + 1 - general) / 3`。这是用于专门指导需求的策略分数，不是联合概率。二阶段进一步进行 fits 判断或 applicability 评分。

证据：[suggestions.py](https://github.com/hndrr/ComfyUI-Jev/blob/12239dab9f03cd4c3dead4b043028ea602b8d43b/suggestions.py#L21)。

值得借鉴的是“廉价描述筛选 → 取必要正文 → 用更充足证据复核”和“允许没有合适候选”。不应把 work/procedure/general 的门控问题搬进通用 Evaluate；它们明显带有 Skill 推荐领域语义。

我们的核心允许用户搭建这一流程，但首版不内置自动 shortlist 控制器，也不自动扫描本机 Skill 文件。

## 5. 连接、缓存与测试思路

API 层集中管理出站请求，使用异步 aiohttp、明确超时、拒绝重定向，针对 429/529 有有限次数重试。值得借鉴统一错误处理；我们的计划补充整次操作截止时间、等待上限和取消路径，避免单次超时并不能限制全部重试耗时的问题。

证据：[api.py](https://github.com/hndrr/ComfyUI-Jev/blob/12239dab9f03cd4c3dead4b043028ea602b8d43b/api.py#L140)。

`refresh` 是固定值输入，用来显式使缓存失效。`JevSkillChoice` 还用 fingerprint_inputs 跟踪文件变化。我们采用前者；核心没有文件发现功能，因此不需要继承后者。

仓库 `tests/test_execution.py` 使用真实 ComfyUI 的验证与执行器，mock API 和学习模型操作，检查示例能接到标准图像节点，并检查生成、判断、采样之间的缓存依赖。这个测试方向比只调用 Python 函数更有价值。

证据：[执行器测试](https://github.com/hndrr/ComfyUI-Jev/blob/12239dab9f03cd4c3dead4b043028ea602b8d43b/tests/test_execution.py)。本次只阅读测试，未执行；不能据此声称 GPU 采样或真实 API 准确率经过验证。

## 6. 采纳决定

直接采纳思路：纯函数层、完整候选文本、外部候选 JSON、严格响应校验、显式 refresh、真实执行器＋mock transport 的集成测试。

调整后采纳：说明与执行值分离改为稳定 ID＋下游映射；单节点 UI 改为公开可组合对象；两阶段推荐作为示例；连接重试加入总预算和取消。

不纳入核心：Skill 扫描、OpenRouter 文本生成、内置推荐 gate、数字专用抽取、统一字符串结果、在模型评估节点内决定阈值和映射。

建议从独立的通用协议开始实现，而不是直接把该仓库全部功能 fork 过来再删减。是否复制局部 MIT 代码，应在实现时按实际收益决定并保留许可证。
