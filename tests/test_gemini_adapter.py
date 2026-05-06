import unittest

from safe_mcp_proxy.integrations.gemini.adapter import (
    GeminiAdapter,
    GeminiAdapterError,
    ToolCall,
)


def _make_request(**overrides):
    base = {
        "functionCall": {"name": "read_file", "args": {"path": "/tmp/x"}},
        "metadata": {"session_id": "sess_1", "agent_id": "agent_2"},
    }
    base.update(overrides)
    return base


class TestGeminiAdapterParse(unittest.TestCase):

    def test_valid_full_request(self):
        req = _make_request()
        tc = GeminiAdapter.parse(req)
        self.assertIsInstance(tc, ToolCall)
        self.assertEqual(tc.tool_name, "read_file")
        self.assertEqual(tc.arguments, {"path": "/tmp/x"})
        self.assertEqual(tc.session_id, "sess_1")
        self.assertEqual(tc.agent_id, "agent_2")

    def test_valid_without_metadata(self):
        req = {"functionCall": {"name": "list_files", "args": {}}}
        tc = GeminiAdapter.parse(req)
        self.assertIsNone(tc.session_id)
        self.assertIsNone(tc.agent_id)
        self.assertEqual(tc.metadata, {})

    def test_args_defaults_to_empty_dict(self):
        req = {"functionCall": {"name": "ping"}}
        tc = GeminiAdapter.parse(req)
        self.assertEqual(tc.arguments, {})

    def test_missing_function_call_raises(self):
        with self.assertRaises(GeminiAdapterError) as ctx:
            GeminiAdapter.parse({"metadata": {}})
        self.assertEqual(ctx.exception.field, "functionCall")

    def test_missing_name_raises(self):
        with self.assertRaises(GeminiAdapterError) as ctx:
            GeminiAdapter.parse({"functionCall": {"args": {}}})
        self.assertEqual(ctx.exception.field, "name")

    def test_empty_name_raises(self):
        with self.assertRaises(GeminiAdapterError) as ctx:
            GeminiAdapter.parse({"functionCall": {"name": "", "args": {}}})
        self.assertEqual(ctx.exception.field, "name")

    def test_not_a_dict_raises(self):
        for bad in [None, "string", 42, ["list"]]:
            with self.subTest(bad=bad):
                with self.assertRaises(GeminiAdapterError) as ctx:
                    GeminiAdapter.parse(bad)
                self.assertEqual(ctx.exception.field, "request")

    def test_extra_metadata_fields_preserved(self):
        req = _make_request(metadata={"session_id": "s", "agent_id": "a", "custom": "val"})
        tc = GeminiAdapter.parse(req)
        self.assertEqual(tc.metadata["custom"], "val")
        self.assertEqual(tc.session_id, "s")

    def test_raw_request_is_original(self):
        req = _make_request()
        tc = GeminiAdapter.parse(req)
        self.assertIs(tc.raw_request, req)

    def test_arguments_with_nested_values(self):
        req = {"functionCall": {"name": "create_issue", "args": {"title": "Bug", "labels": ["p1", "p2"]}}}
        tc = GeminiAdapter.parse(req)
        self.assertEqual(tc.arguments["labels"], ["p1", "p2"])


class TestGeminiAdapterFormatResponse(unittest.TestCase):

    def test_format_response(self):
        result = GeminiAdapter.format_response("read_file", {"content": "hello"})
        self.assertEqual(result, {
            "functionResponse": {
                "name": "read_file",
                "response": {"content": "hello"},
            }
        })

    def test_format_response_empty_result(self):
        result = GeminiAdapter.format_response("ping", {})
        self.assertEqual(result["functionResponse"]["name"], "ping")
        self.assertEqual(result["functionResponse"]["response"], {})


if __name__ == "__main__":
    unittest.main()
