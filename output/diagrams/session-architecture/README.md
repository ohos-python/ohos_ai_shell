# Session 架构独立图解

日期：2026-09-27。每张图分别保存为 PNG 和 SVG。PNG 可直接预览；SVG 为可编辑矢量版本，中文显示依赖查看器字体回退。

所有图均已嵌入 harmony-shell-session-architecture.pdf。逻辑包含关系不等于进程或线程数量。

- `01-logical-ownership.png` / `01-logical-ownership.svg`：逻辑归属。
- `02-page-local-processes.png` / `02-page-local-processes.svg`：按页部署的进程关系。
- `03-shared-ai-process.png` / `03-shared-ai-process.svg`：共享 AIWorker 的进程关系。
- `04-thread-and-task-model.png` / `04-thread-and-task-model.svg`：线程与异步任务关系。
- `05-protocol-sequence.png` / `05-protocol-sequence.svg`：协议调用与回显时序。
- `06-data-isolation.png` / `06-data-isolation.svg`：数据隔离与共享边界。
- `07-proposal-lifecycle.png` / `07-proposal-lifecycle.svg`：建议生命周期与故障恢复。

已确认：Scheduler 与 ModelService 从属 AISession；主 Shell 只运行命令；默认按页隔离；用户 Enter 才执行。
待定：进程部署默认值、线程数、IPC 库、本地/云端选择与系统沙箱。

来源：SESSION_PROTOCOL.md v0.3、TECHNICAL_ARCHITECTURE.md v0.4，以及 D-012 至 D-014 的讨论记录。
