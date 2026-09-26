from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Numero = Annotated[float, Field(ge=0, le=1e15)]
Contagem = Annotated[int, Field(strict=True, ge=0, le=1_000_000_000)]
Identificador = Annotated[int, Field(strict=True, gt=0)]


class Contrato(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class AjusteMatricula(Contrato):
    ibge: Identificador
    etapa: str = Field(min_length=1, max_length=160)
    operacao: Literal["definir", "adicionar", "converter", "percentual"] = "definir"
    valor: float = Field(ge=0, le=1_000_000_000)
    destino: str | None = None

    @model_validator(mode="after")
    def conferir(self):
        if self.operacao != "percentual" and not self.valor.is_integer():
            raise ValueError("Matrículas devem ser contagens inteiras.")
        if self.operacao == "percentual" and self.valor > 10000:
            raise ValueError("Percentual deve ser no máximo 10.000%.")
        if self.operacao == "converter":
            if not self.destino or self.destino == self.etapa:
                raise ValueError("Conversão exige uma categoria de destino diferente.")
        elif self.destino is not None:
            raise ValueError("Destino é permitido apenas em conversões.")
        return self


class PontoPIB(Contrato):
    ano: int = Field(ge=1900, le=2100)
    valor: float = Field(gt=0, le=1e20)


class Receita(Contrato):
    metodo: Literal["informada", "pib_cagr"] = "informada"
    taxa_percentual: float = Field(default=0, gt=-100, le=1000)
    rubricas: list[Literal["recursos_vaaf", "recursos_vaat", "outras_receitas_vaat"]] = Field(
        default_factory=lambda: ["recursos_vaaf", "recursos_vaat"], min_length=1, max_length=3
    )
    complementacoes: Literal["fixas", "proporcionais"] = "fixas"
    fonte: str = Field(default="Hipótese informada pelo usuário", max_length=1000)
    pib: list[PontoPIB] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def conferir(self):
        if len(self.rubricas) != len(set(self.rubricas)):
            raise ValueError("Rubricas de receita repetidas.")
        if self.metodo == "pib_cagr":
            if len(self.pib) < 2 or len({p.ano for p in self.pib}) != len(self.pib):
                raise ValueError("Informe pelo menos dois anos distintos de PIB nominal.")
            if not self.fonte.strip() or self.fonte == "Hipótese informada pelo usuário":
                raise ValueError("Informe a fonte da série de PIB nominal.")
            if self.taxa_percentual != 0:
                raise ValueError("CAGR calcula a taxa; não informe também uma taxa manual.")
            if not -100 < self.taxa() <= 1000:
                raise ValueError("Taxa calculada fora dos limites de simulação.")
        elif self.pib:
            raise ValueError("Série de PIB exige método pib_cagr.")
        return self

    def taxa(self):
        if self.metodo == "informada":
            return self.taxa_percentual
        pontos = sorted(self.pib, key=lambda p: p.ano)
        a, b = pontos[0], pontos[-1]
        return 100 * ((b.valor / a.valor) ** (1 / (b.ano - a.ano)) - 1)


class Parametros(Contrato):
    complementacao_vaaf: Numero | None = None
    complementacao_vaat: Numero | None = None
    complementacao_vaar: Numero | None = None
    min_nse: float | None = Field(default=None, gt=0, le=10)
    max_nse: float | None = Field(default=None, gt=0, le=10)
    min_nf: float | None = Field(default=None, gt=0, le=10)
    max_nf: float | None = Field(default=None, gt=0, le=10)
    pesos_vaaf: dict[str, Annotated[float, Field(gt=0, le=10)]] = Field(default_factory=dict)
    pesos_vaat: dict[str, Annotated[float, Field(gt=0, le=10)]] = Field(default_factory=dict)


class Recorte(Contrato):
    tipo: Literal["estaduais", "todas", "selecionadas", "propag"] = "estaduais"
    ufs: list[str] = Field(default_factory=list, max_length=27)


class CenarioRequest(Contrato):
    base_id: str = Field(default="legado", pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    nome: str = Field(default="Cenário nacional", min_length=1, max_length=120)
    ano_exercicio: int | None = Field(default=None, ge=2000, le=2100)
    ajustes: list[AjusteMatricula] = Field(default_factory=list, max_length=2000)
    parametros: Parametros = Field(default_factory=Parametros)
    receita: Receita = Field(default_factory=Receita)
    recorte: Recorte = Field(default_factory=Recorte)
    fator_amazonico: bool = False


class TrajetoriaRequest(Contrato):
    cenario: CenarioRequest
    ano_inicial: int = Field(ge=2000, le=2100)
    ano_final: int = Field(ge=2000, le=2100)
    entes: list[Identificador] = Field(min_length=1, max_length=100)
    etapa: str
    aumento_total_percentual: float = Field(ge=0, le=1000)
    operacao: Literal["adicionar", "converter"] = "adicionar"
    origem: str | None = None
    hipotese: str = Field(min_length=10, max_length=1000)

    @model_validator(mode="after")
    def conferir(self):
        if not self.ano_inicial < self.ano_final <= self.ano_inicial + 15:
            raise ValueError("Trajetória deve cobrir de 1 a 15 anos.")
        if len(set(self.entes)) != len(self.entes):
            raise ValueError("Entes repetidos na trajetória.")
        if self.operacao == "converter" and (not self.origem or self.origem == self.etapa):
            raise ValueError("Conversão exige categoria de origem diferente da EPT.")
        if self.operacao == "adicionar" and self.origem is not None:
            raise ValueError("Origem é permitida apenas em conversões.")
        if self.cenario.ajustes:
            raise ValueError("Trajetória gera os próprios ajustes; remova ajustes avulsos.")
        return self
