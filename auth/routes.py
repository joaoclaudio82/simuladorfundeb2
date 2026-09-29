"""Compatibilidade de importação; implementação em app.auth.routes."""
import importlib
import sys
sys.modules[__name__] = importlib.import_module("app.auth.routes")
