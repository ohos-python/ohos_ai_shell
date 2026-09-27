# 知识集成：分发、识别、检索与工具接入

> 日期：2026-09-27 · 版本：v0.2 · 关联讨论：D-021、D-022  
> 状态：D-022 用户确认按本方案推进。固定本地知识包、统一 Knowledge API、先兼容过滤与词法检索、按需增加向量与 MCP 的方向；具体存储、模型、框架与 Harmony 适配仍待验证。  
> 沿用 D-020：配方驱动固定工作流 + 有界补证据循环 + 程序校验；只有用户 Enter 才执行。

## 1. 结论：不是二选一，而是三个层次

| 层次 | 解决什么问题 | 可选方式 |
| --- | --- | --- |
| 分发层 | 知识从哪里来，如何安装和更新？ | 应用随附数据、独立数据包、npm / PyPI 包、在线同步 |
| 检索层 | 怎样识别问题并找到适用材料？ | 元数据过滤、关键词 / 全文检索、Embedding 向量召回、重排 |
| 接入层 | 应用或模型如何查询知识？ | 内部函数、Function Calling 工具适配、MCP tools / resources |

因此“npm 包”和“Embedding + MCP”不是同层替代方案。可以把预构建索引放进数据包，也可以通过 MCP 查询完全没有向量化的知识库。

**当前推荐：本地版本化知识包 + 本机统一 Knowledge API；按环境过滤后先做关键词检索，必要时增加向量检索；模型通过受限工具访问，MCP 保留为可选适配层。**

该集成方向已由 D-022 确认，不变更已固定的 Agent 方向。新增数据契约草案见 `KNOWLEDGE_CONTRACTS.md` v0.1 和 `design/knowledge/`；字段与生产发布实现仍待细化。

## 2. 知识究竟怎样被“识别”

知识识别应分为资料整理阶段和运行时匹配阶段，不是把文本生成向量就完成识别。

### 2.1 资料整理阶段

```text
授权来源与固定版本
  → 提取软件、命令、错误特征、系统 / 架构 / ABI 条件
  → 保存原文、来源、许可及定位
  → 区分文档证据与候选执行配方
  → 人工审核 + 对应环境验证
  → 构建检索索引并发布版本化数据包
```

模型可以帮助初步抽取字段，但抽取结果不是兼容性认证。未知适用条件应保存为 unknown，不默认匹配所有 Harmony / OpenHarmony 环境。

尚未对用户提供的 OpenHarmonyPCDeveloper 来源做本轮仓库清点、许可证审核或批量抓取；不能默认组织下的全部内容都可再分发或可执行。

### 2.2 运行时匹配阶段

以某个安装命令失败为例，提取：

- 用户目标与软件名。
- 命令形态、退出码、关键错误字符串。
- 本页系统版本、架构、ABI、Shell 和工具状态。
- 已经尝试的操作与结果。

先进行适用条件与发布状态过滤，再检索证据。关键条件未知的候选可以用于解释和补问，但不能通过执行适用性检查。

精确错误码、包名、版本号保留关键词匹配；自然语言表达差异较大时再增加语义召回。建议组合候选后去重与排序，而不是让向量相似度直接决定能否执行。

## 3. npm / PyPI 知识包是否可行

### 可以作为分发渠道，但不建议成为终端用户的必需依赖

PyPI 的 wheel 格式支持随分发物包含数据文件，所以把资料放进 Python 包在格式层面可行。[S2] npm 也可用于版本化分发；但 npm 具有安装生命周期脚本机制，需要单独控制发布与安装行为。[S1]

本项目最初要解决的就是目标设备运行时和包管理器适配问题。因此不建议为了读取适配知识，再要求用户先安装可用的 Node/npm 或 Python/pip。这会增加初始化依赖，而不是消除适配负担。

另外，**本产品的工程依赖**与**用户正在开发的具体工程**必须区分：知识可以随 Shell 产品打包，不应默认修改用户项目的 package.json、requirements 或依赖锁文件。

### 适合使用包管理器的情况

- 开发机 / CI 已有成熟 Node 或 Python 环境，用包管理器同步知识源，再在产品构建时导出数据包。
- 面向已具备对应运行时的扩展开发者，提供 SDK 或可选知识源插件。
- 组织内明确需要现有仓库分发、版本锁定与发布流程。

### 不建议的做法

- 用户每次安装开发工具前，先运行 npm install 或 pip install 来取得 Shell 基础知识。
- 安装知识包时运行自动环境修改或安装脚本。
- 把“成功安装数据包”理解成“配方已通过目标设备验证”。

即使关闭 npm 生命周期脚本，也仍需审核包内容、来源与更新策略；包格式不能替代可信发布和业务校验。

## 4. 推荐的本地知识包结构

以下目录只是建议，不冻结存储格式：

```text
knowledge-bundle/
  manifest.json
  evidence.jsonl
  recipes/
    recipe-records.jsonl
  indexes/
    lexical.sqlite
    vectors.bin            可选
  sources/
    source-map.json
    licenses.json
  integrity/
    files.sha256
    manifest.signature
```

| 内容 | 作用 |
| --- | --- |
| manifest | 包版本、schema 版本、生成时间、发布者、应用兼容版本、文件清单 |
| evidence | 可引用文本、来源定位、环境条件与验证状态 |
| recipes | 配方定义、参数约束、前置 / 后置条件、动作模板、发布与撤回状态 |
| lexical index | 精确名称、错误信息与全文检索的预构建索引 |
| vectors | 可选语义向量；必须附原文映射及检索模型元数据 |
| source map / licenses | 来源版本、许可、归属和可再分发依据 |
| integrity metadata | 检查文件完整性与可信发布者，不证明配方逻辑安全 |

SQLite FTS5 是官方提供的全文检索扩展，可作为词法索引候选，但目标构建是否启用 FTS5、中文分词和混合命令文本效果仍需实测。[S3] JSONL、SQLite 或其他格式不是已确认选型。

**知识包不是任意可执行插件。** 默认只分发数据和受约束配方定义；真正的执行仍由既有 PlanBuilder 和 Shell 回显流程处理。

## 5. Embedding 的收益、成本与常见误区

### 5.1 Embedding 是索引，不是把知识训练进模型

Embedding 检索把查询和语料编码为适当向量，再以相似度寻找候选。官方语义搜索示例区分 query 与 document 编码，并强调检索任务所用模型需要适合该类检索。[S4]

本项目建议：

- 原文、配方和来源始终保留；向量不替代知识主体。
- 模型生成答案时接收的是取回的文本 / 结构化证据，不是直接阅读向量文件。
- 文档向量和查询向量必须使用相互兼容的编码模型、维度和预处理规则。
- 即使维度相同，也不能默认来自不同模型的向量可比较。

### 5.2 离线向量包仍有运行成本

在构建机预计算文档向量，可以减少设备端索引构建工作；但用户的新问题仍需要编码为查询向量。

三种候选：

| 方式 | 优点 | 限制 |
| --- | --- | --- |
| 端侧小型 embedding 编码器 | 可离线检索，查询无需上传 | 增加模型适配、内存、存储和推理开销 |
| 远端查询编码或检索 | 减少本地模型负担 | 需要网络、授权、超时与费用控制 |
| 端侧先仅用词法检索 | 实现与资源要求较简单 | 需要评测自然语言召回不足的情况 |

因此第一版建议先验证“兼容过滤 + 关键词检索”的效果，确有召回短板时再增加向量能力，不因为已有大模型就假设 embedding 自动可用。

### 5.3 索引版本必须固定

向量索引记录 `embedding_model_id`、revision、dimension、query/document 模板、normalization、距离函数、chunker_version 和 corpus_revision。切换编码器或切片规则时需要相应重建，不能混用不兼容旧索引。

## 6. Function Calling 与 MCP 如何选择

### 6.1 先定义本产品的 Knowledge API

建议先实现与模型供应商无关的应用接口：

```text
search_evidence(query, environment_constraints, limit)
find_recipes(goal, environment_constraints, limit)
get_evidence(evidence_id, excerpt_range)
get_recipe(recipe_id, revision)
check_recipe_compatibility(recipe_id, environment_snapshot)
```

可信会话身份和权限由调用通道绑定，不让模型指定别人的 Session。模型参数、返回条数、文本长度、文件路径与网络访问均受检查。

检索返回至少包含来源、原文片段、适用条件、包 / 配方版本及 match / mismatch / unknown 状态。相似度分数只用于排序，不作为置信度或执行授权。

### 6.2 内部调用与 Function Calling

固定工作流可以由 Scheduler 直接调用 Knowledge API；不需要每次让模型决定是否检索。

需要动态补证据时，建议模型通过结构化工具请求表达查询意图，应用校验后调用同一个接口，再把结果提供给模型。执行权限由应用控制，不因模型生成函数调用参数就自动授予。[S5] 保留为模型供应商工具接口的后续核对入口，本轮未取得可核实正文，不把其具体行为作为已验证前提。

如果端侧模型工具调用能力不稳定，可以由固定流程准备材料，不强制引入 Function Calling 模型能力。

### 6.3 MCP 是可选协议适配，不是另一个知识库

MCP 官方架构包含 host、client、server；server 可以提供 tools、resources 等能力，既有本地 stdio，也有远程 Streamable HTTP 连接方式。因此使用 MCP 不等于必须上云，也不等于必须向量化。[S6][S7]

在本项目中，只有这些需求出现时才优先考虑 MCP：

- 同一套知识服务需要给 Shell、IDE 或其他受控客户端复用。
- 社区或企业要提供独立知识服务。
- 需要统一接入多个外部来源，并愿意承担协议、认证、版本和运维成本。

第一版若只服务本 Shell，直接类型化函数接口更容易限定范围。未来可在 Knowledge API 外加 MCP adapter，不必重做存储与检索。

不接入来源不明的 MCP server，不把服务器返回的文字或配方自动升级为可信内容。只开放知识查询与兼容检查，不通过 MCP 添加任意执行入口。

## 7. 推荐架构：本地优先、在线可选、协议解耦

```text
发布与整理侧
  社区获准来源 → 解析 / 审核 / 测试 → 版本化知识包
                                           ↓
设备侧                               随应用基础包 / 独立更新
  AISession.Scheduler                      ↓
    → ContextBuilder                 本地只读知识库
    → Knowledge API ───────────────→ 环境过滤 + 检索
    → ModelService                         ↓
    ← 文本证据与配方候选 ←───────────────────┘
    → 校验 / 生成命令 → 原 ShellSession → 用户 Enter

可选：Knowledge API → 经授权在线知识服务
可选：外部受控客户端 → MCP adapter → 同一 Knowledge API
```

知识库可以作为公共只读资源共享；页面的日志、查询上下文、权限与模型请求不能因此跨页混合。Knowledge API 不接管 Scheduler，也不成为全局 Agent。

## 8. 端侧与云侧如何组合

模型位置与知识位置独立选择：

| 模型 | 知识 | 可行设计 |
| --- | --- | --- |
| 端侧 | 本地 | 离线主路径，有限知识包和请求预算 |
| 云侧 | 本地 | 本机先筛选，再经授权上传最小相关证据 |
| 端侧 | 在线 | 经授权获取公开资料，在端侧分析 |
| 云侧 | 在线 | 明确服务边界、上传授权与来源验证 |

建议第一版优先覆盖前两种，不因使用云模型就上传整个本地知识库或终端历史。语义检索远端化时，查询中的敏感信息也属于上传数据，需要独立处理。

## 9. 更新与离线安全

建议知识数据可独立于应用更新，但 schema / 索引格式与应用版本需要兼容检查。

更新流程：

```text
下载到临时位置
  → 验证发布者信任与清单签名
  → 验证摘要、schema、索引和应用兼容性
  → 检查撤回与版本策略
  → 安装新快照并原子切换活动版本
  → 保留可回退快照和审计记录
```

具体原子切换机制以平台实现为准，避免读取到新配方配旧索引的半更新状态。签名验证依赖预置信任根或受控密钥轮换，不能信任下载包自行提供的任意公钥。

- 任务固定引用 bundle_revision / recipe_revision；更新后不得静默更换在途计划。
- 回退不应恢复已明确撤回的危险配方，也不应绕过防降级策略。
- 需要重新评估的建议使其失效，再按原回显规则处理，不覆盖用户草稿。
- 断网时无法保证获得最新撤回信息。记录最后同步时间，并按风险设置离线可用或拒绝回显策略；高风险、过期或无法确认状态的方案宁可不生成可执行建议。

知识包分发失败不应阻塞普通 Shell，基础说明和已有可信离线内容仍可使用。

## 10. 方案对比与阶段建议

| 方案 | 离线 | 目标运行时依赖 | 更新 | 当前建议 |
| --- | --- | --- | --- | --- |
| 用户设备通过 npm / PyPI 安装知识 | 安装后可离线，视内容而定 | 增加对应包管理工具链依赖 | 可独立更新 | 不作默认，保留开发 / 插件渠道 |
| 随应用内置数据 | 支持 | 不新增 npm / pip 前提 | 通常随应用或另设更新 | 提供小型基础知识包 |
| 独立版本化数据包 | 支持 | 由本产品读取数据 | 独立增量 / 全量更新 | 建议主分发路径 |
| 纯远程知识服务 | 依赖额外缓存 | 依赖网络与认证 | 集中更新 | 可选增强，不作唯一来源 |

第一阶段：基础离线数据包、词法检索与环境过滤、内部 Knowledge API、工具适配、审核和更新机制。

第二阶段：根据召回评测增加向量检索；根据客户端复用需求增加 MCP。两者独立评估，不捆绑引入。

## 11. 验收与待确认

需要验证：适用配方召回率、错误适用率、无答案识别、查询延迟、存储 / 内存开销、数据包完整性、更新失败恢复、撤回传播、离线过期策略、敏感信息上传、恶意文档和跨页访问。

待确认：

1. ~~是否采用独立知识数据包，而不是把 npm / pip 作为用户端必需前提？~~ D-022 已确认采用该方向，npm / PyPI 保留可选开发 / 分发渠道。
2. 基础知识的覆盖范围、来源许可及发布审核责任人。
3. 第一版词法检索是否足够，何时触发向量能力投入。
4. 是否已有必须支持 MCP 的外部客户端或现成知识服务。
5. 知识更新频率、离线期限、撤回策略与隐私要求。

下一步建议定义 `KnowledgeBundle Manifest`、Evidence 与 Recipe 的数据契约，以及 Knowledge API 的返回 Schema。

## 12. 一手资料与核实边界

2026-09-27 已读取下列 S1、S2、S3、S4、S6、S7 官方正文，S5 页面未取得可核实的工具说明，标为待核对。已读资料用于核实机制，不是本项目目标设备支持或性能证明；本轮没有安装 npm / Python 运行时，没有建立实际向量库或连接第三方 MCP 服务。

- [S1] npm，Scripts / Config：生命周期脚本与 ignore-scripts 配置。`https://docs.npmjs.com/cli/v11/using-npm/scripts/`、`https://docs.npmjs.com/cli/v11/using-npm/config/`
- [S2] Python Packaging，Binary distribution format：wheel 与数据文件。`https://packaging.python.org/en/latest/specifications/binary-distribution-format/`
- [S3] SQLite，FTS5 Extension：全文检索扩展。`https://www.sqlite.org/fts5.html`
- [S4] Sentence Transformers，Semantic Search：查询 / 文档编码与语义检索。`https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html`
- [S5] Claude，Tool use：客户端工具执行与结果返回流程。`https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview`
- [S6] MCP，Architecture：host / client / server 与能力分工。`https://modelcontextprotocol.io/docs/learn/architecture`
- [S7] MCP，Tools：工具调用与安全注意事项。`https://modelcontextprotocol.io/specification/2025-06-18/server/tools`
