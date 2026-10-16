# 本地 TypeSafe 凭证

本目录只用于本机运行时配置，不属于插件源码或工作流数据。

1. 打开 [`.env.local`](./.env.local)。
2. 在 `TYPESAFE_API_KEY=` 的等号后粘贴 TypeSafe/Jev API key。
3. 不要加引号，不要换行，不要把 key 发到聊天中。
4. 保存文件后告诉 agent“已填好”。

agent 随后会把这个值仅加载到测试进程的环境变量中，执行一次最小 Noul 请求。测试输出只保留模型名、判断结果、用量、耗时和错误分类，不记录凭证。

测试入口是 `../tools/real_smoke.py`。脚本固定为一次请求，不进行自动重试。

双击 `run_comfyui_with_jev.cmd` 可用当前本地 CPU/NAI 参数启动 ComfyUI。启动器只把 key 注入该进程及其子进程，不修改用户级或系统级环境变量。关闭 ComfyUI 后，该启动进程中的 key 会被移除。

可用 `pwsh -File .\run_comfyui_with_jev.ps1 -ValidateOnly` 检查凭证、环境和插件链接是否就绪；该检查不启动 ComfyUI，也不发 API 请求。
