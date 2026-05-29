/**
 * Administração de usuários (somente admin)
 */

let modalEditar = null;
let cpfEmEdicao = null;
let usuariosCache = [];

function formatCpf(cpf) {
  const c = String(cpf).replace(/\D/g, '');
  if (c.length !== 11) return cpf;
  return `${c.slice(0, 3)}.${c.slice(3, 6)}.${c.slice(6, 9)}-${c.slice(9)}`;
}

function escapeHtml(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function abrirEdicaoUsuario(user) {
  cpfEmEdicao = user.cpf;
  document.getElementById('edit-cpf').value = formatCpf(user.cpf);
  document.getElementById('edit-nome').value = user.nome || '';
  document.getElementById('edit-role').value = user.role;
  document.getElementById('edit-senha').value = '';
  document.getElementById('edit-ativo').checked = !!user.ativo;
  document.getElementById('edit-erro').textContent = '';
  if (!modalEditar) {
    modalEditar = new bootstrap.Modal(document.getElementById('modal-editar-usuario'));
  }
  modalEditar.show();
}

async function loadUsuarios() {
  const tbody = document.getElementById('usuarios-tbody');
  if (!tbody) return;
  usuariosCache = await apiFetch('/api/admin/usuarios');
  tbody.innerHTML = usuariosCache.map((u) => {
    const ativo = u.ativo ? '<span class="badge bg-success">Sim</span>' : '<span class="badge bg-secondary">Não</span>';
    const perfil = u.role === 'admin' ? 'Administrador' : 'Usuário';
    return `<tr>
      <td>${formatCpf(u.cpf)}</td>
      <td>${escapeHtml(u.nome) || '—'}</td>
      <td>${perfil}</td>
      <td>${ativo}</td>
      <td class="text-nowrap">
        <button type="button" class="btn btn-sm btn-outline-primary btn-editar" data-cpf="${u.cpf}" title="Editar">
          <i class="fas fa-pen"></i>
        </button>
        <button type="button" class="btn btn-sm btn-outline-secondary btn-reset-senha" data-cpf="${u.cpf}" title="Resetar senha">
          <i class="fas fa-key"></i>
        </button>
        <button type="button" class="btn btn-sm btn-outline-${u.ativo ? 'warning' : 'success'} btn-toggle-ativo" data-cpf="${u.cpf}" data-ativo="${u.ativo}">
          <i class="fas fa-${u.ativo ? 'ban' : 'check'}"></i>
        </button>
        <button type="button" class="btn btn-sm btn-outline-danger btn-excluir" data-cpf="${u.cpf}" title="Excluir">
          <i class="fas fa-trash"></i>
        </button>
      </td>
    </tr>`;
  }).join('');

  tbody.querySelectorAll('.btn-editar').forEach((btn) => {
    btn.addEventListener('click', () => {
      const user = usuariosCache.find((u) => u.cpf === btn.dataset.cpf);
      if (user) abrirEdicaoUsuario(user);
    });
  });

  tbody.querySelectorAll('.btn-reset-senha').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const nova = prompt('Nova senha (mín. 6 caracteres):');
      if (!nova || nova.length < 6) return;
      try {
        await apiFetch(`/api/admin/usuarios/${btn.dataset.cpf}`, {
          method: 'PATCH',
          body: JSON.stringify({ senha: nova }),
        });
        alert('Senha atualizada.');
      } catch (e) {
        alert(e.message);
      }
    });
  });

  tbody.querySelectorAll('.btn-toggle-ativo').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const ativo = btn.dataset.ativo === 'true';
      try {
        await apiFetch(`/api/admin/usuarios/${btn.dataset.cpf}`, {
          method: 'PATCH',
          body: JSON.stringify({ ativo: !ativo }),
        });
        await loadUsuarios();
      } catch (e) {
        alert(e.message);
      }
    });
  });

  tbody.querySelectorAll('.btn-excluir').forEach((btn) => {
    btn.addEventListener('click', async () => {
      if (!confirm('Excluir este usuário?')) return;
      try {
        await apiFetch(`/api/admin/usuarios/${btn.dataset.cpf}`, { method: 'DELETE' });
        await loadUsuarios();
      } catch (e) {
        alert(e.message);
      }
    });
  });
}

document.addEventListener('DOMContentLoaded', async () => {
  const cpfInput = document.getElementById('usr-cpf');
  if (cpfInput) maskCpfInput(cpfInput);

  try {
    await guardAdmin();
    await loadUsuarios();
  } catch (e) {
    console.error(e);
  }

  document.getElementById('form-usuario')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const errEl = document.getElementById('form-erro');
    if (errEl) errEl.textContent = '';
    try {
      await apiFetch('/api/admin/usuarios', {
        method: 'POST',
        body: JSON.stringify({
          cpf: document.getElementById('usr-cpf').value.replace(/\D/g, ''),
          nome: document.getElementById('usr-nome').value.trim() || null,
          senha: document.getElementById('usr-senha').value,
          role: document.getElementById('usr-role').value,
        }),
      });
      e.target.reset();
      await loadUsuarios();
    } catch (err) {
      if (errEl) errEl.textContent = err.message;
    }
  });

  document.getElementById('form-editar-usuario')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const errEl = document.getElementById('edit-erro');
    if (errEl) errEl.textContent = '';
    if (!cpfEmEdicao) return;

    const body = {
      nome: document.getElementById('edit-nome').value.trim() || null,
      role: document.getElementById('edit-role').value,
      ativo: document.getElementById('edit-ativo').checked,
    };
    const novaSenha = document.getElementById('edit-senha').value;
    if (novaSenha) {
      if (novaSenha.length < 6) {
        errEl.textContent = 'A senha deve ter no mínimo 6 caracteres.';
        return;
      }
      body.senha = novaSenha;
    }

    try {
      await apiFetch(`/api/admin/usuarios/${cpfEmEdicao}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      });
      modalEditar?.hide();
      cpfEmEdicao = null;
      await loadUsuarios();
    } catch (err) {
      if (errEl) errEl.textContent = err.message;
    }
  });
});
