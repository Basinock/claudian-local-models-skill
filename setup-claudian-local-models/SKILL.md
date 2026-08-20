---
name: setup-claudian-local-models
description: "Configure, verify, update, or uninstall a local multi-model stack for Obsidian Claudian: use CCSwitch to switch the Claude Code primary model, use Ollama to run open-source models, and expose one or more specialist models as user-scope Claude Code MCP tools. Use when a user wants Claudian to use a local Qwen or another Claude-compatible Ollama model, wants MedGemma or another domain model callable through MCP, wants Codex to install this stack, or needs to diagnose CCSwitch/Claudian/Ollama/MCP routing."
---

# Setup Claudian Local Models

Configure this data path:

```text
Obsidian → Claudian → Claude Code → CCSwitch-selected primary model
                              └──→ user-scope specialist MCP → Ollama
```

Treat Codex as the installer. Do not reconfigure Codex as the user's daily model unless explicitly requested.

## Collect the configuration

Ask only for missing values. Obtain:

- Obsidian vault path that contains Claudian.
- Exact Ollama tag for the primary model, or confirmation that no local primary is needed.
- CCSwitch Provider display name.
- Each specialist's exact Ollama tag, MCP server name, tool name, domain description, system prompt, and vision requirement.
- Whether to download missing models after reviewing licenses, disk use, and expected duration.
- Whether to use CCSwitch `guide` mode or the guarded `database` mode. Recommend `guide` for unknown CCSwitch versions.

Do not ask for or store real API keys for a localhost Ollama endpoint. Use the placeholder `ollama` required by compatible clients.

Read [references/configuration.md](references/configuration.md) before creating the JSON configuration. Store the working configuration in the current workspace or a temporary directory, never inside the Skill folder.

## Run the workflow

Resolve this Skill directory and use `scripts/stackctl.py` from it.

1. Run `preflight` and inspect every failed check.
2. Run `plan` and show the user the exact models, MCP names, target paths, CCSwitch Provider, and missing downloads.
3. Obtain explicit confirmation before using `--pull`, `--replace-existing`, or `--ccswitch database`.
4. Run `install` with the approved flags.
5. Run `verify`.
6. Ask the user to select the Provider in CCSwitch and start a new Claudian conversation.
7. Test a simple primary-model response and one explicit specialist MCP call in Claudian.

Example:

```bash
python3 <skill-dir>/scripts/stackctl.py preflight --config /absolute/path/stack.json
python3 <skill-dir>/scripts/stackctl.py plan --config /absolute/path/stack.json
python3 <skill-dir>/scripts/stackctl.py install --config /absolute/path/stack.json --ccswitch guide
python3 <skill-dir>/scripts/stackctl.py verify --config /absolute/path/stack.json
```

Use `--ccswitch database` only after reading [references/ccswitch.md](references/ccswitch.md). The script backs up the database and refuses an unrecognized schema, but CCSwitch's own UI/import path remains preferable.

## Apply compatibility gates

Require more from a primary model than from a specialist:

- Verify `/v1/messages` Anthropic compatibility.
- Test streaming and tool use through a fresh Claudian conversation.
- Reject the primary role if the model cannot reliably call Claude Code tools, even when basic chat succeeds.
- Offer to install an incompatible model as a specialist MCP instead.

For a specialist, verify Ollama reachability, exact model presence, MCP registration, and one actual tool response. Do not claim that every Ollama model supports vision, tool calling, or the same context length.

## Preserve user state

- Do not overwrite Claudian's plugin data; Claudian already embeds Claude Code.
- Register specialist servers with `claude mcp add --scope user` so CCSwitch switching does not remove them.
- Preserve unrelated Claude Code MCP servers.
- Preserve the active CCSwitch Provider unless the user explicitly requests activation.
- Back up Claude and CCSwitch configuration before replacement or database writes.
- Keep Ollama bound to localhost unless the user explicitly accepts network exposure.
- Restrict image-reading MCP tools to the selected vault and explicitly allowed directories.

## Verify the handoff

Read [references/usage.md](references/usage.md) and give the user the relevant instructions. Always mention:

- Switch the primary model in CCSwitch.
- Start a new Claudian conversation after switching.
- Reload Claudian or Obsidian if the old endpoint remains cached.
- Specialist MCP models remain available across CCSwitch Provider changes.
- Domain models provide auxiliary analysis; medical, legal, or financial output is not a final professional decision.

## Diagnose failures

Check in this order:

1. `ollama list` and the Ollama HTTP health endpoint.
2. Exact primary and specialist model tags.
3. Primary `/v1/messages` compatibility.
4. The selected CCSwitch Claude Provider and its endpoint.
5. A fresh Claudian/Claude Code session.
6. `claude mcp list` and `claude mcp get <name>`.
7. Specialist tool health and one real inference.

Do not interpret multiple stdio MCP processes as a leak until checking whether multiple Claudian or Claude Code sessions remain open.

## Uninstall

Run `uninstall` only after showing the targets from the install manifest. Remove generated runtime files only with `--remove-runtime`. Remove a CCSwitch Provider only with `--remove-provider`; the script refuses to remove it while it is active.

```bash
python3 <skill-dir>/scripts/stackctl.py uninstall --config /absolute/path/stack.json --remove-runtime
```
