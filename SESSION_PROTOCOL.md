# Shell / AI Session：配对、共享进程与通信框架

版本：v0.4 · 日期：2026-09-27 · 关联讨论：D-012 至 D-014、D-023

用户已明确：每个 Shell 页面对应一个 AI Session；页面之间不通信；页内 Shell 与 AI 使用统一协议传递上下文和候选命令。

D-013 新增要求：支持多个 Shell 页面对应同一个 AI Session 宿主进程。当前设计将“进程复用”与“逻辑对话合并”分开：默认保留每页独立 AI 上下文，多个 AISession 可运行在一个 AIWorker 中。若还需一个逻辑对话同时关联多个 Shell，作为第 11.7 节的工作组备选单独讨论，不默认放开跨页上下文。

D-014 层级修正：调度器和模型服务从属于各自 AISession，不再作为 AIWorker 下与 AISession 平级的业务模块。AIWorker 仅承载、注册与路由；会话内部的调用、预算、取消和模型配置由 AISession 管理。详见第 12 节。

本文的进程安排、消息格式和隔离实现为助手建议，尚未确定具体语言、IPC 库或 Harmony 系统接口。

## 1. 对象关系

```text
Page A
  ├─ ShellSession A（唯一）
  └─ AISession A（唯一）

Page B
  ├─ ShellSession B（唯一）
  └─ AISession B（唯一）

A 与 B 不交换会话消息，不共享私有上下文。
```

- 页面创建时同时创建 session 对并固定绑定；不能把当前焦点当作返回消息的目的地。
- 页内可以有多个命令任务与多轮问答，但都属于这一对 session，不另建跨页对话。
- 一般能力询问仍属于本页 AISession，但不必附加当前 Shell 的日志。
- Tab 切换只影响展示，不改变身份、上下文归属或回复目标。
- 模型不拥有路由权，模型文本中的 page_id 或 session_id 不作为真实绑定依据。

## 2. 模式 A：每页内置 AI 执行单元

建议以页面为进程隔离单元，不以每条命令、每轮对话为进程。

这是 D-012 的部署建议，继续保留。D-013 增加模式 B：多个页面共享外置 AIWorker，详见第 11 节；两种部署使用同一逻辑 Session 与消息契约。

```text
应用 UI / Supervisor 进程
  │
  ├─ PageHost A 进程
  │    ├─ Shell Adapter / I/O 执行单元
  │    ├─ AI Session 执行单元
  │    ├─ 页内协议通道与私有状态
  │    └─ 真实 Shell A 子进程 → 用户命令子进程
  │
  ├─ PageHost B 进程
  │    ├─ Shell Adapter / I/O 执行单元
  │    ├─ AI Session 执行单元
  │    ├─ 页内协议通道与私有状态
  │    └─ 真实 Shell B 子进程 → 用户命令子进程
  │
  └─ 本地 Model Worker 进程（可选，共享推理能力）
       ├─ 请求 A：独立上下文 / cache / 返回通道
       └─ 请求 B：独立上下文 / cache / 返回通道
```

上图只表达物理进程位置。按 D-014，业务层的调度器和 ModelService 属于各自 AISession；图中的共享 Model Worker 仅表示可选底层算力后端，不是会话外的业务模型服务。云端模式通过会话内部 ModelService 接入，页面隔离和协议不变。

### 为什么不把所有页面放进一个核心会话对象

每个 PageHost 有独立状态和通道，减少跨页面错误引用的可能；页面故障的影响范围限定在本页。公共 UI 只做展示与输入路由，不持有供模型任意检索的全局对话缓冲区。

### 为什么不每页加载一个模型

建议 AI Session 保存问答和编排状态，不保存一份独立模型权重。可共享模型进程与公共只读知识，但不能共享聊天历史、项目日志、授权状态或私有推理缓存。

共享推理进程属于可信基础设施，能够接触其处理的上下文；这不是“模型服务无法访问用户数据”的承诺。若要求比应用级隔离更强，可改为独立推理进程/安全域，并评估资源代价。

## 3. 线程与状态归属

每对 Session 逻辑上有两个执行单元。模式 A 中二者都在本页 PageHost；模式 B 中 AI 单元位于共享 AIWorker：

| 执行单元 | 唯一拥有的状态 | 工作 |
| --- | --- | --- |
| Shell I/O 单元 | PTY、前台进程状态、cwd、提示符代次、输入缓冲区版本 | 处理输入输出、提取命令事件、校验和回显命令 |
| AI 单元 | 本页对话、请求版本、上下文快照、检索候选、建议 | 构造模型请求、处理响应、生成结构化候选 |

首选异步任务/actor 加有界队列；如果运行时需要，可映射为 I/O 线程与 AI 编排线程。不要求每个 Session 必须独占一个 OS 线程，也不以共享可变对象直接相互调用。

- Shell I/O 不能同步等待模型返回；云端网络、本机推理或长检索不阻塞终端。
- AI 单元不直接获得 PTY 写入句柄或 Shell 输入缓冲区指针。
- 模型推理独立进程；AI 请求超时仅结束该请求，不主动终止 Shell。
- 同一 PageHost 内线程不是安全隔离边界；原生代码导致整个 PageHost 崩溃时，本页仍可能一起失效。
- 如果后续要求 AI 编排崩溃也完全不能影响本页 Shell，可将 AI 单元拆为独立进程，沿用相同消息协议；第一版暂不强制这一额外层级。

## 4. 统一协议与传输

协议定义消息语义，传输可替换：同进程使用类型化队列；跨进程使用受保护的本地 IPC。建议原型采用长度前缀 + JSON，避免日志或字段里的换行破坏边界。不要通过终端 stdout 混传控制消息。

- 每个页面的通道由 Supervisor 创建并绑定，不能在消息中任意指定另一个页面作为目标。
- 页内消息必须核对固定的 page_id、session 对与 binding_epoch；检查不是只看可伪造字段，还要核对实际通道归属。
- IPC 句柄只授予对应组件，避免继承到用户命令子进程；日志、模型文本不可以成为控制协议。
- 原始 PTY 字节流直接用于主窗口显示；AI 只接收限量、脱敏后的语义上下文。
- 有界队列、大小限制与优先级防止输出洪水阻塞取消和会话关闭。日志过量时标记截断，不静默丢弃关键命令结束事件。

### 消息信封

```json
{
  "protocol_version": "1.0",
  "message_id": "msg-118",
  "page_id": "page-A",
  "binding_epoch": "epoch-7",
  "shell_session_id": "shell-A",
  "ai_session_id": "ai-A",
  "task_id": "task-12",
  "request_id": "request-9",
  "type": "shell.context.snapshot",
  "sequence": 18,
  "reply_to": null,
  "payload": {}
}
```

字段定义：

- message_id：用于去重和关联回复，不使用进程 PID 替代。
- binding_epoch：页面后端重建或重新绑定时更换，拒收旧连接晚到消息。
- request_id：一次分析请求的身份，目标或约束改变时撤销旧请求。
- sequence：按发送方和当前 epoch 单调递增，不要求双向共享同一个计数器。
- task_id：一般问答可为空；涉及命令回显时需关联明确任务或环境请求。
- 未识别的协议主版本或关键消息类型直接拒绝；不要猜测执行语义。

### 最小消息集合

| 类型 | 方向 | 含义 |
| --- | --- | --- |
| shell.context.snapshot | Shell → AI | 初始或重新同步的上下文快照 |
| shell.context.changed | Shell → AI | 目录、环境或目标任务等关键状态变化 |
| shell.command.finished | Shell → AI | 本次命令结束、状态和输出片段 |
| ai.context.request | AI → Shell | 申请本页额外只读上下文，Shell 侧校验权限 |
| ai.command.propose | AI → Shell 适配器 | 完整候选命令与配方引用，尚非执行指令 |
| shell.command.stage_result | Shell → AI | 回显成功或拒绝原因；成功不代表执行 |
| shell.command.started | Shell → AI | 用户提交后命令实际开始执行 |
| request.cancel / session.close | 双向或 Supervisor 发起 | 取消请求或关闭绑定，撤销未执行建议 |

AI 流式解释通过独立的 `ai.view.delta` 发给本页侧栏渲染，不写入 Shell 标准输出，也不作为 command.propose 的部分内容。

**不提供 AI 可调用的 `shell.execute` 消息。** 用户按 Enter 通过正常键盘输入链路提交命令，不借用模型可伪造的确认消息。

## 5. Shell 发给 AI 的上下文

```text
ContextSnapshot
  context_revision
  host / shell 类型
  cwd 与已授权环境摘要
  当前命令、退出状态
  有限输出片段或本页有效引用
  prompt_generation / input_revision
  foreground_state
  已做检查及其来源
  脱敏、截断与缺失说明
```

- context_revision 在相关环境、cwd、目标命令变化时递增，不因无关屏幕重绘变化。
- prompt_generation 标识当前这一轮可接受命令的提示符。
- input_revision 每次输入文本修改递增，包含用户编辑和系统填入。
- 日志引用必须经本页对象表解析；不能让 AI 用任意文件路径读取其他页记录。
- Shell 发送的是本页最小事实快照，不发送其他页历史，不默认发送全部环境变量或项目文件。
- AI 将快照和本页对话、公共知识候选组合后交给模型。授权状态由本机决定，不接受模型要求“扩大权限”。

## 6. 模型结果如何回到 Shell

模型提出候选配方与参数，由 AI 单元内的程序校验/计划构建模块生成或核验完整命令，再发 propose；Shell 适配器仍做最终检查。

```json
{
  "proposal_id": "proposal-5",
  "based_on_context_revision": 14,
  "expected_prompt_generation": 6,
  "expected_input_revision": 3,
  "recipe_id": "python-venv-create",
  "recipe_revision": "r3",
  "plan_digest": "example-digest",
  "command": "python3 -m venv .venv"
}
```

以上配方标识与校验摘要仅为协议示例，不能用于真实执行。

### 回显前的原子检查

1. 消息通道、页面、session 对和 epoch 正确。
2. request 未取消；proposal 未消费、未过期；配方版本及计划仍有效。
3. 上下文、目录、主机与环境仍匹配。
4. 当前前台是空闲 Shell，不是其他程序、续行输入或输入法提交阶段。
5. prompt_generation 与 input_revision 完全匹配。
6. 输入区为空，或仍是同一请求下用户未修改的旧建议。
7. 命令完整、参数和转义有效，不含隐含回车或终端控制字符。

检查与写入必须由实际行编辑缓冲区拥有者串行执行；不能先在另一个线程检查，再稍后无条件写入。写入只更新文本，不调用 accept-line，不伪造 Enter。

### 回执

- staged：文本已经进入提示符，尚未执行。
- rejected / INPUT_CHANGED：用户已输入，保留草稿，侧栏仍可展示建议。
- rejected / SHELL_BUSY：当前不是空闲 Shell。
- rejected / STALE_CONTEXT：环境或提示符已变化。
- rejected / BINDING_MISMATCH：消息不属于当前页面/epoch。
- rejected / INVALID_PROPOSAL：配方、参数或计划不合法。

对同一 proposal 重试返回已记录回执，不重复写入。用户清除后也不能因重试自动恢复。一次回显回执丢失时先查询状态，不假定未写入而重新填充。

用户编辑建议后，旧校验结论不再适用；提交时重新解析托管动作或视为普通用户命令，不宣称旧配方保障仍然有效。

## 7. 完整时序

```text
用户                 ShellSession A         AISession A          模型
 │ 输入命令 + Enter       │                      │                 │
 ├──────────────────────→│ 执行 / 获取输出       │                 │
 │                       │ context + finished   │                 │
 │                       ├─────────────────────→│ 构建本页上下文   │
 │                       │                      ├────────────────→│
 │                       │                      │←─ 完整候选行动 ─┤
 │                       │                      │ 校验 / 构建计划  │
 │                       │←── command.propose ──┤                 │
 │                       │ 检查 / 仅填入文本    │                 │
 │                       ├── stage_result ─────→│ 侧栏显示状态     │
 │ 看普通命令输入行       │                      │                 │
 ├─ 用户 Enter ─────────→│ 真正提交命令          │                 │
 │                       ├── started/finished ─→│ 更新本页结果     │
```

模型响应到齐之前可以在右侧展示分析进度，但不能把半截响应直接填入命令行。

## 8. 数据隔离与可共享资源

| 数据或资源 | 建议策略 |
| --- | --- |
| Shell 历史、原始输出、输入草稿 | 每页独立，不跨页查询 |
| AI 对话、摘要、私有检索材料 | 每页独立，不做跨页记忆 |
| 上下文快照、proposal、批准状态 | 与 session 对和 epoch 绑定 |
| 本地持久化目录/对象命名空间 | 以页面生成的内部 ID 隔离，由服务校验访问 |
| 公共文档索引、受信任配方、模型权重 | 可以只读共享，不包含其他页私有数据 |
| 模型推理上下文与 KV cache | 请求/会话严格分开，槽位复用前清理或正确重置 |
| 云端会话标识 | 每页独立，禁止复用全局可变对话线程 |

不建立页面之间的消息总线、全局 AI 对话或自动迁移上下文；公共资源更新不携带某页的私有问答或日志。

**这里默认承诺的是应用层会话隔离，不是操作系统级完整安全沙箱。** 同一用户下的进程和两个 Shell 仍可能访问相同文件；在同一目录执行命令也会通过文件变化互相影响。若要求命令本身无法读取其他页数据，必须增加系统沙箱、独立工作目录/权限或更强安全域，需根据目标 Harmony 能力另行验证。

UI/Supervisor 与共享模型服务都是可信边界的一部分；它们可以为展示、路由和推理接触数据，但不得将 A 页数据作为 B 页的上下文。

## 9. 生命周期与故障

- 新建页：创建新 epoch、固定 session 对和专属通道，再启动真实 Shell。
- 切换页：只切换显示；晚到结果仍属于原页，不因页面焦点改绑。
- 关闭页：停止接收 proposal、撤销请求、释放推理槽位，再按用户选择处理仍在运行的 Shell 任务；不以关闭窗口偷偷丢弃重要后台工作。
- 清空 AI 对话：清除本页 AI 历史并撤销未执行请求，不改变 Shell 进程；请求版本更新使旧结果失效。
- 模型失败：本页侧栏显示失败，不填入命令，普通 Shell 可继续运行。
- PageHost 重启：创建新 epoch，历史仅用于查看；不重放旧 Enter、旧 proposal 或自动恢复未执行命令。
- 缓存和日志按本页清理、脱敏和限时保留；不将完整原始上下文放进全局诊断日志。

## 10. 第一版验收

1. A/B 同时运行时，任何上下文、解释或命令建议都不串页。
2. 模型返回前切换 Tab，不改变建议目的地。
3. 用户修改草稿后，迟到建议被拒绝，不覆盖输入。
4. 子程序处于前台时，不向其输入任何 AI 内容。
5. 回显不执行；只有 Shell 用户 Enter 才提交。
6. AI 输入区 Enter 只提问，不影响 Shell 输入。
7. proposal 重复到达、回执丢失、用户清除后重试均不重复回显。
8. 关闭或重建页面后旧消息被拒绝。
9. 本页 AI 请求失败不会自动结束 Shell 或影响另一页。
10. 本地/云端推理切换不合并会话历史，不继承另一页的数据授权。

下一步只需先细化会话状态机和这组消息契约，再选择具体并发运行时与 IPC 实现。

## 11. 模式 B：多个 Shell 页面共享一个 AIWorker（D-013）

### 11.1 区分三类身份

- ShellSession：真实终端的逻辑会话。
- AISession：本页对话、上下文、待处理请求与候选方案。
- AIWorker：承载一个或多个 AISession 的操作系统进程，不等于一个聊天会话，也不等于模型推理进程。

当前建议的对应关系：

```text
ShellSession A ── AISession A ─┐
ShellSession B ── AISession B ─┼── AIWorker 1
ShellSession C ── AISession C ─┘
```

本模式共享处理进程，不共享私有记忆，仍满足 D-012 的默认页面隔离约束。用户尚未要求将所有页面合并成一份聊天历史。

### 11.2 进程与线程结构

```text
UI / Supervisor
  ├─ PageHost A ── ShellAdapter A ── 真实 Shell A
  ├─ PageHost B ── ShellAdapter B ── 真实 Shell B
  ├─ PageHost C ── ShellAdapter C ── 真实 Shell C
  │       │             │               │
  │       └─────────────┼───────────────┘
  │                     ↓ 专属绑定 IPC
  ├─ 共享 AIWorker 1
  │    ├─ SessionRegistry（仅 Supervisor 可创建绑定）
  │    ├─ AISession A
  │    │    ├─ 上下文与历史 A
  │    │    └─ Scheduler A → ModelService A
  │    ├─ AISession B
  │    │    ├─ 上下文与历史 B
  │    │    └─ Scheduler B → ModelService B
  │    └─ AISession C
  │         ├─ 上下文与历史 C
  │         └─ Scheduler C → ModelService C
  └─ 可选底层算力后端（不是独立的会话业务服务）
```

历史层级：~~AIWorker 下的全局调度器与模型网关，与各 AISession 平级。~~ D-014 改为每个 AISession 内部拥有自己的 Scheduler 与 ModelService；原意中的共享进程/算力优化不再等同于共享业务调度状态。

- PageHost 不再内置 AI 编排对象，只保留本页 Shell 状态和对应远端 Session 句柄。
- AIWorker 可用一个异步事件循环承载多页逻辑 actor；不要求为每页新增线程。
- 每个 AISession 的状态与任务由其内部 Scheduler 串行管理；宿主资源配额只限制算力占用，不接管会话工作流。
- 每页独立队列、长度/令牌/时间预算及取消标识，避免某一页大量输出拖住所有页面。
- 用户主动提问可优先于后台诊断，同时要有公平调度，避免其他页面长期饥饿。
- 模型推理依然不在 UI 或 Shell I/O 线程同步执行；本地推理进程保持可独立故障恢复。

### 11.3 路由绑定与协议变化

由 Supervisor 维护可信绑定表：

| page_id | shell_session_id | ai_session_id | ai_worker_id | binding_epoch |
| --- | --- | --- | --- | --- |
| page-A | shell-A | ai-A | worker-1 | epoch-A-1 |
| page-B | shell-B | ai-B | worker-1 | epoch-B-1 |
| page-C | shell-C | ai-C | worker-1 | epoch-C-1 |

`ai_worker_id` 是部署地址，不是对话身份；不能以它作为模型聊天历史、缓存或授权状态的唯一键。

建议保留现有会话协议，将 worker 信息放在服务端路由层，不要求模型感知。必要时在传输层增加 worker_epoch，用于连接恢复；消息正文仍按 page_id、session 对、binding_epoch、request_id 校验。

```text
Shell A 的上下文
→ 校验 A 的 IPC 绑定
→ AIWorker 查找 AISession A
→ 仅装配 A 的上下文
→ 模型请求绑定 A 的 request_id
→ 回复进入 AISession A
→ 校验后发回 Shell A
```

- 不使用“当前活跃页面”或“最后一次发送请求的页面”作为全局返回目标。
- 不把某页输入广播给其他 AISession，也不把共享进程当作共享上下文总线。
- 同一连接多路复用时，每个逻辑通道仍需单独授权；为简化第一版，也可以每个 PageHost 使用独立连接。
- 命令回显的 input_revision、prompt_generation 和环境校验不因进程复用而减少。

### 11.4 数据隔离的新增要求

AISession 必须拥有独立的 history、context_store、proposal_store、permission_scope、pending_requests、cancellation_scope；禁止将这些对象放成共享可变全局变量。

- 只有对应 AISession 内部的 Scheduler 调用其 ModelService；ModelService 只接收本会话的请求，不拼接全部页面上下文。AIWorker 不直接构建 Prompt 或调用会话模型服务。
- 私有检索结果与模型缓存键必须包含会话/请求身份、环境与数据权限范围；公共只读材料可共享。
- 每个会话调度器只管理本会话任务、优先级和预算；宿主层资源限额仅处理必要元信息，不读取其他会话内容参与任务编排。
- 关闭、清空或取消某一页，只处理其对象和缓存；不能复用一个全局取消开关。
- 命令方案的目标仍由本机绑定决定，不接受模型将目标改为其他 Shell。

此处页面 AI 状态位于同一进程，采用逻辑隔离而非 OS 地址空间隔离。共享进程中的实现错误或被攻破的可信服务可能影响多个 AI 会话；需要强隔离时使用模式 A 或独立 AIWorker/系统安全域。

### 11.5 生命周期与故障范围

- 新建页面：在共享 AIWorker 注册新的 AISession，并创建专属绑定；不新建模型聊天历史的全局容器。
- 关闭页面：注销对应 AISession、取消其请求并清理私有缓存；共享 AIWorker 继续服务其他页。
- 最后一个页面关闭后是否回收 AIWorker，由空闲回收策略决定，不影响每页逻辑身份。
- 共享 AIWorker 崩溃：所有绑定页的 AI 暂时不可用，但外部 PageHost 和真实 Shell 不应被连带关闭。
- 重启后由 Supervisor 重建受影响绑定并更换代次；旧请求、未执行 proposal 和旧回执不能自动重放。
- 只恢复用户允许保留的问答历史，不恢复隐含执行授权。某页请求超时不应终止其他页推理。

### 11.6 两种模式对比

| 维度 | 模式 A：每页内置 AI | 模式 B：共享 AIWorker |
| --- | --- | --- |
| 逻辑 Session | 每页独立 | 每页独立 |
| AI 编排状态内存 | 分属不同 PageHost | 共处一个进程，依赖逻辑隔离 |
| AI 编排进程级故障 | 通常影响本页，可能影响本页 Shell | 影响多个 AI 会话，不应结束 Shell |
| 调度器与模型服务 | 从属本页 AISession | 仍从属各 AISession，不设平级全局业务调度器 |
| 公共资源 | 可独立使用或复用后端 | 可复用后端与进程资源，不合并业务状态 |
| 协议 | 相同会话消息 | 相同会话消息，新增 worker 路由管理 |

建议将部署方式配置为 page_local / shared_worker，不在业务逻辑中假设 AISession 必定与 PageHost 同进程。模式 B 建议纳入第一版可设计范围；是否作为默认部署仍待用户确认和目标设备评估。

### 11.7 另一个备选：多个 Shell 共用同一个逻辑对话

这与共享 AIWorker 不同，暂不视为用户已确认需求，也不默认实施。如果后续用户希望一个 AI 对话联合管理多个 Shell，需要额外的 Workspace/Group 模式：

- 用户显式把 Shell 加入工作组，明确允许共享的上下文范围。
- 对话引用按来源 Shell 标注；每份方案必须指定一个明确目标 Shell，不能广播执行。
- 涉及多个 Shell 的方案拆为独立动作，在各自页面完成回显与用户 Enter。
- 未明确目标时先询问，不能根据焦点或文本推断目标后直接写入。
- 将 D-012 的“页面互不通信”保留为默认；工作组作为显式、可撤销的例外授权。

本轮只为该歧义保留扩展位置，不改变默认隔离策略。

### 11.8 追加验收场景

1. A/B 同时请求、响应乱序，仍只返回各自页面。
2. A 清空、取消或关闭时，B 的历史、请求与输入完全不变。
3. 共享 AIWorker 重启不结束任何普通 Shell，旧回复不能回显。
4. 单页大量日志或长推理不会无限挤占全部队列。
5. 模型缓存或云端对话复用不会把 A 的内容带入 B。
6. 伪造另一页 ID 的消息因通道绑定不符被拒绝。

## 12. AISession 内部拥有调度器与模型服务（D-014）

### 12.1 已确认的归属关系

```text
AISession
  ├─ ContextStore：本会话上下文、历史与知识引用
  ├─ ProtocolEndpoint：接收 Shell 消息、返回结果
  └─ Scheduler：管理本会话的任务、顺序、预算和取消
       ├─ 上下文构建 / 检索 / 结果校验
       └─ ModelService：模型配置、请求、流式输出、超时
            └─ 本地推理后端 / 经授权的云端接口
```

本图表示逻辑从属与调用关系，不要求每个节点独占一个进程或线程。对外的会话协议终点始终是 AISession，不是 Scheduler 或 ModelService。

### 12.2 职责边界

- AISession：拥有本会话身份、上下文、权限与生命周期，收发协议消息。
- Scheduler：根据本会话请求安排上下文构建、检索、模型调用、结果校验；不管理其他会话的队列。
- ModelService：使用本会话配置与授权调用模型，返回结果给 Scheduler；不能直接向 Shell 回显命令。
- AIWorker：创建/承载 AISession、做连接路由与必要资源管理，不保存全局聊天历史，不承担会话业务规划。
- 可选共享推理后端：仅作为 ModelService 的底层实现资源，是否共享及具体部署尚待确定，不能反向掌管会话上下文。

### 12.3 更新后的调用与生命周期

```text
ShellSession
→ AISession.ProtocolEndpoint
→ AISession.Scheduler
→ 上下文构建与知识检索
→ AISession.ModelService
→ 模型结果
→ Scheduler 校验与计划构建
→ AISession.ProtocolEndpoint
→ 原 ShellSession 校验并回显
```

- 创建 AISession 时，初始化其 Scheduler、ModelService 配置与本会话状态。
- 清空或取消时，由 AISession 撤销自己的排队任务、在途模型请求、流式响应和未执行建议。
- 销毁 AISession 时释放其上下文、队列、ModelService 句柄及会话私有缓存；不终止其他会话或仍被引用的共享后端。
- 切换模型仅修改该 AISession 的 ModelService 配置；在途请求须取消或保留其原模型版本标记，不混接响应。
- 模型请求完成后仍需验证 request_id、绑定代次及上下文版本，内部从属关系不替代已有回显校验。

### 12.4 本轮修改范围

这次只修正模块归属，不新增跨页共享上下文，不更改 Shell 用户 Enter 执行规则，也不把每个 ModelService 强制解释成一份独立模型权重。

## 13. 开发契约补充（D-023）

具体消息方向、字段、错误、取消与回显状态见 `API_CONTRACTS.md`。开发草案补充 `shell.context.result` 作为补证据响应，明确 `ai.user.ask` 与 Shell 提交的区别，并统一新知识对象的 `recipe_revision` 为整数。历史示例保留；编码时采用新契约并完成协议评审，不混用历史字符串修订与新字段类型。
