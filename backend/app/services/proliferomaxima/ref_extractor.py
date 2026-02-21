from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

REFERENCE_HEADINGS = ("references", "bibliography", "works cited", "reference list")
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s)\];,]+", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
CITATION_MENTION_RE = re.compile(r"\b([A-Z][A-Za-z\-']+)\s*\((19|20)\d{2}\)")


class ReferenceExtractor:
    def __init__(self, parsed_dir: Path | str):
        self.parsed_dir = Path(parsed_dir)

    def extract_all(self, max_files: Optional[int] = None, max_refs_per_paper: Optional[int] = None) -> List[Dict]:
        files = sorted(self.parsed_dir.rglob("*.md"))
        if max_files is not None:
            files = files[: max(0, int(max_files))]
        return self.extract_from_files(files, max_refs_per_paper=max_refs_per_paper)

    def extract_from_files(self, file_paths: List[Path | str], max_refs_per_paper: Optional[int] = None) -> List[Dict]:
        refs: List[Dict] = []
        cap = max(0, int(max_refs_per_paper)) if max_refs_per_paper is not None else None

        for file in file_paths:
            try:
                paper_refs = self.extract_from_file(Path(file))
            except Exception:
                continue
            if cap is not None:
                paper_refs = paper_refs[:cap]
            refs.extend(paper_refs)
        return refs

    def extract_from_file(self, path: Path) -> List[Dict]:
        raw_section = self.extract_raw_reference_section(path)
        if not raw_section.strip():
            return []

        lines = raw_section.splitlines()
        entries = self._split_entries(lines)
        out: List[Dict] = []
        for raw in entries:
            parsed = self._parse_entry(raw)
            if not parsed:
                continue
            parsed["source_paper"] = path.name
            out.append(parsed)
        return out

    def extract_raw_reference_section(self, path: Path) -> str:
        """Return raw references section body between heading and next heading/end."""
        text = path.read_text(encoding="utf-8", errors="ignore")
        # Normalize HTML entities common in parsed PDFs
        text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        lines = text.splitlines()

        section_start = self._find_reference_start(lines)
        if section_start is None:
            return ""

        block: List[str] = []
        for line in lines[section_start:]:
            if line.strip().startswith("#"):
                break
            block.append(line)

        return "\n".join(block).strip()

    def extract_from_text_mentions(self, text: str, source_paper: str, max_refs: Optional[int] = None) -> List[Dict]:
        """Fallback extractor for prose chunks (e.g., cited_for) using Author(Year) mentions."""
        out: List[Dict] = []
        seen = set()
        cap = max(0, int(max_refs)) if max_refs is not None else None

        for m in CITATION_MENTION_RE.finditer(text or ""):
            author = m.group(1)
            ym = YEAR_RE.search(m.group(0))
            if not ym:
                continue
            year = int(ym.group(0))
            key = (author.lower(), year)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "raw_text": m.group(0),
                    "title": f"{author} ({year})",
                    "authors": [author],
                    "year": year,
                    "doi": None,
                    "cited_for": "inferred_from_vf_chunk",
                    "source_paper": source_paper,
                }
            )
            if cap is not None and len(out) >= cap:
                break
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

        # Patterns that start a new reference entry
        NUMBERED_RE = re.compile(r"^((\[\d+\])|(\d+\.)|(\(\d+\)))\s+")
        # Markdown bullet: - or * followed by space (common in parsed PDFs)
        BULLET_RE = re.compile(r"^[-*]\s+")

        for raw in lines:
            line = raw.strip()
            if not line:
                if current:
                    entries.append(" ".join(current).strip())
                    current = []
                continue

            if line.startswith("#"):
                break

            numbered_match = NUMBERED_RE.match(line)
            bullet_match = BULLET_RE.match(line)
            is_new_item = bool(numbered_match or bullet_match)

            if is_new_item and current:
                entries.append(" ".join(current).strip())
                if numbered_match:
                    current = [NUMBERED_RE.sub("", line).strip()]
                else:
                    current = [BULLET_RE.sub("", line).strip()]
            elif is_new_item and not current:
                if numbered_match:
                    current = [NUMBERED_RE.sub("", line).strip()]
                else:
                    current = [BULLET_RE.sub("", line).strip()]
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
