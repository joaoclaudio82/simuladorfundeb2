/**
 * Autenticação — cookie JWT, guard de sessão e apiFetch com credentials
 */

const authState = {
  user: null,
};

let authReadyPromise = null;

function isAdmin() {
  return authState.user?.role === 'admin';
}

function canEditPesos() {
  return isAdmin();
}

async function apiFetch(url, opts = {}) {
  const res = await fetch((typeof API !== 'undefined' ? API : '') + url, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
    ...opts,
  });
  if (res.status === 401) {
    const path = window.location.pathname;
    if (!path.endsWith('/login.html') && path !== '/login.html') {
      window.location.href = '/login.html';
    }
    throw new Error('Não autenticado');
  }
  if (!res.ok) {
    let msg = `Erro ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) msg = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
    } catch (_) { /* ignore */ }
    throw new Error(msg);
  }
  if (res.status === 204) return null;
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) return res.json();
  return res.text();
}

async function guardAuth() {
  if (authReadyPromise) return authReadyPromise;
  authReadyPromise = (async () => {
    try {
      const me = await apiFetch('/api/auth/me');
      authState.user = me;
      if (typeof state !== 'undefined') state.user = me;
      setupAuthUI();
      return me;
    } catch (e) {
      authReadyPromise = null;
      if (!window.location.pathname.endsWith('login.html')) {
        window.location.href = '/login.html';
      }
      throw e;
    }
  })();
  return authReadyPromise;
}

async function guardAdmin() {
  await guardAuth();
  if (!isAdmin()) {
    window.location.href = '/';
    throw new Error('Acesso restrito');
  }
}

function setupAuthUI() {
  const userEl = document.getElementById('sidebar-user');
  if (userEl && authState.user) {
    const nome = authState.user.nome || authState.user.cpf_formatado || authState.user.cpf;
    const perfil = authState.user.role === 'admin' ? 'Administrador' : 'Usuário';
    userEl.innerHTML = `<small><i class="fas fa-user"></i> ${nome}</small><br><small class="text-muted">${perfil}</small>`;
    userEl.classList.remove('d-none');
  }

  const adminLink = document.getElementById('nav-admin-usuarios');
  if (adminLink) {
    adminLink.classList.toggle('d-none', !isAdmin());
  }

  const logoutBtn = document.getElementById('btn-logout');
  if (logoutBtn && !logoutBtn.dataset.wired) {
    logoutBtn.dataset.wired = '1';
    logoutBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      try {
        await apiFetch('/api/auth/logout', { method: 'POST' });
      } catch (_) { /* ignore */ }
      window.location.href = '/login.html';
    });
  }
}

function maskCpfInput(input) {
  input.addEventListener('input', () => {
    let v = input.value.replace(/\D/g, '').slice(0, 11);
    if (v.length > 9) {
      v = v.replace(/(\d{3})(\d{3})(\d{3})(\d{0,2})/, '$1.$2.$3-$4');
    } else if (v.length > 6) {
      v = v.replace(/(\d{3})(\d{3})(\d{0,3})/, '$1.$2.$3');
    } else if (v.length > 3) {
      v = v.replace(/(\d{3})(\d{0,3})/, '$1.$2');
    }
    input.value = v;
  });
}

async function handleLoginSubmit(e) {
  e.preventDefault();
  const cpfEl = document.getElementById('login-cpf');
  const senhaEl = document.getElementById('login-senha');
  const errEl = document.getElementById('login-erro');
  const btn = document.getElementById('btn-login');
  if (errEl) errEl.textContent = '';
  btn.disabled = true;
  try {
    await apiFetch('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        cpf: cpfEl.value.replace(/\D/g, ''),
        senha: senhaEl.value,
      }),
    });
    window.location.href = '/';
  } catch (err) {
    if (errEl) errEl.textContent = err.message || 'Falha no login';
  } finally {
    btn.disabled = false;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('form-login');
  const cpfInput = document.getElementById('login-cpf');
  if (cpfInput) maskCpfInput(cpfInput);
  if (form) form.addEventListener('submit', handleLoginSubmit);
});
