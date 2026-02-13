"""
Tool Validation (B2.2b).

Provides restrictive allowlist validation for bash commands.
This is an additional layer on top of the executor's blocklist.

B2.2 Strategy:
- Use restrictive allowlist (not "path escape detection")
- Rely on sandbox constraints: workspace mount only, network disabled
- Loosen in B2.3+ with verification gates
"""

import re
from typing import Tuple

from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger("agent.tool_validation")


# B2.2b: Restricted command allowlist
# These are the ONLY commands allowed in B2.2
ALLOWED_COMMAND_PREFIXES = [
    "python ",     # Run python scripts
    "python3 ",    # Run python3 scripts
    "ls",          # List files (can be "ls" or "ls -la" etc)
    "pwd",         # Print working directory
    "echo ",       # Echo output
]

# cat > REQUIRES heredoc pattern (prevents `cat > file.py` with no content)
# Matches: cat > file.py <<'EOF' or cat >file.py<<EOF or cat > file.py << 'EOF'
CAT_HEREDOC_PATTERN = re.compile(r"^cat\s*>\s*\S+\s*<<")


def validate_bash_command(command: str) -> Tuple[bool, str]:
    """
    Validate a bash command against the B2.2 allowlist.

    This is a restrictive allowlist - commands not on the list are rejected.
    The executor's blocklist provides additional protection.

    Args:
        command: The bash command to validate

    Returns:
        Tuple of (is_valid, error_message)
        - If valid: (True, "")
        - If invalid: (False, "reason for rejection")
    """
    command_stripped = command.strip()

    if not command_stripped:
        return False, "Empty command"

    # Check cat > separately - must have heredoc
    if command_stripped.startswith("cat"):
        if CAT_HEREDOC_PATTERN.match(command_stripped):
            # Valid cat with heredoc - check against executor blocklist
            if _matches_executor_blocklist(command_stripped):
                return False, "Command matches executor blocklist"
            return True, ""
        else:
            return False, "cat > requires heredoc (e.g., cat > file.py <<'EOF')"

    # Must start with an allowed prefix
    if not any(command_stripped.startswith(prefix) for prefix in ALLOWED_COMMAND_PREFIXES):
        return False, f"Command not in allowlist. Allowed: {ALLOWED_COMMAND_PREFIXES + ['cat > ... <<']}"

    # Check executor blocklist as final safety layer
    if _matches_executor_blocklist(command_stripped):
        return False, "Command matches executor blocklist"

    return True, ""


def _matches_executor_blocklist(command: str) -> bool:
    """
    Check if command matches the executor's blocklist patterns.

    Args:
        command: The command to check

    Returns:
        True if command matches any blocked pattern
    """
    settings = get_settings()

    for blocked_pattern in settings.command_blocklist:
        if blocked_pattern in command:
            logger.warning(
                f"Command matches blocklist pattern",
                extra={
                    "extra_fields": {
                        "pattern": blocked_pattern,
                        "command_preview": command[:50],
                    }
                },
            )
            return True

    return False


def build_bash_command_for_file_creation(
    filename: str,
    content: str,
    delimiter: str = "EOF",
) -> str:
    """
    Build a valid bash command for creating a file with heredoc.

    This helper ensures the command passes validation.

    Args:
        filename: Name of the file to create
        content: Content to write to the file
        delimiter: Heredoc delimiter (default "EOF")

    Returns:
        Valid bash command string
    """
    # Use quoted delimiter to prevent variable expansion
    return f"cat > {filename} <<'{delimiter}'\n{content}\n{delimiter}"


def extract_target_files_from_cat_command(command: str) -> list:
    """
    Extract target filename(s) from a cat > command.

    Args:
        command: A cat > command with heredoc

    Returns:
        List of target filenames
    """
    # Pattern: cat > filename <<
    match = re.match(r"^cat\s*>\s*(\S+)\s*<<", command.strip())
    if match:
        return [match.group(1)]
    return []
