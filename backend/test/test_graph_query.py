import unittest
from unittest.mock import patch

from app.graph.graph_query import GraphQueryService


class TestGraphQueryService(unittest.TestCase):
    def setUp(self):
        self.service = GraphQueryService()

    @patch("app.graph.graph_query.neo4j_client.run_query")
    def test_get_company_overview_returns_company(self, mock_run_query):
        mock_run_query.return_value = [
            {
                "name": "Infosys Limited",
                "ticker": "INFY",
                "sector": "Information Technology",
                "quarters": ["Q3 FY2025"],
                "actions": [{"type": "dividend", "amount": 21}],
            }
        ]

        result = self.service.get_company_overview("INFY")

        self.assertEqual(result["ticker"], "INFY")
        self.assertEqual(result["name"], "Infosys Limited")
        self.assertIn("BELONGS_TO", mock_run_query.call_args[0][0])
        self.assertEqual(mock_run_query.call_args[0][1], {"ticker": "INFY"})

    @patch("app.graph.graph_query.neo4j_client.run_query")
    def test_get_sector_companies_filters_case_insensitive(self, mock_run_query):
        mock_run_query.return_value = [
            {"ticker": "INFY", "name": "Infosys Limited", "sector": "Information Technology"}
        ]

        result = self.service.get_sector_companies("information technology")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["ticker"], "INFY")
        self.assertEqual(mock_run_query.call_args[0][1], {"sector": "information technology"})

    @patch("app.graph.graph_query.neo4j_client.run_query")
    def test_get_companies_by_metric_builds_filters(self, mock_run_query):
        mock_run_query.return_value = [
            {"ticker": "INFY", "name": "Infosys Limited", "quarter": "Q3 FY2025", "value": 21.3, "unit": "%", "direction": "stable"}
        ]

        result = self.service.get_companies_by_metric("operating_margin", min_value=20.0, quarter="Q3 FY2025")

        self.assertEqual(result[0]["ticker"], "INFY")
        self.assertEqual(mock_run_query.call_args[0][1], {"metric_type": "operating_margin", "min_value": 20.0, "quarter": "Q3 FY2025"})
        self.assertIn("m.value >= $min_value", mock_run_query.call_args[0][0])
        self.assertIn("e.quarter = $quarter", mock_run_query.call_args[0][0])

    @patch("app.graph.graph_query.neo4j_client.run_query")
    def test_get_corporate_actions_applies_filters(self, mock_run_query):
        mock_run_query.return_value = [
            {"ticker": "TCS", "company": "Tata Consultancy Services Limited", "action_type": "buyback", "amount": 17000}
        ]

        result = self.service.get_corporate_actions(ticker="TCS", action_type="buyback")

        self.assertEqual(result[0]["company"], "Tata Consultancy Services Limited")
        self.assertEqual(mock_run_query.call_args[0][1], {"ticker": "TCS", "action_type": "buyback"})
        self.assertIn("WHERE c.ticker = $ticker AND a.type = $action_type", mock_run_query.call_args[0][0])

    @patch("app.graph.graph_query.neo4j_client.run_query")
    def test_get_competitors_returns_competitor_list(self, mock_run_query):
        mock_run_query.return_value = [
            {"ticker": "TCS", "name": "Tata Consultancy Services Limited"}
        ]

        result = self.service.get_competitors("INFY")

        self.assertEqual(result[0]["ticker"], "TCS")
        self.assertEqual(mock_run_query.call_args[0][1], {"ticker": "INFY"})

    @patch("app.graph.graph_query.neo4j_client.run_query")
    def test_get_graph_stats_returns_counts(self, mock_run_query):
        mock_run_query.return_value = [{"companies": 3, "sectors": 2, "events": 3, "metrics": 12, "actions": 6}]

        result = self.service.get_graph_stats()

        self.assertEqual(result["companies"], 3)
        self.assertEqual(result["actions"], 6)

    @patch.object(GraphQueryService, "get_corporate_actions")
    @patch.object(GraphQueryService, "get_sector_companies")
    @patch.object(GraphQueryService, "get_companies_by_metric")
    def test_natural_language_to_graph_routes_queries(self, mock_metric, mock_sector, mock_actions):
        mock_actions.return_value = [{"action_type": "dividend"}]
        mock_sector.return_value = [{"ticker": "HDFCBANK"}]
        mock_metric.return_value = [{"ticker": "INFY"}]

        self.assertEqual(self.service.natural_language_to_graph("What is the dividend policy?"), [{"action_type": "dividend"}])
        self.assertEqual(self.service.natural_language_to_graph("Tell me about buyback plans."), [{"action_type": "dividend"}])
        self.assertEqual(self.service.natural_language_to_graph("Show margin data."), [{"ticker": "INFY"}])
        self.assertEqual(self.service.natural_language_to_graph("Banking exposure."), [{"ticker": "HDFCBANK"}])
        self.assertEqual(self.service.natural_language_to_graph("Technology sector companies."), [{"ticker": "HDFCBANK"}])

        mock_actions.assert_called()
        mock_sector.assert_called()
        mock_metric.assert_called_with("operating_margin")


if __name__ == "__main__":
    unittest.main()
