from __future__ import annotations

import json as _json

from .http_client import (
    get_json,
    get_text,
    post_json,
)
from .http_client import (
    long_timeout as _long_timeout,
)
from .http_client import (
    status_timeout as _status_timeout,
)
from .runtime import tool
from .tool_helpers import (
    _active_filename,
    _fetch_paginated_list,
    _is_int_like,
    _mcp_from_json,
    _mcp_from_text,
    _mcp_result,
)


@tool()
def list_methods(offset: int = 0, limit: int = 100) -> dict:
    """List all function names in the program with pagination."""
    file = _active_filename()
    return _fetch_paginated_list(
        "methods",
        file=file,
        offset=offset,
        limit=limit,
        result_key="functions",
    )


@tool()
def get_entry_points() -> dict:
    """List entry point(s) of the loaded binary."""

    file = _active_filename()
    data = get_json("entryPoints")
    return _mcp_from_json(data, file=file)


@tool()
def retype_variable(function_name: str, variable_name: str, type_str: str) -> dict:
    """Retype a variable in a function."""

    file = _active_filename()
    params = {
        "functionName": function_name,
        "variableName": variable_name,
        "type": type_str,
    }
    data = get_json("retypeVariable", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def rename_single_variable(function_name: str, variable_name: str, new_name: str) -> dict:
    """Rename a variable in a function."""

    file = _active_filename()
    params = {
        "functionName": function_name,
        "variableName": variable_name,
        "newName": new_name,
    }
    data = get_json("renameVariable", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def rename_multi_variables(
    function_identifier: str,
    mapping_json: str = "",
    pairs: str = "",
    renames_json: str = "",
) -> dict:
    """Rename multiple local variables in one call.

    - function_identifier: function name or address (hex)
    - Provide either mapping_json (JSON object old->new), renames_json (JSON array of {old,new}), or pairs ("old1:new1,old2:new2").

    Returns per-item results and totals.
    """

    file = _active_filename()
    params: dict[str, object] = {}
    ident = (function_identifier or "").strip()
    if _is_int_like(ident):
        params["address"] = ident
    else:
        params["functionName"] = ident

    if renames_json:
        try:
            _json.loads(renames_json)
        except Exception:
            return _mcp_result(ok=False, file=file, error="renames_json is not valid JSON")
        params["renames"] = renames_json
    elif mapping_json:
        try:
            _json.loads(mapping_json)
        except Exception:
            return _mcp_result(ok=False, file=file, error="mapping_json is not valid JSON")
        params["mapping"] = mapping_json
    elif pairs:
        params["pairs"] = pairs
    else:
        return _mcp_result(
            ok=False, file=file, error="Provide mapping_json, renames_json, or pairs"
        )

    data = post_json("renameVariables", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def define_types(c_code: str) -> dict:
    """Define types from a C code string."""

    file = _active_filename()
    data = post_json("defineTypes", {"cCode": c_code})
    return _mcp_from_json(data, file=file)


@tool()
def list_classes(offset: int = 0, limit: int = 100) -> dict:
    """List all namespace/class names in the program with pagination."""
    file = _active_filename()
    return _fetch_paginated_list(
        "classes",
        file=file,
        offset=offset,
        limit=limit,
        result_key="classes",
    )


@tool()
def hexdump_address(address: str, length: int = -1) -> dict:
    """Hexdump data starting at an address.

    When `length < 0`, the server attempts to read the exact defined size.
    """

    file = _active_filename()
    params = {"address": address, "length": length}
    text = get_text("hexdump", params, timeout=_long_timeout())
    return _mcp_from_text(text, file=file, key="hexdump", **params)


@tool()
def hexdump_data(name_or_address: str, length: int = -1) -> dict:
    """Hexdump a data symbol by name or address."""

    ident = (name_or_address or "").strip()
    if ident.startswith("0x"):
        return hexdump_address(ident, length)

    file = _active_filename()
    params = {"name": ident, "length": length}
    text = get_text("hexdumpByName", params, timeout=_long_timeout())
    return _mcp_from_text(text, file=file, key="hexdump", **params)


@tool()
def get_data_decl(name_or_address: str, length: int = -1) -> dict:
    """Return a declaration and a hexdump for a data symbol."""

    file = _active_filename()
    ident = (name_or_address or "").strip()
    params: dict[str, object] = (
        {"name": ident} if not ident.startswith("0x") else {"address": ident}
    )
    params["length"] = length
    data = get_json("getDataDecl", params, timeout=_long_timeout())
    return _mcp_from_json(data, file=file, **params)


@tool()
def decompile_function(name: str) -> dict:
    """Decompile a specific function by name."""

    file = _active_filename()
    data = get_json("decompile", {"name": name}, timeout=_long_timeout())
    return _mcp_from_json(data, file=file, name=name)


@tool()
def get_il(name_or_address: str, view: str = "hlil", ssa: bool = False) -> dict:
    """Get IL for a function in the selected view."""

    file = _active_filename()
    ident = (name_or_address or "").strip()
    params: dict[str, object] = {"view": view, "ssa": int(bool(ssa))}
    if _is_int_like(ident):
        params["address"] = ident
    else:
        params["name"] = ident
    data = get_json("il", params, timeout=_long_timeout())
    return _mcp_from_json(data, file=file, requested=name_or_address, view=view, ssa=ssa)


@tool()
def fetch_disassembly(name: str) -> dict:
    """Retrieve disassembly for a function by name."""

    file = _active_filename()
    data = get_json("assembly", {"name": name}, timeout=_long_timeout())
    return _mcp_from_json(data, file=file, name=name)


@tool()
def rename_function(old_name: str, new_name: str) -> dict:
    """Rename a function by its current name (or address) to a new user-defined name."""

    file = _active_filename()
    params = {"oldName": old_name, "newName": new_name}
    data = post_json("renameFunction", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def rename_data(address: str, new_name: str) -> dict:
    """Rename a data label at the specified address."""

    file = _active_filename()
    params = {"address": address, "newName": new_name}
    data = post_json("renameData", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def set_comment(address: str, comment: str) -> dict:
    """Set a comment at a specific address."""

    file = _active_filename()
    params = {"address": address, "comment": comment}
    data = post_json("comment", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def set_function_comment(function_name: str, comment: str) -> dict:
    """Set a comment for a function."""

    file = _active_filename()
    params = {"name": function_name, "comment": comment}
    data = post_json("comment/function", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_comment(address: str) -> dict:
    """Get the comment at a specific address."""

    file = _active_filename()
    params = {"address": address}
    data = get_json("comment", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_function_comment(function_name: str) -> dict:
    """Get the comment for a function."""

    file = _active_filename()
    params = {"name": function_name}
    data = get_json("comment/function", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def list_segments(offset: int = 0, limit: int = 100) -> dict:
    """List all memory segments in the program with pagination."""
    file = _active_filename()
    return _fetch_paginated_list(
        "segments",
        file=file,
        offset=offset,
        limit=limit,
        result_key="segments",
    )


@tool()
def list_sections(offset: int = 0, limit: int = 100) -> dict:
    """List sections in the program with pagination."""
    file = _active_filename()
    return _fetch_paginated_list(
        "sections",
        file=file,
        offset=offset,
        limit=limit,
        result_key="sections",
    )


@tool()
def list_imports(offset: int = 0, limit: int = 100) -> dict:
    """List imported symbols in the program with pagination."""
    file = _active_filename()
    return _fetch_paginated_list(
        "imports",
        file=file,
        offset=offset,
        limit=limit,
        result_key="imports",
    )


@tool()
def list_strings(offset: int = 0, count: int = 100) -> dict:
    """List strings in the database (paginated)."""
    file = _active_filename()
    return _fetch_paginated_list(
        "strings",
        file=file,
        offset=offset,
        limit=count,
        result_key="strings",
        timeout=_long_timeout(),
    )


@tool()
def list_strings_filter(offset: int = 0, count: int = 100, filter: str = "") -> dict:
    """List matching strings in the database (paginated, filtered)."""

    file = _active_filename()
    params = {"offset": offset, "limit": count, "filter": filter}
    data = get_json("strings/filter", params, timeout=_long_timeout())
    if isinstance(data, dict) and "error" not in data:
        return _mcp_result(
            ok=True,
            file=file,
            offset=offset,
            limit=count,
            filter=filter,
            strings=data.get("strings", []) or [],
            total=data.get("total"),
        )
    return _mcp_from_json(data, file=file, **params)


@tool()
def list_local_types(offset: int = 0, count: int = 200, include_libraries: bool = False) -> dict:
    """List local types in the database (paginated)."""
    file = _active_filename()
    params = {"includeLibraries": int(bool(include_libraries))}
    return _fetch_paginated_list(
        "localTypes",
        file=file,
        offset=offset,
        limit=count,
        result_key="types",
        params=params,
        timeout=_long_timeout(),
        extra_payload={"includeLibraries": bool(include_libraries)},
    )


@tool()
def search_types(
    query: str, offset: int = 0, count: int = 200, include_libraries: bool = False
) -> dict:
    """Search local types whose name or declaration contains the substring."""

    file = _active_filename()
    params = {
        "query": query,
        "offset": offset,
        "limit": count,
        "includeLibraries": int(bool(include_libraries)),
    }
    data = get_json("searchTypes", params, timeout=_long_timeout())
    if isinstance(data, dict) and "error" not in data:
        return _mcp_result(
            ok=True,
            file=file,
            query=query,
            offset=offset,
            limit=count,
            includeLibraries=bool(include_libraries),
            types=data.get("types", []) or [],
            total=data.get("total"),
        )
    return _mcp_from_json(data, file=file, **params)


@tool()
def list_all_strings() -> dict:
    """List all strings in the database (no pagination)."""

    file = _active_filename()
    data = get_json("allStrings", timeout=_long_timeout())
    if isinstance(data, dict) and "error" not in data:
        return _mcp_result(ok=True, file=file, strings=data.get("strings", []) or [])
    return _mcp_from_json(data, file=file)


@tool()
def list_exports(offset: int = 0, limit: int = 100) -> dict:
    """List exported functions/symbols with pagination."""
    file = _active_filename()
    return _fetch_paginated_list(
        "exports",
        file=file,
        offset=offset,
        limit=limit,
        result_key="exports",
    )


@tool()
def list_namespaces(offset: int = 0, limit: int = 100) -> dict:
    """List all non-global namespaces in the program with pagination."""
    file = _active_filename()
    return _fetch_paginated_list(
        "namespaces",
        file=file,
        offset=offset,
        limit=limit,
        result_key="namespaces",
    )


@tool()
def list_data_items(offset: int = 0, limit: int = 100) -> dict:
    """List defined data labels and their values with pagination."""
    file = _active_filename()
    return _fetch_paginated_list(
        "data",
        file=file,
        offset=offset,
        limit=limit,
        result_key="data",
    )


@tool()
def search_functions_by_name(query: str, offset: int = 0, limit: int = 100) -> dict:
    """Search for functions whose name contains the given substring."""

    file = _active_filename()
    if not query:
        return _mcp_result(ok=False, file=file, error="Query string is required", query=query)

    params = {"query": query, "offset": offset, "limit": limit}
    data = get_json("searchFunctions", params)
    if isinstance(data, dict) and "error" not in data:
        return _mcp_result(
            ok=True,
            file=file,
            query=query,
            offset=offset,
            limit=limit,
            matches=data.get("matches", []) or [],
        )
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_binary_status() -> dict:
    """Get the current status of the loaded binary."""

    data = get_json("status", timeout=_status_timeout())
    return _mcp_from_json(data, file="(none)")


@tool()
def list_binaries() -> dict:
    """List managed/open binaries known to the server with ids and active flag."""

    data = get_json("binaries", timeout=_status_timeout())
    return _mcp_from_json(data, file="(none)")


@tool()
def select_binary(view: str) -> dict:
    """Select which binary to analyze by id, filename, or basename."""

    data = get_json("selectBinary", {"view": view}, timeout=_long_timeout())
    return _mcp_from_json(data, file="(none)", view=view)


@tool()
def delete_comment(address: str) -> dict:
    """Delete the comment at a specific address."""

    file = _active_filename()
    params = {"address": address, "_method": "DELETE"}
    data = post_json("comment", params)
    return _mcp_from_json(data, file=file, address=address)


@tool()
def delete_function_comment(function_name: str) -> dict:
    """Delete the comment for a function."""

    file = _active_filename()
    params = {"name": function_name, "_method": "DELETE"}
    data = post_json("comment/function", params)
    return _mcp_from_json(data, file=file, name=function_name)


@tool()
def function_at(address: str) -> dict:
    """Retrieve the name(s) of the function(s) containing an address."""

    file = _active_filename()
    params = {"address": address}
    data = get_json("functionAt", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_user_defined_type(type_name: str) -> dict:
    """Retrieve a user-defined type definition (struct/enum/typedef/union)."""

    file = _active_filename()
    params = {"name": type_name}
    data = get_json("getUserDefinedType", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_xrefs_to(address: str) -> dict:
    """Get all cross references (code and data) to an address."""

    file = _active_filename()
    params = {"address": address}
    data = get_json("getXrefsTo", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_xrefs_to_field(struct_name: str, field_name: str) -> dict:
    """Get cross references to a named struct field (member)."""

    file = _active_filename()
    params = {"struct": struct_name, "field": field_name}
    data = get_json("getXrefsToField", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_xrefs_to_struct(struct_name: str) -> dict:
    """Get cross references/usages related to a struct name."""

    file = _active_filename()
    params = {"name": struct_name}
    data = get_json("getXrefsToStruct", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_xrefs_to_type(type_name: str) -> dict:
    """Get xrefs/usages related to a struct or type name."""

    file = _active_filename()
    params = {"name": type_name}
    data = get_json("getXrefsToType", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_xrefs_to_enum(enum_name: str) -> dict:
    """Get usages/xrefs of an enum by scanning for member values and matches."""

    file = _active_filename()
    params = {"name": enum_name}
    data = get_json("getXrefsToEnum", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_xrefs_to_union(union_name: str) -> dict:
    """Get cross references/usages related to a union type by name."""

    file = _active_filename()
    params = {"name": union_name}
    data = get_json("getXrefsToUnion", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_stack_frame_vars(function_identifier: str) -> dict:
    """Get stack frame variable information for a function by name or address."""

    file = _active_filename()
    ident = (function_identifier or "").strip()
    params: dict[str, object] = {}
    if _is_int_like(ident):
        params["address"] = ident
    else:
        params["name"] = ident

    data = get_json("getStackFrameVars", params, timeout=_long_timeout())
    return _mcp_from_json(data, file=file, identifier=function_identifier)


@tool()
def format_value(address: str, text: str, size: int = 0) -> dict:
    """Convert and annotate a value at an address in Binary Ninja."""

    file = _active_filename()
    params = {"address": address, "text": text, "size": size}
    data = get_json("formatValue", params, timeout=_long_timeout())
    return _mcp_from_json(data, file=file, **params)


@tool()
def convert_number(text: str, size: int = 0) -> dict:
    """Convert a number/string to multiple representations (hex/dec/bin, LE/BE, C literals)."""

    params = {"text": text, "size": size}
    data = get_json("convertNumber", params, timeout=_long_timeout())
    return _mcp_from_json(data, file="(none)", **params)


@tool()
def get_type_info(type_name: str) -> dict:
    """Resolve a type name and return its declaration and details."""

    file = _active_filename()
    params = {"name": type_name}
    data = get_json("getTypeInfo", params, timeout=_long_timeout())
    return _mcp_from_json(data, file=file, **params)


@tool()
def set_function_prototype(name_or_address: str, prototype: str) -> dict:
    """Set a function's prototype by name or address."""

    file = _active_filename()
    ident = (name_or_address or "").strip()
    params: dict[str, object] = {"prototype": prototype}
    if _is_int_like(ident):
        params["address"] = ident
    else:
        params["name"] = ident

    data = post_json("setFunctionPrototype", params, timeout=_long_timeout())
    return _mcp_from_json(data, file=file, requested=name_or_address)


@tool()
def make_function_at(address: str, platform: str = "") -> dict:
    """Create a function at the given address."""

    file = _active_filename()
    params: dict[str, object] = {"address": address}
    if platform:
        params["platform"] = platform
    data = get_json("makeFunctionAt", params, timeout=_long_timeout())
    return _mcp_from_json(data, file=file, **params)


@tool()
def list_platforms() -> dict:
    """List all available platform names from Binary Ninja."""

    data = get_json("platforms", timeout=_status_timeout())
    return _mcp_from_json(data, file="(none)")


@tool()
def declare_c_type(c_declaration: str) -> dict:
    """Create or update a local type from a C declaration."""

    file = _active_filename()
    data = post_json("declareCType", {"declaration": c_declaration}, timeout=_long_timeout())
    return _mcp_from_json(data, file=file)


@tool()
def set_local_variable_type(function_address: str, variable_name: str, new_type: str) -> dict:
    """Set a local variable's type."""

    file = _active_filename()
    params = {
        "functionAddress": function_address,
        "variableName": variable_name,
        "newType": new_type,
    }
    data = get_json("setLocalVariableType", params, timeout=_long_timeout())
    return _mcp_from_json(data, file=file, **params)


@tool()
def patch_bytes(address: str, data: str, save_to_file: bool = True) -> dict:
    """Patch bytes at a given address in the binary."""

    file = _active_filename()
    if isinstance(save_to_file, str):
        save_to_file = save_to_file.lower() not in ("false", "0", "no")

    params = {"address": address, "data": data, "save_to_file": save_to_file}
    result = post_json("patch", params, timeout=_long_timeout())
    return _mcp_from_json(result, file=file, request_info=params)


__all__ = [
    "convert_number",
    "declare_c_type",
    "decompile_function",
    "define_types",
    "delete_comment",
    "delete_function_comment",
    "fetch_disassembly",
    "format_value",
    "function_at",
    "get_binary_status",
    "get_comment",
    "get_data_decl",
    "get_entry_points",
    "get_function_comment",
    "get_il",
    "get_stack_frame_vars",
    "get_type_info",
    "get_user_defined_type",
    "get_xrefs_to",
    "get_xrefs_to_enum",
    "get_xrefs_to_field",
    "get_xrefs_to_struct",
    "get_xrefs_to_type",
    "get_xrefs_to_union",
    "hexdump_address",
    "hexdump_data",
    "list_all_strings",
    "list_binaries",
    "list_classes",
    "list_data_items",
    "list_exports",
    "list_imports",
    "list_local_types",
    "list_methods",
    "list_namespaces",
    "list_platforms",
    "list_sections",
    "list_segments",
    "list_strings",
    "list_strings_filter",
    "make_function_at",
    "patch_bytes",
    "rename_data",
    "rename_function",
    "rename_multi_variables",
    "rename_single_variable",
    "retype_variable",
    "search_functions_by_name",
    "search_types",
    "select_binary",
    "set_comment",
    "set_function_comment",
    "set_function_prototype",
    "set_local_variable_type",
]
