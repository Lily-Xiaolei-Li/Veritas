from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CLIMode:
    value: str  # "interactive" | "automation"
    source: str  # why this mode was chosen


TRUTHY = {"1", "true", "yes", "on"}


def _is_truthy_env(name: str) -> bool:
    val = os.getenv(name)
    return bool(val and val.strip().lower() in TRUTHY)


def detect_mode(*, force_automation: bool, force_interactive: bool, stdin_isatty: bool) -> CLIMode:
    """
    Mode detection priority (P1-A):
      1) explicit flags --automation / --interactive
      2) CI environment hint
      3) TTY inference fallback
    """
    if force_automation and force_interactive:
        raise ValueError("--automation and --interactive cannot be used together")

    if force_automation:
        return CLIMode("automation", "flag")

    if force_interactive:
        return CLIMode("interactive", "flag")

    if _is_truthy_env("CI") or _is_truthy_env("AGENTB_AUTOMATION"):
        return CLIMode("automation", "env")

    if stdin_isatty:
        return CLIMode("interactive", "tty")

    return CLIMode("automation", "tty")
