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
CenarioSimulacaoId = Literal["B", "C", "D"]
ModoCenarios = Literal["matriculas_independentes", "legado_receita"]
CENARIOS_SIMULACAO_ORDEM: tuple[CenarioSimulacaoId, ...] = ("B", "C", "D")

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
    cenario: CenarioSimulacaoId = "B"
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
    modo_cenarios: Optional[ModoCenarios] = None
    cenarios_ativos: Optional[list[CenarioSimulacaoId]] = None
    ajustes: list[Ajuste] = Field(default_factory=list)
    ajustes_por_cenario: Optional[dict[CenarioSimulacaoId, list[Ajuste]]] = None
    parametros: ParametrosSimulacao = Field(default_factory=ParametrosSimulacao)
    receita: HipoteseReceita = Field(default_factory=HipoteseReceita)
    recorte: Recorte = "estaduais_df"
    selecionadas: list[int] = Field(default_factory=list)
    descricao: Optional[str] = None

    @model_validator(mode="after")
    def _normalizar_cenarios(self):
        if self.cenarios_ativos is not None:
            vistos: list[CenarioSimulacaoId] = [
                c for c in CENARIOS_SIMULACAO_ORDEM if c in self.cenarios_ativos
            ]
            self.cenarios_ativos = vistos

        if self.ajustes_por_cenario is not None:
            normalizado: dict[CenarioSimulacaoId, list[Ajuste]] = {}
            for cen in CENARIOS_SIMULACAO_ORDEM:
                if cen in self.ajustes_por_cenario:
                    normalizado[cen] = [
                        aj.model_copy(update={"cenario": cen})
                        for aj in self.ajustes_por_cenario[cen]
                    ]
            self.ajustes_por_cenario = normalizado
            if not self.ajustes:
                self.ajustes = [
                    aj for cen in CENARIOS_SIMULACAO_ORDEM for aj in normalizado.get(cen, [])
                ]

        tem_config_independente = (
            self.modo_cenarios == "matriculas_independentes"
            or self.ajustes_por_cenario is not None
            or self.cenarios_ativos is not None
            or any(a.cenario in ("C", "D") for a in self.ajustes)
        )
        if self.modo_cenarios == "legado_receita" and (
            self.ajustes_por_cenario is not None
            or self.cenarios_ativos is not None
            or any(a.cenario in ("C", "D") for a in self.ajustes)
        ):
            raise ValueError(
                "O modo legado de receita não aceita ajustes próprios para os cenários C ou D."
            )
        if tem_config_independente and self.receita.tipo != "constante":
            raise ValueError(
                "Cenários independentes (A–D) exigem receita constante em todos os cenários."
            )
        return self

    def usa_cenarios_independentes(self) -> bool:
        """Indica se a requisição executa os cenários independentes A–D com receita constante."""
        if self.modo_cenarios == "matriculas_independentes":
            return True
        if self.modo_cenarios == "legado_receita":
            return False
        if self.receita.tipo == "crescimento":
            return False
        return (
            self.ajustes_por_cenario is not None
            or self.cenarios_ativos is not None
            or any(a.cenario in ("C", "D") for a in self.ajustes)
        )

    def cenarios_simulacao(self) -> list[CenarioSimulacaoId]:
        """Retorna a lista ordenada de cenários de simulação (B, C, D) a executar."""
        if not self.usa_cenarios_independentes():
            return ["B"]
        if self.cenarios_ativos is not None:
            return list(self.cenarios_ativos)
        return list(CENARIOS_SIMULACAO_ORDEM)

    def mapa_ajustes_por_cenario(self) -> dict[CenarioSimulacaoId, list[Ajuste]]:
        """Retorna os ajustes separados por cenário B, C e D."""
        mapa: dict[CenarioSimulacaoId, list[Ajuste]] = {"B": [], "C": [], "D": []}
        if self.ajustes_por_cenario is not None:
            for cen in CENARIOS_SIMULACAO_ORDEM:
                for aj in self.ajustes_por_cenario.get(cen, []):
                    mapa[cen].append(aj.model_copy(update={"cenario": cen}))
            return mapa
        for aj in self.ajustes:
            mapa[aj.cenario].append(aj)
        return mapa
