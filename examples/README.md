# 样例说明

可直接执行的新单节点 API workflow 位于：

- [`semantic-judge-noul.api.json`](../plugin/ComfyUI-Jev-Decision/examples/semantic-judge-noul.api.json)
- [`semantic-judge-choice.api.json`](../plugin/ComfyUI-Jev-Decision/examples/semantic-judge-choice.api.json)
- [`semantic-judge-score.api.json`](../plugin/ComfyUI-Jev-Decision/examples/semantic-judge-score.api.json)
- [`semantic-judge-interop.api.json`](../plugin/ComfyUI-Jev-Decision/examples/semantic-judge-interop.api.json)
- [`semantic-judge-interop.workflow.json`](../plugin/ComfyUI-Jev-Decision/examples/semantic-judge-interop.workflow.json)

前三份 API workflow 把五个固定输出连接到 ComfyUI 内置 `PreviewAny`。interop API/UI 两份文件连接本地 easy-use 的条件、比较、索引和显示节点；UI 文件由实际 ComfyUI 前端保存并重新载入验证。排队时需要本地环境已配置 TypeSafe key。

本目录其余 Context/Questions/Result JSON 属于 DEC-004 之前的多节点协议草案，只用于审计旧设计，不是当前插件的输入格式：

- [context.json](context.json)：旧设计的原文、改写和限制条件。
- [questions.json](questions.json)：旧设计的多问题对象。
- [result.mock.json](result.mock.json)：人工模拟响应，不是 Jev 实测。
- [context-batch.json](context-batch.json)：旧设计的批次草案。

当前节点直接接收一个运行时 STRING；需要结构化上下文时，由上游先序列化为 STRING，再接入 `context`。
