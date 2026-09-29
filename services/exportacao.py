"""Compatibilidade de importação; implementação em app.services.exportacao."""
import importlib
import sys
sys.modules[__name__] = importlib.import_module("app.services.exportacao")
