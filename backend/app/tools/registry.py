from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from app.tools.types import ToolResult, ToolSpec

ToolFn = Callable[[dict[str, Any]], ToolResult | Awaitable[ToolResult]]


_REGISTRY: dict[str, tuple[ToolSpec, ToolFn]] = {}


def register_tool(spec: ToolSpec):
    """Decorator to register a tool function."""

    def _decorator(fn: ToolFn):
        name = spec.name
        if name in _REGISTRY:
            raise ValueError(f"Tool already registered: {name}")
        _REGISTRY[name] = (spec, fn)
        return fn

    return _decorator


def list_tools() -> list[ToolSpec]:
    return [v[0] for v in _REGISTRY.values()]


def get_tool(name: str) -> tuple[ToolSpec, ToolFn]:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown tool: {name}")
    return _REGISTRY[name]


async def execute_tool(name: str, args: dict[str, Any]) -> ToolResult:
    spec, fn = get_tool(name)
    result = fn(args)
    if inspect.isawaitable(result):
        return await result
    return result
