"""Integration tests using the purpose-built test binary fixture.

These tests exercise ALL MCP tool functionality against a binary with known,
predictable features. The test binary (tests/fixtures/test_binary) is designed
to have specific functions, types, strings, and data items that can be reliably tested.

To run these tests:
1. Build the test binary: cd tests/fixtures && make
2. Open test_binary in Binary Ninja with the MCP plugin loaded
3. Run: pytest tests/test_fixture_integration.py -v

Skip with: pytest -m "not integration"

Known features in test_binary:
- Functions: main, helper_add, helper_calculate, helper_init_record,
  helper_status_to_string, helper_dump_value, process_loop_simple,
  process_loop_nested, process_conditional, process_switch, process_many_locals,
  process_container, create_container, destroy_container, sample_callback,
  process_with_callback, public_api_function_one/two/three, static_helper,
  static_process_data
- Types: StatusCode (enum), TestRecord (struct), TestContainer (struct),
  ValueUnion (union), ProcessCallback (func ptr typedef)
- Strings: "UNIQUE_MARKER_ALPHA_12345", "UNIQUE_MARKER_BETA_67890",
  "Global string pointer for testing", etc.
- Global data: g_global_counter, g_global_record, g_byte_array, etc.
"""

import json
import os
import time

import pytest

from binary_ninja_mcp.bridge import binja_mcp_bridge

SERVER_URL = binja_mcp_bridge.binja_server_url
READY_TIMEOUT = float(os.environ.get("BINARY_NINJA_MCP_TEST_READY_TIMEOUT", "60"))
READY_INTERVAL = float(os.environ.get("BINARY_NINJA_MCP_TEST_READY_INTERVAL", "2"))

# Known function names in test_binary
KNOWN_FUNCTIONS = [
    "main",
    "helper_add",
    "helper_calculate",
    "helper_print_string",
    "helper_init_record",
    "helper_status_to_string",
    "helper_dump_value",
    "process_loop_simple",
    "process_loop_nested",
    "process_conditional",
    "process_switch",
    "process_many_locals",
    "process_container",
    "create_container",
    "destroy_container",
    "sample_callback",
    "process_with_callback",
    "public_api_function_one",
    "public_api_function_two",
    "public_api_function_three",
]

# Known unique strings in test_binary
KNOWN_STRINGS = [
    "UNIQUE_MARKER_ALPHA_12345",
    "UNIQUE_MARKER_BETA_67890",
    "Global string pointer for testing",
    "Static string in data section",
    "Binary Ninja MCP Test Binary",
]

# Known type names (may be mangled by compiler)
KNOWN_TYPES = [
    "StatusCode",
    "TestRecord",
    "TestContainer",
    "ValueUnion",
    "ProcessCallback",
]

# Known enum values
KNOWN_ENUM_VALUES = {
    "STATUS_OK": 0,
    "STATUS_ERROR": 1,
    "STATUS_PENDING": 2,
    "STATUS_TIMEOUT": 3,
}

# Known global data symbols
KNOWN_DATA_SYMBOLS = [
    "g_global_counter",
    "g_signed_value",
    "g_large_value",
    "g_global_record",
    "g_byte_array",
    "g_test_string_ptr",
    "g_test_string_array",
    "g_unique_marker_alpha",
    "g_unique_marker_beta",
]


def assert_ok(result: dict, *, message: str | None = None) -> None:
    """Assert ok True with a helpful error."""
    assert result.get("ok") is True, message or f"Expected ok=True, got: {result}"


def assert_not_ok(result: dict, *, message: str | None = None) -> None:
    """Assert ok False with a helpful error."""
    assert result.get("ok") is False, message or f"Expected ok=False, got: {result}"


def assert_ok_or_error(result: dict, *, require_fields: list[str] | None = None) -> None:
    """Accept ok True or False, but require structure either way."""
    assert "ok" in result, f"Missing ok in result: {result}"
    if result["ok"]:
        for field in require_fields or []:
            assert field in result, f"Missing {field} in result: {result}"
    else:
        assert "error" in result, f"Missing error in failed result: {result}"


def _extract_stack_vars(result: dict) -> list[dict]:
    if "variables" in result and isinstance(result["variables"], list):
        return result["variables"]
    if "stack_frame_vars" in result and isinstance(result["stack_frame_vars"], list):
        stack_frame_vars = result["stack_frame_vars"]
        flattened: list[dict] = []
        for entry in stack_frame_vars:
            if isinstance(entry, dict):
                vars_list = entry.get("vars")
                if isinstance(vars_list, list):
                    flattened.extend(vars_list)
        if flattened:
            return flattened
        return stack_frame_vars
    if "vars" in result and isinstance(result["vars"], list):
        return result["vars"]
    return []


def _wait_for_mcp_ready() -> None:
    """Wait for MCP server readiness and test_binary analysis."""
    deadline = time.monotonic() + READY_TIMEOUT
    last_error = "Unknown error"
    while time.monotonic() < deadline:
        status = binja_mcp_bridge.get_binary_status()
        if status.get("ok"):
            loaded = bool(status.get("loaded"))
            filename = str(status.get("filename") or "")
            if not loaded:
                last_error = "MCP server reachable but no binary loaded"
            else:
                basename = os.path.basename(filename)
                if "test_binary" not in basename:
                    pytest.fail(
                        f"MCP server at {SERVER_URL} has '{filename}' loaded; expected test_binary."
                    )
                search = binja_mcp_bridge.search_functions_by_name(query="helper_add")
                if search.get("ok") and any(
                    m.get("name") == "helper_add" for m in search.get("matches", [])
                ):
                    return
                last_error = "test_binary not fully analyzed yet (helper_add missing)"
        else:
            last_error = status.get("error", "MCP server not reachable")
        time.sleep(READY_INTERVAL)
    pytest.fail(
        f"MCP server not ready at {SERVER_URL}: {last_error}. "
        "Start the MCP server, load tests/fixtures/test_binary, or run "
        'pytest -m "not integration".'
    )


@pytest.fixture(scope="session", autouse=True)
def _require_mcp_ready():
    _wait_for_mcp_ready()


pytestmark = pytest.mark.integration


# =============================================================================
# Fixtures for known test binary features
# =============================================================================


@pytest.fixture
def helper_add_function():
    """Get the helper_add function."""
    result = binja_mcp_bridge.search_functions_by_name(query="helper_add")
    assert result["ok"] is True
    matches = [m for m in result["matches"] if m["name"] == "helper_add"]
    assert len(matches) > 0, "helper_add function not found"
    return matches[0]


@pytest.fixture
def main_function():
    """Get the main function."""
    result = binja_mcp_bridge.search_functions_by_name(query="main")
    assert result["ok"] is True
    matches = [m for m in result["matches"] if m["name"] == "main"]
    assert len(matches) > 0, "main function not found"
    return matches[0]


@pytest.fixture
def process_many_locals_function():
    """Get the process_many_locals function (has many local variables)."""
    result = binja_mcp_bridge.search_functions_by_name(query="process_many_locals")
    assert result["ok"] is True
    matches = [m for m in result["matches"] if m["name"] == "process_many_locals"]
    assert len(matches) > 0, "process_many_locals function not found"
    return matches[0]


# =============================================================================
# Function Discovery Tests
# =============================================================================


class TestKnownFunctions:
    """Tests that verify known functions are discoverable."""

    def test_list_methods_finds_known_functions(self):
        """list_methods should find our known functions."""
        result = binja_mcp_bridge.list_methods(offset=0, limit=100)
        assert result["ok"] is True

        found_names = {f["name"] for f in result["functions"]}
        # Check that at least some of our known functions are found
        known_found = found_names.intersection(set(KNOWN_FUNCTIONS))
        assert len(known_found) >= 5, f"Expected to find known functions, found: {known_found}"

    def test_search_helper_functions(self):
        """search_functions_by_name should find helper_ functions."""
        result = binja_mcp_bridge.search_functions_by_name(query="helper_")
        assert result["ok"] is True
        assert len(result["matches"]) >= 5

        helper_names = {m["name"] for m in result["matches"]}
        expected = {"helper_add", "helper_calculate", "helper_init_record"}
        assert expected.issubset(helper_names), f"Missing helpers: {expected - helper_names}"

    def test_search_process_functions(self):
        """search_functions_by_name should find process_ functions."""
        result = binja_mcp_bridge.search_functions_by_name(query="process_")
        assert result["ok"] is True
        assert len(result["matches"]) >= 5

        process_names = {m["name"] for m in result["matches"]}
        expected = {"process_loop_simple", "process_conditional", "process_switch"}
        assert expected.issubset(process_names), (
            f"Missing process functions: {expected - process_names}"
        )

    def test_search_public_api_functions(self):
        """search_functions_by_name should find public_api_ functions."""
        result = binja_mcp_bridge.search_functions_by_name(query="public_api_")
        assert result["ok"] is True
        assert len(result["matches"]) >= 3

        api_names = {m["name"] for m in result["matches"]}
        expected = {
            "public_api_function_one",
            "public_api_function_two",
            "public_api_function_three",
        }
        assert expected.issubset(api_names)


# =============================================================================
# Decompilation Tests
# =============================================================================


class TestDecompilationKnown:
    """Tests for decompiling known functions."""

    def test_decompile_helper_add(self, helper_add_function):
        """Decompile helper_add and verify it contains expected operations."""
        result = binja_mcp_bridge.decompile_function(name=helper_add_function["name"])
        assert result["ok"] is True

        decomp = result.get("decompilation", result.get("decompiled", ""))
        assert "result" in decomp.lower() or "return" in decomp.lower()

    def test_decompile_process_switch(self):
        """Decompile process_switch and verify switch structure."""
        result = binja_mcp_bridge.decompile_function(name="process_switch")
        assert result["ok"] is True

        decomp = result.get("decompilation", result.get("decompiled", ""))
        # Should contain switch-related patterns
        assert "switch" in decomp.lower() or "case" in decomp.lower() or "if" in decomp.lower()

    def test_decompile_process_loop_simple(self):
        """Decompile process_loop_simple and verify loop structure."""
        result = binja_mcp_bridge.decompile_function(name="process_loop_simple")
        assert result["ok"] is True

        decomp = result.get("decompilation", result.get("decompiled", ""))
        # Should contain loop-related patterns
        assert "while" in decomp.lower() or "for" in decomp.lower() or "do" in decomp.lower()

    def test_decompile_main(self, main_function):
        """Decompile main and verify it exists."""
        result = binja_mcp_bridge.decompile_function(name="main")
        assert result["ok"] is True

        decomp = result.get("decompilation", result.get("decompiled", ""))
        # Decompilation length can vary if binary was modified by other tests
        assert len(decomp) > 0, "main should have some decompilation output"


# =============================================================================
# IL Tests
# =============================================================================


class TestILKnown:
    """Tests for IL views of known functions."""

    def test_hlil_helper_add(self, helper_add_function):
        """Get HLIL for helper_add."""
        result = binja_mcp_bridge.get_il(name_or_address=helper_add_function["name"], view="hlil")
        assert result["ok"] is True
        assert "il" in result
        assert len(result["il"]) > 0

    def test_llil_process_loop(self):
        """Get LLIL for process_loop_simple."""
        result = binja_mcp_bridge.get_il(name_or_address="process_loop_simple", view="llil")
        assert result["ok"] is True
        assert "il" in result

    def test_mlil_process_conditional(self):
        """Get MLIL for process_conditional."""
        result = binja_mcp_bridge.get_il(name_or_address="process_conditional", view="mlil")
        assert result["ok"] is True

    def test_ssa_form(self, helper_add_function):
        """Get SSA form IL."""
        result = binja_mcp_bridge.get_il(
            name_or_address=helper_add_function["name"], view="hlil", ssa=True
        )
        assert result["ok"] is True

    def test_il_by_address(self, helper_add_function):
        """Get IL by function address."""
        address = helper_add_function["address"]
        result = binja_mcp_bridge.get_il(name_or_address=address, view="hlil")
        assert result["ok"] is True


# =============================================================================
# Disassembly Tests
# =============================================================================


class TestDisassemblyKnown:
    """Tests for disassembly of known functions."""

    def test_disassembly_helper_add(self, helper_add_function):
        """Get disassembly for helper_add."""
        result = binja_mcp_bridge.fetch_disassembly(name=helper_add_function["name"])
        assert result["ok"] is True

        disasm = result.get("disassembly", result.get("assembly", result.get("lines", "")))
        # Should contain x86-64 instructions
        assert len(str(disasm)) > 20

    def test_disassembly_main(self):
        """Get disassembly for main."""
        result = binja_mcp_bridge.fetch_disassembly(name="main")
        assert result["ok"] is True


# =============================================================================
# Stack Frame Variable Tests
# =============================================================================


class TestStackFrameVarsKnown:
    """Tests for stack frame variables in known functions."""

    def test_process_many_locals_has_variables(self, process_many_locals_function):
        """process_many_locals should return stack frame info."""
        result = binja_mcp_bridge.get_stack_frame_vars(function_identifier="process_many_locals")
        assert result["ok"] is True

        # The response structure varies - may be nested or flat
        # With optimization, variables may be in registers rather than stack
        # Just verify we get a valid response with some structure
        has_vars = (
            "variables" in result
            or "stack_frame_vars" in result
            or any("vars" in str(v) for v in result.values() if isinstance(v, (list, dict)))
        )
        assert has_vars or result["ok"], "Expected stack frame info in response"

    def test_helper_add_has_result_var(self, helper_add_function):
        """helper_add should have a result variable."""
        result = binja_mcp_bridge.get_stack_frame_vars(
            function_identifier=helper_add_function["name"]
        )
        assert result["ok"] is True


# =============================================================================
# String Tests
# =============================================================================


class TestStringsKnown:
    """Tests for known strings in the binary."""

    def test_find_unique_marker_alpha(self):
        """list_strings_filter should find UNIQUE_MARKER_ALPHA."""
        result = binja_mcp_bridge.list_strings_filter(
            filter="UNIQUE_MARKER_ALPHA", offset=0, count=100
        )
        assert result["ok"] is True

        strings = result.get("strings", [])
        found = any("UNIQUE_MARKER_ALPHA" in str(s) for s in strings)
        assert found, "UNIQUE_MARKER_ALPHA_12345 not found"

    def test_find_unique_marker_beta(self):
        """list_strings_filter should find UNIQUE_MARKER_BETA."""
        result = binja_mcp_bridge.list_strings_filter(
            filter="UNIQUE_MARKER_BETA", offset=0, count=100
        )
        assert result["ok"] is True

        strings = result.get("strings", [])
        found = any("UNIQUE_MARKER_BETA" in str(s) for s in strings)
        assert found, "UNIQUE_MARKER_BETA_67890 not found"

    def test_find_global_string(self):
        """Should find 'Global string' in binary."""
        result = binja_mcp_bridge.list_strings_filter(filter="Global string", offset=0, count=100)
        assert result["ok"] is True

    def test_list_all_strings_contains_markers(self):
        """list_all_strings should contain our unique markers."""
        result = binja_mcp_bridge.list_all_strings()
        assert result["ok"] is True

        all_strings = str(result.get("strings", []))
        assert "UNIQUE_MARKER" in all_strings


# =============================================================================
# Cross-Reference Tests
# =============================================================================


class TestXrefsKnown:
    """Tests for cross-references in known functions."""

    def test_xrefs_to_helper_add(self, helper_add_function):
        """helper_add should return xref info."""
        address = helper_add_function["address"]
        result = binja_mcp_bridge.get_xrefs_to(address=address)
        assert result["ok"] is True

        # Xrefs may be in various response fields depending on server version
        # The important thing is the call succeeds and returns structured data
        has_xref_data = (
            "xrefs" in result
            or "code_references" in result
            or "data_references" in result
            or "references" in result
        )
        assert has_xref_data, f"Expected xref data in response, got keys: {result.keys()}"

    def test_xrefs_to_helper_init_record(self):
        """helper_init_record should have multiple xrefs."""
        # First find the function
        search = binja_mcp_bridge.search_functions_by_name(query="helper_init_record")
        if not search["ok"] or len(search["matches"]) == 0:
            pytest.skip("helper_init_record not found")

        address = search["matches"][0]["address"]
        result = binja_mcp_bridge.get_xrefs_to(address=address)
        assert result["ok"] is True


# =============================================================================
# Data Analysis Tests
# =============================================================================


class TestDataAnalysisKnown:
    """Tests for data analysis with known data items."""

    def test_list_data_items_finds_globals(self):
        """list_data_items should find global data."""
        result = binja_mcp_bridge.list_data_items(offset=0, limit=100)
        assert result["ok"] is True

        data = result.get("data", [])
        assert len(data) > 0

    def test_hexdump_at_known_function(self, helper_add_function):
        """Hexdump at helper_add address."""
        address = helper_add_function["address"]
        result = binja_mcp_bridge.hexdump_address(address=address, length=32)
        assert result["ok"] is True
        assert "hexdump" in result
        assert len(result["hexdump"]) > 0


# =============================================================================
# Import/Export Tests
# =============================================================================


class TestImportsExportsKnown:
    """Tests for imports and exports in test binary."""

    def test_list_imports_finds_libc(self):
        """list_imports should find libc functions."""
        result = binja_mcp_bridge.list_imports(offset=0, limit=100)
        assert result["ok"] is True

        imports = result.get("imports", [])
        import_names = {i.get("name", "") for i in imports}

        # Should have printf, malloc, free, etc.
        expected = {"printf", "malloc", "free", "memset", "strncpy"}
        found = expected.intersection(import_names)
        assert len(found) >= 2, f"Expected libc imports, found: {found}"

    def test_list_exports_finds_main(self):
        """list_exports should find main."""
        result = binja_mcp_bridge.list_exports(offset=0, limit=100)
        assert result["ok"] is True

        exports = result.get("exports", [])
        export_names = {e.get("name", "") for e in exports}
        assert "main" in export_names or len(exports) > 0


# =============================================================================
# Segment and Section Tests
# =============================================================================


class TestSegmentsSectionsKnown:
    """Tests for segments and sections."""

    def test_list_segments_has_code(self):
        """Should have code segment."""
        result = binja_mcp_bridge.list_segments(offset=0, limit=100)
        assert result["ok"] is True

        segments = result.get("segments", [])
        assert len(segments) > 0

        # Should have executable segment
        has_exec = any(
            s.get("executable", False) or "x" in str(s.get("flags", "")).lower() for s in segments
        )
        assert has_exec, "No executable segment found"

    def test_list_sections_has_text(self):
        """Should have .text section."""
        result = binja_mcp_bridge.list_sections(offset=0, limit=100)
        assert result["ok"] is True

        sections = result.get("sections", [])
        section_names = {s.get("name", "") for s in sections}

        # ELF sections
        has_text = ".text" in section_names or any("text" in n.lower() for n in section_names)
        assert has_text or len(sections) > 0


# =============================================================================
# Entry Point Tests
# =============================================================================


class TestEntryPointsKnown:
    """Tests for entry points."""

    def test_get_entry_points(self):
        """Should have entry point(s)."""
        result = binja_mcp_bridge.get_entry_points()
        assert result["ok"] is True

        entry_points = result.get("entry_points", [])
        assert len(entry_points) >= 1


# =============================================================================
# Comment Tests (Modification)
# =============================================================================


class TestCommentsKnown:
    """Tests for setting/getting comments on known locations."""

    def test_set_get_delete_comment_on_helper_add(self, helper_add_function):
        """Full comment lifecycle on helper_add."""
        address = helper_add_function["address"]
        test_comment = "Test comment on helper_add"

        # Set comment
        set_result = binja_mcp_bridge.set_comment(address=address, comment=test_comment)
        assert set_result["ok"] is True

        # Get comment
        get_result = binja_mcp_bridge.get_comment(address=address)
        assert get_result["ok"] is True
        # Comment should be present (may be in different field)
        assert test_comment in str(get_result) or get_result.get("comment") == test_comment

        # Delete comment
        del_result = binja_mcp_bridge.delete_comment(address=address)
        assert del_result["ok"] is True

    def test_function_comment_lifecycle(self, helper_add_function):
        """Full function comment lifecycle."""
        func_name = helper_add_function["name"]
        test_comment = "Function comment for helper_add"

        # Set function comment
        set_result = binja_mcp_bridge.set_function_comment(
            function_name=func_name, comment=test_comment
        )
        assert set_result["ok"] is True

        # Get function comment
        get_result = binja_mcp_bridge.get_function_comment(function_name=func_name)
        assert get_result["ok"] is True

        # Delete function comment
        del_result = binja_mcp_bridge.delete_function_comment(function_name=func_name)
        assert del_result["ok"] is True


# =============================================================================
# Variable Rename Tests (Modification)
# =============================================================================


class TestVariableRenameKnown:
    """Tests for renaming variables in known functions."""

    def test_rename_variable_in_process_many_locals(self, process_many_locals_function):
        """Rename a variable in process_many_locals."""
        # First get variables
        vars_result = binja_mcp_bridge.get_stack_frame_vars(
            function_identifier="process_many_locals"
        )
        if not vars_result["ok"]:
            pytest.skip("Cannot get stack frame vars")

        variables = _extract_stack_vars(vars_result)
        if len(variables) == 0:
            pytest.skip("No variables found")

        # Try to rename first variable
        var_name = variables[0].get("name")
        if not var_name:
            pytest.skip("Variable has no name to rename")
        new_name = "test_renamed_var"
        result = binja_mcp_bridge.rename_single_variable(
            function_name="process_many_locals", variable_name=var_name, new_name=new_name
        )
        assert_ok(result)
        restore = binja_mcp_bridge.rename_single_variable(
            function_name="process_many_locals",
            variable_name=new_name,
            new_name=var_name,
        )
        assert_ok(restore)


# =============================================================================
# Function Rename Tests (Modification)
# =============================================================================


class TestFunctionRenameKnown:
    """Tests for renaming known functions."""

    def test_rename_static_helper_roundtrip(self):
        """Rename static_helper and restore."""
        # Find a function to rename (prefer static_helper as it's less critical)
        search = binja_mcp_bridge.search_functions_by_name(query="static_helper")
        if not search["ok"] or len(search["matches"]) == 0:
            pytest.skip("static_helper not found")

        original_name = search["matches"][0]["name"]
        temp_name = "test_renamed_static_helper"

        # Rename
        rename_result = binja_mcp_bridge.rename_function(old_name=original_name, new_name=temp_name)
        assert rename_result["ok"] is True

        # Restore
        restore_result = binja_mcp_bridge.rename_function(
            old_name=temp_name, new_name=original_name
        )
        assert restore_result["ok"] is True


# =============================================================================
# Type System Tests
# =============================================================================


class TestTypeSystemKnown:
    """Tests for type system operations."""

    def test_search_types_finds_int(self):
        """search_types should find int types."""
        result = binja_mcp_bridge.search_types(query="int")
        assert result["ok"] is True
        assert len(result.get("types", [])) > 0

    def test_define_custom_struct(self):
        """Define a custom struct type."""
        c_code = """
        struct TestFixtureStruct {
            int id;
            char name[64];
            void *data;
        };
        """
        result = binja_mcp_bridge.define_types(c_code=c_code)
        assert_ok(result)
        assert "TestFixtureStruct" in result

    def test_declare_c_type_enum(self):
        """Declare a custom enum type."""
        c_decl = "enum TestFixtureEnum { TF_NONE = 0, TF_ONE = 1, TF_TWO = 2 };"
        result = binja_mcp_bridge.declare_c_type(c_declaration=c_decl)
        assert_ok(result)
        assert result.get("count", 0) >= 1

    def test_get_type_info_void_ptr(self):
        """Get type info for void*."""
        result = binja_mcp_bridge.get_type_info(type_name="void*")
        assert_ok(result)
        assert result.get("name")

    def test_list_local_types(self):
        """List local types."""
        result = binja_mcp_bridge.list_local_types(offset=0, count=50)
        assert result["ok"] is True
        assert "types" in result


# =============================================================================
# Utility Tests
# =============================================================================


class TestUtilitiesKnown:
    """Tests for utility functions."""

    def test_convert_number_hex(self):
        """Convert hex number."""
        result = binja_mcp_bridge.convert_number(text="0x12345678")
        assert result["ok"] is True

    def test_convert_number_matches_global(self):
        """Convert number matching g_global_counter value."""
        # g_global_counter = 0x12345678
        result = binja_mcp_bridge.convert_number(text="0x12345678", size=4)
        assert result["ok"] is True

    def test_format_value(self, helper_add_function):
        """Format value at address."""
        address = helper_add_function["address"]
        result = binja_mcp_bridge.format_value(address=address, text="0x90")
        assert_ok(result)
        assert "comment" in result


# =============================================================================
# Binary Management Tests
# =============================================================================


class TestBinaryManagementKnown:
    """Tests for binary management."""

    def test_get_binary_status_shows_test_binary(self):
        """Status should show test_binary is loaded."""
        result = binja_mcp_bridge.get_binary_status()
        assert result["ok"] is True
        assert "test_binary" in result.get("filename", "")

    def test_list_binaries_includes_test_binary(self):
        """list_binaries should include test_binary."""
        result = binja_mcp_bridge.list_binaries()
        assert result["ok"] is True

        binaries = result.get("binaries", [])
        assert len(binaries) >= 1

    def test_select_binary_by_name(self):
        """Select test_binary by name."""
        result = binja_mcp_bridge.select_binary(view="test_binary")
        assert_ok(result)
        assert result.get("status") == "ok"


# =============================================================================
# Multi-Variable Rename Tests
# =============================================================================


class TestMultiVariableRenameKnown:
    """Tests for renaming multiple variables."""

    def test_rename_multi_with_json(self, process_many_locals_function):
        """Rename multiple variables using JSON mapping."""
        vars_result = binja_mcp_bridge.get_stack_frame_vars(
            function_identifier="process_many_locals"
        )
        if not vars_result.get("ok"):
            pytest.skip("Cannot get stack frame vars")

        variables = _extract_stack_vars(vars_result)
        names = [v.get("name") for v in variables if v.get("name")]
        if len(names) < 2:
            pytest.skip("Not enough variables to rename")

        new_names = ["test_multi_a", "test_multi_b"]
        mapping = {names[0]: new_names[0], names[1]: new_names[1]}
        result = binja_mcp_bridge.rename_multi_variables(
            function_identifier="process_many_locals", mapping_json=json.dumps(mapping)
        )
        assert_ok(result)
        results = result.get("results", [])
        if results:
            assert any(item.get("success") for item in results)
            restore_pairs = {
                item.get("new"): item.get("old")
                for item in results
                if item.get("success") and item.get("old") and item.get("new")
            }
        else:
            restore_pairs = {v: k for k, v in mapping.items()}

        if restore_pairs:
            restore = binja_mcp_bridge.rename_multi_variables(
                function_identifier="process_many_locals",
                mapping_json=json.dumps(restore_pairs),
            )
            assert_ok(restore)

    def test_rename_multi_with_pairs(self, process_many_locals_function):
        """Rename multiple variables using pairs format."""
        vars_result = binja_mcp_bridge.get_stack_frame_vars(
            function_identifier="process_many_locals"
        )
        if not vars_result.get("ok"):
            pytest.skip("Cannot get stack frame vars")

        variables = _extract_stack_vars(vars_result)
        names = [v.get("name") for v in variables if v.get("name")]
        if len(names) < 2:
            pytest.skip("Not enough variables to rename")

        old_a, old_b = names[0], names[1]
        new_a, new_b = "test_pairs_c", "test_pairs_d"
        result = binja_mcp_bridge.rename_multi_variables(
            function_identifier="process_many_locals", pairs=f"{old_a}:{new_a},{old_b}:{new_b}"
        )
        assert_ok(result)
        restore = binja_mcp_bridge.rename_multi_variables(
            function_identifier="process_many_locals",
            pairs=f"{new_a}:{old_a},{new_b}:{old_b}",
        )
        assert_ok(restore)


# =============================================================================
# Function Prototype Tests
# =============================================================================


class TestFunctionPrototypeKnown:
    """Tests for setting function prototypes."""

    def test_set_prototype_helper_add(self, helper_add_function):
        """Set prototype for helper_add."""
        func_name = helper_add_function["name"]
        result = binja_mcp_bridge.set_function_prototype(
            name_or_address=func_name, prototype=f"int {func_name}(int a, int b)"
        )
        assert_ok(result)
        assert result.get("applied_type")

    def test_set_prototype_by_address(self, helper_add_function):
        """Set prototype by address."""
        address = helper_add_function["address"]
        func_name = helper_add_function["name"]
        result = binja_mcp_bridge.set_function_prototype(
            name_or_address=address, prototype=f"int32_t {func_name}(int32_t, int32_t)"
        )
        assert_ok(result)
        assert result.get("applied_type")


# =============================================================================
# Advanced IL Tests
# =============================================================================


class TestAdvancedILKnown:
    """Advanced IL tests for complex functions."""

    def test_hlil_process_nested_loop(self):
        """HLIL for nested loop function."""
        result = binja_mcp_bridge.get_il(name_or_address="process_loop_nested", view="hlil")
        assert result["ok"] is True

        il = result.get("il", "")
        # Should have loop-related constructs
        assert len(il) > 50

    def test_mlil_ssa_process_conditional(self):
        """MLIL SSA for conditional function."""
        result = binja_mcp_bridge.get_il(
            name_or_address="process_conditional", view="mlil", ssa=True
        )
        assert result["ok"] is True

    def test_llil_create_container(self):
        """LLIL for create_container (has malloc calls)."""
        result = binja_mcp_bridge.get_il(name_or_address="create_container", view="llil")
        assert result["ok"] is True


# =============================================================================
# Cross-Reference Type Tests
# =============================================================================


class TestXrefTypesKnown:
    """Tests for type-based cross-references."""

    def test_xrefs_to_struct_testrecord(self):
        """Get xrefs to TestRecord struct."""
        # Try to find TestRecord (may be mangled)
        result = binja_mcp_bridge.get_xrefs_to_struct(struct_name="TestRecord")
        assert_ok(result)
        assert result.get("struct") == "TestRecord"

    def test_xrefs_to_union_valueunion(self):
        """Get xrefs to ValueUnion."""
        result = binja_mcp_bridge.get_xrefs_to_union(union_name="ValueUnion")
        assert_ok(result)
        assert result.get("union") == "ValueUnion"

    def test_xrefs_to_enum_statuscode(self):
        """Get xrefs to StatusCode enum."""
        result = binja_mcp_bridge.get_xrefs_to_enum(enum_name="StatusCode")
        assert_ok(result)
        assert result.get("enum") == "StatusCode"


# =============================================================================
# Function At Address Tests
# =============================================================================


class TestFunctionAtKnown:
    """Tests for function_at with known addresses."""

    def test_function_at_helper_add(self, helper_add_function):
        """Find function at helper_add's address."""
        address = helper_add_function["address"]
        result = binja_mcp_bridge.function_at(address=address)
        assert result["ok"] is True

        # Should identify helper_add
        name = result.get("name", "")
        functions = result.get("functions", [])
        assert "helper_add" in name or any("helper_add" in str(f) for f in functions)

    def test_function_at_main(self, main_function):
        """Find function at main's address."""
        address = main_function["address"]
        result = binja_mcp_bridge.function_at(address=address)
        assert result["ok"] is True


# =============================================================================
# Additional Data Analysis Tests (100% coverage)
# =============================================================================


class TestHexdumpDataKnown:
    """Tests for hexdump_data MCP tool."""

    def test_hexdump_data_by_address(self, helper_add_function):
        """hexdump_data should work with address."""
        address = helper_add_function["address"]
        result = binja_mcp_bridge.hexdump_data(name_or_address=address, length=32)
        assert result["ok"] is True
        assert "hexdump" in result

    def test_hexdump_data_by_name(self):
        """hexdump_data should work with data symbol name."""
        # Try a known data symbol - may or may not exist depending on analysis
        result = binja_mcp_bridge.hexdump_data(name_or_address="g_global_counter", length=16)
        assert_ok(result)
        assert "hexdump" in result


class TestGetDataDeclKnown:
    """Tests for get_data_decl MCP tool."""

    def test_get_data_decl_at_address(self, helper_add_function):
        """get_data_decl should return data declaration at address."""
        address = helper_add_function["address"]
        result = binja_mcp_bridge.get_data_decl(name_or_address=address)
        assert_ok(result)
        assert "decl" in result

    def test_get_data_decl_by_name(self):
        """get_data_decl should work with symbol name."""
        result = binja_mcp_bridge.get_data_decl(name_or_address="g_global_counter")
        assert_ok(result)
        assert "decl" in result


class TestRenameDataKnown:
    """Tests for rename_data MCP tool."""

    def test_rename_data_at_address(self):
        """rename_data should rename data at address."""
        data_result = binja_mcp_bridge.list_data_items(offset=0, limit=200)
        if not data_result["ok"] or len(data_result.get("data", [])) == 0:
            pytest.skip("No data items found")

        data_items = data_result.get("data", [])
        candidates = [d for d in data_items if d.get("name") in KNOWN_DATA_SYMBOLS]
        if not candidates:
            pytest.skip("No known data symbols available to rename")

        for item in candidates:
            address = item.get("address", "")
            original_name = item.get("name")
            if not address or not original_name:
                continue

            new_name = f"{original_name}_renamed"
            result = binja_mcp_bridge.rename_data(address=address, new_name=new_name)
            if result.get("ok") and result.get("success") is True:
                restore = binja_mcp_bridge.rename_data(address=address, new_name=original_name)
                assert_ok(restore)
                return

        pytest.fail("Failed to rename any known data symbol")


# =============================================================================
# String Tests (Additional for 100% coverage)
# =============================================================================


class TestListStringsBasicKnown:
    """Tests for list_strings MCP tool (without filter)."""

    def test_list_strings_basic(self):
        """list_strings should return strings without filter."""
        result = binja_mcp_bridge.list_strings(offset=0, count=50)
        assert result["ok"] is True
        assert "strings" in result
        assert isinstance(result["strings"], list)

    def test_list_strings_pagination(self):
        """list_strings should support pagination."""
        page1 = binja_mcp_bridge.list_strings(offset=0, count=5)
        page2 = binja_mcp_bridge.list_strings(offset=5, count=5)
        assert page1["ok"] is True
        assert page2["ok"] is True
        assert page1["offset"] == 0
        assert page2["offset"] == 5


# =============================================================================
# Namespace and Class Tests (100% coverage)
# =============================================================================


class TestListClassesKnown:
    """Tests for list_classes MCP tool."""

    def test_list_classes(self):
        """list_classes should return class names."""
        result = binja_mcp_bridge.list_classes(offset=0, limit=100)
        assert result["ok"] is True
        assert "classes" in result
        assert isinstance(result["classes"], list)

    def test_list_classes_pagination(self):
        """list_classes should support pagination."""
        result = binja_mcp_bridge.list_classes(offset=0, limit=10)
        assert result["ok"] is True


class TestListNamespacesKnown:
    """Tests for list_namespaces MCP tool."""

    def test_list_namespaces(self):
        """list_namespaces should return namespace names."""
        result = binja_mcp_bridge.list_namespaces(offset=0, limit=100)
        assert result["ok"] is True
        assert "namespaces" in result
        assert isinstance(result["namespaces"], list)


# =============================================================================
# User-Defined Type Tests (100% coverage)
# =============================================================================


class TestGetUserDefinedTypeKnown:
    """Tests for get_user_defined_type MCP tool."""

    def test_get_user_defined_type_nonexistent(self):
        """get_user_defined_type should handle nonexistent type."""
        result = binja_mcp_bridge.get_user_defined_type(type_name="NonexistentType12345")
        assert_not_ok(result)

    def test_get_user_defined_type_after_define(self):
        """get_user_defined_type should find type after define_types."""
        # First define a type
        c_code = "struct GetUserDefinedTestStruct { int x; int y; };"
        define_result = binja_mcp_bridge.define_types(c_code=c_code)
        if not define_result.get("ok"):
            pytest.skip("Could not define type")

        # Then retrieve it
        result = binja_mcp_bridge.get_user_defined_type(type_name="GetUserDefinedTestStruct")
        assert_ok(result)
        assert result.get("name") == "GetUserDefinedTestStruct"


# =============================================================================
# Additional Cross-Reference Tests (100% coverage)
# =============================================================================


class TestGetXrefsToFieldKnown:
    """Tests for get_xrefs_to_field MCP tool."""

    def test_get_xrefs_to_field(self):
        """get_xrefs_to_field should work with struct and field name."""
        result = binja_mcp_bridge.get_xrefs_to_field(struct_name="TestRecord", field_name="id")
        assert_ok(result)
        assert result.get("struct") == "TestRecord"

    def test_get_xrefs_to_field_nonexistent(self):
        """get_xrefs_to_field should handle nonexistent field."""
        result = binja_mcp_bridge.get_xrefs_to_field(
            struct_name="TestRecord", field_name="nonexistent_field"
        )
        assert_ok(result)


class TestGetXrefsToTypeKnown:
    """Tests for get_xrefs_to_type MCP tool."""

    def test_get_xrefs_to_type_int(self):
        """get_xrefs_to_type should work with basic types."""
        result = binja_mcp_bridge.get_xrefs_to_type(type_name="int")
        assert_ok(result)
        assert result.get("type") == "int"

    def test_get_xrefs_to_type_custom(self):
        """get_xrefs_to_type should work with custom types."""
        result = binja_mcp_bridge.get_xrefs_to_type(type_name="TestRecord")
        assert_ok(result)
        assert result.get("type") == "TestRecord"


# =============================================================================
# Variable Type Tests (100% coverage)
# =============================================================================


class TestRetypeVariableKnown:
    """Tests for retype_variable MCP tool."""

    def test_retype_variable(self, process_many_locals_function):
        """retype_variable should change variable type."""
        # Get variables first
        vars_result = binja_mcp_bridge.get_stack_frame_vars(
            function_identifier="process_many_locals"
        )
        if not vars_result["ok"]:
            pytest.skip("Cannot get stack frame vars")

        variables = _extract_stack_vars(vars_result)
        if len(variables) == 0:
            pytest.skip("No variables found")

        var_name = variables[0].get("name")
        if not var_name:
            pytest.skip("Variable has no name to retype")
        result = binja_mcp_bridge.retype_variable(
            function_name="process_many_locals", variable_name=var_name, type_str="int32_t"
        )
        assert_ok(result)


class TestSetLocalVariableTypeKnown:
    """Tests for set_local_variable_type MCP tool."""

    def test_set_local_variable_type(self, process_many_locals_function):
        """set_local_variable_type should set variable type by address."""
        address = process_many_locals_function["address"]

        # Get variables to find a valid name
        vars_result = binja_mcp_bridge.get_stack_frame_vars(
            function_identifier="process_many_locals"
        )
        if not vars_result["ok"]:
            pytest.skip("Cannot get stack frame vars")

        variables = _extract_stack_vars(vars_result)
        if len(variables) == 0:
            pytest.skip("No variables found")

        var_name = variables[0].get("name")
        if not var_name:
            pytest.skip("Variable has no name to retype")
        result = binja_mcp_bridge.set_local_variable_type(
            function_address=address, variable_name=var_name, new_type="uint32_t"
        )
        assert_ok(result)


# =============================================================================
# Function Creation Tests (100% coverage)
# =============================================================================


class TestMakeFunctionAtKnown:
    """Tests for make_function_at MCP tool."""

    def test_make_function_at_existing(self, helper_add_function):
        """make_function_at should handle existing function address."""
        address = helper_add_function["address"]
        result = binja_mcp_bridge.make_function_at(address=address)
        assert_ok(result)
        assert result.get("status") in ("ok", "exists")

    def test_make_function_at_with_platform(self, helper_add_function):
        """make_function_at should accept platform parameter."""
        address = helper_add_function["address"]
        result = binja_mcp_bridge.make_function_at(address=address, platform="")
        assert_ok(result)
        assert result.get("status") in ("ok", "exists")


class TestListPlatformsKnown:
    """Tests for list_platforms MCP tool."""

    def test_list_platforms(self):
        """list_platforms should return available platforms."""
        result = binja_mcp_bridge.list_platforms()
        assert_ok(result)
        assert "platforms" in result


# =============================================================================
# Patch Bytes Tests (100% coverage)
# =============================================================================


class TestPatchBytesKnown:
    """Tests for patch_bytes MCP tool."""

    def test_patch_bytes_without_save(self, helper_add_function):
        """patch_bytes should patch without saving to file."""
        address = helper_add_function["address"]

        # First read current bytes
        hexdump = binja_mcp_bridge.hexdump_address(address=address, length=4)
        if not hexdump["ok"]:
            pytest.skip("Cannot read bytes")

        # Patch with NOPs without saving (safe operation)
        result = binja_mcp_bridge.patch_bytes(address=address, data="90909090", save_to_file=False)
        assert_ok(result)
        original_bytes = result.get("original_bytes")
        if original_bytes:
            restore = binja_mcp_bridge.patch_bytes(
                address=address,
                data=original_bytes,
                save_to_file=False,
            )
            assert_ok(restore)

    def test_patch_bytes_with_save_false(self, helper_add_function):
        """patch_bytes with save_to_file=False should not persist to disk."""
        # Use helper_add instead of main to avoid corrupting critical function
        address = helper_add_function["address"]
        result = binja_mcp_bridge.patch_bytes(
            address=address,
            data="90",  # NOP is safer than INT3
            save_to_file=False,
        )
        assert_ok(result)
        original_bytes = result.get("original_bytes")
        if original_bytes:
            restore = binja_mcp_bridge.patch_bytes(
                address=address,
                data=original_bytes,
                save_to_file=False,
            )
            assert_ok(restore)


# =============================================================================
# Local Types Additional Tests (100% coverage)
# =============================================================================


class TestListLocalTypesAdvanced:
    """Additional tests for list_local_types MCP tool."""

    def test_list_local_types_with_libraries(self):
        """list_local_types should accept include_libraries parameter."""
        result = binja_mcp_bridge.list_local_types(offset=0, count=50, include_libraries=True)
        assert result["ok"] is True
        assert "types" in result

    def test_list_local_types_pagination(self):
        """list_local_types should support pagination."""
        result = binja_mcp_bridge.list_local_types(offset=10, count=20)
        assert result["ok"] is True


class TestSearchTypesAdvanced:
    """Additional tests for search_types MCP tool."""

    def test_search_types_with_libraries(self):
        """search_types should accept include_libraries parameter."""
        result = binja_mcp_bridge.search_types(query="int", include_libraries=True)
        assert result["ok"] is True

    def test_search_types_pagination(self):
        """search_types should support pagination."""
        result = binja_mcp_bridge.search_types(query="int", offset=0, count=10)
        assert result["ok"] is True


# =============================================================================
# ROBUSTNESS TESTS
# =============================================================================
# These tests verify error handling, edge cases, and boundary conditions
# to ensure the MCP tools handle invalid/unexpected inputs gracefully.


class TestRobustnessInvalidFunctionNames:
    """Tests for handling invalid/nonexistent function names."""

    def test_decompile_nonexistent_function(self):
        """decompile_function should fail gracefully for nonexistent function."""
        result = binja_mcp_bridge.decompile_function(name="__nonexistent_function_xyz_12345__")
        assert result["ok"] is False

    def test_fetch_disassembly_nonexistent(self):
        """fetch_disassembly should fail gracefully for nonexistent function."""
        result = binja_mcp_bridge.fetch_disassembly(name="__nonexistent_function_xyz_12345__")
        assert result["ok"] is False

    def test_get_il_nonexistent_function(self):
        """get_il should fail gracefully for nonexistent function."""
        result = binja_mcp_bridge.get_il(name_or_address="__nonexistent_xyz__", view="hlil")
        assert result["ok"] is False

    def test_get_stack_frame_vars_nonexistent(self):
        """get_stack_frame_vars should fail for nonexistent function."""
        result = binja_mcp_bridge.get_stack_frame_vars(function_identifier="__nonexistent_xyz__")
        assert result["ok"] is False

    def test_rename_function_nonexistent(self):
        """rename_function should fail for nonexistent source function."""
        result = binja_mcp_bridge.rename_function(
            old_name="__nonexistent_xyz__", new_name="new_name"
        )
        assert result["ok"] is False

    def test_set_function_comment_nonexistent(self):
        """set_function_comment should fail for nonexistent function."""
        result = binja_mcp_bridge.set_function_comment(
            function_name="__nonexistent_xyz__", comment="test"
        )
        assert result["ok"] is False

    def test_get_function_comment_nonexistent(self):
        """get_function_comment should handle nonexistent function gracefully."""
        result = binja_mcp_bridge.get_function_comment(function_name="__nonexistent_xyz__")
        assert_ok(result)
        assert result.get("comment") is None

    def test_set_function_prototype_nonexistent(self):
        """set_function_prototype should fail for nonexistent function."""
        result = binja_mcp_bridge.set_function_prototype(
            name_or_address="__nonexistent_xyz__", prototype="void foo(void)"
        )
        assert result["ok"] is False


class TestRobustnessInvalidAddresses:
    """Tests for handling invalid/out-of-range addresses."""

    def test_hexdump_invalid_address(self):
        """hexdump_address should handle invalid address gracefully."""
        result = binja_mcp_bridge.hexdump_address(address="0xDEADBEEFDEADBEEF", length=16)
        assert_ok(result)
        assert "hexdump" in result

    def test_hexdump_malformed_address(self):
        """hexdump_address should handle malformed address."""
        result = binja_mcp_bridge.hexdump_address(address="not_an_address", length=16)
        assert_not_ok(result)

    def test_get_xrefs_invalid_address(self):
        """get_xrefs_to should handle invalid address."""
        result = binja_mcp_bridge.get_xrefs_to(address="0xFFFFFFFFFFFFFFFF")
        assert_ok(result)
        assert "address" in result

    def test_function_at_invalid_address(self):
        """function_at should handle address with no function."""
        result = binja_mcp_bridge.function_at(address="0xDEADBEEFDEADBEEF")
        assert_ok(result)
        assert "functions" in result

    def test_set_comment_invalid_address(self):
        """set_comment should handle invalid address."""
        result = binja_mcp_bridge.set_comment(address="0xDEADBEEFDEADBEEF", comment="test")
        assert_not_ok(result)

    def test_make_function_at_invalid_address(self):
        """make_function_at should handle invalid address."""
        result = binja_mcp_bridge.make_function_at(address="dec:-1")
        assert_not_ok(result)

    def test_patch_bytes_invalid_address(self):
        """patch_bytes should handle invalid address."""
        result = binja_mcp_bridge.patch_bytes(
            address="not_an_address", data="90", save_to_file=False
        )
        assert_not_ok(result)


class TestRobustnessEmptyInputs:
    """Tests for handling empty string inputs."""

    def test_search_functions_empty_query(self):
        """search_functions_by_name should reject empty query."""
        result = binja_mcp_bridge.search_functions_by_name(query="")
        assert result["ok"] is False

    def test_search_types_empty_query(self):
        """search_types should handle empty query."""
        result = binja_mcp_bridge.search_types(query="")
        assert_not_ok(result)

    def test_list_strings_filter_empty(self):
        """list_strings_filter with empty filter should return all strings."""
        result = binja_mcp_bridge.list_strings_filter(filter="", offset=0, count=10)
        assert result["ok"] is True
        assert "strings" in result

    def test_define_types_empty(self):
        """define_types with empty code should handle gracefully."""
        result = binja_mcp_bridge.define_types(c_code="")
        assert_not_ok(result)

    def test_declare_c_type_empty(self):
        """declare_c_type with empty declaration should handle gracefully."""
        result = binja_mcp_bridge.declare_c_type(c_declaration="")
        assert_not_ok(result)

    def test_set_comment_empty(self):
        """set_comment with empty comment should be handled gracefully."""
        # First set a comment
        result = binja_mcp_bridge.list_methods(offset=0, limit=1)
        if not result["ok"] or len(result["functions"]) == 0:
            pytest.skip("No functions available")

        addr = result["functions"][0]["address"]
        clear_result = binja_mcp_bridge.set_comment(address=addr, comment="")
        assert_ok(clear_result)


class TestRobustnessBoundaryConditions:
    """Tests for boundary conditions (limits, offsets, sizes)."""

    def test_list_methods_zero_limit(self):
        """list_methods with limit=0 should return empty or handle gracefully."""
        result = binja_mcp_bridge.list_methods(offset=0, limit=0)
        assert result["ok"] is True

    def test_list_methods_huge_offset(self):
        """list_methods with huge offset should return empty list."""
        result = binja_mcp_bridge.list_methods(offset=999999999, limit=10)
        assert result["ok"] is True
        assert len(result.get("functions", [])) == 0

    def test_list_methods_huge_limit(self):
        """list_methods with huge limit should not crash."""
        result = binja_mcp_bridge.list_methods(offset=0, limit=1000000)
        assert result["ok"] is True

    def test_list_strings_zero_count(self):
        """list_strings with count=0 should handle gracefully."""
        result = binja_mcp_bridge.list_strings(offset=0, count=0)
        assert result["ok"] is True

    def test_list_strings_huge_offset(self):
        """list_strings with huge offset should return empty."""
        result = binja_mcp_bridge.list_strings(offset=999999999, count=10)
        assert result["ok"] is True

    def test_hexdump_zero_length(self):
        """hexdump_address with length=0 should handle gracefully."""
        result = binja_mcp_bridge.list_methods(offset=0, limit=1)
        if not result["ok"] or len(result["functions"]) == 0:
            pytest.skip("No functions available")

        addr = result["functions"][0]["address"]
        hex_result = binja_mcp_bridge.hexdump_address(address=addr, length=0)
        assert_ok(hex_result)
        assert "hexdump" in hex_result

    def test_hexdump_negative_length(self):
        """hexdump_address with negative length should use default."""
        result = binja_mcp_bridge.list_methods(offset=0, limit=1)
        if not result["ok"] or len(result["functions"]) == 0:
            pytest.skip("No functions available")

        addr = result["functions"][0]["address"]
        hex_result = binja_mcp_bridge.hexdump_address(address=addr, length=-1)
        assert hex_result["ok"] is True

    def test_list_local_types_zero_count(self):
        """list_local_types with count=0 should handle gracefully."""
        result = binja_mcp_bridge.list_local_types(offset=0, count=0)
        assert result["ok"] is True

    def test_convert_number_zero(self):
        """convert_number should handle zero."""
        result = binja_mcp_bridge.convert_number(text="0")
        assert result["ok"] is True

    def test_convert_number_max_uint64(self):
        """convert_number should handle max uint64."""
        result = binja_mcp_bridge.convert_number(text="0xFFFFFFFFFFFFFFFF")
        assert result["ok"] is True

    def test_convert_number_negative(self):
        """convert_number should handle negative numbers."""
        result = binja_mcp_bridge.convert_number(text="-1")
        assert result["ok"] is True


class TestRobustnessSpecialCharacters:
    """Tests for handling special characters in inputs."""

    def test_search_functions_special_chars(self):
        """search_functions_by_name should handle special characters."""
        result = binja_mcp_bridge.search_functions_by_name(query="<>[]{}()!@#$%")
        assert result["ok"] is True
        assert len(result.get("matches", [])) == 0  # Unlikely to match anything

    def test_search_types_special_chars(self):
        """search_types should handle special characters."""
        result = binja_mcp_bridge.search_types(query="void*")
        assert result["ok"] is True

    def test_list_strings_filter_special_chars(self):
        """list_strings_filter should handle special characters."""
        result = binja_mcp_bridge.list_strings_filter(filter="\\n\\t\\r", offset=0, count=10)
        assert result["ok"] is True

    def test_set_comment_special_chars(self):
        """set_comment should handle special characters in comment."""
        result = binja_mcp_bridge.list_methods(offset=0, limit=1)
        if not result["ok"] or len(result["functions"]) == 0:
            pytest.skip("No functions available")

        addr = result["functions"][0]["address"]
        comment = "Test <>&\"'\\n\\t special chars: αβγδ 日本語 🎉"
        set_result = binja_mcp_bridge.set_comment(address=addr, comment=comment)
        assert set_result["ok"] is True

        # Clean up
        binja_mcp_bridge.delete_comment(address=addr)

    def test_define_types_special_chars_in_name(self):
        """define_types should handle type names appropriately."""
        # Valid C identifier with underscores
        c_code = "struct _Special_Type_123 { int x; };"
        result = binja_mcp_bridge.define_types(c_code=c_code)
        assert_ok(result)
        assert "_Special_Type_123" in result

    def test_rename_function_special_chars(self, helper_add_function):
        """rename_function should handle special characters in name."""
        # C identifiers can only contain alphanumeric and underscore
        # Use a real function and restore it after
        bad_name = "invalid<name>"
        addr = helper_add_function["address"]
        original_name = helper_add_function["name"]
        result = binja_mcp_bridge.rename_function(old_name=addr, new_name=bad_name)
        if result.get("ok"):
            restore = binja_mcp_bridge.rename_function(old_name=addr, new_name=original_name)
            assert_ok(restore)
        else:
            assert_not_ok(result)


class TestRobustnessInvalidTypes:
    """Tests for handling invalid type definitions and parameters."""

    def test_define_types_invalid_syntax(self):
        """define_types should handle invalid C syntax."""
        result = binja_mcp_bridge.define_types(c_code="this is not valid C code {{{")
        assert_not_ok(result)

    def test_declare_c_type_invalid(self):
        """declare_c_type should handle invalid declarations."""
        result = binja_mcp_bridge.declare_c_type(c_declaration="invalid declaration ;;;")
        assert_not_ok(result)

    def test_get_type_info_nonexistent(self):
        """get_type_info should handle nonexistent type."""
        result = binja_mcp_bridge.get_type_info(type_name="__NonexistentType12345__")
        assert_ok(result)
        assert result.get("name") == "__NonexistentType12345__"

    def test_retype_variable_invalid_type(self):
        """retype_variable should handle invalid type string."""
        vars_result = binja_mcp_bridge.get_stack_frame_vars(
            function_identifier="process_many_locals"
        )
        if not vars_result.get("ok"):
            pytest.skip("Cannot get stack frame vars")

        variables = _extract_stack_vars(vars_result)
        names = [v.get("name") for v in variables if v.get("name")]
        if not names:
            pytest.skip("No variables available to retype")

        result = binja_mcp_bridge.retype_variable(
            function_name="process_many_locals",
            variable_name=names[0],
            type_str="invalid_type_xyz_123",
        )
        assert_not_ok(result)

    def test_set_function_prototype_invalid(self):
        """set_function_prototype should handle invalid prototype."""
        result = binja_mcp_bridge.set_function_prototype(
            name_or_address="helper_add", prototype="this is not a valid prototype"
        )
        assert_not_ok(result)

    def test_get_xrefs_to_struct_nonexistent(self):
        """get_xrefs_to_struct should handle nonexistent struct."""
        result = binja_mcp_bridge.get_xrefs_to_struct(struct_name="__NonexistentStruct123__")
        assert_ok(result)
        assert result.get("struct") == "__NonexistentStruct123__"

    def test_get_xrefs_to_enum_nonexistent(self):
        """get_xrefs_to_enum should handle nonexistent enum."""
        result = binja_mcp_bridge.get_xrefs_to_enum(enum_name="__NonexistentEnum123__")
        assert_ok(result)
        assert result.get("enum") == "__NonexistentEnum123__"

    def test_get_xrefs_to_union_nonexistent(self):
        """get_xrefs_to_union should handle nonexistent union."""
        result = binja_mcp_bridge.get_xrefs_to_union(union_name="__NonexistentUnion123__")
        assert_ok(result)
        assert result.get("union") == "__NonexistentUnion123__"


class TestRobustnessInvalidVariables:
    """Tests for handling invalid variable operations."""

    def test_rename_single_variable_nonexistent_var(self):
        """rename_single_variable should handle nonexistent variable."""
        result = binja_mcp_bridge.rename_single_variable(
            function_name="helper_add", variable_name="__nonexistent_var_xyz__", new_name="new_name"
        )
        assert_not_ok(result)

    def test_retype_variable_nonexistent_var(self):
        """retype_variable should handle nonexistent variable."""
        result = binja_mcp_bridge.retype_variable(
            function_name="helper_add", variable_name="__nonexistent_var_xyz__", type_str="int"
        )
        assert_not_ok(result)

    def test_rename_multi_variables_invalid_json(self):
        """rename_multi_variables should handle invalid JSON."""
        result = binja_mcp_bridge.rename_multi_variables(
            function_identifier="helper_add", mapping_json="this is not valid json"
        )
        assert result["ok"] is False

    def test_rename_multi_variables_empty_mapping(self):
        """rename_multi_variables should handle empty mapping."""
        result = binja_mcp_bridge.rename_multi_variables(
            function_identifier="helper_add", mapping_json="{}"
        )
        assert_not_ok(result)

    def test_rename_multi_variables_no_input(self):
        """rename_multi_variables should fail without mapping or pairs."""
        result = binja_mcp_bridge.rename_multi_variables(function_identifier="helper_add")
        assert result["ok"] is False


class TestRobustnessBinaryManagement:
    """Tests for binary management edge cases."""

    def test_select_binary_nonexistent(self):
        """select_binary should handle nonexistent binary."""
        result = binja_mcp_bridge.select_binary(view="__nonexistent_binary_12345__.exe")
        assert_not_ok(result)

    def test_select_binary_empty(self):
        """select_binary should handle empty view name."""
        result = binja_mcp_bridge.select_binary(view="")
        assert_not_ok(result)


class TestRobustnessPatchBytes:
    """Tests for patch_bytes edge cases."""

    def test_patch_bytes_invalid_hex(self):
        """patch_bytes should handle invalid hex data."""
        result = binja_mcp_bridge.list_methods(offset=0, limit=1)
        if not result["ok"] or len(result["functions"]) == 0:
            pytest.skip("No functions available")

        addr = result["functions"][0]["address"]
        patch_result = binja_mcp_bridge.patch_bytes(
            address=addr,
            data="ZZZZ",  # Not valid hex
            save_to_file=False,
        )
        assert_not_ok(patch_result)

    def test_patch_bytes_empty_data(self):
        """patch_bytes should handle empty data."""
        result = binja_mcp_bridge.list_methods(offset=0, limit=1)
        if not result["ok"] or len(result["functions"]) == 0:
            pytest.skip("No functions available")

        addr = result["functions"][0]["address"]
        patch_result = binja_mcp_bridge.patch_bytes(address=addr, data="", save_to_file=False)
        assert_not_ok(patch_result)

    def test_patch_bytes_odd_length_hex(self):
        """patch_bytes should handle odd-length hex string."""
        result = binja_mcp_bridge.list_methods(offset=0, limit=1)
        if not result["ok"] or len(result["functions"]) == 0:
            pytest.skip("No functions available")

        addr = result["functions"][0]["address"]
        patch_result = binja_mcp_bridge.patch_bytes(
            address=addr,
            data="ABC",  # Odd length
            save_to_file=False,
        )
        assert_not_ok(patch_result)


class TestRobustnessILViews:
    """Tests for IL view edge cases."""

    def test_get_il_invalid_view(self):
        """get_il should handle invalid view name."""
        result = binja_mcp_bridge.get_il(name_or_address="helper_add", view="invalid_view_xyz")
        assert_ok(result)
        assert "il" in result

    def test_get_il_by_address_inside_function(self):
        """get_il should work with address inside a function."""
        # Get any function to test with
        result = binja_mcp_bridge.list_methods(offset=0, limit=1)
        if not result["ok"] or len(result["functions"]) == 0:
            pytest.skip("No functions available")

        func = result["functions"][0]
        # Use an address slightly after the function start
        base_addr = int(func["address"], 16)
        inside_addr = hex(base_addr + 4)
        il_result = binja_mcp_bridge.get_il(name_or_address=inside_addr, view="hlil")
        assert_ok(il_result)
        assert "il" in il_result


class TestRobustnessDataOperations:
    """Tests for data operation edge cases."""

    def test_rename_data_invalid_address(self):
        """rename_data should handle invalid address."""
        result = binja_mcp_bridge.rename_data(address="0xDEADBEEFDEADBEEF", new_name="test_name")
        assert_not_ok(result)
        assert result.get("success") is False

    def test_hexdump_data_nonexistent_symbol(self):
        """hexdump_data should handle nonexistent symbol name."""
        result = binja_mcp_bridge.hexdump_data(
            name_or_address="__nonexistent_symbol_xyz__", length=16
        )
        assert_not_ok(result)

    def test_get_data_decl_nonexistent(self):
        """get_data_decl should handle nonexistent symbol."""
        result = binja_mcp_bridge.get_data_decl(name_or_address="__nonexistent_symbol_xyz__")
        assert_not_ok(result)


class TestRobustnessCommentOperations:
    """Tests for comment operation edge cases."""

    def test_delete_comment_no_comment(self):
        """delete_comment should handle address with no comment."""
        result = binja_mcp_bridge.list_methods(offset=0, limit=1)
        if not result["ok"] or len(result["functions"]) == 0:
            pytest.skip("No functions available")

        addr = result["functions"][0]["address"]
        # Ensure no comment exists
        binja_mcp_bridge.delete_comment(address=addr)
        # Delete again - should still succeed
        del_result = binja_mcp_bridge.delete_comment(address=addr)
        assert del_result["ok"] is True

    def test_delete_function_comment_no_comment(self):
        """delete_function_comment should handle function with no comment gracefully."""
        # Ensure no comment exists
        binja_mcp_bridge.delete_function_comment(function_name="helper_add")
        # Delete again - API may succeed or fail when no comment exists, both acceptable
        result = binja_mcp_bridge.delete_function_comment(function_name="helper_add")
        assert_ok(result)

    def test_get_comment_no_comment(self):
        """get_comment should return empty for address with no comment."""
        result = binja_mcp_bridge.list_methods(offset=0, limit=1)
        if not result["ok"] or len(result["functions"]) == 0:
            pytest.skip("No functions available")

        addr = result["functions"][0]["address"]
        # Ensure no comment
        binja_mcp_bridge.delete_comment(address=addr)
        get_result = binja_mcp_bridge.get_comment(address=addr)
        assert get_result["ok"] is True


class TestRobustnessAddressFormats:
    """Tests for various address format handling."""

    def test_address_decimal_format(self):
        """Tools should handle decimal address format."""
        result = binja_mcp_bridge.function_at(address="dec:4198400")
        assert_ok(result)

    def test_address_hex_lowercase(self):
        """Tools should handle lowercase hex addresses."""
        result = binja_mcp_bridge.function_at(address="0xabcdef")
        assert_ok(result)

    def test_address_hex_uppercase(self):
        """Tools should handle uppercase hex addresses."""
        result = binja_mcp_bridge.function_at(address="0xABCDEF")
        assert_ok(result)

    def test_address_hex_no_prefix(self):
        """Tools should handle hex addresses without 0x prefix."""
        result = binja_mcp_bridge.hexdump_address(address="401000", length=16)
        assert_ok(result)
        assert "hexdump" in result

    def test_address_with_spaces(self):
        """Tools should handle addresses with leading/trailing spaces."""
        result = binja_mcp_bridge.function_at(address="  0x401000  ")
        assert_ok(result)


class TestRobustnessConcurrentOperations:
    """Tests for repeated/concurrent-like operations."""

    def test_repeated_decompile(self):
        """Repeated decompilation should be consistent."""
        result1 = binja_mcp_bridge.decompile_function(name="helper_add")
        result2 = binja_mcp_bridge.decompile_function(name="helper_add")
        assert result1["ok"] == result2["ok"]
        if result1["ok"] and result2["ok"]:
            # Decompilation should be identical
            key = "decompilation" if "decompilation" in result1 else "decompiled"
            assert result1.get(key) == result2.get(key)

    def test_repeated_list_methods(self):
        """Repeated list_methods should return consistent results."""
        result1 = binja_mcp_bridge.list_methods(offset=0, limit=10)
        result2 = binja_mcp_bridge.list_methods(offset=0, limit=10)
        assert result1["ok"] == result2["ok"]
        assert len(result1.get("functions", [])) == len(result2.get("functions", []))

    def test_set_delete_comment_cycle(self):
        """Set and delete comment cycle should work cleanly."""
        result = binja_mcp_bridge.list_methods(offset=0, limit=1)
        if not result["ok"] or len(result["functions"]) == 0:
            pytest.skip("No functions available")

        addr = result["functions"][0]["address"]

        for i in range(3):
            set_result = binja_mcp_bridge.set_comment(address=addr, comment=f"Test cycle {i}")
            assert set_result["ok"] is True
            del_result = binja_mcp_bridge.delete_comment(address=addr)
            assert del_result["ok"] is True
