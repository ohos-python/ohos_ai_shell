# 知识包、证据与配方：行业映射和数据契约

> 日期：2026-09-27 · 版本：v0.1 · 关联讨论：D-022  
> 已确认：用户采纳 D-021 的本地知识包、统一 Knowledge API、按需向量检索与 MCP 路线。  
> 本文新提出的数据字段、Schema 和状态机为实施草案，不因路线确认而自动视为行业标准或全部冻结。

## 1. 业界如何定义：借鉴规范，不混同规范

“知识包、证据、配方”在这里是三个项目对象，不应描述为一套业界统一且可直接照搬的标准。它们分别对应不同领域的成熟概念。

| 本项目对象 | 可借鉴的行业概念 | 借鉴内容 | 不应混同 |
| --- | --- | --- | --- |
| KnowledgeBundle | Frictionless Data Package 的数据包描述符与资源清单 | 标识、元数据、资源路径、版本和数据契约 | 我们的 manifest 不是宣称兼容该标准的 datapackage.json |
| Evidence | W3C PROV 的 Entity / Activity / Agent 溯源模型 | 资料、采集 / 处理过程、负责主体、派生关系 | 溯源不证明资料内容真实；PROV 的 Agent 不专指大模型 Agent |
| Recipe | Conan 等包管理系统中的构建 / 打包配方 | 输入、依赖、适用条件、步骤、产出与测试 | Conan 配方可以是 Python 代码，本项目不默认执行知识包里的任意代码 |
| 发布元数据 | TUF 的受信任软件更新元数据 | 信任根、目标摘要、版本一致性、过期、防回滚 | 一个 sha256 字段或自带公钥不等于实现 TUF |
| 数据契约 | JSON Schema Draft 2020-12 | 类型、必需字段、条件约束、引用 | Schema 通过不等于安全、兼容或可执行 |

上表的机制依据见 [S1]-[S5]。本项目只是借鉴并定义自己的轻量数据契约，不宣称已获得标准兼容认证。

## 2. 三者的关系

```text
KnowledgeBundle：一个可分发、可校验的快照
  ├─ manifest：包身份、资源清单、摘要、条目及索引描述
  ├─ Evidence：原文或观察 + 来源 + 条件 + 审核状态
  ├─ Recipe：目标 + 参数 + 条件 + 受约束动作 + 验证
  │    └─ evidence_refs → 固定版本的 Evidence
  ├─ source snapshots：可定位的原始来源快照
  └─ indexes：可重建的关键词 / 向量索引

运行时另外生成：
  Plan：绑定当前用户、环境、参数、配方和制品版本的实例
  ExecutionRecord：用户提交后发生的真实执行和验证结果
```

包解决“交付哪一版资料”；证据解决“依据是什么”；配方解决“在什么条件下可以提出哪些动作”。Plan 和执行记录不是发布包内的公共知识，保持会话私有。

一个 Evidence 可被多个 Recipe 引用，一个 Recipe 也可引用多个 Evidence，包括支持、限制及反对证据。索引不是事实来源，不能脱离原文独立解释。

## 3. KnowledgeBundle 的构造

### 核心字段

| 字段 | 语义 |
| --- | --- |
| schema_version | 数据格式版本，与知识内容版本分开 |
| id / revision | 稳定身份 + 不可变内容修订号 |
| status | draft / released / revoked；不单凭该字段授信 |
| publisher_id / created_at | 发布主体标识和创建时间 |
| minimum_reader_version | 读取程序的兼容要求 |
| expires_at / release_metadata_ref | 发布时的有效期与外部受信任更新元数据引用 |
| files | 每个资源的包内相对路径、媒体类型、字节数、SHA-256 |
| entries | Evidence / Recipe 的身份、修订和文件对应关系 |
| indexes | 索引文件、语料修订、构建器与编码配置 |

### 分发目录

```text
bundle/
  manifest.json
  evidence/demo-guide.json
  recipes/demo-runtime.json
  sources/demo-guide.txt
  indexes/                   可选，当前样例未构建索引
```

`manifest.json` 不把自身摘要写进自身，避免递归。发布元数据从包外认证 manifest 的确定字节内容，再由 manifest 认证资源文件。不能接受下载包自行提供的任意密钥作为信任根。

关键词索引记录分词器版本；向量索引额外固定编码器、模型修订、维度、query/document 模板、归一化、距离函数和切片器版本。不同向量空间不得混用。

完整示例：`design/knowledge/examples/manifest.json`。文件摘要和大小对应真实样例字节，不是占位散列。样例处于 draft，不含有效发布签名、不允许实际发布或回显安装建议。

## 4. Evidence 的构造

### 核心字段

| 字段 | 语义 |
| --- | --- |
| id / revision | 稳定证据身份和修订，不用搜索排序位置充当 ID |
| evidence_type | guide、release_note、issue_report、test_report、environment_observation |
| title / content | 可展示、可检索的标题及文本 |
| visibility | public，或带本会话身份及保留期限的 session 私有证据 |
| source | 来源 URI、固定修订、原文定位、采集时间 / 主体、原始快照路径和摘要 |
| source.rights_status | cleared / pending / example_only；对外分发需可审计许可依据 |
| applicability | 适用条件或明确 unknown，不把条件缺失当成全平台通用 |
| claims | 区分来源陈述、真实观察与假设 |
| review | 审核状态及审核记录，字段本身不等于审核者签名 |

### 借鉴 PROV 的方式

- 原始文档和提取证据是 Entity。
- 同步、截取、脱敏、结构化抽取可建模为 Activity。
- 来源作者、采集服务和审核者可建模为 Agent。
- `source` 和记录版本用于保存派生链；当前 JSON 并不是完整 PROV-O / JSON-LD 序列化实现。[S2]

原文“某环境能安装成功”应记录为来源陈述，不自动升级为本产品验证事实。测试报告必须关联测试环境、结果及实际记录；单个用户 Issue 不能自动获得维护者审核地位。

来源标为 public 也不证明内容无秘密或有再分发权，入库流程还需人工 / 规则检查。私有终端日志只保留在本会话存储，不能随公共知识包发布。

完整示例：`design/knowledge/examples/evidence/demo-guide.json`。来源为本次编写的合成资料，不冒用真实社区来源；权限状态为 example_only，审核状态为 unreviewed。

## 5. Recipe 的构造

### 核心字段

| 字段 | 语义 |
| --- | --- |
| id / revision / status | 配方身份、不可变修订、candidate / verified / deprecated / revoked |
| intent | 安装工具、配置环境、检查环境或移除工具 |
| applicability | 对环境事实执行受限条件匹配 |
| parameter_schema | 输入参数类型、白名单和必需项 |
| evidence_refs | 精确证据修订，角色包括依据、验证、限制、反对 |
| dependencies | 固定修订的配方依赖，解析时检测闭环 |
| artifacts | 直接下载制品的来源、摘要、大小和 ID |
| steps | 受支持适配器、受限动作、参数绑定、依赖、锁和幂等策略 |
| effects | 特权、网络来源和逻辑写入范围 |
| verification | 验证目标及缺少观察时的 unverified 状态 |
| failure_policy | 失败停止、部分失败说明和是否存在回滚能力 |
| review / test_records | 审核记录与固定测试证据、环境和结果 |

### 为什么不直接保存一段 shell 脚本

Conan 等配方可以包含源码获取、构建、打包等方法，这说明“配方”常是将输入和动作组织起来的定义，而不只是一条字符串命令。[S3]

我们的首版进一步收紧：采用声明式动作，引用应用内可信适配器，不在知识包里携带可任意执行的适配器实现。例如：

```json
{
  "step_id": "install.runtime",
  "depends_on": [],
  "adapter_id": "demo.package-manager",
  "action": "package.install",
  "arguments": {
    "package": {"literal": "demo-runtime"},
    "version": {"parameter": "version"}
  },
  "artifact_refs": [],
  "submission": "user_enter",
  "idempotency": "check_before_stage",
  "locks": ["package-manager:demo"]
}
```

这里没有实际命令，demo 适配器也尚不存在。程序确认受支持的适配器和动作后，才能绑定参数并生成适合目标 Shell 的命令。未知 adapter/action 必须拒绝，不能退化为让模型编写任意脚本。

直接下载的动作必须引用带散列的 artifacts；使用包管理器的动作还需要由可信适配器在实例化 Plan 时固定来源和解析结果，不能以配方里一个版本字符串替代整个供应链校验。本次未实现该解析锁定机制。

`effects` 是待核对的副作用声明，不是自动授权；适配器实施范围和应用策略必须与其一致。若执行依赖包管理器生命周期脚本，仍需纳入审核，不因 package.install 是结构化动作就忽略。

完整示例：`design/knowledge/examples/recipes/demo-runtime.json`。candidate、unreviewed、无测试报告，只匹配虚构 example-os，不代表任何真实 Harmony 配方。

## 6. 三类“版本”与动态状态不能混用

- schema_version：字段与语义的版本，例如本次 0.1.0。
- id + revision：对象内容版本；同一对身份不得对应不同字节。
- bundle revision：分发快照；可以重新组合不同但固定的对象修订。

任何证据、条件、步骤或审核内容改变，应发布新修订。被引用的旧修订仍可用于审计。

撤回需要独立、受信任且有新鲜度保证的发布元数据，可以指向历史 id / revision。不要为了撤回而覆盖旧文件、使已归档摘要失效；历史文件即使写着 verified，当前有效状态也可以因外部撤回而变成禁止使用。

TUF 处理信任根、目标文件、快照一致性、时间戳和版本等更新安全问题，可作为后续更新实现的参考；本次示例不包含完整 TUF 客户端或服务器。[S4]

## 7. 适用性判断与准入规则

当前 Schema 故意只定义 `eq` 与 `in`，不假装所有 OS / ABI 版本都可按 SemVer 比较。后续增加范围比较时必须同时定义比较方案、边界和测试。

```text
所有必需条件成立 → match
至少一项明确不满足 → mismatch
没有明确不满足，但缺事实 → unknown / need_context
```

证据可以被用于说明 unknown；配方在关键条件 unknown 时不能形成可执行建议。

要允许进入回显流程，后续运行时至少必须同时确认：

1. 知识包发布元数据可信、未过期、未撤回，并满足应用兼容要求。
2. 配方修订经过可信审核与适用环境测试，且当前没有撤回。
3. 引用、依赖、制品完整性、来源和授权检查通过。
4. 当前用户参数和环境全部满足要求，适配器是应用允许的实现。
5. Plan 固定当前会话、环境快照、配方及制品版本。
6. 原 ShellSession 的绑定、提示符和输入状态检查通过。

通过以上门槛也只是允许回显，仍必须等用户 Enter。额外验证命令默认也需要 Enter，不得把 verification 字段当作后台任意命令执行入口。

## 8. 本轮提供的可校验文件

```text
design/knowledge/
  README.md
  schemas/
    common.schema.json
    bundle.schema.json
    evidence.schema.json
    recipe.schema.json
  examples/
    manifest.json
    evidence/demo-guide.json
    recipes/demo-runtime.json
    sources/demo-guide.txt
  validate_examples.py
```

使用 JSON Schema Draft 2020-12。公共 Schema 提供身份、修订、条件、审核与测试环境定义，三份主体 Schema 限制各自字段。[S5]

校验分两层：

- Schema：字段、类型、必需项、状态相关结构约束、参数绑定形态。
- 样例完整性：摘要和大小、包内路径、对象身份、固定引用、公共 / 私有证据边界、步骤顺序、参数引用、依赖闭环和索引修订一致性。

样例校验器拒绝 released 包，始终输出 `release_authorized: false`。它不是生产导入器、发布审核器、签名验证器、命令生成器或沙箱。

本轮已通过正常样例校验和 10 项拒绝检查：文件篡改、未知证据引用、未经审核却标为 verified、额外原始脚本字段、私有证据混入、配方依赖循环、无效步骤依赖、未知制品引用、越界路径及非法参数值。这些检查不等于生产安全认证。

例如，把 candidate 改成 verified 而不提供审核与通过测试记录，会被 Schema 拒绝；即使伪造字段使格式通过，也不能获得运行时权限。测试真实性与发布者身份只能由外部信任机制验证。

## 9. 有意留待下一阶段的内容

- 正式发布者与审核者身份、签名、密钥轮换、撤回和离线过期策略。
- 各个 action / adapter 的精确参数契约和可信命令模板。
- 包管理器依赖解析锁定、产物证明、重定向与来源白名单策略。
- 目标设备的事实采集、版本比较和沙箱能力。
- 可执行验证步骤、锁生命周期和部分失败恢复。
- 知识 API 的检索结果结构、索引构建与召回评测。

第一版数据契约优先固定“对象如何关联、什么不能被冒充”，不把尚未实现的生产能力藏在一个 status 或 confidence 字段里。

## 10. 来源与核实边界

参考一手资料，不宣称采用其全部规范，也不宣称数据契约已在 Harmony 设备上验证。

- [S1] Frictionless Data Package，Data Package standard。`https://datapackage.org/standard/data-package/`
- [S2] W3C，PROV Overview / PROV-DM。`https://www.w3.org/TR/prov-overview/`、`https://www.w3.org/TR/prov-dm/`
- [S3] Conan 2，Recipe API reference。`https://docs.conan.io/2/reference/conanfile.html`
- [S4] The Update Framework，Specification。`https://theupdateframework.github.io/specification/latest/`
- [S5] JSON Schema，Draft 2020-12。`https://json-schema.org/draft/2020-12`
