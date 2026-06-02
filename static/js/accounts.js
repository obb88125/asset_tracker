let editingAccountId = null;

document.addEventListener('DOMContentLoaded', () => {
  bindAccountEvents();
  loadAccounts();
});

function bindAccountEvents() {
  document.getElementById('btnAddAccount')?.addEventListener('click', () => openAccountModal());
  document.getElementById('btnCancel')?.addEventListener('click', closeAccountModal);
  document.getElementById('btnCloseAccount')?.addEventListener('click', closeAccountModal);
  document.getElementById('btnSave')?.addEventListener('click', saveAccount);
}

async function loadAccounts() {
  const res = await api('/api/accounts');
  if (!res.success) {
    showToast(res.error || '계좌를 불러오지 못했습니다.', 'error');
    return;
  }

  renderAccounts(res.data || []);
}

function renderAccounts(accounts) {
  const grid = document.getElementById('accountGrid');
  if (!grid) return;

  if (!accounts.length) {
    grid.innerHTML = `
      <div class="empty-state card">
        <div class="empty-state__icon"><i data-lucide="building-2"></i></div>
        <div class="empty-state__title">등록된 계좌가 없습니다</div>
        <div class="empty-state__desc">업로드할 거래내역이 어느 계좌의 데이터인지 연결하려면 계좌를 먼저 추가하세요.</div>
      </div>
    `;
    if (window.lucide) lucide.createIcons({ nodes: [grid] });
    return;
  }

  grid.innerHTML = accounts.map(account => `
    <article class="account-card">
      <div class="account-card__header">
        <div class="account-card__icon"><i data-lucide="building-2"></i></div>
        <div class="account-card__actions">
          <button class="btn-icon" data-action="edit" data-id="${account.id}" title="수정"><i data-lucide="pencil"></i></button>
          <button class="btn-icon" data-action="delete" data-id="${account.id}" title="삭제"><i data-lucide="trash-2"></i></button>
        </div>
      </div>
      <div class="account-card__name">${escapeHtml(account.name)}</div>
      <div class="account-card__number">${escapeHtml(account.institution)} · ${escapeHtml(account.account_number || '번호 없음')}</div>
      <div class="account-card__stats">
        <div class="account-card__stat">
          <div class="account-card__stat-value text-positive">${formatCurrency(account.total_deposit || 0)}</div>
          <div class="account-card__stat-label">입금</div>
        </div>
        <div class="account-card__stat">
          <div class="account-card__stat-value text-negative">${formatCurrency(account.total_withdrawal || 0)}</div>
          <div class="account-card__stat-label">출금</div>
        </div>
        <div class="account-card__stat">
          <div class="account-card__stat-value">${formatNumber(account.tx_count || 0)}</div>
          <div class="account-card__stat-label">거래</div>
        </div>
      </div>
    </article>
  `).join('');

  grid.querySelectorAll('[data-action="edit"]').forEach(btn => {
    const account = accounts.find(item => item.id === Number(btn.dataset.id));
    btn.addEventListener('click', () => openAccountModal(account));
  });
  grid.querySelectorAll('[data-action="delete"]').forEach(btn => {
    btn.addEventListener('click', () => deleteAccount(Number(btn.dataset.id)));
  });
  if (window.lucide) lucide.createIcons({ nodes: [grid] });
}

function openAccountModal(account = null) {
  editingAccountId = account?.id || null;
  document.getElementById('modalTitle').textContent = account ? '계좌 수정' : '계좌 추가';
  document.getElementById('accName').value = account?.name || '';
  document.getElementById('accInstitution').value = account?.institution || '';
  document.getElementById('accNumber').value = account?.account_number || '';
  document.getElementById('accountModal').classList.add('active');
}

function closeAccountModal() {
  document.getElementById('accountModal').classList.remove('active');
}

async function saveAccount() {
  const payload = {
    name: document.getElementById('accName').value.trim(),
    institution: document.getElementById('accInstitution').value.trim(),
    account_number: document.getElementById('accNumber').value.trim()
  };

  if (!payload.name || !payload.institution) {
    showToast('별칭과 기관명은 필수입니다.', 'error');
    return;
  }

  const url = editingAccountId ? `/api/accounts/${editingAccountId}` : '/api/accounts';
  const method = editingAccountId ? 'PUT' : 'POST';
  const res = await api(url, { method, body: payload });

  if (!res.success) {
    showToast(res.error || '저장에 실패했습니다.', 'error');
    return;
  }

  showToast('계좌를 저장했습니다.');
  closeAccountModal();
  await loadAccounts();
}

async function deleteAccount(id) {
  if (!window.confirm('이 계좌와 연결된 거래내역도 삭제됩니다. 계속할까요?')) return;

  const res = await api(`/api/accounts/${id}`, { method: 'DELETE' });
  if (!res.success) {
    showToast(res.error || '삭제에 실패했습니다.', 'error');
    return;
  }

  showToast('계좌를 삭제했습니다.');
  await loadAccounts();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}
