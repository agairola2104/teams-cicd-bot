"""
bot/command_parser.py
Parses incoming Teams messages into structured command objects.

Supported commands:
  build <app> <branch>
  deploy <app> <build_number> <environment>
  status <app>
  rollback <app> <environment>
  history <app>
  help
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedCommand:
    action: str                      # build | deploy | status | rollback | history | help | unknown
    app: Optional[str] = None
    branch: Optional[str] = None
    build_number: Optional[str] = None
    environment: Optional[str] = None
    raw: str = ""
    error: Optional[str] = None      # Set if parsing failed


VALID_ENVS = {"qa", "uat", "prod"}
VALID_ACTIONS = {"build", "deploy", "status", "rollback", "history", "help"}


def parse_command(message: str) -> ParsedCommand:
    """
    Parse a raw Teams message into a ParsedCommand.
    Strips @mentions automatically before parsing.
    """
    # Strip @mention prefix (e.g. "<at>DeployBot</at> build ...")
    text = message.strip()
    if "<at>" in text:
        # Remove the XML mention tag Teams injects
        import re
        text = re.sub(r"<at>[^<]*</at>", "", text).strip()

    raw = text
    parts = text.lower().split()

    if not parts:
        return ParsedCommand(action="help", raw=raw)

    action = parts[0]

    if action not in VALID_ACTIONS:
        return ParsedCommand(
            action="unknown",
            raw=raw,
            error=f"Unknown command `{action}`. Type `help` to see available commands."
        )

    # ── help ────────────────────────────────────────────────────
    if action == "help":
        return ParsedCommand(action="help", raw=raw)

    # ── build <app> <branch> ────────────────────────────────────
    if action == "build":
        if len(parts) < 3:
            return ParsedCommand(action="build", raw=raw,
                                 error="Usage: `build <app> <branch>`  e.g. `build myapp main`")
        return ParsedCommand(action="build", app=parts[1], branch=parts[2], raw=raw)

    # ── deploy <app> <build_number> <environment> ───────────────
    if action == "deploy":
        if len(parts) < 4:
            return ParsedCommand(action="deploy", raw=raw,
                                 error="Usage: `deploy <app> <build#> <qa|uat|prod>`  e.g. `deploy myapp 42 qa`")
        env = parts[3]
        if env not in VALID_ENVS:
            return ParsedCommand(action="deploy", raw=raw,
                                 error=f"Invalid environment `{env}`. Choose from: qa, uat, prod")
        return ParsedCommand(action="deploy", app=parts[1],
                             build_number=parts[2], environment=env, raw=raw)

    # ── status <app> ────────────────────────────────────────────
    if action == "status":
        if len(parts) < 2:
            return ParsedCommand(action="status", raw=raw,
                                 error="Usage: `status <app>`  e.g. `status myapp`")
        return ParsedCommand(action="status", app=parts[1], raw=raw)

    # ── rollback <app> <environment> ────────────────────────────
    if action == "rollback":
        if len(parts) < 3:
            return ParsedCommand(action="rollback", raw=raw,
                                 error="Usage: `rollback <app> <environment>`  e.g. `rollback myapp prod`")
        env = parts[2]
        if env not in VALID_ENVS:
            return ParsedCommand(action="rollback", raw=raw,
                                 error=f"Invalid environment `{env}`. Choose from: qa, uat, prod")
        return ParsedCommand(action="rollback", app=parts[1], environment=env, raw=raw)

    # ── history <app> ───────────────────────────────────────────
    if action == "history":
        if len(parts) < 2:
            return ParsedCommand(action="history", raw=raw,
                                 error="Usage: `history <app>`  e.g. `history myapp`")
        return ParsedCommand(action="history", app=parts[1], raw=raw)

    return ParsedCommand(action="unknown", raw=raw, error="Could not parse command.")
