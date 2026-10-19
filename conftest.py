import sys
import os
import types
import importlib

# Add src/ to sys.path for direct module imports required by mutmut
src_path = os.path.join(os.path.dirname(__file__), "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Create a virtual src package for compatibility with existing tests
_src_pkg = types.ModuleType("src")
_src_pkg.__path__ = [src_path]
_src_pkg.__package__ = "src"
sys.modules.setdefault("src", _src_pkg)

# Alias the same module objects under src.* without changing their names
for _mod_name in ["calculator", "output", "payment"]:
    _mod = importlib.import_module(_mod_name)
    sys.modules.setdefault(f"src.{_mod_name}", _mod)
    setattr(_src_pkg, _mod_name, _mod)