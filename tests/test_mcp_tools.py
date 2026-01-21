"""Integration tests for MCP tool functions with mocked HTTP responses."""

import responses
from binary_ninja_mcp.bridge import binja_mcp_bridge

# Use the same server URL as the bridge
SERVER_URL = "http://localhost:9009"


class TestListMethods:
    """Tests for list_methods MCP tool."""

    @responses.activate
    def test_returns_functions_list(self, sample_functions):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/methods",
            json={"functions": sample_functions},
            status=200,
        )

        result = binja_mcp_bridge.list_methods(offset=0, limit=100)

        assert result["ok"] is True
        assert result["functions"] == sample_functions
        assert result["offset"] == 0
        assert result["limit"] == 100

    @responses.activate
    def test_handles_empty_response(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/methods",
            json={"functions": []},
            status=200,
        )

        result = binja_mcp_bridge.list_methods()

        assert result["ok"] is True
        assert result["functions"] == []

    @responses.activate
    def test_handles_server_error(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/methods",
            json={"error": "Internal server error"},
            status=500,
        )

        result = binja_mcp_bridge.list_methods()

        assert result["ok"] is False
        assert "error" in result


class TestListStrings:
    """Tests for list_strings MCP tool."""

    @responses.activate
    def test_returns_strings_list(self, sample_strings):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/strings",
            json={"strings": sample_strings},
            status=200,
        )

        result = binja_mcp_bridge.list_strings(offset=0, count=100)

        assert result["ok"] is True
        assert result["strings"] == sample_strings
        assert result["offset"] == 0
        assert result["limit"] == 100

    @responses.activate
    def test_pagination_parameters(self, sample_strings):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/strings",
            json={"strings": sample_strings[1:]},
            status=200,
        )

        result = binja_mcp_bridge.list_strings(offset=1, count=50)

        assert result["ok"] is True
        assert result["offset"] == 1
        assert result["limit"] == 50


class TestListStringsFilter:
    """Tests for list_strings_filter MCP tool."""

    @responses.activate
    def test_filters_strings(self, sample_strings):
        filtered = [s for s in sample_strings if "text" in s["value"].lower()]
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/strings/filter",
            json={"strings": filtered, "total": len(filtered)},
            status=200,
        )

        result = binja_mcp_bridge.list_strings_filter(offset=0, count=100, filter="text")

        assert result["ok"] is True
        assert result["filter"] == "text"
        assert "total" in result

    @responses.activate
    def test_empty_filter_returns_all(self, sample_strings):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/strings/filter",
            json={"strings": sample_strings, "total": len(sample_strings)},
            status=200,
        )

        result = binja_mcp_bridge.list_strings_filter(filter="")

        assert result["ok"] is True
        assert result["filter"] == ""


class TestSearchFunctionsByName:
    """Tests for search_functions_by_name MCP tool."""

    @responses.activate
    def test_searches_functions(self, sample_functions):
        matches = [f for f in sample_functions if "sub" in f["name"]]
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/searchFunctions",
            json={"matches": matches},
            status=200,
        )

        result = binja_mcp_bridge.search_functions_by_name(query="sub")

        assert result["ok"] is True
        assert result["query"] == "sub"
        assert "matches" in result

    @responses.activate
    def test_empty_query_returns_error(self):
        result = binja_mcp_bridge.search_functions_by_name(query="")

        assert result["ok"] is False
        assert "error" in result


class TestDecompileFunction:
    """Tests for decompile_function MCP tool."""

    @responses.activate
    def test_decompiles_by_name(self):
        decompiled = "int main() {\n    return 0;\n}"
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/decompile",
            json={"decompilation": decompiled},
            status=200,
        )

        result = binja_mcp_bridge.decompile_function(name="main")

        assert result["ok"] is True
        assert "decompilation" in result

    @responses.activate
    def test_handles_function_not_found(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/decompile",
            json={"error": "Function not found"},
            status=404,
        )

        result = binja_mcp_bridge.decompile_function(name="nonexistent")

        assert result["ok"] is False


class TestHexdumpAddress:
    """Tests for hexdump_address MCP tool."""

    @responses.activate
    def test_returns_hexdump(self):
        hexdump = "00000000  48 65 6c 6c 6f 20 57 6f  72 6c 64 00           |Hello World.|"
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/hexdump",
            body=hexdump,
            status=200,
        )

        result = binja_mcp_bridge.hexdump_address(address="0x1000", length=12)

        assert result["ok"] is True
        assert "hexdump" in result

    @responses.activate
    def test_handles_invalid_address(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/hexdump",
            body="Error 400: Invalid address",
            status=400,
        )

        result = binja_mcp_bridge.hexdump_address(address="invalid")

        assert result["ok"] is False


class TestGetEntryPoints:
    """Tests for get_entry_points MCP tool."""

    @responses.activate
    def test_returns_entry_points(self):
        entry_points = {
            "entry_points": [
                {"address": "0x401000", "name": "_start"},
                {"address": "0x401500", "name": "main"},
            ]
        }
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/entryPoints",
            json=entry_points,
            status=200,
        )

        result = binja_mcp_bridge.get_entry_points()

        assert result["ok"] is True
        assert "entry_points" in result


class TestListSegments:
    """Tests for list_segments MCP tool."""

    @responses.activate
    def test_returns_segments(self):
        segments = {
            "segments": [
                {"name": ".text", "start": "0x401000", "end": "0x402000"},
                {"name": ".data", "start": "0x403000", "end": "0x404000"},
            ]
        }
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/segments",
            json=segments,
            status=200,
        )

        result = binja_mcp_bridge.list_segments()

        assert result["ok"] is True
        assert "segments" in result


class TestListImports:
    """Tests for list_imports MCP tool."""

    @responses.activate
    def test_returns_imports(self):
        imports = {
            "imports": [
                {"name": "printf", "address": "0x401000", "library": "libc.so"},
                {"name": "malloc", "address": "0x401008", "library": "libc.so"},
            ]
        }
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/imports",
            json=imports,
            status=200,
        )

        result = binja_mcp_bridge.list_imports()

        assert result["ok"] is True
        assert "imports" in result


class TestListExports:
    """Tests for list_exports MCP tool."""

    @responses.activate
    def test_returns_exports(self):
        exports = {
            "exports": [
                {"name": "main", "address": "0x401500"},
                {"name": "helper", "address": "0x401600"},
            ]
        }
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/exports",
            json=exports,
            status=200,
        )

        result = binja_mcp_bridge.list_exports()

        assert result["ok"] is True
        assert "exports" in result


class TestSearchTypes:
    """Tests for search_types MCP tool."""

    @responses.activate
    def test_searches_types(self, sample_types):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/searchTypes",
            json={"types": sample_types, "total": len(sample_types)},
            status=200,
        )

        result = binja_mcp_bridge.search_types(query="DWORD")

        assert result["ok"] is True
        assert "types" in result
        assert "total" in result


class TestRenameFunction:
    """Tests for rename_function MCP tool."""

    @responses.activate
    def test_renames_function(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{SERVER_URL}/renameFunction",
            json={"status": "renamed", "old_name": "sub_401000", "new_name": "main"},
            status=200,
        )

        result = binja_mcp_bridge.rename_function(old_name="sub_401000", new_name="main")

        assert result["ok"] is True


class TestSetComment:
    """Tests for set_comment MCP tool."""

    @responses.activate
    def test_sets_comment(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{SERVER_URL}/comment",
            json={"status": "comment set"},
            status=200,
        )

        result = binja_mcp_bridge.set_comment(address="0x401000", comment="Entry point")

        assert result["ok"] is True


class TestGetComment:
    """Tests for get_comment MCP tool."""

    @responses.activate
    def test_gets_comment(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/comment",
            json={"comment": "Entry point"},
            status=200,
        )

        result = binja_mcp_bridge.get_comment(address="0x401000")

        assert result["ok"] is True
        assert "comment" in result


class TestGetBinaryStatus:
    """Tests for get_binary_status MCP tool."""

    @responses.activate
    def test_returns_status(self, sample_status):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json=sample_status,
            status=200,
        )

        result = binja_mcp_bridge.get_binary_status()

        assert result["ok"] is True
        assert "filename" in result


class TestFunctionAt:
    """Tests for function_at MCP tool."""

    @responses.activate
    def test_finds_function_at_address(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/functionAt",
            json={"name": "main", "address": "0x401500", "start": "0x401500", "end": "0x401600"},
            status=200,
        )

        result = binja_mcp_bridge.function_at(address="0x401500")

        assert result["ok"] is True
        assert "name" in result


class TestGetXrefsTo:
    """Tests for get_xrefs_to MCP tool."""

    @responses.activate
    def test_returns_xrefs(self):
        xrefs = {
            "xrefs": [
                {"from": "0x401000", "type": "call"},
                {"from": "0x401100", "type": "call"},
            ]
        }
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/getXrefsTo",
            json=xrefs,
            status=200,
        )

        result = binja_mcp_bridge.get_xrefs_to(address="0x401500")

        assert result["ok"] is True
        assert "xrefs" in result


class TestListLocalTypes:
    """Tests for list_local_types MCP tool."""

    @responses.activate
    def test_returns_types(self, sample_types):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/localTypes",
            json={"types": sample_types},
            status=200,
        )

        result = binja_mcp_bridge.list_local_types()

        assert result["ok"] is True
        assert "types" in result

    @responses.activate
    def test_include_libraries_param(self, sample_types):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/localTypes",
            json={"types": sample_types},
            status=200,
        )

        result = binja_mcp_bridge.list_local_types(include_libraries=True)

        assert result["ok"] is True
        assert result["includeLibraries"] is True


class TestGetIL:
    """Tests for get_il MCP tool."""

    @responses.activate
    def test_returns_hlil(self):
        il_output = {"il": "var_8 = arg1\nreturn var_8", "view": "hlil"}
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/il",
            json=il_output,
            status=200,
        )

        result = binja_mcp_bridge.get_il(name_or_address="main", view="hlil")

        assert result["ok"] is True
        assert "il" in result

    @responses.activate
    def test_handles_address_input(self):
        il_output = {"il": "var_8 = arg1", "view": "llil"}
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/il",
            json=il_output,
            status=200,
        )

        result = binja_mcp_bridge.get_il(name_or_address="0x401000", view="llil")

        assert result["ok"] is True


class TestRetypeVariable:
    """Tests for retype_variable MCP tool."""

    @responses.activate
    def test_retypes_variable(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/retypeVariable",
            json={"success": True},
            status=200,
        )

        result = binja_mcp_bridge.retype_variable(
            function_name="main", variable_name="var_8", type_str="int*"
        )

        assert result["ok"] is True

    @responses.activate
    def test_handles_invalid_type(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/retypeVariable",
            json={"error": "Invalid type"},
            status=400,
        )

        result = binja_mcp_bridge.retype_variable(
            function_name="main", variable_name="var_8", type_str="invalid_type"
        )

        assert result["ok"] is False


class TestRenameSingleVariable:
    """Tests for rename_single_variable MCP tool."""

    @responses.activate
    def test_renames_variable(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/renameVariable",
            json={"success": True, "old_name": "var_8", "new_name": "counter"},
            status=200,
        )

        result = binja_mcp_bridge.rename_single_variable(
            function_name="main", variable_name="var_8", new_name="counter"
        )

        assert result["ok"] is True


class TestRenameMultiVariables:
    """Tests for rename_multi_variables MCP tool."""

    @responses.activate
    def test_renames_multiple_variables_with_mapping(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{SERVER_URL}/renameVariables",
            json={"success": True, "renamed": 2},
            status=200,
        )

        result = binja_mcp_bridge.rename_multi_variables(
            function_identifier="main", mapping_json='{"var_8": "counter", "var_c": "index"}'
        )

        assert result["ok"] is True

    @responses.activate
    def test_renames_with_pairs(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{SERVER_URL}/renameVariables",
            json={"success": True, "renamed": 2},
            status=200,
        )

        result = binja_mcp_bridge.rename_multi_variables(
            function_identifier="main", pairs="var_8:counter,var_c:index"
        )

        assert result["ok"] is True

    def test_rejects_no_mapping(self):
        result = binja_mcp_bridge.rename_multi_variables(function_identifier="main")

        assert result["ok"] is False
        assert "error" in result

    def test_rejects_invalid_json(self):
        result = binja_mcp_bridge.rename_multi_variables(
            function_identifier="main", mapping_json="not valid json"
        )

        assert result["ok"] is False


class TestDefineTypes:
    """Tests for define_types MCP tool."""

    @responses.activate
    def test_defines_types(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{SERVER_URL}/defineTypes",
            json={"success": True, "types_defined": 1},
            status=200,
        )

        result = binja_mcp_bridge.define_types(c_code="struct MyStruct { int x; int y; };")

        assert result["ok"] is True


class TestListClasses:
    """Tests for list_classes MCP tool."""

    @responses.activate
    def test_returns_classes(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/classes",
            json={"classes": ["MyClass", "OtherClass"]},
            status=200,
        )

        result = binja_mcp_bridge.list_classes()

        assert result["ok"] is True
        assert "classes" in result


class TestHexdumpData:
    """Tests for hexdump_data MCP tool."""

    @responses.activate
    def test_hexdump_by_name(self):
        hexdump = "00000000  48 65 6c 6c 6f 00  |Hello.|"
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/hexdumpByName",
            body=hexdump,
            status=200,
        )

        result = binja_mcp_bridge.hexdump_data(name_or_address="my_string")

        assert result["ok"] is True
        assert "hexdump" in result

    @responses.activate
    def test_hexdump_by_address(self):
        hexdump = "00000000  48 65 6c 6c 6f 00  |Hello.|"
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/hexdump",
            body=hexdump,
            status=200,
        )

        result = binja_mcp_bridge.hexdump_data(name_or_address="0x401000")

        assert result["ok"] is True


class TestGetDataDecl:
    """Tests for get_data_decl MCP tool."""

    @responses.activate
    def test_gets_data_declaration(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/getDataDecl",
            json={"declaration": "char my_string[6]", "hexdump": "Hello"},
            status=200,
        )

        result = binja_mcp_bridge.get_data_decl(name_or_address="my_string")

        assert result["ok"] is True
        assert "declaration" in result


class TestFetchDisassembly:
    """Tests for fetch_disassembly MCP tool."""

    @responses.activate
    def test_returns_disassembly(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/assembly",
            json={"disassembly": "push rbp\nmov rbp, rsp"},
            status=200,
        )

        result = binja_mcp_bridge.fetch_disassembly(name="main")

        assert result["ok"] is True
        assert "disassembly" in result


class TestRenameData:
    """Tests for rename_data MCP tool."""

    @responses.activate
    def test_renames_data(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{SERVER_URL}/renameData",
            json={"success": True},
            status=200,
        )

        result = binja_mcp_bridge.rename_data(address="0x401000", new_name="my_data")

        assert result["ok"] is True


class TestSetFunctionComment:
    """Tests for set_function_comment MCP tool."""

    @responses.activate
    def test_sets_function_comment(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{SERVER_URL}/comment/function",
            json={"success": True},
            status=200,
        )

        result = binja_mcp_bridge.set_function_comment(
            function_name="main", comment="Entry point function"
        )

        assert result["ok"] is True


class TestGetFunctionComment:
    """Tests for get_function_comment MCP tool."""

    @responses.activate
    def test_gets_function_comment(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/comment/function",
            json={"comment": "Entry point function"},
            status=200,
        )

        result = binja_mcp_bridge.get_function_comment(function_name="main")

        assert result["ok"] is True
        assert "comment" in result


class TestListSections:
    """Tests for list_sections MCP tool."""

    @responses.activate
    def test_returns_sections(self):
        sections = {
            "sections": [
                {"name": ".text", "start": "0x401000", "end": "0x402000"},
                {"name": ".data", "start": "0x403000", "end": "0x404000"},
            ]
        }
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/sections",
            json=sections,
            status=200,
        )

        result = binja_mcp_bridge.list_sections()

        assert result["ok"] is True
        assert "sections" in result


class TestListAllStrings:
    """Tests for list_all_strings MCP tool."""

    @responses.activate
    def test_returns_all_strings(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/allStrings",
            json={"strings": ["Hello", "World", "Test"]},
            status=200,
        )

        result = binja_mcp_bridge.list_all_strings()

        assert result["ok"] is True
        assert "strings" in result


class TestListNamespaces:
    """Tests for list_namespaces MCP tool."""

    @responses.activate
    def test_returns_namespaces(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/namespaces",
            json={"namespaces": ["std", "boost"]},
            status=200,
        )

        result = binja_mcp_bridge.list_namespaces()

        assert result["ok"] is True
        assert "namespaces" in result


class TestListDataItems:
    """Tests for list_data_items MCP tool."""

    @responses.activate
    def test_returns_data_items(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/data",
            json={"data": [{"name": "g_var", "address": "0x403000", "type": "int"}]},
            status=200,
        )

        result = binja_mcp_bridge.list_data_items()

        assert result["ok"] is True
        assert "data" in result


class TestListBinaries:
    """Tests for list_binaries MCP tool."""

    @responses.activate
    def test_returns_binaries(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/binaries",
            json={"binaries": [{"id": "1", "filename": "test.exe", "active": True}]},
            status=200,
        )

        result = binja_mcp_bridge.list_binaries()

        assert result["ok"] is True
        assert "binaries" in result


class TestSelectBinary:
    """Tests for select_binary MCP tool."""

    @responses.activate
    def test_selects_binary(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/selectBinary",
            json={"success": True, "filename": "other.exe"},
            status=200,
        )

        result = binja_mcp_bridge.select_binary(view="other.exe")

        assert result["ok"] is True


class TestDeleteComment:
    """Tests for delete_comment MCP tool."""

    @responses.activate
    def test_deletes_comment(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{SERVER_URL}/comment",
            json={"success": True},
            status=200,
        )

        result = binja_mcp_bridge.delete_comment(address="0x401000")

        assert result["ok"] is True


class TestDeleteFunctionComment:
    """Tests for delete_function_comment MCP tool."""

    @responses.activate
    def test_deletes_function_comment(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{SERVER_URL}/comment/function",
            json={"success": True},
            status=200,
        )

        result = binja_mcp_bridge.delete_function_comment(function_name="main")

        assert result["ok"] is True


class TestGetUserDefinedType:
    """Tests for get_user_defined_type MCP tool."""

    @responses.activate
    def test_gets_user_defined_type(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/getUserDefinedType",
            json={"name": "MyStruct", "definition": "struct MyStruct { int x; }"},
            status=200,
        )

        result = binja_mcp_bridge.get_user_defined_type(type_name="MyStruct")

        assert result["ok"] is True
        assert "definition" in result


class TestGetXrefsToField:
    """Tests for get_xrefs_to_field MCP tool."""

    @responses.activate
    def test_gets_xrefs_to_field(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/getXrefsToField",
            json={"xrefs": [{"address": "0x401000", "function": "main"}]},
            status=200,
        )

        result = binja_mcp_bridge.get_xrefs_to_field(struct_name="MyStruct", field_name="x")

        assert result["ok"] is True
        assert "xrefs" in result


class TestGetXrefsToStruct:
    """Tests for get_xrefs_to_struct MCP tool."""

    @responses.activate
    def test_gets_xrefs_to_struct(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/getXrefsToStruct",
            json={"xrefs": [{"address": "0x401000"}]},
            status=200,
        )

        result = binja_mcp_bridge.get_xrefs_to_struct(struct_name="MyStruct")

        assert result["ok"] is True


class TestGetXrefsToType:
    """Tests for get_xrefs_to_type MCP tool."""

    @responses.activate
    def test_gets_xrefs_to_type(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/getXrefsToType",
            json={"xrefs": [{"address": "0x401000"}]},
            status=200,
        )

        result = binja_mcp_bridge.get_xrefs_to_type(type_name="MyType")

        assert result["ok"] is True


class TestGetXrefsToEnum:
    """Tests for get_xrefs_to_enum MCP tool."""

    @responses.activate
    def test_gets_xrefs_to_enum(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/getXrefsToEnum",
            json={"xrefs": [{"address": "0x401000", "member": "VALUE_1"}]},
            status=200,
        )

        result = binja_mcp_bridge.get_xrefs_to_enum(enum_name="MyEnum")

        assert result["ok"] is True


class TestGetXrefsToUnion:
    """Tests for get_xrefs_to_union MCP tool."""

    @responses.activate
    def test_gets_xrefs_to_union(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/getXrefsToUnion",
            json={"xrefs": [{"address": "0x401000"}]},
            status=200,
        )

        result = binja_mcp_bridge.get_xrefs_to_union(union_name="MyUnion")

        assert result["ok"] is True


class TestGetStackFrameVars:
    """Tests for get_stack_frame_vars MCP tool."""

    @responses.activate
    def test_gets_stack_frame_vars_by_name(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/getStackFrameVars",
            json={"variables": [{"name": "var_8", "type": "int", "offset": -8}]},
            status=200,
        )

        result = binja_mcp_bridge.get_stack_frame_vars(function_identifier="main")

        assert result["ok"] is True
        assert "variables" in result

    @responses.activate
    def test_gets_stack_frame_vars_by_address(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/getStackFrameVars",
            json={"variables": []},
            status=200,
        )

        result = binja_mcp_bridge.get_stack_frame_vars(function_identifier="0x401000")

        assert result["ok"] is True


class TestFormatValue:
    """Tests for format_value MCP tool."""

    @responses.activate
    def test_formats_value(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/formatValue",
            json={"success": True, "formatted": "0x1234"},
            status=200,
        )

        result = binja_mcp_bridge.format_value(address="0x401000", text="4660")

        assert result["ok"] is True


class TestConvertNumber:
    """Tests for convert_number MCP tool."""

    @responses.activate
    def test_converts_number(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/convertNumber",
            json={
                "hex": "0x1234",
                "decimal": "4660",
                "binary": "0b1001000110100",
            },
            status=200,
        )

        result = binja_mcp_bridge.convert_number(text="4660")

        assert result["ok"] is True
        assert "hex" in result


class TestGetTypeInfo:
    """Tests for get_type_info MCP tool."""

    @responses.activate
    def test_gets_type_info(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/getTypeInfo",
            json={"name": "int", "size": 4, "signed": True},
            status=200,
        )

        result = binja_mcp_bridge.get_type_info(type_name="int")

        assert result["ok"] is True
        assert "size" in result


class TestSetFunctionPrototype:
    """Tests for set_function_prototype MCP tool."""

    @responses.activate
    def test_sets_prototype_by_name(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{SERVER_URL}/setFunctionPrototype",
            json={"success": True},
            status=200,
        )

        result = binja_mcp_bridge.set_function_prototype(
            name_or_address="main", prototype="int main(int argc, char** argv)"
        )

        assert result["ok"] is True

    @responses.activate
    def test_sets_prototype_by_address(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{SERVER_URL}/setFunctionPrototype",
            json={"success": True},
            status=200,
        )

        result = binja_mcp_bridge.set_function_prototype(
            name_or_address="0x401000", prototype="void sub_401000(void)"
        )

        assert result["ok"] is True


class TestMakeFunctionAt:
    """Tests for make_function_at MCP tool."""

    @responses.activate
    def test_creates_function(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/makeFunctionAt",
            json={"success": True, "name": "sub_401000"},
            status=200,
        )

        result = binja_mcp_bridge.make_function_at(address="0x401000")

        assert result["ok"] is True

    @responses.activate
    def test_creates_function_with_platform(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/makeFunctionAt",
            json={"success": True},
            status=200,
        )

        result = binja_mcp_bridge.make_function_at(address="0x401000", platform="linux-x86_64")

        assert result["ok"] is True


class TestListPlatforms:
    """Tests for list_platforms MCP tool."""

    @responses.activate
    def test_returns_platforms(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/platforms",
            json={"platforms": ["linux-x86_64", "windows-x86_64", "linux-armv7"]},
            status=200,
        )

        result = binja_mcp_bridge.list_platforms()

        assert result["ok"] is True
        assert "platforms" in result


class TestDeclareCType:
    """Tests for declare_c_type MCP tool."""

    @responses.activate
    def test_declares_c_type(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{SERVER_URL}/declareCType",
            json={"success": True, "name": "MyStruct"},
            status=200,
        )

        result = binja_mcp_bridge.declare_c_type(c_declaration="struct MyStruct { int x; };")

        assert result["ok"] is True


class TestSetLocalVariableType:
    """Tests for set_local_variable_type MCP tool."""

    @responses.activate
    def test_sets_variable_type(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{SERVER_URL}/setLocalVariableType",
            json={"success": True},
            status=200,
        )

        result = binja_mcp_bridge.set_local_variable_type(
            function_address="0x401000", variable_name="var_8", new_type="int*"
        )

        assert result["ok"] is True


class TestPatchBytes:
    """Tests for patch_bytes MCP tool."""

    @responses.activate
    def test_patches_bytes(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{SERVER_URL}/patch",
            json={"success": True, "bytes_written": 4},
            status=200,
        )

        result = binja_mcp_bridge.patch_bytes(address="0x401000", data="90909090")

        assert result["ok"] is True

    @responses.activate
    def test_patches_without_saving(self):
        responses.add(
            responses.GET,
            f"{SERVER_URL}/status",
            json={"filename": "test.exe"},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{SERVER_URL}/patch",
            json={"success": True},
            status=200,
        )

        result = binja_mcp_bridge.patch_bytes(address="0x401000", data="90", save_to_file=False)

        assert result["ok"] is True
