# 知识数据契约与样例

版本：0.1.0。解释文档见根目录 `KNOWLEDGE_CONTRACTS.md`。

本目录提供三类对象的 JSON Schema、公共定义、合成样例和完整性校验脚本。不是产品运行时，也不提供真实安装配方。

## 文件

- `schemas/bundle.schema.json`：知识包清单。
- `schemas/evidence.schema.json`：证据、来源与可见性。
- `schemas/recipe.schema.json`：声明式配方及审核、测试结构。
- `schemas/common.schema.json`：共用字段与条件。
- `examples/manifest.json`：引用证据与配方的完整草案包。
- `validate_examples.py`：Schema 和跨文件完整性校验。

## 校验

开发机需要 Python 3.10+ 和 `jsonschema[format-nongpl]` 4.x。它们只用于开发期校验，不是目标 Harmony Shell 的运行时依赖。本轮校验使用 jsonschema 4.26.0，安装在临时目录，没有写入用户业务工程依赖。

具备依赖的开发环境中执行：

```sh
python3 design/knowledge/validate_examples.py
```

建议在独立虚拟环境安装根目录 `requirements-dev.txt`。本轮曾使用临时依赖目录进行检查，该目录不随仓库分发，也不是部署配置。

预期结果：4 份 Schema、3 个已核对资源文件、2 条对象记录，`release_authorized` 为 false。Schema 引用在本地注册表中解析，不联网取模型或知识。

校验覆盖格式、文件摘要、身份和证据引用、公共包禁止会话私有证据、步骤和配方依赖、参数引用及索引版本。它不验证实际兼容性、许可授权真实性、测试真实性、签名、源站或命令安全。

## 修改样例

修改证据原始快照后，更新 Evidence 中的 source.sha256；修改任一资源后，更新 manifest.files 的 bytes 与 sha256。manifest 不在自己的文件清单中，正式发布应通过外部受信任元数据认证 manifest。

所有实例保持 draft / candidate / unreviewed。不得将本目录测试数据作为已验证知识发布。参数使用显式 literal / parameter 绑定，不接受自由脚本；发布与执行权限不能由 JSON 字段自行授予。
