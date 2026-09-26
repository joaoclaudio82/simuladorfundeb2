"""Snapshots persistidos: exportações não consultam os controles da interface."""
import gzip
import json
from pathlib import Path
import re
import sqlite3


class ScenarioStore:
    def __init__(self, path, limite=1000):
        self.path = Path(path)
        self.limite = limite
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.conexao() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS cenarios (id TEXT PRIMARY KEY, criado TEXT NOT NULL, payload BLOB NOT NULL)")

    def conexao(self):
        return sqlite3.connect(self.path, timeout=30)

    def salvar(self, resultado):
        blob = gzip.compress(json.dumps(resultado, ensure_ascii=False, allow_nan=False).encode(), mtime=0)
        with self.conexao() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT count(*) FROM cenarios").fetchone()[0] >= self.limite:
                raise ValueError("Limite de cenários armazenados atingido; contate o administrador.")
            db.execute("INSERT INTO cenarios VALUES (?, ?, ?)", (resultado["id"], resultado["criado_em"], blob))

    def obter(self, cenario_id):
        if not re.fullmatch(r"[0-9a-f]{32}", cenario_id):
            raise KeyError("Cenário não encontrado.")
        with self.conexao() as db:
            row = db.execute("SELECT payload FROM cenarios WHERE id=?", (cenario_id,)).fetchone()
        if row is None:
            raise KeyError("Cenário não encontrado.")
        return json.loads(gzip.decompress(row[0]))
