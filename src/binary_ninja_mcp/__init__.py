import importlib.util as _importlib

__all__ = ["BinaryNinjaMCP"]

# Only import the Binary Ninja plugin when the Binary Ninja Python API is present.
_bn_spec = _importlib.find_spec("binaryninja")
if _bn_spec:
    from .plugin import BinaryNinjaMCP  # type: ignore
else:
    BinaryNinjaMCP = None  # type: ignore
