from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

REFERENCE_HEADINGS = ("references", "bibliography", "works cited", "reference list")
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s)\];,]+", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


class ReferenceExtractor:
    def __init__(self, parsed_dir: Path | str):
        self.parsed_dir = Path(parsed_dir)

    def extract_all(self, max_files: Optional[int] = None) -> List[Dict]:
        refs: List[Dict] = []
        files = sorted(self.parsed_dir.rglob("*.md"))
        if max_files is not None:
            files = files[: max(0, int(max_files))]

        for file in files:
            try:
                refs.extend(self.extract_from_file(file))
            except Exception:
                continue
        return refs

    def extract_from_file(self, path: Path) -> List[Dict]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()

        section_start = self._find_reference_start(lines)
        if section_start is None:
            return []

        block = lines[section_start:]
        entries = self._split_entries(block)
        out: List[Dict] = []
        for raw in entries:
            parsed = self._parse_entry(raw)
            if not parsed:
                continue
            parsed["source_paper"] = path.name
            out.append(parsed)
        return out

    def _find_reference_start(self, lines: List[str]) -> Optional[int]:
        for idx, line in enumerate(lines):
            normalized = line.strip().strip("#").strip().lower()
            if normalized in REFERENCE_HEADINGS:
                return idx + 1
        return None

    def _split_entries(self, lines: List[str]) -> List[str]:
        entries: List[str] = []
        current: List[str] = []

        for raw in lines:
            line = raw.strip()
            if not line:
                if current:
                    entries.append(" ".join(current).strip())
                    current = []
                continue

            if line.startswith("#"):
                break

            is_new_item = bool(re.match(r"^((\[\d+\])|(\d+\.)|(\(\d+\)))\s+", line))
            if is_new_item and current:
                entries.append(" ".join(current).strip())
                current = [re.sub(r"^((\[\d+\])|(\d+\.)|(\(\d+\)))\s+", "", line).strip()]
            else:
                current.append(line)

        if current:
            entries.append(" ".join(current).strip())

        return [e for e in entries if len(e) > 20]

    def _parse_entry(self, raw: str) -> Optional[Dict]:
        doi_match = DOI_RE.search(raw)
        doi = doi_match.group(0).rstrip(".") if doi_match else None

        year_match = YEAR_RE.search(raw)
        year = int(year_match.group(0)) if year_match else None

        title = self._extract_title(raw)
        if not title and not doi:
            return None

        authors = self._extract_authors(raw)

        return {
            "raw_text": raw,
            "title": title,
            "authors": authors,
            "year": year,
            "doi": doi.lower() if doi else None,
            "cited_for": None,
        }

    def _extract_title(self, raw: str) -> str:
        text = re.sub(r"\s+", " ", raw).strip()
        m = re.search(r"\(\d{4}\)\.\s*([^\.]+)\.", text)
        if m:
            return m.group(1).strip(" \"'")

        parts = [p.strip() for p in text.split(".") if p.strip()]
        if len(parts) >= 2:
            return parts[1].strip(" \"'")
        if parts:
            return parts[0][:180].strip(" \"'")
        return ""

    def _extract_authors(self, raw: str) -> List[str]:
        head = raw.split("(", 1)[0].strip()
        if not head:
            return []
        chunks = re.split(r",\s+|\s+and\s+|\s*&\s*", head)
        authors = [c.strip() for c in chunks if c.strip()]
        return authors[:8]
