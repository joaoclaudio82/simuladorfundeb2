"""Compatibilidade de importação; implementação em app.services.calibracao."""
import importlib
import sys
sys.modules[__name__] = importlib.import_module("app.services.calibracao")
