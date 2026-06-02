let aliasData = [];
let peopleData = [];

document.addEventListener('DOMContentLoaded', () => {
  bindPeopleEvents();
  loadPeopleWorkspace();
});

function bindPeopleEvents() {
  document.getElementById('selectAllAliases')?.addEventListener('change', event => {
    document.querySelectorAll('.alias-checkbox').forEach(cb => {
      if (cb.closest('tr').style.display !== 'none') cb.checked = event.target.checked;
    });
    updateMergeButton();
  });

  document.getElementById('searchInput')?.addEventListener('input', debounce(filterAliases, 200));
  document.getElementById('btnMergeAliases')?.addEventListener('click', openMergeModal);
  document.getElementById('btnCancelMerge')?.addEventListener('click', closeMergeModal);
  document.getElementById('btnCloseMerge')?.addEventListener('click', closeMergeModal);
  document.getElementById('btnConfirmMerge')?.addEventListener('click', executeAliasMerge);
  document.getElementById('mergeTargetSelect')?.addEventListener('change', syncMergeName);
}

async function loadPeopleWorkspace() {
  const [aliasRes, peopleRes] = await Promise.all([
    api('/api/people/aliases'),
    api('/api/people')
  ]);

  if (aliasRes.success) {
    aliasData = aliasRes.data || [];
    renderAliasTable(aliasData);
  }
  if (peopleRes.success) {
    peopleData = peopleRes.data || [];
    renderPeopleList(peopleData);
  }
}

function renderAliasTable(data) {
  const tbody = document.querySelector('#aliasTable tbody');
  if (!tbody) return;

  document.getElementById('aliasCount').textContent = `${formatNumber(data.length)}개`;

  if (!data.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8">
          <div class="empty-inline">업로드된 거래의 예금자명이 아직 없습니다.</div>
        </td>
      </tr>
    `;
    return;
  }

  const aliasCountByPerson = data.reduce((acc, row) => {
    acc[row.person_id] = (acc[row.person_id] || 0) + 1;
    return acc;
  }, {});

  tbody.innerHTML = data.map(row => {
    const canSplit = aliasCountByPerson[row.person_id] > 1;
    return `
      <tr data-search="${escapeHtml(`${row.alias_name} ${row.person_name || ''}`.toLowerCase())}">
        <td class="col-checkbox">
          <input type="checkbox" class="checkbox alias-checkbox" value="${row.alias_id}">
        </td>
        <td><strong>${escapeHtml(row.alias_name)}</strong></td>
        <td>
          <a href="/people/${row.person_id}" class="text-accent">${escapeHtml(row.person_name || '-')}</a>
        </td>
        <td class="text-right">${formatNumber(row.tx_count || 0)}건</td>
        <td class="text-right text-positive">${formatCurrency(row.total_deposit || 0)}</td>
        <td class="text-right text-negative">${formatCurrency(row.total_withdrawal || 0)}</td>
        <td>${row.last_seen ? formatDate(row.last_seen) : '-'}</td>
        <td class="text-right">
          ${canSplit ? `<button class="btn btn-ghost btn-sm" data-action="split" data-person-id="${row.person_id}" data-alias-id="${row.alias_id}">분리</button>` : ''}
        </td>
      </tr>
    `;
  }).join('');

  document.querySelectorAll('.alias-checkbox').forEach(cb => {
    cb.addEventListener('change', updateMergeButton);
  });
  document.querySelectorAll('[data-action="split"]').forEach(btn => {
    btn.addEventListener('click', () => splitAlias(btn.dataset.personId, btn.dataset.aliasId));
  });
}

function renderPeopleList(data) {
  const list = document.getElementById('peopleList');
  if (!list) return;

  if (!data.length) {
    list.innerHTML = '<div class="empty-inline">아직 묶인 인물이 없습니다.</div>';
    return;
  }

  list.innerHTML = data.map(person => `
    <a class="person-group" href="/people/${person.id}">
      <div>
        <strong>${escapeHtml(person.display_name)}</strong>
        <span>${formatCurrency(person.net_amount || 0)} · ${formatNumber((person.aliases || []).length)}개 별칭</span>
      </div>
      <div class="person-group__aliases">
        ${(person.aliases || []).slice(0, 4).map(alias => `<span class="badge">${escapeHtml(alias)}</span>`).join('')}
      </div>
    </a>
  `).join('');
}

function filterAliases() {
  const term = document.getElementById('searchInput').value.trim().toLowerCase();
  document.querySelectorAll('#aliasTable tbody tr').forEach(row => {
    const target = row.dataset.search || row.innerText.toLowerCase();
    row.style.display = target.includes(term) ? '' : 'none';
  });
}

function getSelectedAliasIds() {
  return Array.from(document.querySelectorAll('.alias-checkbox:checked'))
    .map(cb => Number(cb.value));
}

function updateMergeButton() {
  const selectedCount = getSelectedAliasIds().length;
  const button = document.getElementById('btnMergeAliases');
  if (button) button.disabled = selectedCount < 2;
}

function openMergeModal() {
  const selectedIds = getSelectedAliasIds();
  const selectedAliases = aliasData.filter(row => selectedIds.includes(row.alias_id));
  const targetSelect = document.getElementById('mergeTargetSelect');
  const nameInput = document.getElementById('mergeDisplayName');
  const preview = document.getElementById('mergeAliasPreview');

  const uniquePeople = Array.from(
    new Map(selectedAliases.map(row => [row.person_id, row])).values()
  );

  targetSelect.innerHTML = uniquePeople.map(row => `
    <option value="${row.person_id}" data-name="${escapeHtml(row.person_name || row.alias_name)}">
      ${escapeHtml(row.person_name || row.alias_name)}
    </option>
  `).join('');

  nameInput.value = uniquePeople[0]?.person_name || selectedAliases[0]?.alias_name || '';
  preview.innerHTML = selectedAliases.map(row => `<span class="badge">${escapeHtml(row.alias_name)}</span>`).join('');
  document.getElementById('mergeModal').classList.add('active');
}

function closeMergeModal() {
  document.getElementById('mergeModal').classList.remove('active');
}

function syncMergeName() {
  const selected = document.getElementById('mergeTargetSelect').selectedOptions[0];
  document.getElementById('mergeDisplayName').value = selected?.dataset.name || '';
}

async function executeAliasMerge() {
  const aliasIds = getSelectedAliasIds();
  const targetPersonId = Number(document.getElementById('mergeTargetSelect').value);
  const targetName = document.getElementById('mergeDisplayName').value.trim();

  const res = await api('/api/people/merge-aliases', {
    method: 'POST',
    body: { alias_ids: aliasIds, target_person_id: targetPersonId, target_name: targetName }
  });

  if (!res.success) {
    showToast(res.error || '합치기에 실패했습니다.', 'error');
    return;
  }

  showToast('선택한 예금자명을 같은 사람으로 저장했습니다.');
  closeMergeModal();
  document.getElementById('selectAllAliases').checked = false;
  await loadPeopleWorkspace();
}

async function splitAlias(personId, aliasId) {
  const alias = aliasData.find(row => row.alias_id === Number(aliasId));
  const ok = window.confirm(`"${alias?.alias_name || '선택한 예금자명'}"을 별도 인물로 분리할까요?`);
  if (!ok) return;

  const res = await api(`/api/people/${personId}/split`, {
    method: 'POST',
    body: { alias_id: Number(aliasId) }
  });

  if (!res.success) {
    showToast(res.error || '분리에 실패했습니다.', 'error');
    return;
  }

  showToast('예금자명을 별도 인물로 분리했습니다.');
  await loadPeopleWorkspace();
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}
