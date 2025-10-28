import unittest
from unittest.mock import patch, Mock


class TestFrontendGraphApiClients(unittest.TestCase):
    def test_call_graph_stats_success(self):
        # Import the module under test
        import frontend.api_client_graph as graph_api

        # Mock requests.post to return a successful payload
        fake_report = {
            "status": "success",
            "repo_url": "https://github.com/org/repo",
            "stats": {"files": 123, "ccg_counts": {"calls": 10, "inherits": 2, "imports": 5}},
            "error": ""
        }
        fake_resp = Mock()
        fake_resp.raise_for_status = Mock()
        fake_resp.json = Mock(return_value={"reports": [fake_report]})

        with patch.object(graph_api.requests, "post", return_value=fake_resp) as post_mock:
            out = graph_api.call_graph_stats("https://github.com/org/repo", depth="deep", top_n=10, backend_url="http://localhost:8000")

        self.assertIsInstance(out, dict)
        self.assertEqual(out.get("status"), "success")
        self.assertIn("stats", out)
        self.assertEqual(out["stats"].get("files"), 123)
        post_mock.assert_called_once()

    def test_call_graph_docs_error_handling(self):
        import frontend.api_client_graph as graph_api

        # Simulate request failure
        with patch.object(graph_api.requests, "post", side_effect=Exception("boom")):
            out = graph_api.call_graph_docs("https://github.com/org/repo", depth="deep", top_n=10, backend_url="http://localhost:8000")

        self.assertIsInstance(out, dict)
        self.assertEqual(out.get("status"), "error")
        self.assertIn("graph_docs failed", out.get("message", ""))


if __name__ == "__main__":
    unittest.main()

