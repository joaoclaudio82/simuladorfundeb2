"""
FND-05 / FND-10 — Contratos de entrada e saída dos cenários.
"""
from __future__ import annotations

import math
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

Operacao = Literal["definir", "acrescentar", "converter"]
Recorte = Literal["estaduais_df", "selecionadas", "propag", "universo"]
RubricaReceita = Literal["recursos_vaaf", "recursos_vaat"]

AVISO_METODOLOGICO = (
    "Os resultados representam cenários hipotéticos condicionados aos dados, parâmetros "
    "e regras informados. Não constituem previsão de repasses futuros."
)


def _finito(v: float | None, campo: str) -> float | None:
    if v is not None and not math.isfinite(v):
        raise ValueError(f"{campo} deve ser um número finito")
    return v


class Ajuste(BaseModel):
    """
    Alteração de matrículas de um ente em uma categoria (etapa).
    - definir: substitui a contagem da categoria por `valor`;
    - acrescentar: soma `valor` novas matrículas à categoria;
    - converter: move `valor` matrículas de `categoria` para `categoria_destino` (total preservado).
    Contagens são usadas como informadas, sem arredondamento.
    """
    ibge: int
    categoria: str
    operacao: Operacao = "definir"
    valor: float = Field(ge=0)
    categoria_destino: Optional[str] = None

    @field_validator("valor")
    @classmethod
    def _valor_finito(cls, v):
        return _finito(v, "valor")

    @model_validator(mode="after")
    def _destino(self):
        if self.operacao == "converter":
            if not self.categoria_destino:
                raise ValueError("conversão exige categoria_destino")
            if self.categoria_destino == self.categoria:
                raise ValueError("categoria_destino deve ser diferente da categoria de origem")
        elif self.categoria_destino is not None:
            raise ValueError("categoria_destino só se aplica à operação converter")
        return self


class ParametrosSimulacao(BaseModel):
    """Parâmetros do motor. Campos omitidos usam os parâmetros de referência da base."""
    complementacao_vaaf: Optional[float] = Field(default=None, ge=0)
    complementacao_vaat: Optional[float] = Field(default=None, ge=0)
    complementacao_vaar: Optional[float] = Field(default=None, ge=0)
    max_nse: Optional[float] = None
    min_nse: Optional[float] = None
    max_nf: Optional[float] = None
    min_nf: Optional[float] = None
    pesos_vaaf: Optional[list[float]] = None
    pesos_vaat: Optional[list[float]] = None

    @model_validator(mode="after")
    def _finitos(self):
        for nome in ["complementacao_vaaf", "complementacao_vaat", "complementacao_vaar",
                     "max_nse", "min_nse", "max_nf", "min_nf"]:
            _finito(getattr(self, nome), nome)
        for nome in ["pesos_vaaf", "pesos_vaat"]:
            for v in getattr(self, nome) or []:
                _finito(v, nome)
                if v < 0:
                    raise ValueError(f"{nome} não aceita valores negativos")
        return self


class HipoteseReceita(BaseModel):
    """
    FND-10 — Hipótese de receita. Valores nominais, sem deflacionamento.
    A taxa incide apenas sobre as rubricas listadas; as complementações da União
    permanecem fixas, salvo indicação explícita.
    """
    tipo: Literal["constante", "crescimento"] = "constante"
    taxa: float = 0.0
    rubricas: list[RubricaReceita] = Field(default_factory=lambda: ["recursos_vaaf", "recursos_vaat"])
    complementacoes: Literal["fixas", "acompanham_taxa"] = "fixas"
    fonte_taxa: Optional[str] = None

    @model_validator(mode="after")
    def _coerencia(self):
        _finito(self.taxa, "taxa")
        if self.taxa <= -1:
            raise ValueError("taxa deve ser maior que -100%")
        if self.tipo == "constante" and self.taxa != 0:
            raise ValueError("receita constante exige taxa 0")
        if len(set(self.rubricas)) != len(self.rubricas):
            raise ValueError("rubricas repetidas")
        return self


class CenarioRequest(BaseModel):
    base_id: Optional[str] = None
    ano_exercicio: Optional[int] = None
    ajustes: list[Ajuste] = Field(default_factory=list)
    parametros: ParametrosSimulacao = Field(default_factory=ParametrosSimulacao)
    receita: HipoteseReceita = Field(default_factory=HipoteseReceita)
    recorte: Recorte = "estaduais_df"
    selecionadas: list[int] = Field(default_factory=list)
    descricao: Optional[str] = None
