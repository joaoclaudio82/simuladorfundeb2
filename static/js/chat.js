/**
 * Painel do assistente. A chave do modelo fica no servidor.
 */
(function () {
  const CHAVE = 'fundeb-chat-conversa';

  function texto(valor) {
    return document.createTextNode(valor == null ? '' : String(valor));
  }

  function avatar() {
    const marca = document.createElement('div');
    marca.className = 'chat-avatar';
    marca.setAttribute('aria-hidden', 'true');
    marca.innerHTML = '<i class="fas fa-comments"></i>';
    return marca;
  }

  function rico(alvo, conteudo) {
    String(conteudo || '').split(/(\*\*[^*]+\*\*)/g).forEach(function (parte) {
      if (!parte) return;
      if (parte.startsWith('**') && parte.endsWith('**') && parte.length > 4) {
        const forte = document.createElement('strong');
        forte.textContent = parte.slice(2, -2);
        alvo.appendChild(forte);
      } else {
        alvo.appendChild(texto(parte));
      }
    });
  }

  function escrever(destino, conteudo) {
    let paragrafo = null;
    let lista = null;
    String(conteudo || '').replace(/\r/g, '').split('\n').forEach(function (linhaTexto) {
      const item = linhaTexto.match(/^\s*[-*]\s+(.*)$/);
      if (!linhaTexto.trim()) {
        paragrafo = null;
        lista = null;
        return;
      }
      if (item) {
        paragrafo = null;
        if (!lista) {
          lista = document.createElement('ul');
          destino.appendChild(lista);
        }
        const li = document.createElement('li');
        rico(li, item[1]);
        lista.appendChild(li);
        return;
      }
      lista = null;
      if (!paragrafo) {
        paragrafo = document.createElement('p');
        destino.appendChild(paragrafo);
      } else {
        paragrafo.appendChild(document.createElement('br'));
      }
      rico(paragrafo, linhaTexto.replace(/^#{1,3}\s+/, ''));
    });
  }

  function semMarcacao(conteudo) {
    return String(conteudo || '')
      .replace(/<tool_call>[\s\S]*?<\/tool_call>/gi, '')
      .replace(/<tool_call>[\s\S]*$/i, '')
      .trim();
  }

  function linha(papel, conteudo) {
    const original = String(conteudo || '');
    const limpo = papel === 'assistant' ? semMarcacao(original) : original;
    if (papel === 'assistant' && !limpo && /<tool_call/i.test(original)) return null;
    const item = document.createElement('article');
    item.className = 'chat-bolha chat-bolha-' + papel;
    const corpo = document.createElement('div');
    corpo.className = 'chat-corpo';
    escrever(corpo, limpo);
    if (papel === 'assistant') item.appendChild(avatar());
    item.appendChild(corpo);
    return item;
  }

  function referencias(lista, destino) {
    if (!lista || !lista.length) return;
    const bloco = document.createElement('div');
    bloco.className = 'chat-refs';
    const titulo = document.createElement('span');
    titulo.textContent = 'Fontes';
    bloco.appendChild(titulo);
    lista.forEach(function (ref) {
      const item = document.createElement('em');
      item.appendChild(texto(ref.descricao || ref.tipo || 'referência'));
      bloco.appendChild(item);
    });
    destino.querySelector('.chat-corpo').appendChild(bloco);
  }

  function digitando() {
    const item = linha('assistant', '');
    item.id = 'chat-digitando';
    item.querySelector('.chat-corpo').replaceChildren();
    const pontos = document.createElement('span');
    pontos.className = 'chat-pontos';
    pontos.setAttribute('aria-label', 'Consultando');
    pontos.innerHTML = '<i></i><i></i><i></i>';
    item.querySelector('.chat-corpo').appendChild(pontos);
    return item;
  }

  document.addEventListener('DOMContentLoaded', async function () {
    if (typeof guardAuth !== 'function') return;
    try {
      await guardAuth();
    } catch (e) {
      return;
    }
    const resposta = await fetch('/static/chat.html?v=4');
    if (!resposta.ok) return;
    const embrulho = document.createElement('div');
    embrulho.innerHTML = await resposta.text();
    document.body.appendChild(embrulho);

    const painel = document.getElementById('chat-painel');
    const abrir = document.getElementById('chat-abrir');
    const mensagens = document.getElementById('chat-mensagens');
    const boasVindas = document.getElementById('chat-boas-vindas');
    const form = document.getElementById('chat-form');
    const contexto = document.getElementById('chat-contexto');
    let conversaId = sessionStorage.getItem(CHAVE);

    function rolar() {
      mensagens.scrollTop = mensagens.scrollHeight;
    }

    function mostrarBoasVindas(visivel) {
      boasVindas.hidden = !visivel;
    }

    function alternar(aberto) {
      painel.hidden = !aberto;
      abrir.setAttribute('aria-expanded', aberto ? 'true' : 'false');
      if (aberto) form.mensagem.focus();
    }

    abrir.addEventListener('click', function () { alternar(painel.hidden); });
    document.getElementById('chat-fechar').addEventListener('click', function () { alternar(false); });
    document.getElementById('chat-contexto-abrir').addEventListener('click', function () {
      const aberto = contexto.hidden;
      contexto.hidden = !aberto;
      this.setAttribute('aria-expanded', aberto ? 'true' : 'false');
    });

    if (conversaId) {
      try {
        const historico = await apiFetch('/api/chat/conversas/' + conversaId);
        const anteriores = (historico.mensagens || []).filter(function (msg) {
          return msg.role === 'user' || msg.role === 'assistant';
        });
        anteriores.forEach(function (msg) {
          const item = linha(msg.role, msg.content);
          if (item) mensagens.appendChild(item);
        });
        mostrarBoasVindas(anteriores.length === 0);
      } catch (e) {
        sessionStorage.removeItem(CHAVE);
        conversaId = null;
      }
    }

    form.mensagem.addEventListener('keydown', function (evento) {
      if (evento.key === 'Enter' && !evento.shiftKey) {
        evento.preventDefault();
        form.requestSubmit();
      }
    });

    document.querySelectorAll('[data-sugestao]').forEach(function (botao) {
      botao.addEventListener('click', function () {
        form.mensagem.value = botao.getAttribute('data-sugestao');
        form.requestSubmit();
      });
    });

    form.addEventListener('submit', async function (evento) {
      evento.preventDefault();
      const dados = new FormData(form);
      const mensagem = String(dados.get('mensagem') || '').trim();
      if (!mensagem || form.querySelector('button[type="submit"]').disabled) return;
      mostrarBoasVindas(false);
      mensagens.appendChild(linha('user', mensagem));
      const espera = digitando();
      mensagens.appendChild(espera);
      form.mensagem.value = '';
      const botao = form.querySelector('button[type="submit"]');
      botao.disabled = true;
      rolar();
      const ano = String(dados.get('ano') || '').trim();
      const pedido = {
        mensagem: mensagem,
        conversa_id: conversaId,
        contexto: {
          ano: ano ? Number(ano) : null,
          municipio: String(dados.get('municipio') || '').trim() || null,
          cenario_id: String(dados.get('cenario') || '').trim() || null,
        },
      };
      try {
        const corpo = await apiFetch('/api/chat', {
          method: 'POST',
          body: JSON.stringify(pedido),
        });
        conversaId = corpo.conversa_id;
        sessionStorage.setItem(CHAVE, conversaId);
        espera.remove();
        const item = linha('assistant', corpo.resposta);
        if (item) {
          referencias(corpo.referencias, item);
          mensagens.appendChild(item);
        }
      } catch (e) {
        espera.remove();
        mensagens.appendChild(linha('assistant', e.message || 'Não foi possível consultar agora.'));
      }
      botao.disabled = false;
      rolar();
    });
  });
})();
