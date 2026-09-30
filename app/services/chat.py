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
Diferença observada não é causa. Se causa_demonstravel for falso, não invente o motivo da mudança.
Para transferência de matrículas entre etapas, chame consultar_ponderacoes uma única vez. Compare os pesos. Peso maior aumenta a matrícula ponderada e pode alterar a participação no fundo, mas não prova que o repasse sobe. Não execute simulação e não ofereça criar um cenário. Oriente a tela Município para ver o número.
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
    mensagens = [
        {"role": "system", "content": SISTEMA},
        {"role": "system", "content": "Contexto selecionado pelo usuário, ainda não verificado: " + json.dumps(contexto, ensure_ascii=False)},
        *anteriores,
        {"role": "user", "content": pedido.mensagem},
    ]
    evidencias = []
    inicio = time.perf_counter()
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
    duracao = int((time.perf_counter() - inicio) * 1000)
    mensagem_id = repositorio.acrescentar_mensagem(conversa_id, "assistant", texto)
    repositorio.registrar_evidencias(mensagem_id, evidencias)
    repositorio.registrar_chamada(
        mensagem_id,
        modelo=modelo_efetivo,
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
