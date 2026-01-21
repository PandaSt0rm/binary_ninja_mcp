"""Unit tests for MCP bridge helper functions."""


from binary_ninja_mcp.bridge import binja_mcp_bridge


class TestMcpResult:
    """Tests for _mcp_result envelope function."""

    def test_creates_ok_envelope(self):
        result = binja_mcp_bridge._mcp_result(ok=True, file="test.bin")
        assert result["ok"] is True
        assert result["file"] == "test.bin"

    def test_creates_error_envelope(self):
        result = binja_mcp_bridge._mcp_result(ok=False, file="test.bin", error="bad")
        assert result["ok"] is False
        assert result["file"] == "test.bin"
        assert result["error"] == "bad"

    def test_includes_extra_payload(self):
        result = binja_mcp_bridge._mcp_result(
            ok=True, file="test.bin", address="0x1000", count=5
        )
        assert result["ok"] is True
        assert result["address"] == "0x1000"
        assert result["count"] == 5


class TestMcpFromJson:
    """Tests for _mcp_from_json response parsing."""

    def test_omits_request_on_success(self):
        data = {"success": True, "address": "0x123", "value": 7}
        out = binja_mcp_bridge._mcp_from_json(data, file="a.bin", address="0x456")

        assert out["ok"] is True
        assert out["file"] == "a.bin"
        assert out["address"] == "0x123"
        assert out["value"] == 7
        assert "request" not in out

    def test_includes_request_on_error(self):
        data = {"error": "bad"}
        out = binja_mcp_bridge._mcp_from_json(data, file="a.bin", address="0x456")

        assert out["ok"] is False
        assert out["file"] == "a.bin"
        assert out["error"] == "bad"
        assert out["request"] == {"address": "0x456"}

    def test_strips_reserved_envelope_keys(self):
        data = {"success": True, "file": "server.bin", "ok": False}
        out = binja_mcp_bridge._mcp_from_json(data, file="client.bin")

        assert out["ok"] is True
        assert out["file"] == "client.bin"

    def test_handles_none_data(self):
        out = binja_mcp_bridge._mcp_from_json(None, file="a.bin")
        assert out["ok"] is False
        assert "error" in out

    def test_handles_non_dict_data(self):
        out = binja_mcp_bridge._mcp_from_json([1, 2, 3], file="a.bin")
        assert out["ok"] is True
        assert out["raw"] == [1, 2, 3]

    def test_uses_request_info_parameter(self):
        data = {"error": "failed"}
        out = binja_mcp_bridge._mcp_from_json(
            data, file="a.bin", request_info={"query": "test"}
        )
        assert out["request"] == {"query": "test"}

    def test_detects_error_from_success_false(self):
        data = {"success": False, "message": "Operation failed"}
        out = binja_mcp_bridge._mcp_from_json(data, file="a.bin")
        assert out["ok"] is False


class TestMcpFromText:
    """Tests for _mcp_from_text response parsing."""

    def test_allows_duplicate_output_key(self):
        out = binja_mcp_bridge._mcp_from_text(
            "hello",
            file="a.bin",
            key="value",
            value="ignored",
        )

        assert out["ok"] is True
        assert out["file"] == "a.bin"
        assert out["value"] == "hello"

    def test_handles_none_text(self):
        out = binja_mcp_bridge._mcp_from_text(None, file="a.bin")
        assert out["ok"] is False
        assert "error" in out

    def test_detects_error_prefix(self):
        out = binja_mcp_bridge._mcp_from_text("Error 404: not found", file="a.bin")
        assert out["ok"] is False
        assert "Error 404" in out["error"]

    def test_detects_request_failed_prefix(self):
        out = binja_mcp_bridge._mcp_from_text("Request failed: timeout", file="a.bin")
        assert out["ok"] is False

    def test_strips_whitespace(self):
        out = binja_mcp_bridge._mcp_from_text("  hello world  \n", file="a.bin")
        assert out["text"] == "hello world"

    def test_custom_key_name(self):
        out = binja_mcp_bridge._mcp_from_text("content here", file="a.bin", key="hexdump")
        assert out["hexdump"] == "content here"


class TestMcpFromList:
    """Tests for _mcp_from_list response parsing."""

    def test_allows_duplicate_output_key(self):
        out = binja_mcp_bridge._mcp_from_list(
            [1, 2],
            file="a.bin",
            key="value",
            value=[0],
        )

        assert out["ok"] is True
        assert out["file"] == "a.bin"
        assert out["value"] == [1, 2]

    def test_handles_none_items(self):
        out = binja_mcp_bridge._mcp_from_list(None, file="a.bin")
        assert out["ok"] is False
        assert "error" in out

    def test_handles_empty_list(self):
        out = binja_mcp_bridge._mcp_from_list([], file="a.bin")
        assert out["ok"] is True
        assert out["items"] == []

    def test_custom_key_name(self):
        out = binja_mcp_bridge._mcp_from_list([1, 2, 3], file="a.bin", key="strings")
        assert out["strings"] == [1, 2, 3]


class TestIsIntLike:
    """Tests for _is_int_like address detection."""

    def test_hex_with_prefix(self):
        assert binja_mcp_bridge._is_int_like("0x1234") is True
        assert binja_mcp_bridge._is_int_like("0X1234") is True
        assert binja_mcp_bridge._is_int_like("0xABCD") is True
        assert binja_mcp_bridge._is_int_like("0xabcdef") is True

    def test_hex_with_suffix(self):
        assert binja_mcp_bridge._is_int_like("1234h") is True
        assert binja_mcp_bridge._is_int_like("ABCDh") is True

    def test_decimal(self):
        assert binja_mcp_bridge._is_int_like("1234") is True
        assert binja_mcp_bridge._is_int_like("0") is True
        assert binja_mcp_bridge._is_int_like("999999") is True

    def test_binary_prefix(self):
        assert binja_mcp_bridge._is_int_like("0b1010") is True
        assert binja_mcp_bridge._is_int_like("0B1111") is True

    def test_octal_prefix(self):
        assert binja_mcp_bridge._is_int_like("0o777") is True
        assert binja_mcp_bridge._is_int_like("0O123") is True

    def test_explicit_prefixes(self):
        assert binja_mcp_bridge._is_int_like("hex:1234") is True
        assert binja_mcp_bridge._is_int_like("h:abcd") is True
        assert binja_mcp_bridge._is_int_like("dec:1234") is True
        assert binja_mcp_bridge._is_int_like("decimal:1234") is True
        assert binja_mcp_bridge._is_int_like("d:1234") is True

    def test_with_underscores(self):
        assert binja_mcp_bridge._is_int_like("1_000_000") is True
        assert binja_mcp_bridge._is_int_like("0x1234_5678") is True

    def test_with_sign(self):
        assert binja_mcp_bridge._is_int_like("+123") is True
        assert binja_mcp_bridge._is_int_like("-456") is True

    def test_function_names_are_not_int_like(self):
        assert binja_mcp_bridge._is_int_like("main") is False
        assert binja_mcp_bridge._is_int_like("sub_401000") is False
        assert binja_mcp_bridge._is_int_like("_start") is False
        assert binja_mcp_bridge._is_int_like("MyFunction") is False

    def test_empty_and_none(self):
        assert binja_mcp_bridge._is_int_like("") is False
        assert binja_mcp_bridge._is_int_like("   ") is False

    def test_pure_hex_digits(self):
        # Pure hex digits without prefix are considered int-like
        assert binja_mcp_bridge._is_int_like("abcd") is True
        assert binja_mcp_bridge._is_int_like("DEAD") is True
        assert binja_mcp_bridge._is_int_like("BEEF") is True

    def test_mixed_content(self):
        # Contains non-hex characters
        assert binja_mcp_bridge._is_int_like("hello") is False
        assert binja_mcp_bridge._is_int_like("test123") is False
        assert binja_mcp_bridge._is_int_like("0xGHIJ") is False
