# 开发实施说明

> 版本：v0.1 · 日期：2026-09-27 · 基于 D-020 至 D-024 的设计整理  
> 用途：将现有产品和架构设计拆成可实施的模块、接口和交付顺序。  
> 状态：开发规格与建议默认值，不代表已有可运行的 Shell 产品。目标设备、系统接口和具体技术栈需在 P0 阶段确认。

## 1. 第一版的可交付范围

首个纵向闭环：本页命令失败或用户主动询问，系统采集已有事实、检索适用配方、生成结构化候选，经程序校验后将纯命令回显至空闲提示符，用户 Enter 执行，侧栏依据真实事件解释结果。

第一版必须满足：

- 主 Shell 保持普通终端界面，原始输出不混入 AI 信息。
- 侧栏支持本页问答、分析进度、依据、风险及拒绝原因。
- 每页独立 ShellSession / AISession，共享 AIWorker 不共享私有对话。
- Scheduler / ModelService 归属 AISession，模型无任意执行工具。
- ContextStore 保存事实，KV cache 只作可丢弃的后端状态。
- 知识采用本地基础包和独立更新，词法检索及环境过滤优先。
- 私有数据上传需要独立授权，拒绝上传时仍保留普通 Shell。

不纳入首个闭环：源代码 bug 修复、工程业务实现、跨页逻辑工作组、全自治执行、多 Agent、自动安装未知脚本、真实生产知识发布或模型后训练。

## 2. P0：实现前必须完成的平台门槛

| 项目 | 必须记录的结果 | 未满足时的处理 |
| --- | --- | --- |
| 目标设备 | 系统名称 / 版本、架构、ABI、应用形态和权限 | 只能交付宿主机协议原型，不宣称 Harmony 可用 |
| 首种 Shell | 可启动路径、版本、命令边界和行编辑集成方式 | 关闭自动回显，仅在侧栏提供文本建议 |
| 终端宿主 | PTY、缩放、全屏应用、Unicode、输入法事件 | 不通过截图或提示符猜测替代可靠状态 |
| 输入桥 | 可读取输入版本、原子比较并替换、不会提交 Enter | 安全默认拒绝回显，不盲发 PTY 字节 |
| 进程能力 | 子进程、IPC、退出监视、文件权限 | 用同进程传输模拟协议，记录能力缺口 |
| 资源预算 | 可分配内存、存储、模型推理性能和并发 | 先使用模型 stub，端侧和云侧适配分别验收 |

具体语言不在本轮虚构为已适配选型。团队在目标工具链可构建、上述能力可验证后登记 ADR。接口以语言无关结构定义，可以先实现宿主机 stub、契约测试和本地知识解析。

部署建议默认采用共享 AIWorker 作为 PoC 的主要验证模式，便于验证 AI 宿主退出后 Shell 继续运行；按页部署模式继续保留。这是实施默认建议，不替代真实设备上的部署决策。

## 3. 建议代码模块

```text
src/
  terminal/           PTY、终端渲染、Shell 事件和输入桥
  ui/                 侧栏与焦点管理
  sessions/           身份绑定、生命周期、协议与路由
  context/            ContextStore、TaskState、预算与脱敏
  knowledge/          包读取、词法检索、配方注册、更新
  orchestration/      本会话状态机与有界工具循环
  models/             stub、本地和云端适配器
  planning/           策略检查、可信命令模板与 Plan
  storage/            本页事件、证据、保留策略与审计
tests/
  contract/           消息、知识和候选数据契约
  integration/        stub 与真实 Shell 的纵向链路
  regression/         并发、输入竞争、隐私与故障恢复
```

上述为目标模块布局，不暗示目录里已有产品代码。公共知识与推理资源可共享，私有状态始终通过会话绑定访问。

## 4. 模块职责与最小接口

| 模块 | 最小操作 | 输出与错误 |
| --- | --- | --- |
| ShellAdapter | start、resize、subscribeEvents、getSnapshot、stageCommand、close | ShellEvent / StageResult，忙碌或版本冲突必须拒绝 |
| SessionRegistry | bind、resolveChannel、rotateEpoch、closeBinding | 可信绑定，不接受模型选择目标页 |
| ContextStore | appendFact、getSnapshot、readExcerpt、updateTask、clear | 不可变快照与授权范围内的证据 |
| ContextBuilder | build(task, backendProfile, snapshot) | ContextEnvelope，或 budget_exceeded / missing_facts |
| KnowledgeService | searchEvidence、findRecipes、getRecipe、checkCompatibility | 带来源和固定修订的结果，match / mismatch / unknown |
| ModelService | capabilities、generate、cancel | 完整 ModelResult 与侧栏流式事件，未完成输出不能生成命令 |
| Scheduler | submit、onEvent、cancel、close | 本会话任务状态与候选，不占用 Shell I/O 等待推理 |
| PlanBuilder | validateCandidate、compileNextStep、invalidate | 校验后的 Plan / Proposal，失败必须提供稳定错误码 |
| KnowledgeUpdater | stage、verify、activate、rollback | 完整快照切换，不能混用旧索引与新配方 |

实际接口字段、消息和事件顺序见 `API_CONTRACTS.md`。

## 5. 页面启动与关闭

### 启动

1. UI 请求创建页面，Supervisor 生成 page / shell / ai 身份及新 binding_epoch。
2. PageHost 启动真实 Shell，ShellAdapter 初始化终端和行编辑集成。
3. Registry 将通信通道与身份固定绑定，AIWorker 创建逻辑 AISession。
4. ShellAdapter 上报初始快照。输入桥未就绪时，侧栏可问答，但不自动回显。
5. AISession 初始化 ContextStore、Scheduler 和 ModelService 配置。

### 关闭

先使绑定失效并取消 AI 请求，再清理侧栏与私有内存；Shell 是否终止取决于用户关闭页面的产品语义。仅关闭 AI 能力时不结束真实 Shell。关闭后返回的任何旧 epoch 消息都不得生效。

## 6. 首个任务闭环

1. 用户提交命令，ShellAdapter 发出 started / finished 事件。
2. Scheduler 做轻量分类，正常状态码或用户中断不直接升级为修复任务。
3. ContextBuilder 获取固定版本快照、关键日志和任务状态。
4. KnowledgeService 按环境过滤，检索公开证据及可信配方。
5. 明确匹配的规则可绕过模型；有歧义时调用 ModelService。
6. 模型返回 recipe_candidate / need_context / need_clarification / no_verified_solution 等互斥类型。
7. 如需补证据，Scheduler 只开放本任务允许的工具，限量、限时、限轮。
8. PlanBuilder 检查发布信任、配方、参数、依赖、制品与权限，生成当前一步命令。
9. AISession 经绑定协议发送 proposal，ShellAdapter 原子检查后填入输入缓冲区。
10. staged 只更新侧栏为“等待 Enter”；没有 Enter 不得产生 started。
11. 真实执行事件更新 TaskState；验证缺事实则保持 unverified，需要新命令时再次等待用户提交。

无可信配方时不向普通用户自动回显模型自由生成的脚本。开发样例 candidate / draft 必须被生产准入逻辑拒绝。

## 7. 输入桥的并发算法

stageCommand 必须在真实输入缓冲区所有者的串行执行单元处理：

```text
校验 channel / session pair / epoch
校验 request 未取消、proposal 未过期且未消费
校验 plan 注册记录仍有效，recipe 和 bundle 没有撤回
比较 context_revision、prompt_generation、input_revision
检查前台为空闲 Shell、无续行、无输入法组合态
检查草稿为空或为同一任务未修改的旧 AI 草稿
检查命令完整、目标 Shell 转义正确、无控制字符或隐含回车
在同一串行单元内只修改输入文本，并增加 input_revision
记录 proposal 消费状态，返回 staged
```

不得分成“线程 A 检查、线程 B 稍后无条件写入”。同一 proposal 重试返回原有结果或明确已处理，不重复填入。普通用户自行输入的命令仍按原 Shell 语义执行；产品校验不能假装覆盖所有用户命令。

## 8. 状态机

### AI 任务

`created → queued → collecting → analyzing → validating → proposed → awaiting_user → observing → completed`

分支状态：waiting_context、waiting_clarification、cancelled、stale、failed、no_verified_solution。TaskState 保存已做动作和真实观察，模型假设单独记录。

### 命令建议

`created → validated → staged → submitted → finished`

旁路：rejected、expired、superseded、cancelled。用户修改建议后，旧 Plan 与原文本的绑定失效，后续事件标记 user_edited_proposal，不继承未经重新检查的后置验证结论。

### 进程故障

共享 AIWorker 退出时取消其在途 AI 请求，主 Shell 继续工作。重启创建新 epoch，主动重新采集上下文，不重放旧 proposal 或用户 Enter。推理后端故障只使相关请求失败，不能让模型切换时静默上传数据。

## 9. 数据与存储边界

- 每页独立事件流、快照、对话、取消令牌、计划与日志引用。
- 存储接口支持 append、read、deleteSession 和按保留期清理；实际数据库在平台门槛通过后确定。
- 原始 PTY 流用于显示，AI 只接收限量脱敏材料，不把终端控制字符当作模型指令。
- 公共包和索引只读共享，模型上下文、云端会话及私有 KV 槽位不跨页合并。
- 计划和执行记录不进入公共知识包，真实日志不上传 Git 仓库。
- 发布包的签名、审核、撤回和过期必须由程序验证，JSON 中的 verified 不能自授信任。

## 10. 工程起始参数

以下仅用于可复现的开发配置，必须允许覆盖，并受实际模型能力画像限制：

```yaml
session_queue_capacity: 4
local_inference_concurrency: 1
tool_followup_rounds: 2
model_request_timeout_seconds: 30
ipc_max_frame_bytes: 262144
log_excerpt_max_bytes: 16384
proposal_ttl_seconds: 60
local_total_token_budget: 4096
local_output_reserve: 768
local_safety_margin: 256
cloud_total_token_budget: 32768
cloud_output_reserve: 4096
cloud_safety_margin: 1024
```

这些不是目标设备的性能保证。推理 token 单独计量时由适配器调整，不能重复扣减。队列满返回 REQUEST_BUSY，不无限缓存；IPC 大小限制不允许丢弃取消、关闭等关键事件。

## 11. 交付顺序与真实能力边界

详细任务见 `IMPLEMENTATION_PLAN.md`，验收场景见 `ACCEPTANCE_MATRIX.md`。

- M0：确认平台和 Shell 输入桥能力，准备契约与假实现。
- M1：先完成无模型的安全回显链路，验证 Enter、并发和关闭语义。
- M2：接入本地知识包、可信配方和确定性命令生成。
- M3：加入模型与有限工具循环，按授权接入云端。
- M4：目标设备验证、更新与故障演练，达到发布门槛。

不能用宿主机演示替代目标设备验收，不能用测试夹具 candidate 配方冒充生产发布配方。

## 12. Definition of Done

一个模块完成必须包含接口实现、异常路径、日志脱敏、回归用例和集成记录。产品发布还必须具备：

- 明确目标设备、系统、Shell 与已支持任务清单。
- 可信且可撤回的首批配方及真实环境测试记录。
- 输入桥、页面隔离、故障恢复和上传授权的验收结果。
- 峰值内存、延迟、有效覆盖率和错误建议率基线。
- 未支持能力的显式降级、用户可理解的说明与回滚 / 恢复文档。

本轮交付到开发规格、演示和契约样例阶段，没有宣称这些发布条件已经满足。
