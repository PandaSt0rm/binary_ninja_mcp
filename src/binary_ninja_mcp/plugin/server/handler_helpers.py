from __future__ import annotations

import re as _re
from typing import Any

from ..utils.number_utils import parse_address


def resolve_name_to_address(binary_ops: Any, ident: str):
    """Resolve a symbol name or hex address string to (address:int, label:str)."""
    bv = getattr(binary_ops, "current_view", None)
    if not bv:
        return None, None
    s = (ident or "").strip()
    # Address literal (supports hex/dec prefixes; defaults to hex for digit-only)
    try:
        return parse_address(s), s
    except Exception:
        pass
    try:
        get_raw = getattr(bv, "get_symbol_by_raw_name", None)
        sym = get_raw(s) if callable(get_raw) else None
        if sym and hasattr(sym, "address"):
            return int(sym.address), getattr(sym, "name", s)
    except Exception:
        pass
    try:
        get_by_name = getattr(bv, "get_symbol_by_name", None)
        sym = get_by_name(s) if callable(get_by_name) else None
        if sym and hasattr(sym, "address"):
            return int(sym.address), getattr(sym, "name", s)
    except Exception:
        pass
    try:
        m = _re.match(r"^(?i)(?:data|byte|word|dword|qword|off|unk)_(?:0x)?([0-9a-fA-F]+)$", s)
        if m:
            a = int(m.group(1), 16)
            return a, s
    except Exception:
        pass
    try:
        for var in list(bv.data_vars):
            try:
                sy = bv.get_symbol_at(var)
                if not sy:
                    continue
                if getattr(sy, "name", None) == s or getattr(sy, "raw_name", None) == s:
                    return int(var), getattr(sy, "name", s)
            except Exception:
                continue
    except Exception:
        pass
    return None, None


def c_escape(raw: bytes, limit: int | None = None) -> str:
    """Escape bytes as a C string literal."""
    try:
        b = raw if limit is None else raw[:limit]
        out = []
        for ch in b:
            if ch == 0x22:  # '"'
                out.append('\\"')
            elif ch == 0x5C:  # '\\'
                out.append("\\\\")
            elif 32 <= ch <= 126:
                out.append(chr(ch))
            elif ch == 0x0A:
                out.append("\\n")
            elif ch == 0x0D:
                out.append("\\r")
            elif ch == 0x09:
                out.append("\\t")
            else:
                out.append(f"\\x{ch:02x}")
        return '"' + "".join(out) + '"'
    except Exception:
        return '""'


def compute_read_length(
    binary_ops: Any, address: int, length_param: str | None, default: int = 64
) -> int:
    """Resolve a byte count for hexdumps, honoring explicit length and inferred size."""
    read_len: int | None = None
    if length_param is not None:
        try:
            read_len = int(length_param)
        except Exception:
            read_len = None
    if read_len is None:
        read_len = -1
    if read_len < 0:
        try:
            inferred = binary_ops.infer_data_size(address)
            if inferred is not None and inferred > 0:
                read_len = int(inferred)
        except Exception:
            pass
    if read_len is None or read_len < 0:
        read_len = default
    return read_len


def read_bytes(binary_ops: Any, address: int, length: int) -> bytes:
    """Best-effort BinaryView read with safe fallback."""
    try:
        data = binary_ops.current_view.read(address, length)
        return data or b""
    except Exception:
        return b""


def format_hexdump(address: int, data: bytes, label: str | None = None) -> str:
    """Format bytes into a classic hex+ASCII dump with an optional label header."""

    def _printable(b: int) -> str:
        try:
            return chr(b) if 32 <= b <= 126 else "."
        except Exception:
            return "."

    lines: list[str] = []
    addr_hex = format(address, "x")
    if label:
        lines.append(f"{addr_hex}  {label}:")
    else:
        lines.append(f"{addr_hex}:")

    total = len(data)
    offset = 0
    first_pad = address % 16
    if first_pad != 0 and total > 0:
        take = min(16 - first_pad, total)
        chunk = data[0:take]
        hex_area = ("   " * first_pad) + "".join(f"{b:02x} " for b in chunk)
        hex_area += "   " * (16 - first_pad - take)
        ascii_area = (" " * first_pad) + "".join(_printable(b) for b in chunk)
        ascii_area += " " * (16 - first_pad - take)
        lines.append(f"{addr_hex}  {hex_area} {ascii_area}")
        offset += take
    while offset < total:
        line_addr = address + offset
        take = min(16, total - offset)
        chunk = data[offset : offset + take]
        hex_area = "".join(f"{b:02x} " for b in chunk) + ("   " * (16 - take))
        ascii_area = "".join(_printable(b) for b in chunk) + (" " * (16 - take))
        lines.append(f"{format(line_addr, 'x')}  {hex_area} {ascii_area}")
        offset += take

    return "\n".join(lines) + "\n"


__all__ = [
    "c_escape",
    "compute_read_length",
    "format_hexdump",
    "read_bytes",
    "resolve_name_to_address",
]
