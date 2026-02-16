from __future__ import annotations

import csv
import io
import re
from typing import Any


class BatchProcessor:
    def parse_csv(self, csv_data: str) -> list[dict[str, Any]]:
        rows = []
        reader = csv.DictReader(io.StringIO(csv_data))
        for row in reader:
            norm = {str(k).strip().lower(): str(v).strip() for k, v in row.items() if k is not None and v is not None}
            rows.append({
                "title": norm.get("title", ""),
                "doi": norm.get("doi", ""),
                "author": norm.get("author", norm.get("authors", "")),
                "year": norm.get("year", ""),
            })
        return rows

    def parse_dois(self, dois: str) -> list[str]:
        return [d.strip() for d in re.split(r"[\s,;]+", dois) if d.strip()]

    def parse_bibtex(self, bibtex: str) -> list[dict[str, Any]]:
        entries = re.split(r"@\w+\{", bibtex)[1:]
        out = []
        for entry in entries:
            fields = {m.group(1).lower(): m.group(2).strip() for m in re.finditer(r"(\w+)\s*=\s*\{([^}]*)\}", entry)}
            if fields.get("title") or fields.get("doi"):
                out.append({
                    "title": fields.get("title", ""),
                    "doi": fields.get("doi", ""),
                    "author": fields.get("author", ""),
                    "year": fields.get("year", ""),
                })
        return out
