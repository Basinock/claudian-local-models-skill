# Claudian 使用方法

## 切换主模型

1. 保持 Ollama 正在运行。
2. 在 CCSwitch 的 Claude Provider 列表中选择目标模型。
3. 在 Claudian 新建对话，使新的 Claude Code 会话重新读取 Provider。
4. 如果仍连接旧模型，重载 Claudian；仍未生效时重启 Obsidian。

切换 CCSwitch Provider 不会修改用户级 MCP 配置，因此 MedGemma 等专业模型会继续可用。

## 调用专业模型

让 Claude Code 根据工具描述自动选择：

```text
分析当前笔记；涉及医学术语、临床推断或医学图像时，调用 medgemma MCP 获取第二意见，并标出不确定性。
```

明确指定：

```text
调用 medgemma MCP 的 ask_medical_model，分析当前笔记中的检查结果。不要给出最终诊断。
```

Claudian 支持 MCP 提及时，也可以在消息中提到对应的 `@服务器名`。不同版本的显示形式可能不同，以 Claudian 的 MCP 列表为准。

## 验证

```bash
claude mcp list
claude mcp get medgemma
ollama list
```

然后在 Claudian 新对话中先要求调用 MCP 的健康检查工具，再进行真实问题测试。

## 常见问题

- 主模型能聊天但不会操作文件：该模型可能不能可靠执行 Claude Code 工具调用，把它降级为专业 MCP。
- 切换后仍是旧模型：新建对话，随后重载 Claudian 或 Obsidian。
- MCP 在终端可见但 Claudian 不可见：确认 Claudian 使用 Claude Code 后端，并重建 Claudian 会话。
- 多个 MCP Python 进程：每个仍打开的 Claudian/Claude Code 会话可能各自启动一份 stdio Server；关闭旧会话后再次检查。
- 医学或法律模型输出：只作为辅助分析，不当作诊断、处方或正式法律意见。
