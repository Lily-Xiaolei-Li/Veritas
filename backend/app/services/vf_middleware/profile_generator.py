from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import httpx

from app.logging_config import get_logger

logger = get_logger("vf_middleware.profile_generator")

CHUNK_IDS = [
    "meta",
    "abstract",
    "theory",
    "literature",
    "research_questions",
    "contributions",
    "key_concepts",
    "cited_for",
]

META_KEYS = [
    "authors",
    "year",
    "title",
    "journal",
    "volume",
    "issue",
    "pages",
    "paper_type",
    "primary_method",
    "secondary_methods",
    "empirical_context",
    "keywords_author",
    "keywords_inferred",
    "in_library",
]

# Agent definitions — model can be overridden via XIAOLEI_DEFAULT_MODEL env var
_DEFAULT_MODEL = os.getenv("XIAOLEI_DEFAULT_MODEL", "openai-codex/gpt-5.3-codex")

AGENTS: Dict[str, Dict[str, str]] = {
    "helper": {
        "description": "默认通用助手",
        "model": _DEFAULT_MODEL,
        "persona": "General academic analysis assistant.",
    },
    "dr-xiaolei": {
        "description": "博士小蕾（学术深度分析）",
        "model": _DEFAULT_MODEL,
        "persona": "You are Dr. Xiaolei, a rigorous academic researcher with deep expertise in qualitative methodology, critical accounting, and social theory. Provide thorough, methodologically strict analysis.",
    },
    "asst-xiaolei": {
        "description": "助手小蕾（轻量快速处理）",
        "model": _DEFAULT_MODEL,
        "persona": "You are Assistant Xiaolei, concise and practical. Focus on extracting key information efficiently without excessive elaboration.",
    },
}


def list_available_agents() -> list[dict[str, str]]:
    return [{"name": name, **meta} for name, meta in AGENTS.items()]


class VFProfileGenerator:
    """Generate 8-chunk VF citation profiles via gateway LLM."""

    def __init__(self, gateway_url: Optional[str] = None, auth_token: Optional[str] = None):
        self.gateway_url, self.auth_token = self._load_gateway_config(gateway_url, auth_token)

    @staticmethod
    def _load_gateway_config(gateway_url: Optional[str], auth_token: Optional[str]) -> tuple[str, str]:
        if gateway_url is not None and auth_token is not None:
            return gateway_url, auth_token

        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            ".env",
        )
        env_vars: Dict[str, str] = {}
        if os.path.exists(env_path):
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, val = line.partition("=")
                        env_vars[key.strip()] = val.strip()

        url = gateway_url or os.getenv("XIAOLEI_GATEWAY_URL") or env_vars.get("XIAOLEI_GATEWAY_URL", "http://localhost:18789")
        token = auth_token or os.getenv("XIAOLEI_AUTH_TOKEN") or env_vars.get("XIAOLEI_AUTH_TOKEN", "")
        return url, token

    async def generate_profile(
        self,
        *,
        paper_id: str,
        metadata: Dict[str, Any],
        abstract: str,
        full_text: Optional[str] = None,
        in_library: bool = True,
        agent: str = "helper",
    ) -> Dict[str, Any]:
        """Generate a normalized profile dict with required chunks and metadata."""
        source_type = "library" if in_library else "external"
        system_prompt = self._system_prompt(in_library=in_library, agent=agent)
        user_prompt = self._user_prompt(metadata=metadata, abstract=abstract, full_text=full_text, in_library=in_library)
        content = await self._llm_call(system_prompt, user_prompt, agent=agent)
        parsed = self._parse_json_object(content)

        chunks = parsed.get("chunks") if isinstance(parsed, dict) else None
        if not isinstance(chunks, dict):
            raise ValueError("LLM response missing 'chunks' object")

        normalized_meta = self._normalize_meta(
            chunks.get("meta") if isinstance(chunks.get("meta"), dict) else metadata,
            in_library=in_library,
        )
        normalized_chunks: Dict[str, str] = {"meta": json.dumps(normalized_meta, ensure_ascii=False)}

        for chunk_id in CHUNK_IDS[1:]:
            value = chunks.get(chunk_id, "")
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)
            value = value.strip()
            if not value and chunk_id == "abstract":
                value = abstract.strip()
            if not value:
                value = ""
            normalized_chunks[chunk_id] = value

        return {
            "paper_id": paper_id,
            "source_type": source_type,
            "in_library": in_library,
            "meta": normalized_meta,
            "chunks": normalized_chunks,
        }

    async def _llm_call(self, system_prompt: str, user_prompt: str, agent: str) -> str:
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        # Route to helper agent (GPT-5.3) — never use Anthropic for VF generation
        headers["x-openclaw-agent-id"] = "helper"

        conf = AGENTS.get(agent, AGENTS["helper"])

        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{self.gateway_url}/v1/chat/completions",
                headers=headers,
                json={
                    "model": conf["model"],
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 7000,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    @staticmethod
    def _parse_json_object(text: str) -> Dict[str, Any]:
        text = text.strip()
        if text.startswith("```"):
            parts = text.split("\n")
            if parts:
                parts = parts[1:]
            if parts and parts[-1].strip().startswith("```"):
                parts = parts[:-1]
            text = "\n".join(parts).strip()

        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            result = json.loads(text[start : end + 1])
            if isinstance(result, dict):
                return result

        raise ValueError("Failed to parse profile generator JSON response")

    @staticmethod
    def _normalize_meta(meta: Dict[str, Any], *, in_library: bool) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for k in META_KEYS:
            out[k] = meta.get(k)

        out["authors"] = out.get("authors") if isinstance(out.get("authors"), list) else []
        out["secondary_methods"] = out.get("secondary_methods") if isinstance(out.get("secondary_methods"), list) else []
        out["keywords_author"] = out.get("keywords_author") if isinstance(out.get("keywords_author"), list) else []
        out["keywords_inferred"] = out.get("keywords_inferred") if isinstance(out.get("keywords_inferred"), list) else []

        try:
            out["year"] = int(out["year"]) if out.get("year") is not None else None
        except Exception:
            out["year"] = None

        out["in_library"] = bool(in_library)
        return out

    @staticmethod
    def _system_prompt(*, in_library: bool, agent: str) -> str:
        mode = "FULL TEXT AVAILABLE" if in_library else "ABSTRACT-ONLY INFERENCE"
        persona = AGENTS.get(agent, AGENTS["helper"])["persona"]
        return (
            f"You generate Veritafactum citation profiles for academic works.\n\n"
            f"Persona: {persona}\n"
            f"Mode: {mode}\n\n"
            f"Return STRICT JSON only, with this schema:\n"
            "{\n"
            '  "chunks": {\n'
            '    "meta": {\n'
            '      "authors": ["..."],\n'
            '      "year": 2020,\n'
            '      "title": "...",\n'
            '      "journal": null,\n'
            '      "volume": null,\n'
            '      "issue": null,\n'
            '      "pages": null,\n'
            '      "paper_type": "...",\n'
            '      "primary_method": "...",\n'
            '      "secondary_methods": ["..."],\n'
            '      "empirical_context": "...",\n'
            '      "keywords_author": ["..."],\n'
            '      "keywords_inferred": ["..."],\n'
            f'      "in_library": {str(in_library).lower()}\n'
            "    },\n"
            '    "abstract": "verbatim abstract",\n'
            '    "theory": "...",\n'
            '    "literature": "...",\n'
            '    "research_questions": "...",\n'
            '    "contributions": "...",\n'
            '    "key_concepts": "...",\n'
            '    "cited_for": "..."\n'
            "  }\n"
            "}\n\n"
            "No markdown. No extra keys.\n"
            "For chunks 3-8: content-determined length, usually 100-300 words, no hard cap."
        )

    @staticmethod
    def _user_prompt(*, metadata: Dict[str, Any], abstract: str, full_text: Optional[str], in_library: bool) -> str:
        full_text_section = full_text.strip() if full_text else ""
        if not in_library:
            full_text_section = "[Full text not available. Infer chunks 3-8 from metadata + abstract and label uncertainty where appropriate.]"

        return (
            "Generate the 8-chunk VF profile.\n\n"
            f"Metadata (input):\n{json.dumps(metadata, ensure_ascii=False, indent=2)}\n\n"
            f"Abstract:\n{abstract.strip()}\n\n"
            f"Full text/context:\n{full_text_section}\n"
        )
