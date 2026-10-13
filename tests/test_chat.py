"""Chat consulta dados gravados e não envia a chave ao provedor."""

import inspect
import json
from unittest.mock import patch

from sqlalchemy import create_engine

from app.auth.deps import get_current_user
from app.auth.models import Role, UserRecord
from app.db.schema import (
    base_aliases,
    base_sources,
    base_versions,
    categories,
    entities,
    financial_inputs,
    metadata,
    scenario_results,
    scenarios,
    source_files,
)
from app.integrations.openrouter import completar
from app.services import chat as servico
from app.services.chat import extrair_chamadas_texto, pergunta_de_indicador, texto_da_consulta_municipal
import pandas as pd

from app.services.chat_tools import (
    comparar_simulacoes,
    consultar_municipio,
    consultar_ponderacoes,
    consultar_simulacao,
    escolher_etapa,
    limpar,
    simular_transferencia,
)


def test_chamada_escrita_no_texto_nao_vai_para_o_usuario():
    bruto = """<tool_call>
<function=consultar_ponderacoes>
<parameter=ibge>
2304400
</parameter>
<parameter=ano>
2026
</parameter>
</function>
</tool_call>"""
    visivel, chamadas = extrair_chamadas_texto(bruto)
    assert visivel == ""
    assert chamadas[0]["function"]["name"] == "consultar_ponderacoes"
    assert json.loads(chamadas[0]["function"]["arguments"]) == {"ibge": 2304400, "ano": 2026}


def test_rota_exige_usuario_autenticado():
    from app.api.chat import enviar

    dependencia = inspect.signature(enviar).parameters["usuario"].default
    assert dependencia.dependency is get_current_user


def test_modelo_pago_e_recusado_antes_da_chamada(monkeypatch):
    monkeypatch.setenv("FUNDEB_CHAT_ENABLED", "true")
    monkeypatch.setenv("FUNDEB_CHAT_FREE_ONLY", "true")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o")
    monkeypatch.setenv("OPENROUTER_API_KEY", "chave-de-teste")
    from app.integrations.openrouter import ErroChat
    from app.schemas.chat import PedidoChat

    usuario = UserRecord(cpf="11111111111", role=Role.usuario)
    with patch("app.integrations.openrouter.urllib.request.urlopen") as aberto:
        try:
            servico.responder(usuario, PedidoChat(mensagem="quanto é o VAAF?"))
        except ErroChat as exc:
            assert exc.situacao == "modelo_pago"
        else:
            raise AssertionError("modelo pago deveria ser recusado")
    aberto.assert_not_called()


def test_chave_nao_entra_no_corpo_do_pedido():
    capturado = {}

    class Resposta:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({
                "model": "openrouter/free",
                "choices": [{"message": {"role": "assistant", "content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }).encode()

    def urlopen(pedido, timeout=0):
        capturado["corpo"] = pedido.data.decode()
        capturado["autorizacao"] = pedido.get_header("Authorization")
        return Resposta()

    with patch("app.integrations.openrouter.urllib.request.urlopen", urlopen):
        saida = completar([{"role": "user", "content": "oi"}], [], modelo="openrouter/free", chave="chave-de-teste")
    assert "chave-de-teste" not in capturado["corpo"]
    assert capturado["autorizacao"] == "Bearer chave-de-teste"
    assert "chave-de-teste" not in json.dumps(saida)


def _banco():
    motor = create_engine("sqlite://")
    metadata.create_all(motor)
    return motor


def _usuario(cpf="11111111111"):
    return UserRecord(cpf=cpf, role=Role.usuario)


def test_simulacao_de_outro_usuario_nao_e_revelada():
    motor = _banco()
    with motor.begin() as conn:
        conn.execute(scenarios.insert().values(
            id="cena-1",
            created_at="2026-01-01",
            owner_cpf="99999999999",
            base_id="fundeb-2026",
            engine_version="teste",
            request_json="{}",
            snapshot=b"x",
            snapshot_sha256="a" * 64,
        ))
    assert consultar_simulacao({"cenario_id": "cena-1"}, _usuario(), engine=motor)["motivo"] == "nao_encontrado"


def test_comparacao_nao_afirma_causa():
    motor = _banco()
    with motor.begin() as conn:
        conn.execute(scenarios.insert().values(
            id="cena-2",
            created_at="2026-01-01",
            owner_cpf="11111111111",
            base_id="fundeb-2026",
            base_version=None,
            engine_version="teste",
            request_json="{}",
            snapshot=b"x",
            snapshot_sha256="b" * 64,
        ))
        for variante, valor in (("A", 10), ("B", 12)):
            conn.execute(scenario_results.insert().values(
                scenario_id="cena-2",
                variant=variante,
                ibge=2304400,
                position=0,
                values_json=json.dumps({"vaaf_final": valor, "cpf": "nao-enviar"}),
            ))
    saida = comparar_simulacoes(
        {"cenario_id": "cena-2", "ibge": 2304400},
        _usuario(),
        engine=motor,
    )
    assert saida["causa_demonstravel"] is False
    assert saida["diferencas"]["vaaf_final"]["diferenca_observada"] == 2
    assert "cpf" not in json.dumps(saida)


def test_municipio_ausente_e_ambiguo():
    motor = _banco()
    with motor.begin() as conn:
        conn.execute(source_files.insert().values(sha256="c" * 64, size=1, content=b"x"))
        conn.execute(base_versions.insert().values(
            version_id="v1",
            base_id="fundeb-2026",
            year=2026,
            created_at="2026-01-01",
            manifest="{}",
            snapshot=b"x",
            snapshot_sha256="d" * 64,
            etl_sha256="e" * 64,
            source_commit="abc",
        ))
        conn.execute(base_aliases.insert().values(base_id="fundeb-2026", version_id="v1"))
        conn.execute(base_sources.insert().values(version_id="v1", path="origem.csv", source_sha256="c" * 64))
        for ibge, rede in ((2304400, "municipal"), (23, "estadual")):
            conn.execute(entities.insert().values(
                version_id="v1", ibge=ibge, position=0, uf="CE", name="Fortaleza", network=rede,
            ))
        conn.execute(financial_inputs.insert().values(
            version_id="v1", ibge=2304400, values_json=json.dumps({"vaaf_final": 1, "senha": "x"}),
        ))
    ausente = consultar_municipio({"nome": "Cidade Inexistente", "ano": 2026}, _usuario(), engine=motor)
    assert ausente["encontrado"] is False
    assert ausente["motivo"] == "nao_encontrado"
    ambiguo = consultar_municipio({"nome": "Fortaleza", "ano": 2026}, _usuario(), engine=motor)
    assert ambiguo["motivo"] == "ambiguo"
    assert len(ambiguo["candidatos"]) == 2
    escolhido = consultar_municipio(
        {"nome": "Fortaleza", "ano": 2026, "ibge": 2304400}, _usuario(), engine=motor,
    )
    assert escolhido["encontrado"] is True
    assert escolhido["tipo_dado"] == "oficial_importado"
    assert "resultado_tela" not in escolhido
    assert "senha" not in json.dumps(escolhido)


def test_consulta_municipal_devolve_os_numeros_da_tela():
    motor = _banco()
    with motor.begin() as conn:
        conn.execute(base_versions.insert().values(
            version_id="v1",
            base_id="fundeb-2024",
            year=2024,
            created_at="2024-01-01",
            manifest=json.dumps({"homologada": False, "base_id": "fundeb-2024", "ano_exercicio": 2024}),
            snapshot=b"x",
            snapshot_sha256="d" * 64,
            etl_sha256="e" * 64,
            source_commit="abc",
        ))
        conn.execute(base_aliases.insert().values(base_id="fundeb-2024", version_id="v1"))
        conn.execute(entities.insert().values(
            version_id="v1", ibge=2307304, position=0, uf="CE", name="Juazeiro do Norte", network="municipal",
        ))
        conn.execute(financial_inputs.insert().values(
            version_id="v1",
            ibge=2307304,
            values_json=json.dumps({"recursos_vaaf": 150612916.19, "nse": 1.01}),
        ))
    dataset = type("Base", (), {})()
    dataset.cenario_atual = pd.DataFrame([{
        "ibge": 2307304,
        "matriculas_vaaf": 40297.27,
        "matriculas_vaat": 42934.98,
        "vaaf_final": 5361.43,
        "recursos_vaaf_final": 216050955.87,
        "recursos_vaaf": 150612916.2,
    }])
    saida = consultar_municipio(
        {"nome": "Juazeiro do Norte", "ano": 2024},
        _usuario(),
        engine=motor,
        dataset=dataset,
    )
    tela = saida["resultado_tela"]["indicadores"]
    assert tela["matriculas_vaaf"]["exibicao"] == "40.297,27"
    assert tela["vaaf_final"]["exibicao"] == "5.361,43"
    assert tela["recursos_vaaf_final"]["exibicao"] == "R$ 216.050.956"
    assert tela["recursos_vaaf_final"]["rotulo"] == "Recursos VAAF totais"
    assert saida["valores_oficiais"]["recursos_vaaf"] == 150612916.19
    assert "matriculas_vaaf" not in saida["valores_oficiais"]


def test_ponderacoes_comparam_etapas_sem_afirmar_aumento_de_repasse():
    motor = _banco()
    with motor.begin() as conn:
        conn.execute(base_versions.insert().values(
            version_id="v1",
            base_id="fundeb-2026",
            year=2026,
            created_at="2026-01-01",
            manifest="{}",
            snapshot=b"x",
            snapshot_sha256="d" * 64,
            etl_sha256="e" * 64,
            source_commit="abc",
        ))
        conn.execute(base_aliases.insert().values(base_id="fundeb-2026", version_id="v1"))
        for nome, peso in (
            ("Educação Especial - Eja Médio", 1.4),
            ("Eja Médio", 1.0),
            ("Eja Médio Integrado À Ed. Profissional", 1.35),
        ):
            conn.execute(categories.insert().values(
                version_id="v1", code=nome, position=0, name=nome, weight_vaaf=peso, weight_vaat=peso,
            ))
    saida = consultar_ponderacoes(
        {"ano": 2026, "etapas": ["EJA médio", "profissional"]},
        _usuario(),
        engine=motor,
    )
    assert saida["causa_demonstravel"] is False
    assert "não executa uma simulação" in saida["leitura"]
    primeiro = saida["grupos"][0]["etapas"][0]["nome"]
    assert primeiro == "Eja Médio"
    assert saida["grupos"][1]["etapas"][0]["peso_vaaf"] == 1.35


def test_consulta_encontra_capital_com_acento():
    motor = _banco()
    with motor.begin() as conn:
        conn.execute(base_versions.insert().values(
            version_id="v1",
            base_id="fundeb-2024",
            year=2024,
            created_at="2024-01-01",
            manifest="{}",
            snapshot=b"x",
            snapshot_sha256="d" * 64,
            etl_sha256="e" * 64,
            source_commit="abc",
        ))
        conn.execute(base_aliases.insert().values(base_id="fundeb-2024", version_id="v1"))
        conn.execute(entities.insert().values(
            version_id="v1", ibge=2111300, position=0, uf="MA", name="SAO LUIS", network="rede municipal",
        ))
    dataset = type("Base", (), {})()
    dataset.cenario_atual = pd.DataFrame([{
        "ibge": 2111300,
        "matriculas_vaaf": 119544.70,
        "vaaf_final": 5361.43,
        "recursos_vaaf_final": 640930514.76,
    }])
    saida = consultar_municipio(
        {"nome": "São Luís", "ano": 2024},
        _usuario(),
        engine=motor,
        dataset=dataset,
    )
    assert saida["encontrado"] is True
    assert saida["ente"]["ibge"] == 2111300
    assert saida["resultado_tela"]["indicadores"]["matriculas_vaaf"]["exibicao"] == "119.544,70"


def test_pergunta_de_matriculas_responde_com_a_tela():
    pergunta = "qual o valor de Matrículas VAAF (ponderadas) na cidade de Juazeiro do Norte no ano de 2024?"
    assert pergunta_de_indicador(pergunta) == ("Juazeiro do Norte", 2024)
    assert pergunta_de_indicador("se eu transferir 100 alunos de Fortaleza do médio para o técnico em 2025") is None
    texto = texto_da_consulta_municipal({
        "encontrado": True,
        "ano_exercicio": 2024,
        "base_id": "fundeb-2024",
        "homologada": False,
        "ente": {"name": "Juazeiro do Norte", "uf": "CE", "network": "municipal", "ibge": 2307304},
        "resultado_tela": {
            "indicadores": {
                "matriculas_vaaf": {"rotulo": "Matrículas VAAF (ponderadas)", "exibicao": "40.297,27"},
                "vaaf_final": {"rotulo": "VAAF por aluno", "exibicao": "5.361,43"},
                "recursos_vaaf_final": {"rotulo": "Recursos VAAF totais", "exibicao": "R$ 216.050.956"},
            }
        },
    })
    assert "40.297,27" in texto
    assert "5.361,43" in texto
    assert "R$ 216.050.956" in texto
    assert "36.107" not in texto
    assert "|" not in texto


def test_medio_sem_adjetivo_nao_escolhe_o_integral():
    opcoes = [
        {"codigo": "integral", "nome": "Ensino Médio Integral", "alunos": 127324},
        {"codigo": "parcial", "nome": "Ensino Médio Parcial", "alunos": 98483},
        {"codigo": "eja", "nome": "Eja Médio", "alunos": 8345},
    ]
    assert escolher_etapa("médio", opcoes)["codigo"] == "parcial"


def test_transferencia_de_fortaleza_usa_a_rede_estadual_quando_o_municipio_nao_tem_a_etapa():
    class Base:
        simulacao_habilitada = True
        modo_ponderador = "drec"
        defaults_complementacao = {"vaaf": 1, "vaat": 1, "vaar": 0}
        etapas = ["parcial", "tecnico"]
        etapas_nomes = {
            "parcial": "Ensino Médio Parcial",
            "tecnico": "Ensino Médio Integrado À Ed. Profissional",
        }
        pesos = pd.DataFrame([
            {"etapa": "parcial", "nome": "Ensino Médio Parcial", "peso_vaaf": 1.25, "peso_vaat": 1.25},
            {"etapa": "tecnico", "nome": "Ensino Médio Integrado À Ed. Profissional", "peso_vaaf": 1.35, "peso_vaat": 1.35},
        ])
        complementar = pd.DataFrame([
            {"ibge": 2304400, "uf": "CE", "nome": "Fortaleza"},
            {"ibge": 23, "uf": "CE", "nome": "Ceará"},
        ])
        matriculas = pd.DataFrame([
            {"ibge": 2304400, "parcial": 0, "tecnico": 0},
            {"ibge": 23, "parcial": 1000, "tecnico": 500},
        ])

    def motor(matriculas, **_kwargs):
        linha = matriculas.loc[matriculas["ibge"] == 23].iloc[0]
        ponderado = float(linha["parcial"]) * 1.25 + float(linha["tecnico"]) * 1.35
        return pd.DataFrame([{
            "ibge": 23,
            "vaaf_final": 10.0,
            "matriculas_vaaf": ponderado,
            "recursos_vaaf": ponderado * 10,
            "recursos_vaaf_final": ponderado * 10,
            "complemento_vaaf": 0.0,
            "recursos_fundeb": ponderado * 10,
        }])

    saida = simular_transferencia(
        {"nome": "Fortaleza", "ano": 2025, "origem": "médio", "destino": "técnico", "alunos": 100},
        _usuario(),
        dataset=Base(),
        simulador=motor,
    )
    assert saida["encontrado"] is True
    assert saida["ente"]["ibge"] == 23
    assert saida["aviso"]
    assert saida["origem"]["codigo"] == "parcial"
    assert saida["destino"]["codigo"] == "tecnico"
    assert saida["alunos_movidos"] == 100
    assert saida["variacao"]["matriculas_vaaf"] == 10
    assert saida["variacao"]["recursos_vaaf"] == 100
    assert saida["causa_demonstravel"] is True


def test_limpar_remove_credenciais():
    assert "cpf" not in limpar({"cpf": "1", "vaaf_final": 2})
