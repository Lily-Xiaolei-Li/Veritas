from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

RiskLevel = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    args_schema: dict[str, Any]
    risk_level: RiskLevel = "low"
    timeout_seconds: int = 30
    requires_approval: bool = False


@dataclass
class ToolResult:
    success: bool
    output: Any = None
    error: Optional[str] = None
    artifacts: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "artifacts": self.artifacts or [],
        }
