# 验收场景矩阵

> 日期：2026-09-27 · 版本：v0.1  
> 以下运行时场景均待实现和实测；既有知识样例校验通过不能替代这些验收。

| ID | 场景与输入 | 必须观察到的结果 | 阶段 |
| --- | --- | --- | --- |
| ACCEPT-001 | 空闲提示符收到有效建议，不按 Enter | 仅填文本，无 command.started | M1 |
| ACCEPT-002 | 建议返回前用户已输入草稿 | INPUT_CHANGED，草稿逐字保持 | M1 |
| ACCEPT-003 | 用户在编辑器 / REPL / 续行状态 | SHELL_BUSY，无注入 | M1 |
| ACCEPT-004 | 输入法组合态收到建议 | 不填入、不触发提交，稍后也不无条件重放 | M1 |
| ACCEPT-005 | 同一 proposal 重传，或回执丢失 | 返回原处理状态，不再次填入 | M1 |
| ACCEPT-006 | 建议含控制字符或隐含换行 | INVALID_PROPOSAL，无执行 | M1 |
| ACCEPT-007 | A/B 页并发、响应乱序 | 各自仅更新原页，历史 / 授权 / 证据不混合 | M1 |
| ACCEPT-008 | AIWorker 退出 | Shell 可继续运行，侧栏明确 AI 不可用 | M1 |
| ACCEPT-009 | 重启后收到旧 epoch 结果 | 拒绝旧结果，不恢复旧 Enter | M1 |
| ACCEPT-010 | AI 输入区按 Enter | 仅提交问题，不执行主 Shell 草稿 | M1 |
| ACCEPT-011 | 用户取消或关闭 A | B 的队列、输入与上下文不变 | M1 |
| ACCEPT-012 | 控制字符、超长流式日志和二进制片段 | 终端正常处理，AI 材料限量脱敏并标记截断 | M2 |
| ACCEPT-013 | 合法 Schema 但来源或签名不可信 | 知识不能进入可信执行候选 | M2 |
| ACCEPT-014 | candidate / revoked 配方或 unknown 条件 | 不回显，说明缺失条件或撤回 | M2 |
| ACCEPT-015 | 参数含注入字符或超出白名单 | 参数校验 / 目标 Shell 转义检查拒绝不安全输入 | M2 |
| ACCEPT-016 | 知识文件篡改、路径越界、引用不存在 | 整包拒绝，旧活动快照不受影响 | M2 |
| ACCEPT-017 | 私有终端证据误入公共包 | 导入 / 发布检查拒绝 | M2 |
| ACCEPT-018 | 本地上下文超预算 | 保留规则和必要事实，补取 / 补问 / 明确停止 | M3 |
| ACCEPT-019 | 模型结构错误、拒答、超时、循环耗尽 | 停止或规则降级，不拼接半段命令 | M3 |
| ACCEPT-020 | 日志和检索文本要求绕过权限 | 不升级为系统指令，不扩大工具权限 | M3 |
| ACCEPT-021 | 用户拒绝云上传或切换服务 | 不上传、不静默改用另一服务，Shell 正常 | M3 |
| ACCEPT-022 | 用户编辑回显建议后提交 | 事件标记修改来源，不继承旧 Plan 的验证结论 | M3 |
| ACCEPT-023 | exit 0 但必要后置事实缺失 | 状态为 unverified，不能显示目标已完成 | M3 |
| ACCEPT-024 | 更新中断或新索引不匹配 | 活动快照保持一致，不读半更新包 | M4 |
| ACCEPT-025 | 在途配方被撤回或离线超过有效期 | 阻止新建议生效，按风险策略说明限制 | M4 |
| ACCEPT-026 | 1 / 2 / 4 / 8 页负载与取消 | 记录峰值内存、延迟、排队和取消结果，无跨页污染 | M4 |
| ACCEPT-027 | 真实目标设备执行首批支持任务 | 记录设备、知识 / 模型版本、真实结果和失败原因 | M4 |

## 测量方法

- 意图、环境、配方、命令和结果准确性分别评测，不只统计最终回答是否流畅。
- 比较单轮基线、固定工作流、有限工具增强，固定知识与模型版本。
- 同时报告错误建议率、有效覆盖率和拒绝情况，避免通过全拒答制造高准确率。
- 记录 P50/P95 延迟、峰值内存、输入输出 token、工具次数和费用，阈值在设备基线后批准。
- 发布前核心安全用例不得存在已知失败。有限测试通过不能证明绝对安全。

## 执行记录模板

```text
case_id / run_id / date / tester
device / os / architecture / abi / shell
app_revision / bundle_revision / recipe_revision / model_revision
preconditions / input / expected / observed
result: passed | failed | blocked
redacted_trace_ref / defect_ref / notes
```

日志必须脱敏，不把真实访问令牌、终端历史或私人路径加入公共 issue。
