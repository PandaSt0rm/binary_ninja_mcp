"""Tests for HTTP request functions in the bridge."""

import responses
from binary_ninja_mcp.bridge import binja_mcp_bridge

SERVER_URL = "http://localhost:9009"


class TestGetJson:
    """Tests for get_json HTTP function."""

    @responses.activate
    def test_returns_parsed_json_on_success(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/test",
            json={"key": "value", "count": 42},
            status=200,
        )

        result = binja_mcp_bridge.get_json("test")

        assert result == {"key": "value", "count": 42}

    @responses.activate
    def test_returns_error_dict_on_4xx(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/test",
            json={"error": "Not found"},
            status=404,
        )

        result = binja_mcp_bridge.get_json("test")

        assert result["error"] == "Not found"
        assert result["status"] == 404

    @responses.activate
    def test_returns_error_dict_on_5xx(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/test",
            json={"error": "Internal error"},
            status=500,
        )

        result = binja_mcp_bridge.get_json("test")

        assert "error" in result
        assert result["status"] == 500

    @responses.activate
    def test_synthesizes_error_for_non_json_error_response(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/test",
            body="Server Error",
            status=500,
        )

        result = binja_mcp_bridge.get_json("test")

        assert "error" in result
        assert "500" in result["error"]

    @responses.activate
    def test_handles_empty_response(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/test",
            body="",
            status=200,
        )

        result = binja_mcp_bridge.get_json("test")

        # Empty response can't be parsed as JSON
        assert result is None

    @responses.activate
    def test_passes_query_params(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/test",
            json={"result": "ok"},
            status=200,
        )

        result = binja_mcp_bridge.get_json("test", {"offset": 10, "limit": 50})

        assert result == {"result": "ok"}
        # Verify params were sent
        assert "offset=10" in responses.calls[0].request.url
        assert "limit=50" in responses.calls[0].request.url

    @responses.activate
    def test_handles_connection_error(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/test",
            body=responses.ConnectionError("Connection refused"),
        )

        result = binja_mcp_bridge.get_json("test")

        assert "error" in result
        assert "Request failed" in result["error"]


class TestPostJson:
    """Tests for post_json HTTP function."""

    @responses.activate
    def test_returns_parsed_json_on_success(self):
        responses.add(
            responses.POST,
            f"{SERVER_URL}/test",
            json={"status": "created"},
            status=201,
        )

        result = binja_mcp_bridge.post_json("test", {"data": "value"})

        assert result == {"status": "created"}

    @responses.activate
    def test_returns_error_dict_on_failure(self):
        responses.add(
            responses.POST,
            f"{SERVER_URL}/test",
            json={"error": "Bad request"},
            status=400,
        )

        result = binja_mcp_bridge.post_json("test", {"data": "invalid"})

        assert "error" in result
        assert result["status"] == 400

    @responses.activate
    def test_handles_string_data(self):
        responses.add(
            responses.POST,
            f"{SERVER_URL}/test",
            json={"status": "ok"},
            status=200,
        )

        result = binja_mcp_bridge.post_json("test", "raw string data")

        assert result == {"status": "ok"}


class TestGetText:
    """Tests for get_text HTTP function."""

    @responses.activate
    def test_returns_text_on_success(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/test",
            body="Hello World",
            status=200,
        )

        result = binja_mcp_bridge.get_text("test")

        assert result == "Hello World"

    @responses.activate
    def test_returns_error_string_on_failure(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/test",
            body="Not Found",
            status=404,
        )

        result = binja_mcp_bridge.get_text("test")

        assert "Error 404" in result

    @responses.activate
    def test_handles_multiline_text(self):
        multiline = "Line 1\nLine 2\nLine 3"
        responses.add(
            responses.GET,
            f"{SERVER_URL}/test",
            body=multiline,
            status=200,
        )

        result = binja_mcp_bridge.get_text("test")

        assert result == multiline

    @responses.activate
    def test_passes_query_params(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/test",
            body="result",
            status=200,
        )

        binja_mcp_bridge.get_text("test", {"address": "0x1000"})

        assert "address=0x1000" in responses.calls[0].request.url


class TestSafeGet:
    """Tests for safe_get HTTP function (returns list of lines)."""

    @responses.activate
    def test_returns_lines_on_success(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/test",
            body="Line 1\nLine 2\nLine 3",
            status=200,
        )

        result = binja_mcp_bridge.safe_get("test")

        assert result == ["Line 1", "Line 2", "Line 3"]

    @responses.activate
    def test_returns_error_list_on_failure(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/test",
            body="Server Error",
            status=500,
        )

        result = binja_mcp_bridge.safe_get("test")

        assert len(result) == 1
        assert "Error 500" in result[0]

    @responses.activate
    def test_handles_empty_response(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/test",
            body="",
            status=200,
        )

        result = binja_mcp_bridge.safe_get("test")

        # "".splitlines() returns [] not [""]
        assert result == []


class TestRetryBehavior:
    """Tests for retry behavior on busy responses."""

    @responses.activate
    def test_retries_on_503(self):
        # First call returns 503, second succeeds
        responses.add(
            responses.GET,
            f"{SERVER_URL}/test",
            json={"error": "Server busy"},
            status=503,
            headers={"Retry-After": "0"},
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/test",
            json={"result": "ok"},
            status=200,
        )

        result = binja_mcp_bridge.get_json("test")

        # Should have made 2 requests
        assert len(responses.calls) == 2
        assert result == {"result": "ok"}

    @responses.activate
    def test_no_retry_on_429(self):
        # 429 is NOT retried (only 503 is retried)
        responses.add(
            responses.GET,
            f"{SERVER_URL}/test",
            json={"error": "Rate limited"},
            status=429,
        )

        result = binja_mcp_bridge.get_json("test")

        # Should only make 1 request (no retry for 429)
        assert len(responses.calls) == 1
        assert result["error"] == "Rate limited"
        assert result["status"] == 429


class TestTimeoutBehavior:
    """Tests for timeout handling."""

    @responses.activate
    def test_custom_timeout_is_used(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/test",
            json={"result": "ok"},
            status=200,
        )

        # Should not raise with reasonable timeout
        result = binja_mcp_bridge.get_json("test", timeout=30)

        assert result == {"result": "ok"}

    @responses.activate
    def test_none_timeout_for_long_operations(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/test",
            json={"result": "ok"},
            status=200,
        )

        # None timeout should be allowed for long operations
        result = binja_mcp_bridge.get_json("test", timeout=None)

        assert result == {"result": "ok"}
