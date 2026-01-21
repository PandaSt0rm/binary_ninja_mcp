"""Tests for URL encoding edge cases in HTTP requests."""

import re
import urllib.parse

import responses
from binary_ninja_mcp.bridge import binja_mcp_bridge

SERVER_URL = "http://localhost:9009"


class TestUrlEncodingInQueries:
    """Tests for URL encoding of query parameters."""

    @responses.activate
    def test_filter_with_spaces(self):
        """Spaces should be URL-encoded as + or %20."""
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            re.compile(rf"{SERVER_URL}/strings/filter\?.*"),
            json={"strings": [], "total": 0},
            status=200,
        )

        result = binja_mcp_bridge.list_strings_filter(filter="hello world")

        assert result["ok"] is True
        # Check the request was made with proper encoding
        assert len(responses.calls) == 2
        request_url = responses.calls[1].request.url
        # Spaces should be encoded as + or %20
        assert "hello+world" in request_url or "hello%20world" in request_url

    @responses.activate
    def test_filter_with_ampersand(self):
        """Ampersands should be URL-encoded as %26."""
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            re.compile(rf"{SERVER_URL}/strings/filter\?.*"),
            json={"strings": [], "total": 0},
            status=200,
        )

        result = binja_mcp_bridge.list_strings_filter(filter="foo&bar")

        assert result["ok"] is True
        request_url = responses.calls[1].request.url
        assert "foo%26bar" in request_url

    @responses.activate
    def test_filter_with_equals_sign(self):
        """Equals signs should be URL-encoded as %3D."""
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            re.compile(rf"{SERVER_URL}/strings/filter\?.*"),
            json={"strings": [], "total": 0},
            status=200,
        )

        result = binja_mcp_bridge.list_strings_filter(filter="a=b")

        assert result["ok"] is True
        request_url = responses.calls[1].request.url
        assert "a%3Db" in request_url

    @responses.activate
    def test_filter_with_percent_sign(self):
        """Percent signs should be URL-encoded as %25."""
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            re.compile(rf"{SERVER_URL}/strings/filter\?.*"),
            json={"strings": [], "total": 0},
            status=200,
        )

        result = binja_mcp_bridge.list_strings_filter(filter="%d")

        assert result["ok"] is True
        request_url = responses.calls[1].request.url
        assert "%25d" in request_url

    @responses.activate
    def test_filter_with_plus_sign(self):
        """Plus signs should be URL-encoded as %2B."""
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            re.compile(rf"{SERVER_URL}/strings/filter\?.*"),
            json={"strings": [], "total": 0},
            status=200,
        )

        result = binja_mcp_bridge.list_strings_filter(filter="a+b")

        assert result["ok"] is True
        request_url = responses.calls[1].request.url
        assert "a%2Bb" in request_url

    @responses.activate
    def test_filter_with_hash_sign(self):
        """Hash signs should be URL-encoded as %23."""
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            re.compile(rf"{SERVER_URL}/strings/filter\?.*"),
            json={"strings": [], "total": 0},
            status=200,
        )

        result = binja_mcp_bridge.list_strings_filter(filter="#define")

        assert result["ok"] is True
        request_url = responses.calls[1].request.url
        assert "%23define" in request_url

    @responses.activate
    def test_filter_with_unicode(self):
        """Unicode characters should be properly encoded."""
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            re.compile(rf"{SERVER_URL}/strings/filter\?.*"),
            json={"strings": [], "total": 0},
            status=200,
        )

        result = binja_mcp_bridge.list_strings_filter(filter="日本語")

        assert result["ok"] is True

    @responses.activate
    def test_search_query_with_special_chars(self):
        """Search queries with special characters should be encoded."""
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            re.compile(rf"{SERVER_URL}/searchFunctions\?.*"),
            json={"matches": []},
            status=200,
        )

        result = binja_mcp_bridge.search_functions_by_name(query="operator+")

        assert result["ok"] is True
        request_url = responses.calls[1].request.url
        assert "operator%2B" in request_url

    @responses.activate
    def test_search_query_with_brackets(self):
        """Search queries with brackets should be encoded."""
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            re.compile(rf"{SERVER_URL}/searchFunctions\?.*"),
            json={"matches": []},
            status=200,
        )

        result = binja_mcp_bridge.search_functions_by_name(query="func[0]")

        assert result["ok"] is True

    @responses.activate
    def test_type_query_with_angle_brackets(self):
        """Type queries with angle brackets should be encoded."""
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            re.compile(rf"{SERVER_URL}/searchTypes\?.*"),
            json={"types": [], "total": 0},
            status=200,
        )

        result = binja_mcp_bridge.search_types(query="vector<int>")

        assert result["ok"] is True
        request_url = responses.calls[1].request.url
        # < and > should be encoded
        assert "%3C" in request_url  # <
        assert "%3E" in request_url  # >


class TestUrlEncodingHelpers:
    """Tests for URL encoding utility behavior."""

    def test_urlencode_with_doseq(self):
        """Verify urlencode with doseq=True works correctly."""
        params = {"offset": 0, "limit": 100, "filter": "hello world"}
        result = urllib.parse.urlencode(params, doseq=True)

        # Should produce a valid query string
        assert "offset=0" in result
        assert "limit=100" in result
        assert "filter=hello" in result  # Space will be encoded

    def test_urlencode_preserves_order(self):
        """Verify parameter order is preserved."""
        params = {"a": 1, "b": 2, "c": 3}
        result = urllib.parse.urlencode(params, doseq=True)

        # Python 3.7+ dicts maintain insertion order
        parts = result.split("&")
        assert parts[0].startswith("a=")
        assert parts[1].startswith("b=")
        assert parts[2].startswith("c=")

    def test_urlencode_handles_empty_values(self):
        """Verify empty values are handled correctly."""
        params = {"filter": "", "offset": 0}
        result = urllib.parse.urlencode(params, doseq=True)

        assert "filter=" in result
        assert "offset=0" in result


class TestUrlDecodingOnServer:
    """Tests verifying server-side decoding expectations."""

    def test_parse_qsl_decodes_plus_as_space(self):
        """parse_qsl should decode + as space."""
        query = "filter=hello+world"
        params = dict(urllib.parse.parse_qsl(query))
        assert params["filter"] == "hello world"

    def test_parse_qsl_decodes_percent_encoding(self):
        """parse_qsl should decode percent-encoded characters."""
        query = "filter=hello%20world"
        params = dict(urllib.parse.parse_qsl(query))
        assert params["filter"] == "hello world"

    def test_parse_qsl_decodes_special_chars(self):
        """parse_qsl should decode various special characters."""
        query = "filter=%25d%26%3D"  # %d & =
        params = dict(urllib.parse.parse_qsl(query))
        assert params["filter"] == "%d&="

    def test_roundtrip_encoding(self):
        """Verify encoding and decoding round-trip correctly."""
        original = "hello world & foo=bar %d"
        encoded = urllib.parse.urlencode({"filter": original})
        decoded = dict(urllib.parse.parse_qsl(encoded))
        assert decoded["filter"] == original
