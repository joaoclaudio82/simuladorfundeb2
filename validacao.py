"""Compatibilidade de importação; implementação em app.domain.calculo.validacao."""
import importlib
import sys
sys.modules[__name__] = importlib.import_module("app.domain.calculo.validacao")
