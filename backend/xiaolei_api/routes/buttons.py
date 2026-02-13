from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from config import get_settings
from fastapi import APIRouter, HTTPException, status
from models import Button, ButtonCreateRequest, ButtonsResponse

router = APIRouter()
logger = logging.getLogger("xiaolei_api.buttons")

DEFAULT_BUTTONS = [
    {
        "id": "citation",
        "name": "Look for citation",
        "prompt": "Search our library and find sources that strongly support this sentence. Return all reasonably relevant results with title, author, year, and a brief explanation of why it's relevant.",
        "icon": "search",
    },
    {
        "id": "harvard",
        "name": "Harvard referencing",
        "prompt": "Check this citation list against our library, identify any missing ones, then generate a Harvard-style reference list in the artifact.",
        "icon": "book",
    },
    {
        "id": "summarize",
        "name": "Summarize paper",
        "prompt": "Summarize this academic paper, including: research question, methodology, key findings, and implications.",
        "icon": "file-text",
    },
    {
        "id": "similar",
        "name": "Find similar papers",
        "prompt": "Find papers in our library that are similar to this one in terms of topic, methodology, or theoretical framework.",
        "icon": "copy",
    },
    {
        "id": "argument",
        "name": "Check argument",
        "prompt": "Analyze this argument for logical consistency and identify any potential weaknesses or gaps in reasoning.",
        "icon": "alert-circle",
    },
]


def _dump_button(button: Button | dict) -> dict:
    if isinstance(button, dict):
        return button
    if hasattr(button, "model_dump"):
        return button.model_dump(exclude_none=True)
    return button.dict(exclude_none=True)


def _write_buttons(path: Path, buttons: list[Button] | list[dict]) -> None:
    data = {"buttons": [_dump_button(button) for button in buttons]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _ensure_file(path: Path) -> None:
    if not path.exists():
        _write_buttons(path, DEFAULT_BUTTONS)


def _read_buttons(path: Path) -> list[Button]:
    _ensure_file(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_buttons = data.get("buttons", [])
    buttons: list[Button] = []
    for item in raw_buttons:
        if isinstance(item, dict):
            try:
                buttons.append(Button(**item))
            except Exception:
                buttons.append(
                    Button(
                        id=str(item.get("id", "")),
                        name=str(item.get("name", "")),
                        prompt=str(item.get("prompt", "")),
                        icon=item.get("icon"),
                    )
                )
    return buttons


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "button"


def _unique_id(desired: str, existing_ids: set[str]) -> str:
    if desired not in existing_ids:
        return desired
    index = 2
    while f"{desired}-{index}" in existing_ids:
        index += 1
    return f"{desired}-{index}"


@router.get("/buttons", response_model=ButtonsResponse)
async def list_buttons() -> ButtonsResponse:
    settings = get_settings()
    buttons = _read_buttons(settings.buttons_path)
    return ButtonsResponse(buttons=buttons)


@router.post("/buttons", response_model=Button, status_code=status.HTTP_201_CREATED)
async def create_button(request: ButtonCreateRequest) -> Button:
    settings = get_settings()
    buttons = _read_buttons(settings.buttons_path)
    existing_ids = {button.id for button in buttons}

    if request.id:
        if request.id in existing_ids:
            raise HTTPException(status_code=409, detail="Button id already exists")
        button_id = request.id
    else:
        button_id = _unique_id(_slugify(request.name), existing_ids)

    button = Button(
        id=button_id,
        name=request.name,
        prompt=request.prompt,
        icon=request.icon,
    )
    buttons.append(button)
    _write_buttons(settings.buttons_path, buttons)
    return button


@router.delete("/buttons/{button_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_button(button_id: str) -> None:
    settings = get_settings()
    buttons = _read_buttons(settings.buttons_path)
    remaining = [button for button in buttons if button.id != button_id]

    if len(remaining) == len(buttons):
        raise HTTPException(status_code=404, detail="Button not found")

    _write_buttons(settings.buttons_path, remaining)
    return None
