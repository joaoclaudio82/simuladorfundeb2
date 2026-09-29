"""Compatibilidade de importação; implementação em app.api.legacy."""
import importlib
import sys
sys.modules[__name__] = importlib.import_module("app.api.legacy")
