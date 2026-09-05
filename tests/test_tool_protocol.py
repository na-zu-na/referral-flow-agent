import unittest

from tools import REGISTRY, call_tool, failure, register_tool, success


class ToolProtocolTests(unittest.TestCase):
    def setUp(self):
        self.original_registry = REGISTRY.copy()
        REGISTRY.clear()

    def tearDown(self):
        REGISTRY.clear()
        REGISTRY.update(self.original_registry)

    def test_successful_call(self):
        register_tool("echo", lambda value: success({"value": value}))

        self.assertEqual(
            call_tool("echo", {"value": "REF-5602"}),
            {"ok": True, "data": {"value": "REF-5602"}},
        )

    def test_tool_failure_passes_through(self):
        register_tool("missing", lambda: failure("NOT_FOUND", "Missing."))

        self.assertEqual(
            call_tool("missing", {}),
            {"ok": False, "error": {"code": "NOT_FOUND", "message": "Missing."}},
        )

    def test_unknown_tool_is_structured(self):
        result = call_tool("not_registered", {})

        self.assertEqual(result["error"]["code"], "UNKNOWN_TOOL")

    def test_arguments_must_be_an_object(self):
        register_tool("echo", lambda value: success(value))

        result = call_tool("echo", ["REF-5602"])

        self.assertEqual(result["error"]["code"], "INVALID_ARGUMENTS")

    def test_signature_is_checked_before_execution(self):
        called = False

        def tool(required):
            nonlocal called
            called = True
            return success(required)

        register_tool("needs_argument", tool)
        result = call_tool("needs_argument", {})

        self.assertFalse(called)
        self.assertEqual(result["error"]["code"], "INVALID_ARGUMENTS")

    def test_invalid_or_non_json_results_are_blocked(self):
        register_tool("invalid", lambda: {"value": 1})
        register_tool("non_json", lambda: success({1, 2}))

        self.assertEqual(
            call_tool("invalid", {})["error"]["code"], "TOOL_PROTOCOL_ERROR"
        )
        self.assertEqual(
            call_tool("non_json", {})["error"]["code"], "TOOL_PROTOCOL_ERROR"
        )


if __name__ == "__main__":
    unittest.main()
