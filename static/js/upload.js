let currentSessionId = null;
let detectedColumns = {};
let previewColumns = [];
let previewRows = [];

const mappingOptions = [
  ['', '사용 안 함'],
  ['date_col', '날짜'],
  ['counterparty_col', '예금자명'],
  ['type_col', '구분'],
  ['amount_col', '금액'],
  ['deposit_col', '입금'],
  ['withdrawal_col', '출금'],
  ['balance_col', '잔액'],
  ['description_col', '적요/메모'],
  ['stock_name_col', '종목명'],
  ['stock_code_col', '종목코드'],
  ['quantity_col', '수량'],
  ['price_col', '단가'],
  ['fee_col', '수수료'],
  ['tax_col', '세금']
];

document.addEventListener('DOMContentLoaded', () => {
  bindUploadEvents();
  loadAccounts();
  loadUploadHistory();
});

function bindUploadEvents() {
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');

  dropZone?.addEventListener('click', () => fileInput.click());
  dropZone?.addEventListener('dragover', event => {
    event.preventDefault();
    dropZone.classList.add('dragover');
  });
  dropZone?.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
  dropZone?.addEventListener('drop', event => {
    event.preventDefault();
    dropZone.classList.remove('dragover');
    const file = event.dataTransfer.files[0];
    if (file) uploadAndPreview(file);
  });

  fileInput?.addEventListener('change', event => {
    const file = event.target.files[0];
    if (file) uploadAndPreview(file);
  });

  document.getElementById('btnImport')?.addEventListener('click', importData);
}

async function uploadAndPreview(file) {
  const formData = new FormData();
  formData.append('file', file);

  const uploadRes = await api('/api/upload', {
    method: 'POST',
    body: formData
  });

  if (!uploadRes.success) {
    showToast(uploadRes.error || '업로드 실패', 'error');
    return;
  }

  currentSessionId = uploadRes.data.session_id;
  const previewRes = await api('/api/upload/preview', {
    method: 'POST',
    body: { session_id: currentSessionId }
  });

  if (!previewRes.success) {
    showToast(previewRes.error || '미리보기 생성 실패', 'error');
    return;
  }

  detectedColumns = previewRes.data.detected || {};
  previewColumns = previewRes.data.columns || [];
  previewRows = previewRes.data.preview || [];
  renderPreview();
  document.getElementById('mappingSection').classList.remove('hidden');
  showToast('파일을 읽었습니다. 컬럼 매핑을 확인하세요.');
}

async function loadAccounts() {
  const select = document.getElementById('accountSelect');
  if (!select) return;

  const res = await api('/api/accounts');
  const accounts = res.success ? (res.data || []) : [];
  select.innerHTML = accounts.length
    ? accounts.map(acc => `<option value="${acc.id}">${escapeHtml(acc.name)} · ${escapeHtml(acc.institution)}</option>`).join('')
    : '<option value="">먼저 계좌를 추가하세요</option>';
}

async function loadUploadHistory() {
  const tbody = document.querySelector('#historyTable tbody');
  if (!tbody) return;

  const res = await api('/api/upload/sessions');
  const sessions = res.success ? (res.data || []) : [];
  if (!sessions.length) {
    tbody.innerHTML = '<tr><td colspan="4"><div class="empty-inline">업로드 이력이 없습니다.</div></td></tr>';
    return;
  }

  tbody.innerHTML = sessions.map(session => `
    <tr>
      <td>${formatDate(session.date)}</td>
      <td>${escapeHtml(session.filename)}</td>
      <td class="text-right">${formatNumber(session.imported || 0)}</td>
      <td class="text-right">${formatNumber(session.total || 0)}</td>
    </tr>
  `).join('');
}

function renderPreview() {
  const mappingHeaders = document.getElementById('mappingHeaders');
  const originalHeaders = document.getElementById('originalHeaders');
  const tbody = document.querySelector('#previewTable tbody');

  mappingHeaders.innerHTML = previewColumns.map(col => {
    const detected = detectedColumns[col] || {};
    return `
      <th>
        <select class="column-mapping-select" data-column="${escapeHtml(col)}">
          ${mappingOptions.map(([value, label]) => `
            <option value="${value}" ${detected.suggestion === value ? 'selected' : ''}>${label}</option>
          `).join('')}
        </select>
      </th>
    `;
  }).join('');

  originalHeaders.innerHTML = previewColumns.map(col => `
    <th>
      ${escapeHtml(col)}
      <div class="column-sample">${escapeHtml(detectedColumns[col]?.type || 'text')}</div>
    </th>
  `).join('');

  tbody.innerHTML = previewRows.map(row => `
    <tr>
      ${previewColumns.map(col => `<td>${escapeHtml(row[col] ?? '')}</td>`).join('')}
    </tr>
  `).join('');
}

function getColumnMapping() {
  const mapping = {};
  document.querySelectorAll('.column-mapping-select').forEach(select => {
    if (select.value) mapping[select.value] = select.dataset.column;
  });
  return mapping;
}

async function importData() {
  const accountId = Number(document.getElementById('accountSelect').value);
  const dataType = document.getElementById('dataTypeSelect').value;
  const columnMapping = getColumnMapping();

  if (!currentSessionId) {
    showToast('먼저 파일을 업로드하세요.', 'error');
    return;
  }
  if (!accountId) {
    showToast('계좌를 선택하세요.', 'error');
    return;
  }

  const res = await api('/api/upload/import', {
    method: 'POST',
    body: {
      session_id: currentSessionId,
      account_id: accountId,
      data_type: dataType,
      column_mapping: columnMapping
    }
  });

  if (!res.success) {
    showToast(res.error || '임포트 실패', 'error');
    return;
  }

  const { imported, skipped, errors } = res.data;
  showToast(`${formatNumber(imported)}행 임포트 완료, ${formatNumber(skipped)}행 제외`);
  if (errors?.length) {
    console.warn('[Import errors]', errors);
  }
  await loadUploadHistory();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}
