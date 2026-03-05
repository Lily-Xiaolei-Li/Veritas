"""Phase 0 / 0.5 environment checks for GP pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests

from app.utils.config import Settings
from app.utils.qdrant_client import validate_collection


@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str


def check_http(url: str, timeout: int = 5) -> tuple[bool, str]:
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            return True, f"OK ({response.status_code})"
        return False, f"Status {response.status_code}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def check_env_vars(settings: Settings) -> CheckResult:
    required = {
        "QDRANT_HOST": settings.qdrant_host,
        "QDRANT_PORT": str(settings.qdrant_port),
        "XIAOLEI_API_URL": settings.xiaolei_url,
        "GP_EXCEL_PATH": settings.excel_path,
        "GP_PDF_DIR": settings.pdf_dir,
        "GP_VECTR_COLLECTION/GP_QDRANT_COLLECTION": settings.data_source_collection,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        return CheckResult("Environment Variables", False, f"Missing: {', '.join(missing)}")
    return CheckResult("Environment Variables", True, "All required variables present")


def check_excel_path(path: str) -> CheckResult:
    if os.path.isfile(path):
        return CheckResult("Excel source file", True, f"{path} EXISTS")
    return CheckResult("Excel source file", False, f"{path} MISSING")


def check_pdf_dir(path: str) -> CheckResult:
    if os.path.isdir(path):
        return CheckResult("PDF library path", True, f"{path} EXISTS")
    return CheckResult("PDF library path", False, f"{path} MISSING")


def check_qdrant(host: str, port: int, collection: str) -> CheckResult:
    url = f"http://{host}:{port}/collections"
    ok, msg = check_http(url, timeout=3)
    if not ok:
        return CheckResult("Qdrant API", False, f"{msg}")
    if not validate_collection(f"http://{host}:{port}", collection):
        return CheckResult("Qdrant collection", False, f"collection '{collection}' not found")
    return CheckResult("Qdrant collection", True, f"collection '{collection}' exists")


def check_xiaolei(xiaolei_url: str) -> CheckResult:
    return CheckResult(
        "XiaoLei API",
        *check_http(f"{xiaolei_url.rstrip('/')}/chat", timeout=3),
    )


def _print_check(check: CheckResult) -> None:
    marker = "OK" if check.ok else "X"
    print(f"[{marker}] {check.name}: {check.message}")


def main() -> None:
    settings = Settings.from_env()

    checks = [
        check_env_vars(settings),
        check_excel_path(settings.excel_path),
        check_pdf_dir(settings.pdf_dir),
        check_qdrant(settings.qdrant_host, settings.qdrant_port, settings.data_source_collection),
        check_xiaolei(settings.xiaolei_url),
    ]

    print("\nPhase 0 / Phase 0.5 environment checks")
    for check in checks:
        _print_check(check)

    failed = [c for c in checks if not c.ok]
    if failed:
        print("\nPhase check failed:")
        for f in failed:
            print(f" - {f.name}: {f.message}")
        raise SystemExit(1)
    print("\nAll checks passed")


if __name__ == "__main__":
    main()
