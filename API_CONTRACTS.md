# 运行时接口与消息契约

> 版本：v0.1 · 日期：2026-09-27  
> 用于第一条开发纵向链路。继承 `SESSION_PROTOCOL.md` 的身份和执行边界，补齐调用方、输入、输出、错误及幂等语义。

## 1. 类型与规则

- Identifier 为非空字符串，程序生成且绑定连接，不使用进程 PID 作为会话身份。
- Revision 为非负整数，知识对象 revision 从 1 开始。旧 Session 文档中的 r3 仅为说明示例，新知识契约统一使用整数。
- 时间使用带时区的 RFC3339 字符串；超时判定采用进程内单调时钟，跨进程传递有效期并做保守检查。
- 所有数组、文本和帧受开发配置上限限制，未知主协议版本拒绝。
- 一个命令建议只绑定一个确定页面、任务和原始请求，不能随活动 Tab 切换重定向。

## 2. SessionBinding

```text
page_id, shell_session_id, ai_session_id, worker_id, binding_epoch
channel_identity, created_at, state(active | closing | closed)
```

Supervisor 创建绑定。模型不接收可修改路由的权限。断连 / 重建后使用新的 binding_epoch，旧绑定不可复用。

## 3. 消息信封

```json
{
  "protocol_version": "1.0",
  "message_id": "msg-example-001",
  "page_id": "page-example-A",
  "binding_epoch": "epoch-example-1",
  "shell_session_id": "shell-example-A",
  "ai_session_id": "ai-example-A",
  "task_id": "task-example-1",
  "request_id": "request-example-1",
  "type": "shell.context.snapshot",
  "sequence": 1,
  "reply_to": null,
  "payload": {}
}
```

该 JSON 只演示信封，payload 必须按消息类型补齐。sequence 在发送方与 epoch 内递增，不要求双向共用计数器。task_id / request_id 在一般问答中可为空，但 propose 必须有明确任务与请求。

| 类型 | 发送方 / 接收方 | payload 必要内容 |
| --- | --- | --- |
| ai.user.ask | UI / AISession | question、context_mode(none / current_task)、task_ref |
| shell.context.snapshot | ShellAdapter / AISession | ContextSnapshot |
| shell.context.changed | ShellAdapter / AISession | 新 revision、changed_fields、snapshot_ref |
| shell.command.started | ShellAdapter / AISession | command_id、文本摘要、origin、proposal_id 或 null |
| shell.command.finished | ShellAdapter / AISession | command_id、exit_status、signal、output_refs、truncation |
| ai.context.request | AISession / ShellAdapter | query_id、允许的 fact_names 或 evidence_refs、limit |
| shell.context.result | ShellAdapter / AISession | query_id、facts / excerpts、missing、denied、revision |
| ai.command.propose | AISession / ShellAdapter | CommandProposal |
| shell.command.stage_result | ShellAdapter / AISession | StageResult |
| ai.view.delta | AISession / 本页侧栏 | stream_id、sequence、text、done |
| request.cancel | UI 或会话端 / 对端 | request_id、reason |
| session.close | Supervisor / 页内端点 | binding_epoch、reason |

新增 context.result 明确完成补取请求回执；既有快照仍承担初始同步和全量重同步。view.delta 不进入 PTY，不包含可提交命令的隐含控制动作。协议不存在 shell.execute。

## 4. ContextSnapshot

```text
context_revision, captured_at, command_id?
host_identity, cwd, shell_kind
facts[{name, value, source, observed_at, freshness}]
prompt_generation, input_revision
foreground_state(idle_shell | running | repl | editor | continuation | unknown)
composition_active, input_owner, input_empty
last_exit_status?, evidence_refs[], missing_facts[], redactions[], truncation
```

事实缺失保留 unknown；输入桥状态未知时不回显。readExcerpt 只接受本会话证据 ID 与范围，不接受任意文件路径。

## 5. ModelResult

ModelService 返回完整对象后才交 Scheduler 校验，类型互斥：

| kind | 必要字段 | 后续动作 |
| --- | --- | --- |
| answer | text、evidence_ids | 只显示侧栏 |
| need_context | tool_name、arguments、reason | 工具白名单与本页权限检查 |
| need_clarification | question、missing_conditions | 等待用户回答 |
| recipe_candidate | recipe_id、recipe_revision、parameters、evidence_ids、missing_conditions | 交 PlanBuilder，不直接填命令 |
| no_verified_solution | reason、missing_conditions | 说明限制并停止当前生成 |
| out_of_scope | reason | 告知范围，不读取工程源代码 |

模型输出中的身份、风险或成功自评不能覆盖程序事实。模型拒答、截断、非法结构、超时和工具循环耗尽均明确返回失败状态。

## 6. Knowledge API

调用上下文由可信代码注入：`session_binding + authorization + knowledge_snapshot`。模型只提供允许的业务参数。

| 操作 | 参数 | 结果 |
| --- | --- | --- |
| searchEvidence | query、environment_constraints、limit | items[{id, revision, excerpt, source, applicability}] |
| findRecipes | goal、environment_constraints、limit | candidates[{id, revision, status, compatibility, missing_conditions}] |
| getRecipe | id、revision | 固定 Recipe，或 NOT_FOUND / REVOKED |
| checkCompatibility | recipe_ref、environment_snapshot | match / mismatch / unknown，逐条件依据 |
| readTaskExcerpt | evidence_id、range、byte_limit | text、actual_range、truncation、redactions |

检索结果 pin 到 bundle revision。模型或客户端不能通过修改查询参数访问另一页面私有日志。unknown 不能通过可执行建议准入。

## 7. Plan 与 CommandProposal

Plan 属于本会话，至少包含：

```text
plan_id, plan_revision, request_id, context_revision
bundle_id, bundle_revision, recipe_id, recipe_revision
validated_parameters, evidence_refs, resolved_dependencies, artifact_lock
adapter_revision, shell_kind, current_step, affected_scopes
verification_state, authorization_ref, expires_at, plan_digest
```

plan_digest 必须由规范化的可信 Plan 表示计算，且 Plan 存在于程序注册表。不能只比较模型自报摘要就相信计划已审核。

CommandProposal 示例字段：

```text
proposal_id, plan_id, plan_digest
based_on_context_revision
expected_prompt_generation, expected_input_revision
recipe_id, recipe_revision
command_text, command_digest
expires_at
```

本次没有规定 Plan 序列化和签名算法的最终生产实现。开发时固定一种确定性编码并加入摘要回归样例；私有计划不从不可信 IPC 消息中重新构建授权。

## 8. StageResult 与提交语义

```text
proposal_id
status: staged | rejected | already_processed
reason_code?, resulting_input_revision?
original_status?  用于重复请求回执
```

- staged 表示文本已进入输入行，不表示执行或全部副作用获准。
- already_processed 不再次修改输入，返回原处理状态。
- 用户手动清除草稿后，重复消息也不能重新填回。
- 提交源 origin 为 user、accepted_proposal 或 user_edited_proposal。
- 编辑后的文本由正常 Shell 执行，但不得把原计划验证结论套到新文本。
- 调用 stageCommand 不得调用 accept-line 或模拟键盘 Enter。

## 9. 错误分类

| 错误码 | 行为 |
| --- | --- |
| BINDING_MISMATCH / STALE_EPOCH | 丢弃结果，记录脱敏路由错误 |
| INPUT_CHANGED / SHELL_BUSY | 保留 Shell 输入，侧栏说明 |
| STALE_CONTEXT / PLAN_EXPIRED | 使建议失效，必要时重新取快照 |
| INVALID_PROPOSAL | 不回显，不进行无限模型修复 |
| RECIPE_UNTRUSTED / REVOKED | 阻止候选进入回显链路 |
| PERMISSION_DENIED / UPLOAD_NOT_AUTHORIZED | 停止对应读取或上传，保留本地路径 |
| REQUEST_BUSY / BUDGET_EXCEEDED | 有界排队或拒绝，不无限积压 |
| MODEL_TIMEOUT / MODEL_UNAVAILABLE | 侧栏提示或规则降级，Shell 继续运行 |
| NO_VERIFIED_SOLUTION | 输出缺少的证据或条件，不编造命令 |

所有 AI 错误只显示在侧栏，普通 Shell 的 stderr 保持真实程序语义。

## 10. 取消、重试和一致性

取消先更新本会话取消状态，再通知模型 / 工具；不能因工具暂时不可取消而接受迟到结果。重复 context request 可返回相同快照，但不能扩大读取范围。

context.changed、用户新问题或模型切换会使相关在途任务保留版本关联或取消。不同请求可以共享只读索引，但不能共享可变任务队列。

协议字段、传输编码和 Schema 的机器化实现属于 M0 / M1 任务。本文是开发契约，不声称已有完整运行时协议库。
