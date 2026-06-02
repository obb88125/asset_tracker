document.addEventListener('DOMContentLoaded', () => {
    loadPeople();
    
    document.getElementById('selectAll').addEventListener('change', (e) => {
        document.querySelectorAll('.person-checkbox').forEach(cb => cb.checked = e.target.checked);
        updateMergeButton();
    });
    
    document.getElementById('searchInput').addEventListener('input', debounce((e) => {
        // 검색 로직 (프론트엔드 필터링)
        const term = e.target.value.toLowerCase();
        document.querySelectorAll('#peopleTable tbody tr').forEach(tr => {
            const text = tr.innerText.toLowerCase();
            tr.style.display = text.includes(term) ? '' : 'none';
        });
    }, 300));
    
    document.getElementById('btnMerge').addEventListener('click', openMergeModal);
    document.getElementById('btnCancelMerge').addEventListener('click', () => {
        document.getElementById('mergeModal').classList.add('hidden');
    });
    document.getElementById('btnConfirmMerge').addEventListener('click', executeMerge);
});

let peopleData = [];

async function loadPeople() {
    const res = await api('/api/people');
    if (res.success) {
        peopleData = res.data;
        renderTable(res.data);
    }
}

function renderTable(data) {
    const tbody = document.querySelector('#peopleTable tbody');
    tbody.innerHTML = '';
    
    data.forEach(p => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="checkbox" class="person-checkbox" value="${p.id}"></td>
            <td><a href="/people/${p.id}" class="text-accent">${p.display_name}</a></td>
            <td>${p.aliases.map(a => `<span class="badge">${a}</span>`).join(' ')}</td>
            <td class="text-positive">${formatCurrency(p.total_deposit)}</td>
            <td class="text-negative">${formatCurrency(p.total_withdrawal)}</td>
            <td>${formatCurrency(p.net_amount)}</td>
        `;
        tbody.appendChild(tr);
    });
    
    document.querySelectorAll('.person-checkbox').forEach(cb => {
        cb.addEventListener('change', updateMergeButton);
    });
}

function updateMergeButton() {
    const checked = document.querySelectorAll('.person-checkbox:checked');
    document.getElementById('btnMerge').disabled = checked.length < 2;
}

function openMergeModal() {
    const checked = Array.from(document.querySelectorAll('.person-checkbox:checked')).map(cb => parseInt(cb.value));
    const targetSelect = document.getElementById('mergeTargetSelect');
    targetSelect.innerHTML = '';
    
    checked.forEach(id => {
        const person = peopleData.find(p => p.id === id);
        if (person) {
            const option = document.createElement('option');
            option.value = person.id;
            option.textContent = person.display_name;
            targetSelect.appendChild(option);
        }
    });
    
    document.getElementById('mergeModal').classList.remove('hidden');
}

async function executeMerge() {
    const checked = Array.from(document.querySelectorAll('.person-checkbox:checked')).map(cb => parseInt(cb.value));
    const targetId = parseInt(document.getElementById('mergeTargetSelect').value);
    const sourceIds = checked.filter(id => id !== targetId);
    
    const res = await api('/api/people/merge', {
        method: 'POST',
        body: JSON.stringify({ source_ids: sourceIds, target_id: targetId })
    });
    
    if (res.success) {
        showToast('성공적으로 합쳤습니다.');
        document.getElementById('mergeModal').classList.add('hidden');
        loadPeople();
    } else {
        showToast('오류 발생: ' + res.error, 'error');
    }
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => { clearTimeout(timeout); func(...args); };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
