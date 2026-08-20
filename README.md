# Claudian Local Models Skill

[中文](#中文说明) · [English](#english)

## 中文说明

这是一个供 Codex 使用的安装型 Skill。它帮助用户把 Obsidian、Claudian、Claude Code、CCSwitch、Ollama 和专业模型 MCP 连接成一套本地多模型工作流。

日常使用入口是 Obsidian 里的 Claudian。主模型由 CCSwitch 随时切换，MedGemma 等专业模型保持为独立 MCP，不会随着主模型切换而消失。

```text
Obsidian
  └─ Claudian
       └─ Claude Code
            ├─ CCSwitch 当前选中的主模型
            │    ├─ 本地 Qwen
            │    ├─ DeepSeek
            │    └─ 其他兼容模型
            └─ 专业模型 MCP
                 ├─ MedGemma
                 └─ 其他 Ollama 模型
```

### 能做什么

- 检查 Obsidian 仓库中是否安装了 Claudian
- 检查 Claude Code、CCSwitch、Ollama 和 Python
- 把兼容 Claude Code 的 Ollama 模型添加为 CCSwitch Claude Provider
- 把一个或多个专业模型注册为 Claude Code 用户级 MCP
- 支持文本模型和受限目录内的图像输入
- 提供预检、计划、安装、验证和卸载流程
- 写入 Claude Code 或 CCSwitch 配置前创建备份
- 防止卸载正在使用的 CCSwitch Provider
- 处理部分本地模型泄露思考过程的问题，只返回最终答案

### 适合谁

这套 Skill 适合主要在 Obsidian Claudian 中工作，同时希望保留以下能力的用户。

- 用 CCSwitch 在本地模型和在线模型之间切换
- 用 Qwen 等模型承担日常对话、笔记编辑和文件操作
- 在医学、翻译、法律或其他专业任务中调用单独的本地模型
- 让 Codex 完成环境检查、安装和验证

### 前置条件

准备以下软件。

- macOS 或 Linux
- Obsidian 桌面版
- Claudian 插件
- Claude Code
- CCSwitch
- Ollama
- Python 3.10 或更高版本
- Codex

主模型还需要兼容 Claude Code 所使用的 Anthropic Messages 接口。一个模型能够在 Ollama 中聊天，并不代表它能够可靠执行 Claude Code 的文件和工具操作。

当前版本已经实际验证 `qwen3.5-claude:4b` 的 Anthropic Messages 接口，以及 `medgemma1.5:4b-it-q4_K_M` 的 MCP 健康检查和真实推理。其他模型仍需逐个验证能力和许可证。

### 安装 Skill

仓库为私人仓库时，先确认本机的 GitHub 凭据能够访问它。

```bash
git clone https://github.com/Basinock/claudian-local-models-skill.git
mkdir -p ~/.codex/skills
cp -R claudian-local-models-skill/setup-claudian-local-models ~/.codex/skills/
```

已经登录 GitHub CLI 时，也可以运行 `gh repo clone Basinock/claudian-local-models-skill`。

重新打开 Codex 任务，使新 Skill 出现在可用列表中。

### 最简单的使用方式

在 Codex 中输入下面的请求，并替换模型标签。

```text
使用 $setup-claudian-local-models，
把 qwen3.5-claude:4b 添加为 CCSwitch 主模型，
把 medgemma1.5:4b-it-q4_K_M 添加为 Claudian 可调用的医学 MCP。
```

也可以让 Skill 逐项询问。

```text
使用 $setup-claudian-local-models 交互式配置我的 Claudian 本地多模型环境。
```

Skill 会依次运行预检和计划。模型下载、替换已有 MCP、直接写入 CCSwitch 数据库等操作仍需用户明确确认。

### 配置示例

Skill 内置的安装器使用 JSON 描述目标环境。

```json
{
  "vault": "/Users/example/Documents/MyVault",
  "ollama_url": "http://127.0.0.1:11434",
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
      "description": "Use for medical text and supported medical-image analysis. The result is informational, not a diagnosis.",
      "system_prompt": "你是医学信息分析助手。明确区分事实、推断和不确定性，不得把输出表述为最终诊断。",
      "vision": true
    }
  ]
}
```

完整字段说明见 [`configuration.md`](setup-claudian-local-models/references/configuration.md)。

### 安装器命令

多数用户直接让 Codex 调用 Skill 即可。需要手动排查时，可以运行下面的命令。

```bash
python3 setup-claudian-local-models/scripts/stackctl.py preflight --config /absolute/path/stack.json
python3 setup-claudian-local-models/scripts/stackctl.py plan --config /absolute/path/stack.json
python3 setup-claudian-local-models/scripts/stackctl.py install --config /absolute/path/stack.json --ccswitch guide
python3 setup-claudian-local-models/scripts/stackctl.py verify --config /absolute/path/stack.json
```

`plan` 相当于只读预演。只有确认模型许可证、下载体积和磁盘空间后才使用 `--pull`。

### CCSwitch 的两种配置方式

`guide` 是默认方式。安装器输出 Provider 配置，由用户在 CCSwitch 中确认和添加。这种方式对不同 CCSwitch 版本更稳妥。

`database` 会直接写入 CCSwitch 的 SQLite 数据库。脚本会先检查结构并创建备份，默认不会激活新 Provider。只有看过计划输出并确认目标数据库后才应使用。

```bash
python3 setup-claudian-local-models/scripts/stackctl.py install \
  --config /absolute/path/stack.json \
  --ccswitch database
```

更多说明见 [`ccswitch.md`](setup-claudian-local-models/references/ccswitch.md)。

### 在 Claudian 中使用

在 CCSwitch 里选择目标 Claude Provider，随后在 Claudian 新建对话。新的 Claude Code 会话会读取当前 Provider。

如果 Claudian 仍然连接旧模型，依次尝试新建对话、重载 Claudian、重启 Obsidian。

专业模型可以自动调用。

```text
分析当前笔记。涉及医学术语、临床推断或医学图像时，调用 medgemma MCP 获取第二意见，并标出不确定性。
```

也可以明确指定工具。

```text
调用 medgemma MCP 的 ask_medical_model，分析当前笔记中的检查结果。不要给出最终诊断。
```

切换 CCSwitch 主模型不会修改用户级 MCP。完整用法见 [`usage.md`](setup-claudian-local-models/references/usage.md)。

### 安全边界

- Ollama 默认连接 `127.0.0.1`，不要在不了解风险时暴露到公网
- 图像工具只能读取所选 Obsidian 仓库和明确允许的目录
- 医学、法律和金融模型只提供辅助分析
- 安装器不会把真实 API Key 写入示例配置
- 同名 MCP 只有在用户确认 `--replace-existing` 后才会替换
- 正在使用的 CCSwitch Provider 不会被卸载器删除

### 卸载

先查看安装清单，再运行卸载命令。

```bash
python3 setup-claudian-local-models/scripts/stackctl.py uninstall \
  --config /absolute/path/stack.json \
  --remove-runtime
```

只有确认目标 Provider 已经停用后才添加 `--remove-provider`。

### 项目结构

```text
setup-claudian-local-models/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── assets/
│   └── ollama-specialist-mcp/
├── references/
│   ├── ccswitch.md
│   ├── configuration.md
│   └── usage.md
└── scripts/
    └── stackctl.py
```

## English

This repository contains a Codex installation Skill for a local multi-model workflow built around Obsidian Claudian.

Claudian remains the daily interface. Claude Code runs inside Claudian, CCSwitch selects the current primary model, and specialist Ollama models remain available through user-scoped MCP servers.

```text
Obsidian
  └─ Claudian
       └─ Claude Code
            ├─ Primary model selected in CCSwitch
            │    ├─ Local Qwen
            │    ├─ DeepSeek
            │    └─ Other compatible providers
            └─ Specialist MCP servers
                 ├─ MedGemma
                 └─ Other Ollama models
```

### What it provides

- Detects Claudian inside the selected Obsidian vault
- Checks Claude Code, CCSwitch, Ollama, and a suitable Python runtime
- Adds a Claude-compatible Ollama model as a CCSwitch Claude Provider
- Registers one or more specialist models as user-scoped Claude Code MCP servers
- Supports text models and image input from explicitly allowed directories
- Provides preflight, plan, install, verify, and uninstall commands
- Backs up Claude Code and CCSwitch configuration before replacement or database writes
- Refuses to remove an active CCSwitch Provider
- Removes common reasoning wrappers from local-model tool output

### Requirements

- macOS or Linux
- Obsidian Desktop
- Claudian
- Claude Code
- CCSwitch
- Ollama
- Python 3.10 or newer
- Codex

The primary model must support the Anthropic Messages interface used by Claude Code. Basic Ollama chat support does not guarantee reliable file operations or tool use.

The current release has been tested with `qwen3.5-claude:4b` through the Anthropic Messages interface and `medgemma1.5:4b-it-q4_K_M` through an MCP health check and a real inference call. Other models still require individual capability and license review.

### Install the Skill

Make sure the current GitHub credentials can access this private repository.

```bash
git clone https://github.com/Basinock/claudian-local-models-skill.git
mkdir -p ~/.codex/skills
cp -R claudian-local-models-skill/setup-claudian-local-models ~/.codex/skills/
```

When GitHub CLI is authenticated, `gh repo clone Basinock/claudian-local-models-skill` is also available.

Open a new Codex task so the installed Skill is discovered.

### Use it from Codex

Replace the model tags in this example.

```text
Use $setup-claudian-local-models to add qwen3.5-claude:4b as a CCSwitch primary model and expose medgemma1.5:4b-it-q4_K_M as a medical MCP for Claudian.
```

For an interactive setup, use this prompt.

```text
Use $setup-claudian-local-models to configure my Claudian local multi-model environment interactively.
```

The Skill runs preflight and plan before installation. Model downloads, replacement of existing MCP servers, and direct CCSwitch database writes require explicit confirmation.

### Configuration example

```json
{
  "vault": "/Users/example/Documents/MyVault",
  "ollama_url": "http://127.0.0.1:11434",
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
      "description": "Use for medical text and supported medical-image analysis. The result is informational, not a diagnosis.",
      "system_prompt": "Act as a medical information assistant. Separate facts, inference, and uncertainty. Do not present the output as a final diagnosis.",
      "vision": true
    }
  ]
}
```

See [`configuration.md`](setup-claudian-local-models/references/configuration.md) for every supported field.

### Installer commands

Most users should let Codex run these commands through the Skill. They are also available for manual diagnostics.

```bash
python3 setup-claudian-local-models/scripts/stackctl.py preflight --config /absolute/path/stack.json
python3 setup-claudian-local-models/scripts/stackctl.py plan --config /absolute/path/stack.json
python3 setup-claudian-local-models/scripts/stackctl.py install --config /absolute/path/stack.json --ccswitch guide
python3 setup-claudian-local-models/scripts/stackctl.py verify --config /absolute/path/stack.json
```

`plan` is the read-only preview. Use `--pull` only after reviewing model licenses, download size, disk space, and expected duration.

### CCSwitch modes

`guide` is the default. The installer prints the Provider configuration so the user can review and add it in CCSwitch. This is the safer choice across unknown CCSwitch versions.

`database` writes directly to the CCSwitch SQLite database. The installer validates the schema, creates a backup, and leaves the new Provider inactive unless activation was explicitly requested.

```bash
python3 setup-claudian-local-models/scripts/stackctl.py install \
  --config /absolute/path/stack.json \
  --ccswitch database
```

See [`ccswitch.md`](setup-claudian-local-models/references/ccswitch.md) before using database mode.

### Use it in Claudian

Select a Claude Provider in CCSwitch, then start a new Claudian conversation. If the previous endpoint remains cached, reload Claudian or restart Obsidian.

Example with automatic specialist routing

```text
Analyze the current note. Call the medgemma MCP for medical terminology, clinical inference, or supported medical-image analysis, and clearly mark uncertainty.
```

Example with an explicit tool request

```text
Call ask_medical_model from the medgemma MCP to analyze the test results in the current note. Do not provide a final diagnosis.
```

Changing the CCSwitch primary Provider does not remove user-scoped MCP servers. See [`usage.md`](setup-claudian-local-models/references/usage.md) for troubleshooting and operating details.

### Safety boundaries

- Keep Ollama on `127.0.0.1` unless network exposure is intentional and secured
- Image tools can only read the selected vault and explicitly allowed directories
- Medical, legal, and financial models provide supporting analysis only
- Real API keys are not stored in the example configuration
- Existing MCP servers require `--replace-existing` before replacement
- The uninstaller refuses to delete the active CCSwitch Provider

### Uninstall

```bash
python3 setup-claudian-local-models/scripts/stackctl.py uninstall \
  --config /absolute/path/stack.json \
  --remove-runtime
```

Add `--remove-provider` only after switching away from the Provider that will be removed.

### Repository layout

```text
setup-claudian-local-models/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── assets/
│   └── ollama-specialist-mcp/
├── references/
│   ├── ccswitch.md
│   ├── configuration.md
│   └── usage.md
└── scripts/
    └── stackctl.py
```

## License

No repository license has been added yet. Access to the private repository does not grant redistribution rights. Individual model licenses remain separate and must be reviewed before download or use.
