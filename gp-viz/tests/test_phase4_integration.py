import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api import create_app


class TestPhase4Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(create_app())

    def test_f1_health_ok(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")

    @patch("app.api.routes.validate_collection", return_value=True)
    def test_f2_check_endpoint_with_mock(self, _mock_validate):
        r = self.client.get("/check")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["qdrant_ok"])
        self.assertIn("collection", data)

    @patch("app.api.routes.search_profiles")
    def test_f3_search_papers_with_mock(self, mock_search):
        class DummyRecord:
            def as_dict(self):
                return {"id": "p1", "title": "A"}

        class DummyResult:
            collection = "vf_profiles_slr"
            records = [DummyRecord()]

        mock_search.return_value = DummyResult()
        r = self.client.get("/papers", params={"query": "governance", "limit": 5})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["id"], "p1")

    @patch("app.api.routes.get_profile")
    def test_f4_paper_detail_with_mock(self, mock_get_profile):
        class DummyRecord:
            def as_dict(self):
                return {"id": "p-42"}

        mock_get_profile.return_value = DummyRecord()
        r = self.client.get("/papers/p-42")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["id"], "p-42")

    @patch("app.api.routes.load_timeline_data")
    def test_f5_viz_f1_with_mock(self, mock_timeline):
        mock_timeline.return_value = {"years": [2020, 2021], "series": [{"name": "A", "values": [1, 2]}]}
        r = self.client.get("/viz/f1")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["years"], [2020, 2021])

    @patch("app.api.routes.load_heatmap_sheets")
    def test_f6_viz_f2_with_mock(self, mock_heatmaps):
        mock_heatmaps.return_value = [{"sheet": "Heatmap (theme) 1", "x": ["X"], "y": ["Y"], "z": [[1.0]]}]
        r = self.client.get("/viz/f2")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["count"], 1)
        self.assertTrue(data["sheets"][0]["sheet"].startswith("Heatmap"))

    @patch("app.api.routes.load_profile_filter_options")
    def test_f7_viz_filters_with_mock(self, mock_filters):
        mock_filters.return_value = {"count": 10, "availableYears": ["2020"]}
        r = self.client.get("/viz/filters")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["count"], 10)


if __name__ == "__main__":
    unittest.main()
