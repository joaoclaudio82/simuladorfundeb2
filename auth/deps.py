"""Compatibilidade de importação; implementação em app.auth.deps."""
import importlib
import sys
sys.modules[__name__] = importlib.import_module("app.auth.deps")
