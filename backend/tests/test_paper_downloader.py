"""Tests for paper_downloader service."""

import pytest
from unittest.mock import patch, MagicMock

from app.services.paper_downloader import (
    sanitize_filename,
    is_valid_pdf,
    _title_similarity,
    parse_google_scholar_csv,
    parse_bibtex,
    resolve_doi_crossref,
    find_oa_pdf_url,
    DownloadStatus,
    PaperResult,
)


class TestSanitizeFilename:
    def test_basic(self):
        result = sanitize_filename("Smith", "2025", "Machine Learning in Audit Quality Assessment")
        assert result == "Smith_2025_Machine_Learning_in_Audit_Quality_Assessment.pdf"

    def test_missing_author(self):
        result = sanitize_filename("", "2025", "Some Title")
        assert result.startswith("Unknown_")

    def test_missing_year(self):
        result = sanitize_filename("Jones", "", "A Paper")
        assert "_XXXX_" in result

    def test_special_chars(self):
        result = sanitize_filename("O'Brien", "2024", "What's New? A Review")
        assert "'" not in result.replace(".pdf", "")


class TestIsValidPdf:
    def test_valid(self):
        assert is_valid_pdf(b"%PDF-1.4 rest of content")

    def test_invalid_html(self):
        assert not is_valid_pdf(b"<html><body>Login required</body></html>")

    def test_empty(self):
        assert not is_valid_pdf(b"")


class TestTitleSimilarity:
    def test_identical(self):
        assert _title_similarity("hello world", "hello world") == 1.0

    def test_partial(self):
        sim = _title_similarity("machine learning audit", "machine learning for audit quality")
        assert sim > 0.5

    def test_disjoint(self):
        assert _title_similarity("apples oranges", "cats dogs") == 0.0


class TestParseGoogleScholarCsv:
    def test_basic_csv(self):
        csv_content = "Title,Author,Year,DOI\nSome Paper,Smith,2025,10.1234/test\n"
        papers = parse_google_scholar_csv(csv_content)
        assert len(papers) == 1
        assert papers[0]["doi"] == "10.1234/test"
        assert papers[0]["title"] == "Some Paper"
        assert papers[0]["author"] == "Smith"

    def test_empty(self):
        papers = parse_google_scholar_csv("Title,Author,Year,DOI\n")
        assert len(papers) == 0


class TestParseBibtex:
    def test_basic(self):
        bib = """@article{smith2025,
  title={Machine Learning in Audit},
  author={Smith, John and Doe, Jane},
  year={2025},
  doi={10.1234/ml-audit}
}"""
        papers = parse_bibtex(bib)
        assert len(papers) == 1
        assert papers[0]["doi"] == "10.1234/ml-audit"
        assert "Smith" in papers[0]["author"]

    def test_no_doi(self):
        bib = "@article{x, title={Test Paper}, author={Author}, year={2024}}"
        papers = parse_bibtex(bib)
        assert len(papers) == 1
        assert papers[0]["doi"] == ""


class TestPaperResult:
    def test_to_dict(self):
        r = PaperResult(doi="10.1234/test", status=DownloadStatus.SUCCESS)
        d = r.to_dict()
        assert d["doi"] == "10.1234/test"
        assert d["status"] == "success"
