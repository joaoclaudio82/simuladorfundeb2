"""Compatibilidade de importação; implementação em app.services.cenarios."""
import importlib
import sys
sys.modules[__name__] = importlib.import_module("app.services.cenarios")
