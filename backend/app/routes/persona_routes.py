"""Persona CRUD routes (Phase 6).

Provides endpoints to manage named system prompts (personas).

- GET    /personas
- POST   /personas
- PUT    /personas/{persona_id}
- DELETE /personas/{persona_id}

Auth: currently mirrors the rest of the dev UI (no auth required when AUTH_ENABLED=false).
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Persona

router = APIRouter()

# Seed defaults for first run (so UI dropdown is never empty)
DEFAULT_PERSONAS = [
    {
        "id": "default",
        "label": "Default Assistant",
        "system_prompt": "You are a helpful academic research assistant. Assist the user with their research tasks professionally and accurately.",
    },
    {
        "id": "cleaner",
        "label": "The Cleaner",
        "system_prompt": "You are a Document Restoration Expert. Clean 'messy' Markdown from PDFs. Remove artifacts (broken headers, page numbers, line breaks) while preserving academic structure. Constraint: Never rewrite prose; only repair formatting.",
    },
    {
        "id": "thinker",
        "label": "The Thinker",
        "system_prompt": "You are a Creative Research Thinker. Find 'hidden' patterns and novel insights from provided data. Use lateral thinking to connect ideas. Constraint: Do not repeat user input; focus entirely on new implications and 'So What?'.",
    },
    {
        "id": "templator",
        "label": "The Templator",
        "system_prompt": "You are a Structural Writing Analyst. Reverse-engineer published articles into blueprints. Identify the functional purpose of every sentence. Constraint: Focus 100% on the rhetorical skeleton, not the subject matter.",
    },
    {
        "id": "drafter",
        "label": "The Drafter",
        "system_prompt": "You are an expert Academic Drafter. Write in a neutral, sophisticated, concise tone. Avoid AI-isms like 'delve' or 'vibrant.' Use active verbs. Constraint: Match the dry, precise tone of high-impact journals.",
    },
    {
        "id": "referencer",
        "label": "The Referencer",
        "system_prompt": "You are a precise Citation Specialist. Format reference lists and in-text citations perfectly according to the user's specified style. Constraint: Follow style guide punctuation/italics exactly. Do not comment on content.",
    },
    {
        "id": "skeptic",
        "label": "The Skeptic",
        "system_prompt": "You are a professional Devil's Advocate. Find the weakest link in any argument. Look for selection bias and alternative explanations. Constraint: You must disagree with the user's thesis and provide 3 credible counter-arguments.",
    },
    {
        "id": "reviewer",
        "label": "The Reviewer",
        "system_prompt": "You are a Senior Editor at a top-tier journal. Critically evaluate logic, scope, and contribution. Provide 'Major' and 'Minor' revisions. Constraint: Be rigorous and focus on why a paper might be rejected.",
    },
]


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------


class PersonaResponse(BaseModel):
    id: str
    label: str
    system_prompt: str
    sort_order: int
    created_at: datetime
    updated_at: datetime


class PersonaListResponse(BaseModel):
    personas: List[PersonaResponse]


class PersonaCreateRequest(BaseModel):
    id: str = Field(..., min_length=1, max_length=64, description="Stable persona identifier")
    label: str = Field(..., min_length=1, max_length=255)
    system_prompt: str = Field(..., min_length=1)


class PersonaUpdateRequest(BaseModel):
    label: Optional[str] = Field(None, min_length=1, max_length=255)
    system_prompt: Optional[str] = Field(None, min_length=1)


class PersonaReorderRequest(BaseModel):
    ordered_ids: List[str] = Field(default_factory=list)


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@router.get("/personas", response_model=PersonaListResponse)
async def list_personas(
    include_deleted: bool = False,
    db: AsyncSession = Depends(get_session),
):
    q = select(Persona)
    if not include_deleted:
        q = q.where(Persona.is_deleted.is_(False))
    q = q.order_by(Persona.sort_order.asc(), Persona.label.asc())

    res = await db.execute(q)
    personas = res.scalars().all()

    # Seed defaults if DB is empty (first run)
    if not include_deleted and len(personas) == 0:
        for idx, d in enumerate(DEFAULT_PERSONAS):
            db.add(
                Persona(
                    id=d["id"],
                    label=d["label"],
                    system_prompt=d["system_prompt"],
                    sort_order=idx * 10,
                    is_deleted=False,
                )
            )
        await db.commit()

        res = await db.execute(q)
        personas = res.scalars().all()

    return {
        "personas": [
            PersonaResponse(
                id=p.id,
                label=p.label,
                system_prompt=p.system_prompt,
                sort_order=getattr(p, "sort_order", 0) or 0,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in personas
        ]
    }


@router.post("/personas", response_model=PersonaResponse, status_code=status.HTTP_201_CREATED)
async def create_persona(
    body: PersonaCreateRequest,
    db: AsyncSession = Depends(get_session),
):
    existing = await db.get(Persona, body.id)
    if existing and not existing.is_deleted:
        raise HTTPException(status_code=409, detail="Persona id already exists")

    if existing and existing.is_deleted:
        # revive
        existing.label = body.label
        existing.system_prompt = body.system_prompt
        existing.is_deleted = False
        await db.commit()
        await db.refresh(existing)
        return PersonaResponse(
            id=existing.id,
            label=existing.label,
            system_prompt=existing.system_prompt,
            sort_order=getattr(existing, "sort_order", 0) or 0,
            created_at=existing.created_at,
            updated_at=existing.updated_at,
        )

    persona = Persona(
        id=body.id,
        label=body.label,
        system_prompt=body.system_prompt,
        sort_order=9999,
        is_deleted=False,
    )
    db.add(persona)
    await db.commit()
    await db.refresh(persona)

    return PersonaResponse(
        id=persona.id,
        label=persona.label,
        system_prompt=persona.system_prompt,
        sort_order=getattr(persona, "sort_order", 0) or 0,
        created_at=persona.created_at,
        updated_at=persona.updated_at,
    )


@router.post("/personas/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_personas(
    body: PersonaReorderRequest,
    db: AsyncSession = Depends(get_session),
):
    if not body.ordered_ids:
        return

    # Fetch all current personas in the provided list
    res = await db.execute(
        select(Persona).where(Persona.id.in_(body.ordered_ids), Persona.is_deleted.is_(False))
    )
    found = {p.id: p for p in res.scalars().all()}

    # Apply order; keep gaps for easy insert (10,20,30...)
    for idx, pid in enumerate(body.ordered_ids):
        p = found.get(pid)
        if p is None:
            continue
        p.sort_order = idx * 10

    await db.commit()
    return


@router.put("/personas/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    persona_id: str,
    body: PersonaUpdateRequest,
    db: AsyncSession = Depends(get_session),
):
    persona = await db.get(Persona, persona_id)
    if not persona or persona.is_deleted:
        raise HTTPException(status_code=404, detail="Persona not found")

    if body.label is not None:
        persona.label = body.label
    if body.system_prompt is not None:
        persona.system_prompt = body.system_prompt

    await db.commit()
    await db.refresh(persona)

    return PersonaResponse(
        id=persona.id,
        label=persona.label,
        system_prompt=persona.system_prompt,
        sort_order=getattr(persona, "sort_order", 0) or 0,
        created_at=persona.created_at,
        updated_at=persona.updated_at,
    )


@router.delete("/personas/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_persona(
    persona_id: str,
    db: AsyncSession = Depends(get_session),
):
    persona = await db.get(Persona, persona_id)
    if not persona or persona.is_deleted:
        return

    persona.is_deleted = True
    await db.commit()
    return
