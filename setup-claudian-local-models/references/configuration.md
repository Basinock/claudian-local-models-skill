# 配置格式

使用 JSON 保存一次安装所需的信息。不要在配置文件中保存真实 API Key；Ollama 的本机兼容接口只使用占位值 `ollama`。

```json
{
  "vault": "/Users/example/Documents/MyVault",
  "ollama_url": "http://127.0.0.1:11434",
  "python": "/opt/homebrew/bin/python3.12",
  "install_root": "~/.local/share/claudian-local-models",
  "primary": {
    "provider_name": "Ollama Qwen",
    "model": "qwen3.5-claude:4b",
    "auto_compact_window": 28000,
    "activate": false
  },
  "specialists": [
    {
      "name": "medgemma",
      "model": "medgemma1.5:4b-it-q4_K_M",
      "tool_name": "ask_medical_model",
      "description": "Use for medical terminology, medical text analysis, clinical reasoning, and supported medical-image interpretation. Treat the result as informational, not a diagnosis.",
      "system_prompt": "你是医学信息分析助手。明确区分事实、推断和不确定性，不得把输出表述为最终诊断。",
      "vision": true,
      "allowed_image_roots": []
    }
  ]
}
```

## 字段

- `vault`：使用 Claudian 的 Obsidian 仓库。安装器据此检查 Claudian，并限制专业模型可读取的图片路径。
- `ollama_url`：只使用受信任的本机或内网 Ollama 地址。默认 `http://127.0.0.1:11434`。
- `python`：可选的 Python 3.10+ 路径。省略时自动寻找 3.13、3.12、3.11 或 3.10；macOS 自带的旧版 Python 不会被用于 MCP 虚拟环境。
- `primary`：省略时不创建 CCSwitch Provider。
- `primary.provider_name`：CCSwitch 中显示的名称。
- `primary.model`：精确的 Ollama 标签，包含 tag。
- `primary.activate`：默认 `false`，避免安装时打断当前 CCSwitch Provider。
- `specialists`：可配置多个模型；每个条目生成一个 Claude Code 用户级 MCP Server。
- `specialists[].name`：MCP Server 名称。使用短横线，不要与现有服务器重名。
- `specialists[].tool_name`：该 MCP 内暴露的专业工具名。
- `specialists[].description`：决定 Claude Code 何时调用工具，必须写清适用范围和限制。
- `specialists[].vision`：允许传入图片路径。开启后仍只能读取仓库和 `allowed_image_roots` 中的图片。

## 命令

```bash
python3 scripts/stackctl.py plan --config stack.json
python3 scripts/stackctl.py install --config stack.json --ccswitch guide
python3 scripts/stackctl.py install --config stack.json --ccswitch database --pull
python3 scripts/stackctl.py verify --config stack.json
python3 scripts/stackctl.py uninstall --config stack.json --remove-runtime
```

只有在确认模型许可证、下载大小和磁盘空间后才传 `--pull`。只有在检查计划输出和 CCSwitch 数据库备份位置后才使用 `--ccswitch database`。
