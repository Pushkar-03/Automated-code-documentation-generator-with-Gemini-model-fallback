import unittest
from unittest.mock import MagicMock, patch

from generator import GeminiGenerationError, _extract_json, generate_documentation


class GeneratorTests(unittest.TestCase):
    def test_extract_json_clean(self):
        data = '{"docstrings": {"module": "test"}, "readme": "# Readme"}'
        parsed = _extract_json(data)
        self.assertEqual(parsed["docstrings"]["module"], "test")

    def test_extract_json_markdown_wrapped(self):
        data = '```json\n{"docstrings": {}, "readme": "Hello"}\n```'
        parsed = _extract_json(data)
        self.assertEqual(parsed["readme"], "Hello")

    def test_extract_json_invalid(self):
        with self.assertRaises(GeminiGenerationError):
            _extract_json("not a valid json")

    @patch("generator.genai.Client")
    def test_fallback_on_503(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        # First model throws 503, second model succeeds
        error_503 = Exception(
            "503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand.'}}"
        )
        success_response = MagicMock()
        success_response.text = '{"docstrings": {"func_1": "Does something."}, "readme": "# Project"}'

        mock_client.models.generate_content.side_effect = [
            error_503,
            error_503,
            success_response,
        ]

        targets = [{"id": "func_1", "kind": "function", "name": "foo", "qualified_name": "foo"}]
        result = generate_documentation(
            source_code="def foo(): pass",
            targets=targets,
            api_key="fake-test-key",
        )
        self.assertIn("func_1", result["docstrings"])
        self.assertEqual(result["docstrings"]["func_1"], "Does something.")


if __name__ == "__main__":
    unittest.main()
