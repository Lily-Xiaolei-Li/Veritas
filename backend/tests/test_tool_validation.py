"""
Tests for Tool Validation (B2.2b).

Tests bash command allowlist validation.
"""

import pytest

from app.agent.tool_validation import (
    validate_bash_command,
    build_bash_command_for_file_creation,
    extract_target_files_from_cat_command,
)


class TestValidateBashCommand:
    """Tests for validate_bash_command function."""

    # ========================================================================
    # ALLOWED COMMANDS
    # ========================================================================

    def test_allow_python_script(self):
        """Should allow running python scripts."""
        is_valid, error = validate_bash_command("python hello.py")

        assert is_valid is True
        assert error == ""

    def test_allow_python3_script(self):
        """Should allow running python3 scripts."""
        is_valid, error = validate_bash_command("python3 script.py")

        assert is_valid is True
        assert error == ""

    def test_allow_ls_command(self):
        """Should allow ls command."""
        is_valid, error = validate_bash_command("ls")

        assert is_valid is True
        assert error == ""

    def test_allow_ls_with_flags(self):
        """Should allow ls with flags."""
        is_valid, error = validate_bash_command("ls -la")

        assert is_valid is True
        assert error == ""

    def test_allow_pwd_command(self):
        """Should allow pwd command."""
        is_valid, error = validate_bash_command("pwd")

        assert is_valid is True
        assert error == ""

    def test_allow_echo_command(self):
        """Should allow echo command."""
        is_valid, error = validate_bash_command("echo hello world")

        assert is_valid is True
        assert error == ""

    def test_allow_cat_with_heredoc(self):
        """Should allow cat with heredoc."""
        command = """cat > hello.py <<'EOF'
print("Hello")
EOF"""
        is_valid, error = validate_bash_command(command)

        assert is_valid is True
        assert error == ""

    def test_allow_cat_heredoc_no_quotes(self):
        """Should allow cat with unquoted heredoc delimiter."""
        command = """cat > file.txt <<EOF
content
EOF"""
        is_valid, error = validate_bash_command(command)

        assert is_valid is True
        assert error == ""

    # ========================================================================
    # REJECTED COMMANDS
    # ========================================================================

    def test_reject_empty_command(self):
        """Should reject empty command."""
        is_valid, error = validate_bash_command("")

        assert is_valid is False
        assert "Empty" in error

    def test_reject_whitespace_only(self):
        """Should reject whitespace-only command."""
        is_valid, error = validate_bash_command("   ")

        assert is_valid is False
        assert "Empty" in error

    def test_reject_cat_without_heredoc(self):
        """Should reject cat > without heredoc."""
        is_valid, error = validate_bash_command("cat > file.py")

        assert is_valid is False
        assert "heredoc" in error.lower()

    def test_reject_rm_command(self):
        """Should reject rm command (not in allowlist)."""
        is_valid, error = validate_bash_command("rm file.txt")

        assert is_valid is False
        assert "allowlist" in error.lower()

    def test_reject_curl_command(self):
        """Should reject curl command (not in allowlist)."""
        is_valid, error = validate_bash_command("curl http://example.com")

        assert is_valid is False
        assert "allowlist" in error.lower()

    def test_reject_wget_command(self):
        """Should reject wget command (not in allowlist)."""
        is_valid, error = validate_bash_command("wget http://example.com")

        assert is_valid is False
        assert "allowlist" in error.lower()

    def test_reject_apt_command(self):
        """Should reject apt command (not in allowlist)."""
        is_valid, error = validate_bash_command("apt install something")

        assert is_valid is False
        assert "allowlist" in error.lower()

    def test_reject_chmod_command(self):
        """Should reject chmod command (not in allowlist)."""
        is_valid, error = validate_bash_command("chmod +x script.sh")

        assert is_valid is False
        assert "allowlist" in error.lower()

    def test_reject_sudo_command(self):
        """Should reject sudo command (not in allowlist)."""
        is_valid, error = validate_bash_command("sudo ls")

        assert is_valid is False
        assert "allowlist" in error.lower()


class TestBuildBashCommandForFileCreation:
    """Tests for build_bash_command_for_file_creation function."""

    def test_build_simple_file(self):
        """Should build valid heredoc command."""
        command = build_bash_command_for_file_creation(
            filename="hello.py",
            content='print("Hello")',
        )

        assert "cat > hello.py <<'EOF'" in command
        assert 'print("Hello")' in command
        assert command.endswith("EOF")

    def test_build_file_custom_delimiter(self):
        """Should use custom delimiter."""
        command = build_bash_command_for_file_creation(
            filename="test.txt",
            content="content",
            delimiter="MYEOF",
        )

        assert "<<'MYEOF'" in command
        assert command.endswith("MYEOF")

    def test_built_command_passes_validation(self):
        """Built command should pass validation."""
        command = build_bash_command_for_file_creation(
            filename="script.py",
            content="print('test')",
        )

        is_valid, error = validate_bash_command(command)
        assert is_valid is True


class TestExtractTargetFilesFromCatCommand:
    """Tests for extract_target_files_from_cat_command function."""

    def test_extract_single_file(self):
        """Should extract filename from cat command."""
        command = "cat > hello.py <<'EOF'"
        files = extract_target_files_from_cat_command(command)

        assert files == ["hello.py"]

    def test_extract_file_no_quotes(self):
        """Should extract filename with unquoted delimiter."""
        command = "cat > test.txt <<EOF"
        files = extract_target_files_from_cat_command(command)

        assert files == ["test.txt"]

    def test_extract_file_with_path(self):
        """Should extract filename with path."""
        command = "cat > subdir/file.py <<'EOF'"
        files = extract_target_files_from_cat_command(command)

        assert files == ["subdir/file.py"]

    def test_extract_no_match(self):
        """Should return empty list for non-matching command."""
        command = "echo hello"
        files = extract_target_files_from_cat_command(command)

        assert files == []

    def test_extract_cat_without_heredoc(self):
        """Should return empty list for cat without heredoc."""
        command = "cat > file.py"
        files = extract_target_files_from_cat_command(command)

        assert files == []
