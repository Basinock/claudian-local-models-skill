# CCSwitch 配置策略

优先使用 CCSwitch 自身的导入、编辑或 UI 功能。只有在用户明确同意、`plan` 输出正确且数据库结构匹配时，才使用安装器的数据库模式。

## Guide 模式

运行：

```bash
python3 scripts/stackctl.py plan --config stack.json
```

读取输出中的 `ccswitch_provider`，在 CCSwitch 新建 Claude Provider，并填写其中的环境变量。该模式不修改 CCSwitch。

## Database 模式

运行：

```bash
python3 scripts/stackctl.py install --config stack.json --ccswitch database
```

安装器会：

1. 检查 `providers` 表所需字段。
2. 将数据库备份到同目录的 `backups/`。
3. 按 `app_type=claude` 和 Provider 名称更新或插入。
4. 默认保持 Provider 未激活，除非配置含 `"activate": true`。

不要在 CCSwitch 正在执行切换或数据库迁移时写入。写入完成后重新打开 Provider 列表；如果 UI 未刷新，重启 CCSwitch。

卸载时只删除安装清单记录的、当前未激活的 Provider，避免删除正在使用的主模型。
