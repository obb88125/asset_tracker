let currentPersonId = null;
let currentPerson = null;

document.addEventListener('DOMContentLoaded', () => {
  currentPersonId = Number(window.location.pathname.split('/').pop());
  loadPersonDetail();
});

async function loadPersonDetail() {
  const res = await api(`/api/people/${currentPersonId}`);
  if (!res.success) {
    showToast(res.error || '인물 정보를 불러오지 못했습니다.', 'error');
    return;
  }

  currentPerson = res.data;
  renderPerson();
  renderTransactions();
  await renderTimeline();
}

function renderPerson() {
  document.getElementById('personName').textContent = currentPerson.display_name;
  document.getElementById('personMemo').textContent = currentPerson.memo || '';
  document.getElementById('totalDeposit').textContent = formatCurrency(currentPerson.total_deposit || 0);
  document.getElementById('totalWithdrawal').textContent = formatCurrency(currentPerson.total_withdrawal || 0);
  document.getElementById('netAmount').textContent = formatCurrency(currentPerson.net_amount || 0);

  const aliases = currentPerson.aliases || [];
  const container = document.getElementById('aliasesContainer');
  container.innerHTML = aliases.map(alias => `
    <span class="alias-chip">
      ${escapeHtml(alias.name)}
      ${aliases.length > 1 ? `<button data-alias-id="${alias.id}" title="이 별칭 분리"><i data-lucide="split"></i></button>` : ''}
    </span>
  `).join('');

  container.querySelectorAll('button[data-alias-id]').forEach(button => {
    button.addEventListener('click', () => splitAlias(button.dataset.aliasId));
  });
  if (window.lucide) lucide.createIcons({ nodes: [container] });
}

function renderTransactions() {
  const tbody = document.querySelector('#txTable tbody');
  const rows = currentPerson.transactions || [];

  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="4"><div class="empty-inline">거래 내역이 없습니다.</div></td></tr>';
    return;
  }

  tbody.innerHTML = rows.map(tx => `
    <tr>
      <td>${formatDate(tx.date)}</td>
      <td><span class="badge ${tx.type === 'deposit' ? 'badge--positive' : 'badge--negative'}">${tx.type === 'deposit' ? '입금' : '출금'}</span></td>
      <td class="${tx.type === 'deposit' ? 'text-positive' : 'text-negative'}">${formatCurrency(tx.amount)}</td>
      <td>${escapeHtml(tx.description || '-')}</td>
    </tr>
  `).join('');
}

async function renderTimeline() {
  const res = await api(`/api/people/${currentPersonId}/timeline`);
  if (!res.success) return;

  const chart = echarts.init(document.getElementById('timelineChart'), 'assetDark');
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', formatter: params => {
      const p = params[0];
      return `${p.axisValue}<br>${p.marker}누적: ${formatCurrency(p.value)}`;
    }},
    grid: { left: 48, right: 24, top: 24, bottom: 32 },
    xAxis: { type: 'category', data: res.data.dates || [] },
    yAxis: { type: 'value', axisLabel: { formatter: value => formatCurrencyShort(value).replace('₩', '') } },
    series: [{
      name: '누적 거래',
      type: 'line',
      smooth: true,
      areaStyle: { color: 'rgba(59, 130, 246, 0.12)' },
      lineStyle: { color: '#3b82f6', width: 3 },
      data: res.data.cumulative || []
    }]
  });
  registerChart(chart);
}

async function splitAlias(aliasId) {
  const alias = (currentPerson.aliases || []).find(item => item.id === Number(aliasId));
  const ok = window.confirm(`"${alias?.name || '선택한 별칭'}"을 별도 인물로 분리할까요?`);
  if (!ok) return;

  const res = await api(`/api/people/${currentPersonId}/split`, {
    method: 'POST',
    body: { alias_id: Number(aliasId) }
  });

  if (!res.success) {
    showToast(res.error || '분리에 실패했습니다.', 'error');
    return;
  }

  showToast('별칭을 별도 인물로 분리했습니다.');
  await loadPersonDetail();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}
