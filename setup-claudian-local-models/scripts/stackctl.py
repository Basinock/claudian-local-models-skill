#!/usr/bin/env python3
"""Configure Claudian's Claude Code backend with CCSwitch and Ollama MCP models."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import re
import shutil
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parent.parent
ASSET_DIR = SKILL_DIR / "assets" / "ollama-specialist-mcp"
DEFAULT_ROOT = Path.home() / ".local" / "share" / "claudian-local-models"
DEFAULT_CCSWITCH_DB = Path.home() / ".cc-switch" / "cc-switch.db"
DEFAULT_CLAUDE_CONFIG = Path.home() / ".claude.json"
MANIFEST_NAME = "stack-manifest.json"


class StackError(RuntimeError):
    pass


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")


def backup_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    backup_dir = path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    destination = backup_dir / f"{path.name}.{now_stamp()}.bak"
    shutil.copy2(path, destination)
    return destination


def backup_sqlite_database(path: Path) -> Path:
    backup_dir = path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    destination = backup_dir / f"{path.name}.{now_stamp()}.bak"
    source = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    target = sqlite3.connect(destination)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    return destination


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=check)


def python_version(command: str) -> tuple[int, int, int] | None:
    result = run(
        [command, "-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))"],
        check=False,
    )
    if result.returncode:
        return None
    try:
        parts = tuple(int(value) for value in result.stdout.strip().split("."))
    except ValueError:
        return None
    return parts if len(parts) == 3 else None


def select_mcp_python(config: dict[str, Any]) -> tuple[str | None, tuple[int, int, int] | None]:
    configured = config.get("python") or os.getenv("CLAUDIAN_LOCAL_MODELS_PYTHON")
    candidates = [str(configured)] if configured else []
    candidates.extend([sys.executable, "python3.13", "python3.12", "python3.11", "python3.10", "python3"])
    seen: set[str] = set()
    for candidate in candidates:
        resolved = shutil.which(candidate) if not Path(candidate).is_absolute() else candidate
        if not resolved or resolved in seen:
            continue
        seen.add(resolved)
        version = python_version(resolved)
        if version and version >= (3, 10, 0):
            return resolved, version
    return None, None


def load_config(path: Path) -> dict[str, Any]:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StackError(f"Config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise StackError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(config, dict):
        raise StackError("The config root must be an object.")
    specialists = config.get("specialists", [])
    if not isinstance(specialists, list):
        raise StackError("specialists must be an array.")
    for specialist in specialists:
        if not isinstance(specialist, dict):
            raise StackError("Each specialist must be an object.")
        for key in ("name", "model", "description"):
            if not specialist.get(key):
                raise StackError(f"Each specialist requires {key}.")
        name = str(specialist["name"])
        tool_name = str(specialist.get("tool_name", "ask_specialist"))
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            raise StackError(f"Invalid specialist name: {name}. Use letters, digits, underscores, or hyphens.")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", tool_name):
            raise StackError(f"Invalid MCP tool name: {tool_name}.")
    return config


def ollama_url(config: dict[str, Any]) -> str:
    return str(config.get("ollama_url", "http://127.0.0.1:11434")).rstrip("/")


def request_json(url: str, payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise StackError(f"Request failed: {url}: {exc}") from exc


def installed_models(config: dict[str, Any]) -> set[str]:
    data = request_json(f"{ollama_url(config)}/api/tags")
    return {item.get("name", "") for item in data.get("models", [])}


def required_models(config: dict[str, Any]) -> list[str]:
    models: list[str] = []
    primary = config.get("primary")
    if isinstance(primary, dict) and primary.get("model"):
        models.append(str(primary["model"]))
    models.extend(str(item["model"]) for item in config.get("specialists", []))
    return list(dict.fromkeys(models))


def find_claudian(vault: Path) -> list[Path]:
    plugin_dir = vault / ".obsidian" / "plugins"
    if not plugin_dir.is_dir():
        return []
    matches: list[Path] = []
    for manifest in plugin_dir.glob("*/manifest.json"):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("id") in {"claudian", "realclaudian"} or "claudian" in str(data.get("name", "")).lower():
            matches.append(manifest)
    return matches


def preflight(config: dict[str, Any]) -> dict[str, Any]:
    vault_value = config.get("vault")
    vault = Path(vault_value).expanduser().resolve() if vault_value else None
    mcp_python, mcp_python_version = select_mcp_python(config)
    result: dict[str, Any] = {
        "platform": platform.platform(),
        "controller_python": sys.version.split()[0],
        "mcp_python": mcp_python,
        "mcp_python_version": ".".join(map(str, mcp_python_version)) if mcp_python_version else None,
        "python_ok": mcp_python is not None,
        "ollama_command": shutil.which("ollama"),
        "claude_command": shutil.which("claude"),
        "ccswitch_database": str(DEFAULT_CCSWITCH_DB) if DEFAULT_CCSWITCH_DB.exists() else None,
        "vault": str(vault) if vault else None,
        "claudian_manifests": [str(path) for path in find_claudian(vault)] if vault else [],
    }
    try:
        models = installed_models(config)
        result["ollama_reachable"] = True
        result["installed_models"] = sorted(models)
        result["missing_models"] = [model for model in required_models(config) if model not in models]
    except StackError as exc:
        result["ollama_reachable"] = False
        result["ollama_error"] = str(exc)
        result["missing_models"] = required_models(config)
    return result


def ccswitch_env(primary: dict[str, Any], base_url: str) -> dict[str, str]:
    model = str(primary["model"])
    env = {
        "ANTHROPIC_API_KEY": "ollama",
        "ANTHROPIC_AUTH_TOKEN": "ollama",
        "ANTHROPIC_BASE_URL": base_url,
        "ANTHROPIC_MODEL": model,
    }
    for tier in ("HAIKU", "SONNET", "OPUS", "FABLE"):
        env[f"ANTHROPIC_DEFAULT_{tier}_MODEL"] = model
        env[f"ANTHROPIC_DEFAULT_{tier}_MODEL_NAME"] = model
    compact_window = primary.get("auto_compact_window")
    if compact_window:
        env["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] = str(compact_window)
    return env


def provider_preview(config: dict[str, Any]) -> dict[str, Any] | None:
    primary = config.get("primary")
    if not isinstance(primary, dict) or not primary.get("model"):
        return None
    return {
        "app_type": "claude",
        "name": primary.get("provider_name", f"Ollama {primary['model']}"),
        "settings_config": {"env": ccswitch_env(primary, ollama_url(config))},
        "endpoint": ollama_url(config),
        "activate": bool(primary.get("activate", False)),
    }


def configure_ccswitch(config: dict[str, Any], database: Path) -> dict[str, Any] | None:
    preview = provider_preview(config)
    if preview is None:
        return None
    if not database.is_file():
        raise StackError(f"CCSwitch database not found: {database}")

    backup = backup_sqlite_database(database)
    connection = sqlite3.connect(database, timeout=10)
    try:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(providers)")}
        required = {"id", "app_type", "name", "settings_config", "meta", "is_current"}
        if not required.issubset(columns):
            raise StackError("Unsupported CCSwitch database schema; no changes were made.")

        endpoint_columns = {row[1] for row in connection.execute("PRAGMA table_info(provider_endpoints)")}
        if not {"provider_id", "app_type", "url", "added_at"}.issubset(endpoint_columns):
            raise StackError("Unsupported CCSwitch endpoint schema; no changes were made.")

        existing = connection.execute(
            "SELECT id, is_current FROM providers WHERE app_type = 'claude' AND name = ?",
            (preview["name"],),
        ).fetchone()
        provider_id = existing[0] if existing else str(uuid.uuid4())
        provider_is_current = 1 if preview["activate"] else (int(existing[1]) if existing else 0)
        settings = json.dumps(preview["settings_config"], ensure_ascii=False, separators=(",", ":"))
        meta = json.dumps(
            {
                "commonConfigEnabled": True,
                "endpointAutoSelect": True,
                "apiFormat": "anthropic",
                "apiKeyField": "ANTHROPIC_API_KEY",
            },
            separators=(",", ":"),
        )
        created_at = int(dt.datetime.now().timestamp() * 1000)

        with connection:
            if preview["activate"]:
                connection.execute("UPDATE providers SET is_current = 0 WHERE app_type = 'claude'")
            if existing:
                connection.execute(
                    "UPDATE providers SET settings_config = ?, meta = ?, is_current = ? WHERE id = ? AND app_type = 'claude'",
                    (settings, meta, provider_is_current, provider_id),
                )
                connection.execute(
                    "DELETE FROM provider_endpoints WHERE provider_id = ? AND app_type = 'claude'",
                    (provider_id,),
                )
            else:
                connection.execute(
                    "INSERT INTO providers (id, app_type, name, settings_config, created_at, meta, is_current) VALUES (?, 'claude', ?, ?, ?, ?, ?)",
                    (provider_id, preview["name"], settings, created_at, meta, provider_is_current),
                )
            connection.execute(
                "INSERT INTO provider_endpoints (provider_id, app_type, url, added_at) VALUES (?, 'claude', ?, ?)",
                (provider_id, preview["endpoint"], created_at),
            )
    finally:
        connection.close()

    return {"provider_id": provider_id, "backup": str(backup) if backup else None, **preview}


def create_runtime(root: Path, base_python: str) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    server = root / "server.py"
    requirements = root / "requirements.txt"
    shutil.copy2(ASSET_DIR / "server.py", server)
    shutil.copy2(ASSET_DIR / "requirements.txt", requirements)

    venv = root / ".venv"
    if not venv.exists():
        result = run([base_python, "-m", "venv", str(venv)], check=False)
        if result.returncode:
            raise StackError(result.stderr.strip() or "Failed to create Python virtual environment.")
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    result = run([str(python), "-m", "pip", "install", "-r", str(requirements)], check=False)
    if result.returncode:
        raise StackError(result.stderr.strip() or "Failed to install MCP dependencies.")
    return python, server


def mcp_env(config: dict[str, Any], specialist: dict[str, Any]) -> dict[str, str]:
    vault_value = config.get("vault")
    roots = [str(Path(vault_value).expanduser().resolve())] if vault_value else []
    roots.extend(str(Path(value).expanduser().resolve()) for value in specialist.get("allowed_image_roots", []))
    safe_name = str(specialist["name"]).replace(" ", "-")
    return {
        "OLLAMA_URL": ollama_url(config),
        "OLLAMA_MODEL": str(specialist["model"]),
        "MCP_SERVER_NAME": safe_name,
        "MCP_TOOL_NAME": str(specialist.get("tool_name", "ask_specialist")),
        "MCP_TOOL_DESCRIPTION": str(specialist["description"]),
        "MCP_SYSTEM_PROMPT": str(
            specialist.get(
                "system_prompt",
                "You are a specialist assistant. State uncertainty, distinguish facts from inference, and do not invent facts.",
            )
        ),
        "MCP_ALLOW_IMAGES": str(bool(specialist.get("vision", False))).lower(),
        "MCP_ALLOWED_IMAGE_ROOTS": os.pathsep.join(dict.fromkeys(roots)),
    }


def claude_mcp_exists(claude: str, name: str) -> bool:
    result = run([claude, "mcp", "get", name], check=False)
    return result.returncode == 0


def register_mcp(
    claude: str,
    name: str,
    python: Path,
    server: Path,
    env: dict[str, str],
    *,
    replace: bool,
) -> None:
    if claude_mcp_exists(claude, name):
        if not replace:
            raise StackError(f"MCP server already exists: {name}. Use --replace-existing to replace it.")
        result = run([claude, "mcp", "remove", "--scope", "user", name], check=False)
        if result.returncode:
            raise StackError(result.stderr.strip() or f"Failed to remove existing MCP server {name}.")

    command = [claude, "mcp", "add", "--scope", "user", name]
    for key, value in env.items():
        command.extend(["--env", f"{key}={value}"])
    command.extend(["--", str(python), str(server)])
    result = run(command, check=False)
    if result.returncode:
        raise StackError(result.stderr.strip() or f"Failed to register MCP server {name}.")


def pull_models(config: dict[str, Any], models: list[str]) -> None:
    ollama = shutil.which("ollama")
    if not ollama:
        raise StackError("ollama command not found.")
    for model in models:
        result = subprocess.run([ollama, "pull", model], check=False)
        if result.returncode:
            raise StackError(f"Failed to pull model: {model}")


def verify_primary(config: dict[str, Any]) -> dict[str, Any] | None:
    primary = config.get("primary")
    if not isinstance(primary, dict) or not primary.get("model"):
        return None
    payload = {
        "model": primary["model"],
        "max_tokens": 16,
        "messages": [{"role": "user", "content": "Reply with READY only."}],
    }
    response = request_json(
        f"{ollama_url(config)}/v1/messages",
        payload,
        {"Content-Type": "application/json", "x-api-key": "ollama", "anthropic-version": "2023-06-01"},
    )
    return {"model": primary["model"], "response_type": response.get("type"), "has_content": bool(response.get("content"))}


def verify(config: dict[str, Any]) -> dict[str, Any]:
    result = preflight(config)
    result["primary_protocol"] = None
    if result.get("ollama_reachable") and config.get("primary"):
        try:
            result["primary_protocol"] = verify_primary(config)
        except StackError as exc:
            result["primary_protocol_error"] = str(exc)

    claude = shutil.which("claude")
    mcp: dict[str, Any] = {}
    if claude:
        for specialist in config.get("specialists", []):
            name = str(specialist["name"]).replace(" ", "-")
            check = run([claude, "mcp", "get", name], check=False)
            mcp[name] = {"registered": check.returncode == 0, "details": (check.stdout or check.stderr).strip()}
    result["mcp"] = mcp
    return result


def install(config: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    report = preflight(config)
    if not report["python_ok"]:
        raise StackError("Python 3.10 or newer is required.")
    if not report.get("ollama_reachable"):
        raise StackError(report.get("ollama_error", "Ollama is not reachable."))
    if config.get("vault") and not report["claudian_manifests"]:
        raise StackError("Claudian was not found in the configured Obsidian vault.")

    missing = report["missing_models"]
    if missing and not args.pull:
        raise StackError(f"Missing Ollama models: {', '.join(missing)}. Re-run with --pull after reviewing download size and licenses.")
    if missing:
        pull_models(config, missing)

    root = Path(config.get("install_root", DEFAULT_ROOT)).expanduser().resolve()
    claude = shutil.which("claude")
    specialists = config.get("specialists", [])
    if specialists and not claude:
        raise StackError("claude command not found; cannot register specialist MCP servers.")

    python: Path | None = None
    server: Path | None = None
    if specialists:
        backup_file(DEFAULT_CLAUDE_CONFIG)
        base_python, _ = select_mcp_python(config)
        if not base_python:
            raise StackError("Python 3.10 or newer is required for the generated MCP runtime.")
        python, server = create_runtime(root, base_python)

    installed_specialists: list[dict[str, Any]] = []
    for specialist in specialists:
        name = str(specialist["name"]).replace(" ", "-")
        env = mcp_env(config, specialist)
        register_mcp(claude, name, python, server, env, replace=args.replace_existing)  # type: ignore[arg-type]
        installed_specialists.append({"name": name, "model": specialist["model"]})

    provider = None
    if args.ccswitch == "database" and config.get("primary"):
        provider = configure_ccswitch(config, Path(args.ccswitch_db).expanduser().resolve())

    root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "installed_at": dt.datetime.now().isoformat(),
        "config": config,
        "specialists": installed_specialists,
        "ccswitch_provider": provider,
    }
    (root / MANIFEST_NAME).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"install_root": str(root), "specialists": installed_specialists, "ccswitch_provider": provider}


def uninstall(config: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    root = Path(config.get("install_root", DEFAULT_ROOT)).expanduser().resolve()
    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file():
        raise StackError(f"Install manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    removed: list[str] = []
    claude = shutil.which("claude")
    if claude:
        for specialist in manifest.get("specialists", []):
            name = specialist["name"]
            result = run([claude, "mcp", "remove", "--scope", "user", name], check=False)
            if result.returncode == 0:
                removed.append(name)

    provider = manifest.get("ccswitch_provider")
    if args.remove_provider and provider:
        database = Path(args.ccswitch_db).expanduser().resolve()
        backup_sqlite_database(database)
        connection = sqlite3.connect(database, timeout=10)
        try:
            row = connection.execute(
                "SELECT is_current FROM providers WHERE id = ? AND app_type = 'claude'",
                (provider["provider_id"],),
            ).fetchone()
            if row and int(row[0]):
                raise StackError("Refusing to remove the active CCSwitch Provider. Switch providers first.")
            with connection:
                connection.execute(
                    "DELETE FROM provider_endpoints WHERE provider_id = ? AND app_type = 'claude'",
                    (provider["provider_id"],),
                )
                connection.execute(
                    "DELETE FROM providers WHERE id = ? AND app_type = 'claude' AND is_current = 0",
                    (provider["provider_id"],),
                )
        finally:
            connection.close()

    if args.remove_runtime:
        shutil.rmtree(root)
    return {"removed_mcp": removed, "runtime_removed": bool(args.remove_runtime)}


def print_plan(config: dict[str, Any]) -> None:
    root = Path(config.get("install_root", DEFAULT_ROOT)).expanduser().resolve()
    plan = {
        "preflight": preflight(config),
        "targets": {
            "install_root": str(root),
            "claude_user_config": str(DEFAULT_CLAUDE_CONFIG),
            "ccswitch_database": str(DEFAULT_CCSWITCH_DB),
        },
        "ccswitch_provider": provider_preview(config),
        "specialists": [
            {
                "name": str(item["name"]).replace(" ", "-"),
                "model": item["model"],
                "tool_name": item.get("tool_name", "ask_specialist"),
                "vision": bool(item.get("vision", False)),
            }
            for item in config.get("specialists", [])
        ],
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "plan", "install", "verify", "uninstall"))
    parser.add_argument("--config", required=True, type=Path, help="Path to the JSON stack configuration.")
    parser.add_argument("--pull", action="store_true", help="Download missing models after license and disk review.")
    parser.add_argument("--replace-existing", action="store_true", help="Replace same-named user-scope MCP servers.")
    parser.add_argument("--ccswitch", choices=("guide", "database", "skip"), default="guide")
    parser.add_argument("--ccswitch-db", default=str(DEFAULT_CCSWITCH_DB))
    parser.add_argument("--remove-provider", action="store_true", help="Remove the inactive provider created by this installer.")
    parser.add_argument("--remove-runtime", action="store_true", help="Remove the generated virtualenv and manifest.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_config(args.config)
        if args.command == "preflight":
            print(json.dumps(preflight(config), ensure_ascii=False, indent=2))
        elif args.command == "plan":
            print_plan(config)
        elif args.command == "install":
            if args.ccswitch == "guide" and config.get("primary"):
                print("CCSwitch database will not be changed in guide mode. Provider JSON is included in the plan output.", file=sys.stderr)
            print(json.dumps(install(config, args), ensure_ascii=False, indent=2))
        elif args.command == "verify":
            print(json.dumps(verify(config), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(uninstall(config, args), ensure_ascii=False, indent=2))
    except StackError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
