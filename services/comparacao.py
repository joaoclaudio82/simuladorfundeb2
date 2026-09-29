"""Compatibilidade de importação; implementação em app.services.comparacao."""
import importlib
import sys
sys.modules[__name__] = importlib.import_module("app.services.comparacao")
