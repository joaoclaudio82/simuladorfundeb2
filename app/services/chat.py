"""Organiza a conversa e só envia ao modelo o que as ferramentas devolveram."""

from __future__ import annotations

import json
import re
import time
import uuid

from app.auth.models import Role, UserRecord
from app.core.chat_config import chave_openrouter, chat_habilitado, modelo_configurado, modelo_permitido
from app.integrations.openrouter import ErroChat, completar
from app.repositories import chat as repositorio
from app.schemas.chat import PedidoChat
from app.services.chat_tools import FERRAMENTAS, executar

SISTEMA = """Você responde em português sobre o FUNDEB e sobre este simulador.
Números só podem vir do resultado de uma ferramenta. Se a ferramenta não encontrou o dado, diga o que faltou.
Não escolha ano, rede ou indicador quando a consulta vier ambígua. Se faltar o exercício ou a rede, pergunte em vez de repetir ferramentas.
Separe três coisas: valor oficial importado, resultado simulado e a sua interpretação.
Uma base não homologada não é repasse oficial. Simulação não é previsão de repasse.
Se a ferramenta devolver periodo_exibicao, identifique a base por esse período (por exemplo, 1 a 8/2026) em vez de destacar "não homologada".
Diferença observada não é causa. Se causa_demonstravel for falso, não invente o motivo da mudança.
Quando a pergunta for o valor de matrículas ponderadas, VAAF por aluno, VAAT por aluno, recursos VAAF ou VAAT, ou complementações de um município, chame consultar_municipio uma vez e copie resultado_tela. Matrículas VAAF (ponderadas) é matriculas_vaaf. VAAF por aluno é vaaf_final. Recursos VAAF totais é recursos_vaaf_final. VAAT por aluno é vaat_final. Recursos VAAT totais é recursos_vaat_final. Complementação VAAT é complemento_vaat. Use o campo exibicao. valores_oficiais são insumos importados e não substituem esses indicadores. Não calcule nem invente o número.
Quando a pergunta for quanto muda o VAAF, o repasse ou os recursos se alunos passarem de uma etapa para outra, chame simular_transferencia uma única vez, com nome, ano, origem, destino e alunos. Responda só com os números dessa ferramenta: rede, etapas, pesos, alunos movidos, variação de vaaf_final, de recursos_vaaf e de recursos_fundeb. Se houver aviso, reproduza-o: a rede pedida pode não ter essas matrículas e o cálculo ter sido feito na rede estadual. Não troque a etapa escolhida pela ferramenta e não invente valor. Use consultar_ponderacoes apenas quando pedirem os pesos, sem quantidade de alunos.
Se a ferramenta devolver ambiguo ou nao_encontrado, pare e pergunte. Não repita a mesma consulta.
Cite exercício, versão da base, cenário e documento quando a ferramenta os devolver.
Não peça nem repita CPF, senha ou chave."""


_BLOCO_FERRAMENTA = re.compile(r"<tool_call>(.*?)</tool_call>", re.IGNORECASE | re.DOTALL)
_NOME_FUNCAO = re.compile(r"<function(?:=|\s+name=)[\"']?([A-Za-z0-9_]+)", re.IGNORECASE)
_PARAMETRO = re.compile(
    r"<parameter(?:=|\s+name=)[\"']?([A-Za-z0-9_]+)[\"']?[^>]*>(.*?)</parameter>",
    re.IGNORECASE | re.DOTALL,
)


def extrair_chamadas_texto(conteudo: str) -> tuple[str, list[dict]]:
    """O modelo gratuito às vezes escreve a consulta no texto em vez de usar a ferramenta."""
    if not conteudo or "<tool_call" not in conteudo.lower():
        return (conteudo or "").strip(), []
    chamadas = []

    def substituir(trecho):
        bloco = trecho.group(1)
        nome = _NOME_FUNCAO.search(bloco)
        if not nome:
            return ""
        argumentos = {}
        for chave, valor in _PARAMETRO.findall(bloco):
            texto = valor.strip()
            argumentos[chave] = int(texto) if texto.isdigit() else texto
        chamadas.append({
            "id": uuid.uuid4().hex,
            "type": "function",
            "function": {
                "name": nome.group(1),
                "arguments": json.dumps(argumentos, ensure_ascii=False),
            },
        })
        return ""

    limpo = _BLOCO_FERRAMENTA.sub(substituir, conteudo)
    limpo = re.sub(r"<tool_call>[\s\S]*", "", limpo, flags=re.IGNORECASE).strip()
    return limpo, chamadas


_MOVIMENTO = re.compile(r"transfer|tirar|mover|passar|aument|reduz", re.IGNORECASE)
_CIDADE_ANO = re.compile(
    r"(?:cidade|munic[ií]pio)\s+de\s+(.+?)\s+(?:no\s+ano(?:\s+de)?|em)\s+(20\d{2})",
    re.IGNORECASE,
)
_CIDADE_VIRGULA_ANO = re.compile(
    r"(?:cidade|munic[ií]pio)\s+(?:de\s+|do\s+|da\s+)?([^,;?]+?)\s*[,;].*?\b(20\d{2})\b",
    re.IGNORECASE,
)
_INDICADOR = re.compile(r"valor|quanto|matr[ií]cula|vaaf|vaat|recursos", re.IGNORECASE)
_ORDEM_TELA = (
    "matriculas_vaaf",
    "matriculas_vaat",
    "vaaf_final",
    "recursos_vaaf_final",
    "complemento_vaaf",
    "vaat_final",
    "recursos_vaat_final",
    "complemento_vaat",
    "complemento_vaar",
    "complemento_uniao",
)


def pergunta_de_indicador(mensagem: str) -> tuple[str, int] | None:
    """Pergunta pelo número atual de uma rede. Transferência de alunos fica com o modelo."""
    if not mensagem or _MOVIMENTO.search(mensagem) or not _INDICADOR.search(mensagem):
        return None
    achado = _CIDADE_ANO.search(mensagem) or _CIDADE_VIRGULA_ANO.search(mensagem)
    if not achado:
        return None
    nome = achado.group(1).strip(" .?")
    if len(nome) < 3:
        return None
    return nome, int(achado.group(2))


def texto_da_consulta_municipal(resultado: dict) -> str | None:
    if not resultado:
        return None
    if resultado.get("motivo") == "ambiguo":
        linhas = ["Há mais de uma rede com esse nome. Informe qual delas:"]
        for candidato in resultado.get("candidatos") or []:
            linhas.append(
                f"- {candidato.get('name') or candidato.get('nome')} "
                f"({candidato.get('uf')}), rede {candidato.get('network') or 'não informada'}, "
                f"IBGE {candidato.get('ibge')}"
            )
        return "\n".join(linhas)
    if resultado.get("motivo") == "nao_encontrado":
        return "Não encontrei essa rede nesse exercício."
    tela = resultado.get("resultado_tela") or {}
    indicadores = tela.get("indicadores") or {}
    if not indicadores:
        return None
    ente = resultado.get("ente") or {}
    nome = ente.get("name") or ente.get("nome") or "Rede"
    linhas = [
        f"{nome} ({ente.get('uf') or ''}), {ente.get('network') or 'rede municipal'}, exercício {resultado.get('ano_exercicio')}.",
        "Números da tela Simular, sem alteração de matrículas.",
        "",
    ]
    for chave in _ORDEM_TELA:
        item = indicadores.get(chave)
        if not item:
            continue
        linhas.append(f"- {item['rotulo']}: {item['exibicao']}")
    periodo = resultado.get("periodo_exibicao")
    if periodo:
        linhas.append("")
        linhas.append(
            f"Base {resultado.get('base_id')}, período {periodo}. "
            "Estes números são o resultado do simulador, não o repasse oficial publicado."
        )
    elif resultado.get("homologada") is False:
        linhas.append("")
        linhas.append(
            f"A base {resultado.get('base_id')} não está homologada. "
            "Estes números são o resultado do simulador, não o repasse oficial publicado."
        )
    return "\n".join(linhas)


def _referencias(resultados: list[dict]) -> list[dict]:
    saida = []
    for item in resultados:
        if not item.get("encontrado"):
            continue
        tipo = item.get("tipo_dado") or "consulta"
        saida.append({
            "tipo": tipo,
            "descricao": item.get("base_id") or item.get("cenario_id") or tipo,
            "referencia": {
                chave: item.get(chave)
                for chave in ("ano_exercicio", "base_id", "version_id", "cenario_id", "base_version")
                if item.get(chave)
            },
        })
        for trecho in item.get("trechos") or []:
            saida.append({
                "tipo": "documento",
                "descricao": trecho.get("titulo"),
                "referencia": {"caminho": trecho.get("caminho"), "versao": trecho.get("versao")},
            })
    return saida


def _entregar(conversa_id, texto, evidencias, modelo, uso, inicio, situacao="ok", erro=None) -> dict:
    duracao = int((time.perf_counter() - inicio) * 1000)
    mensagem_id = repositorio.acrescentar_mensagem(conversa_id, "assistant", texto)
    repositorio.registrar_evidencias(mensagem_id, evidencias)
    repositorio.registrar_chamada(
        mensagem_id,
        modelo=modelo,
        uso=uso,
        duracao_ms=duracao,
        situacao=situacao,
        erro=erro,
    )
    return {
        "conversa_id": conversa_id,
        "resposta": texto,
        "referencias": evidencias,
        "situacao": situacao,
    }


def responder(usuario: UserRecord, pedido: PedidoChat) -> dict:
    if not chat_habilitado():
        raise ErroChat("desligado", "O chat está desligado.")
    modelo = modelo_configurado()
    if not modelo_permitido(modelo):
        raise ErroChat("modelo_pago", "Só é permitido um modelo gratuito.")
    chave = chave_openrouter()
    if not chave:
        raise ErroChat("sem_chave", "O chat ainda não tem chave do OpenRouter no servidor.")
    repositorio.garantir_tabelas()
    repositorio.indexar_documentos()
    admin = usuario.role == Role.admin
    contexto = pedido.contexto.model_dump()
    if pedido.conversa_id:
        conversa = repositorio.conversa_do_usuario(pedido.conversa_id, usuario.cpf, admin=admin)
        if not conversa:
            raise ErroChat("nao_encontrado", "Conversa não encontrada.")
        conversa_id = pedido.conversa_id
        repositorio.atualizar_contexto(conversa_id, contexto)
    else:
        conversa_id = repositorio.nova_conversa(usuario.cpf, contexto)
    anteriores = [
        {"role": item["role"], "content": item["content"]}
        for item in repositorio.listar_mensagens(conversa_id)
        if item["role"] in ("user", "assistant")
    ]
    repositorio.acrescentar_mensagem(conversa_id, "user", pedido.mensagem)
    inicio = time.perf_counter()
    consulta = pergunta_de_indicador(pedido.mensagem)
    if consulta:
        nome, ano = consulta
        argumentos = {"nome": nome, "ano": ano}
        if contexto.get("uf"):
            argumentos["uf"] = contexto["uf"]
        resultado = executar("consultar_municipio", argumentos, usuario)
        texto = texto_da_consulta_municipal(resultado)
        if texto:
            return _entregar(
                conversa_id,
                texto,
                _referencias([resultado]),
                modelo,
                {},
                inicio,
            )
    mensagens = [
        {"role": "system", "content": SISTEMA},
        {"role": "system", "content": "Contexto selecionado pelo usuário, ainda não verificado: " + json.dumps(contexto, ensure_ascii=False)},
        *anteriores,
        {"role": "user", "content": pedido.mensagem},
    ]
    evidencias = []
    situacao = "ok"
    erro = None
    uso = {}
    modelo_efetivo = modelo
    texto = ""
    try:
        for _ in range(3):
            resposta = completar(mensagens, FERRAMENTAS, modelo=modelo, chave=chave)
            modelo_efetivo = resposta["modelo"]
            uso = {
                "prompt_tokens": resposta.get("prompt_tokens"),
                "completion_tokens": resposta.get("completion_tokens"),
            }
            mensagem = resposta["mensagem"]
            chamadas = list(mensagem.get("tool_calls") or [])
            visivel, embutidas = extrair_chamadas_texto(mensagem.get("content") or "")
            if embutidas:
                chamadas.extend(embutidas)
                mensagem = {
                    "role": "assistant",
                    "content": visivel or None,
                    "tool_calls": chamadas,
                }
            if not chamadas:
                texto = visivel or "Não encontrei uma resposta com os dados disponíveis."
                break
            mensagens.append(mensagem)
            for chamada in chamadas:
                funcao = chamada.get("function") or {}
                try:
                    argumentos = json.loads(funcao.get("arguments") or "{}")
                except json.JSONDecodeError:
                    argumentos = {}
                resultado = executar(funcao.get("name"), argumentos, usuario)
                evidencias.extend(_referencias([resultado]))
                mensagens.append({
                    "role": "tool",
                    "tool_call_id": chamada.get("id"),
                    "content": json.dumps(resultado, ensure_ascii=False)[:8000],
                })
        else:
            mensagens.append({
                "role": "system",
                "content": "Responda agora com o que as ferramentas já devolveram. Não chame ferramentas. Se faltar exercício ou rede, peça esses dados e explique o mecanismo com os pesos já obtidos.",
            })
            resposta = completar(mensagens, modelo=modelo, chave=chave, escolha="none")
            modelo_efetivo = resposta["modelo"]
            uso = {
                "prompt_tokens": resposta.get("prompt_tokens"),
                "completion_tokens": resposta.get("completion_tokens"),
            }
            texto, _ = extrair_chamadas_texto(resposta["mensagem"].get("content") or "")
            texto = texto or (
                "Não consegui fechar a resposta. Informe o exercício e a rede, por exemplo Fortaleza municipal em 2026."
            )
    except ErroChat as exc:
        situacao = exc.situacao
        erro = exc.mensagem
        texto = exc.mensagem
    return _entregar(conversa_id, texto, evidencias, modelo_efetivo, uso, inicio, situacao, erro)
