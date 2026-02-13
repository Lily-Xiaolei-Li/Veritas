import os
import sys
from typing import Any, Dict, List, Optional

from app.docker_check import as_health_payload


def get_api_base() -> str:
    """Get the API base URL from environment or default."""
    return os.getenv("AGENTB_API_URL", "http://localhost:8001")


def _first_failure(checks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for check in checks:
        if not check.get("ok"):
            return check
    return None


def _print_section(title: str, checks: List[Dict[str, Any]], ok: bool) -> None:
    """Print a check section with status."""
    status = "✓ READY" if ok else "✗ NOT READY"
    print(f"\n{title}: {status}")

    for check in checks:
        name = check.get("name", "unknown")
        check_ok = check.get("ok", False)
        detail = check.get("detail", "")
        check_status = "✓" if check_ok else "✗"

        print(f"  {check_status} {name}: {detail}")

        # Show remediation if check failed
        if not check_ok:
            remediation = check.get("remediation")
            if remediation:
                print("\n    REMEDIATION:")
                for line in remediation.split("\n"):
                    if line.strip():
                        print(f"    {line}")
                print()


def main(argv: Optional[list] = None) -> int:
    print("Agent B - System Health Check")
    print("=" * 50)

    payload = as_health_payload()
    overall_status = payload.get("status", "unknown")

    # Check Docker
    docker_data = payload.get("docker", {})
    docker_ok = docker_data.get("ok", False)
    docker_checks = docker_data.get("checks", [])
    _print_section("Docker", docker_checks, docker_ok)

    # Check Resources
    resources_data = payload.get("resources", {})
    resources_ok = resources_data.get("ok", False)
    resources_checks = resources_data.get("checks", [])
    _print_section("Resources", resources_checks, resources_ok)

    # Overall result
    print("\n" + "=" * 50)
    if overall_status == "ok":
        print("✓ ALL CHECKS PASSED - System ready for Agent B")
        return 0
    else:
        print("✗ SOME CHECKS FAILED - Please resolve issues above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
