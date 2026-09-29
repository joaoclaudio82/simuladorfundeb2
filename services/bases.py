"""Compatibilidade de importação; implementação em app.services.bases."""
import importlib
import sys
sys.modules[__name__] = importlib.import_module("app.services.bases")
