"""Compatibilidade de importação; implementação em app.schemas.cenarios."""
import importlib
import sys
sys.modules[__name__] = importlib.import_module("app.schemas.cenarios")
