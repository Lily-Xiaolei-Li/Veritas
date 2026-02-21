from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

import httpx

from app.logging_config import get_logger

logger = get_logger("proliferomaxima.ref_normalizer")


class ReferenceNormalizer:
    """AI-based reference normalizer for messy PDF-extracted reference sections."""

    def __init__(
        self,
        *,
        gateway_url: str | None = None,
        token: str | None = None,
        agent_id: str = "helper",
        model: str = "anthropic/claude-sonnet-4-5",
        timeout_seconds: float = 300.0,
    ):
        self.gateway_url = (gateway_url or os.getenv("OPENCLAW_GATEWAY_URL") or "http://localhost:18789").rstrip("/")
        self.token = token or os.getenv("OPENCLAW_GATEWAY_TOKEN") or "cf8bf99bedae98b1c3feea260670dcb023a0dfb04fddf379"
        self.agent_id = agent_id
        self.model = model
        self.timeout_seconds = float(timeout_seconds)

    async def normalize_references(self, raw_text: str, source_paper: str, max_refs: int = 100) -> List[Dict[str, Any]]:
        text = str(raw_text or "").strip()
        if not text:
            return []

        chunks = self._chunk_text(text, chunk_size=8000)
        max_refs = max(0, int(max_refs))
        normalized: List[Dict[str, Any]] = []

        for i, chunk in enumerate(chunks, start=1):
            if max_refs and len(normalized) >= max_refs:
                break

            remaining = max_refs - len(normalized) if max_refs else 0
            logger.info(f"Normalizing chunk {i}/{len(chunks)} ({len(chunk)} chars) for {source_paper}")
            batch = await self._normalize_chunk(chunk=chunk, source_paper=source_paper, chunk_index=i, max_refs=(remaining if max_refs else None))
            logger.info(f"Chunk {i} done: {len(batch)} refs")

            for item in batch:
                if max_refs and len(normalized) >= max_refs:
                    break
                normalized.append(self._ensure_output_shape(item=item, source_paper=source_paper))

        return normalized

    def _chunk_text(self, text: str, chunk_size: int = 4000) -> List[str]:
        if len(text) <= chunk_size:
            return [text]

        lines = text.splitlines()
        chunks: List[str] = []
        current: List[str] = []
        current_len = 0

        for line in lines:
            l = line.rstrip("\n")
            # +1 for newline join cost
            projected = current_len + len(l) + 1
            if current and projected > chunk_size:
                chunks.append("\n".join(current).strip())
                current = [l]
                current_len = len(l) + 1
            else:
                current.append(l)
                current_len = projected

        if current:
            chunks.append("\n".join(current).strip())

        return [c for c in chunks if c]

    async def _normalize_chunk(
        self,
        *,
        chunk: str,
        source_paper: str,
        chunk_index: int,
        max_refs: int | None,
    ) -> List[Dict[str, Any]]:
        user_prompt = self._build_user_prompt(chunk=chunk, source_paper=source_paper, chunk_index=chunk_index, max_refs=max_refs)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You output strict JSON only. No markdown fences."},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
        }

        headers = {
            "Authorization": f"Bearer {self.token}",
            "x-openclaw-agent-id": self.agent_id,
            "Content-Type": "application/json",
        }

        url = f"{self.gateway_url}/v1/chat/completions"

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = self._extract_content_text(data)
        parsed = self._parse_json_array(content)
        return parsed

    @staticmethod
    def _extract_content_text(response_json: Dict[str, Any]) -> str:
        choices = response_json.get("choices") or []
        if not choices:
            return "[]"

        msg = choices[0].get("message") or {}
        content = msg.get("content")

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            parts: List[str] = []
            for p in content:
                if isinstance(p, dict):
                    t = p.get("text")
                    if isinstance(t, str):
                        parts.append(t)
            return "\n".join(parts).strip()

        return "[]"

    @staticmethod
    def _parse_json_array(text: str) -> List[Dict[str, Any]]:
        raw = (text or "").strip()
        if not raw:
            return []

        raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            arr = json.loads(raw)
            if isinstance(arr, list):
                return [x for x in arr if isinstance(x, dict)]
        except Exception:
            pass

        # Fallback: locate first JSON array in output
        m = re.search(r"\[.*\]", raw, flags=re.DOTALL)
        if m:
            try:
                arr = json.loads(m.group(0))
                if isinstance(arr, list):
                    return [x for x in arr if isinstance(x, dict)]
            except Exception:
                return []

        return []

    @staticmethod
    def _ensure_output_shape(item: Dict[str, Any], source_paper: str) -> Dict[str, Any]:
        structured = item.get("structured") if isinstance(item.get("structured"), dict) else {}
        cite_how = item.get("cite_how") if isinstance(item.get("cite_how"), dict) else {}

        out = {
            "raw_text": str(item.get("raw_text") or ""),
            "structured": {
                "title": structured.get("title") or "",
                "authors": structured.get("authors") if isinstance(structured.get("authors"), list) else [],
                "year": structured.get("year") if isinstance(structured.get("year"), int) else None,
                "journal": structured.get("journal"),
                "volume": structured.get("volume"),
                "issue": structured.get("issue"),
                "pages": structured.get("pages"),
                "doi": (str(structured.get("doi")).lower() if structured.get("doi") else None),
                "type": structured.get("type") if isinstance(structured.get("type"), str) else "other",
            },
            "cite_how": {
                "intext_first": str(cite_how.get("intext_first") or ""),
                "intext_subsequent": str(cite_how.get("intext_subsequent") or ""),
                "intext_narrative_first": str(cite_how.get("intext_narrative_first") or ""),
                "intext_narrative_subsequent": str(cite_how.get("intext_narrative_subsequent") or ""),
                "full_ref": str(cite_how.get("full_ref") or ""),
            },
            "corrupted": bool(item.get("corrupted", False)),
            "source_paper": source_paper,
        }
        return out

    @staticmethod
    def _build_user_prompt(chunk: str, source_paper: str, chunk_index: int, max_refs: int | None) -> str:
        cap_line = f"Maximum references to return for this chunk: {max_refs}." if max_refs is not None else ""

        return f"""
You are an academic reference formatting expert. Given a raw reference list extracted from a PDF (which may contain formatting artifacts, character codes, or inconsistent styles), normalize each reference into Harvard referencing style.

For EACH reference, output a JSON object with:

1. "structured" - extracted fields:
   - "title": string (paper/book title)
   - "authors": string[] (list of author names, format: "Surname, F.I.")
   - "year": int or null
   - "journal": string or null
   - "volume": string or null
   - "issue": string or null
   - "pages": string or null
   - "doi": string or null (if present in the raw text)
   - "type": "journal_article" | "book" | "book_chapter" | "conference" | "report" | "thesis" | "webpage" | "other"

2. "cite_how" - citation formatting:
   - "intext_first": string - first appearance with ALL authors, e.g. "(Adams, Hill & Roberts, 1998)" for 3 authors, "(Adams et al., 1998)" for 4+ authors
   - "intext_subsequent": string - subsequent appearances, e.g. "(Adams et al., 1998)" for 3+ authors, "(Adams & Hill, 1998)" for exactly 2
   - "intext_narrative_first": string - narrative form first use, e.g. "Adams, Hill and Roberts (1998)"
   - "intext_narrative_subsequent": string - narrative form subsequent, e.g. "Adams et al. (1998)"
   - "full_ref": string - full Harvard reference list entry, e.g. "Adams, C.A., Hill, W.-Y. & Roberts, C.B. (1998) 'Corporate social reporting practices in Western Europe: legitimating corporate behaviour?', *The British Accounting Review*, 30(1), pp. 1-21."

Harvard style rules to follow:
- Authors: Surname, Initials. Use & before last author.
- Year in parentheses after authors.
- Article title in sentence case with single quotes.
- Journal name in italics (indicate with *Journal Name*).
- Volume(Issue), pp. pages.
- Books: Author (Year) Title in italics. City: Publisher.
- Capitalize first word + proper nouns only in titles.
- For 4+ authors in parenthetical citations: first author et al.
- For 3 authors parenthetical: list all on first use, et al. after.
- For 2 authors: always list both.

Output a JSON array of objects. If a reference is completely unreadable/corrupted, still include it with "corrupted": true and best-effort parsing.
Do not include any text outside the JSON array.

Context:
- source_paper: {source_paper}
- chunk_index: {chunk_index}
{cap_line}

Raw reference text:
{chunk}
""".strip()
