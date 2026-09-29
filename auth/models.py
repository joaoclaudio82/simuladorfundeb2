"""Compatibilidade de importação; implementação em app.auth.models."""
import importlib
import sys
sys.modules[__name__] = importlib.import_module("app.auth.models")
