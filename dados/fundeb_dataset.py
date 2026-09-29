"""Compatibilidade de importação; implementação em app.ingestion.fundeb_dataset."""
import importlib
import sys
sys.modules[__name__] = importlib.import_module("app.ingestion.fundeb_dataset")
