"""Shared pytest fixtures for MCP bridge testing."""

import pytest
import responses

# Default test server URL
TEST_SERVER_URL = "http://localhost:9009"


@pytest.fixture
def mock_server():
    """Fixture that provides a mocked HTTP server using responses library."""
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def sample_strings():
    """Sample string data for testing."""
    return [
        {
            "address": "0x400208",
            "length": 5,
            "type": "StringType.AsciiString",
            "value": ".text",
        },
        {
            "address": "0x687d1c",
            "length": 14,
            "type": "StringType.AsciiString",
            "value": "GetWindowTextA",
        },
        {
            "address": "0x687dbe",
            "length": 14,
            "type": "StringType.AsciiString",
            "value": "SetWindowTextA",
        },
    ]


@pytest.fixture
def sample_functions():
    """Sample function data for testing."""
    return [
        {"name": "sub_401000", "address": "0x401000", "raw_name": "sub_401000"},
        {"name": "sub_401130", "address": "0x401130", "raw_name": "sub_401130"},
        {"name": "main", "address": "0x401500", "raw_name": "main"},
    ]


@pytest.fixture
def sample_types():
    """Sample type data for testing."""
    return [
        {"name": "DWORD", "declaration": "typedef uint32_t DWORD;"},
        {"name": "HANDLE", "declaration": "typedef void* HANDLE;"},
    ]


@pytest.fixture
def sample_status():
    """Sample binary status for testing."""
    return {
        "filename": "test_binary.exe",
        "status": "loaded",
        "arch": "x86_64",
        "platform": "windows",
    }


def add_json_response(rsps, method, endpoint, json_data, status=200):
    """Helper to add a JSON response to the mock server."""
    rsps.add(
        method,
        f"{TEST_SERVER_URL}/{endpoint}",
        json=json_data,
        status=status,
        content_type="application/json",
    )


def add_text_response(rsps, method, endpoint, text, status=200):
    """Helper to add a text response to the mock server."""
    rsps.add(
        method,
        f"{TEST_SERVER_URL}/{endpoint}",
        body=text,
        status=status,
        content_type="text/plain",
    )


@pytest.fixture
def add_json():
    """Fixture that provides the add_json_response helper."""
    return add_json_response


@pytest.fixture
def add_text():
    """Fixture that provides the add_text_response helper."""
    return add_text_response


# =============================================================================
# Test Binary Fixture Data
# =============================================================================
# These fixtures provide sample data that matches the purpose-built test binary
# located at tests/fixtures/test_binary

@pytest.fixture
def test_binary_functions():
    """Sample function data matching tests/fixtures/test_binary."""
    return [
        {"name": "main", "address": "0x1540", "raw_name": "main"},
        {"name": "helper_add", "address": "0x1199", "raw_name": "helper_add"},
        {"name": "helper_calculate", "address": "0x11b8", "raw_name": "helper_calculate"},
        {"name": "helper_print_string", "address": "0x11f2", "raw_name": "helper_print_string"},
        {"name": "helper_init_record", "address": "0x1226", "raw_name": "helper_init_record"},
        {"name": "helper_status_to_string", "address": "0x127c", "raw_name": "helper_status_to_string"},
        {"name": "helper_dump_value", "address": "0x12c8", "raw_name": "helper_dump_value"},
        {"name": "process_loop_simple", "address": "0x1328", "raw_name": "process_loop_simple"},
        {"name": "process_loop_nested", "address": "0x1358", "raw_name": "process_loop_nested"},
        {"name": "process_conditional", "address": "0x13a0", "raw_name": "process_conditional"},
        {"name": "process_switch", "address": "0x13d0", "raw_name": "process_switch"},
        {"name": "process_many_locals", "address": "0x1420", "raw_name": "process_many_locals"},
    ]


@pytest.fixture
def test_binary_strings():
    """Sample string data matching tests/fixtures/test_binary."""
    return [
        {"value": "UNIQUE_MARKER_ALPHA_12345", "type": "StringType.AsciiString"},
        {"value": "UNIQUE_MARKER_BETA_67890", "type": "StringType.AsciiString"},
        {"value": "Global string pointer for testing", "type": "StringType.AsciiString"},
        {"value": "Static string in data section", "type": "StringType.AsciiString"},
        {"value": "Binary Ninja MCP Test Binary", "type": "StringType.AsciiString"},
        {"value": "OK", "type": "StringType.AsciiString"},
        {"value": "ERROR", "type": "StringType.AsciiString"},
        {"value": "PENDING", "type": "StringType.AsciiString"},
        {"value": "TIMEOUT", "type": "StringType.AsciiString"},
    ]


@pytest.fixture
def test_binary_types():
    """Sample type data matching tests/fixtures/test_binary."""
    return [
        {"name": "StatusCode", "declaration": "enum StatusCode { STATUS_OK = 0, STATUS_ERROR = 1, STATUS_PENDING = 2, STATUS_TIMEOUT = 3 };"},
        {"name": "TestRecord", "declaration": "struct TestRecord { int32_t id; char name[32]; StatusCode status; uint32_t flags; };"},
        {"name": "TestContainer", "declaration": "struct TestContainer { TestRecord record; void* data; size_t data_size; struct { uint8_t priority; uint8_t reserved[3]; } metadata; };"},
        {"name": "ValueUnion", "declaration": "union ValueUnion { uint32_t as_u32; int32_t as_i32; float as_float; uint8_t as_bytes[4]; };"},
        {"name": "ProcessCallback", "declaration": "typedef int (*ProcessCallback)(TestRecord*, void*);"},
    ]


@pytest.fixture
def test_binary_status():
    """Sample binary status for test_binary."""
    return {
        "filename": "test_binary",
        "loaded": True,
        "arch": "x86_64",
        "platform": "linux",
        "entry_point": "0x10e0",
    }


@pytest.fixture
def test_binary_imports():
    """Sample imports from tests/fixtures/test_binary."""
    return [
        {"name": "printf", "address": "0x1040"},
        {"name": "malloc", "address": "0x1050"},
        {"name": "free", "address": "0x1060"},
        {"name": "memset", "address": "0x1070"},
        {"name": "strncpy", "address": "0x1080"},
        {"name": "strlen", "address": "0x1090"},
    ]


@pytest.fixture
def test_binary_globals():
    """Sample global data from tests/fixtures/test_binary."""
    return [
        {"name": "g_global_counter", "value": "0x12345678", "type": "uint32_t"},
        {"name": "g_signed_value", "value": "-42", "type": "int32_t"},
        {"name": "g_large_value", "value": "0xDEADBEEFCAFEBABE", "type": "uint64_t"},
        {"name": "g_test_string_ptr", "type": "char*"},
        {"name": "g_byte_array", "type": "uint8_t[16]"},
    ]
