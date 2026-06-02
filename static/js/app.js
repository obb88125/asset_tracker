/**
 * Asset Tracker — 공통 유틸리티 (app.js)
 * 포맷터, 토스트 알림, API 래퍼, 사이드바 토글, ECharts 테마
 */

/* ============================================================
   포맷터 유틸리티
   ============================================================ */

/** 원화 포맷 (예: ₩1,234,567 / -₩500,000) */
function formatCurrency(amount) {
  if (amount == null || isNaN(amount)) return '₩0';
  const abs = Math.abs(Number(amount));
  const formatted = abs.toLocaleString('ko-KR');
  if (amount < 0) return `-₩${formatted}`;
  return `₩${formatted}`;
}

/** 숫자 포맷 (천 단위 콤마) */
function formatNumber(num) {
  if (num == null || isNaN(num)) return '0';
  return Number(num).toLocaleString('ko-KR');
}

/** 날짜 포맷 (YYYY.MM.DD) */
function formatDate(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}.${m}.${day}`;
}

/** 간략 금액 포맷 (1.2억, 3,500만 등) */
function formatCurrencyShort(amount) {
  if (amount == null || isNaN(amount)) return '₩0';
  const abs = Math.abs(Number(amount));
  const sign = amount < 0 ? '-' : '';
  if (abs >= 100000000) {
    return `${sign}₩${(abs / 100000000).toFixed(1)}억`;
  }
  if (abs >= 10000) {
    return `${sign}₩${(abs / 10000).toFixed(0)}만`;
  }
  return `${sign}₩${abs.toLocaleString('ko-KR')}`;
}


/* ============================================================
   토스트 알림 시스템
   ============================================================ */

/** 토스트 표시 */
function showToast(message, type = 'success') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const iconMap = {
    success: 'check-circle',
    error: 'alert-circle',
    info: 'info',
    warning: 'alert-triangle'
  };

  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;
  toast.innerHTML = `
    <i data-lucide="${iconMap[type] || 'info'}"></i>
    <span>${message}</span>
  `;

  container.appendChild(toast);

  // Lucide 아이콘 다시 초기화
  if (window.lucide) lucide.createIcons({ nodes: [toast] });

  // 4초 후 제거
  setTimeout(() => {
    if (toast.parentNode) toast.remove();
  }, 4000);
}


/* ============================================================
   API 래퍼
   ============================================================ */

/**
 * fetch 래퍼 — JSON 자동 처리 & 에러 핸들링
 * @param {string} url
 * @param {object} options — method, body 등
 * @returns {Promise<any>}
 */
async function api(url, options = {}) {
  const defaultHeaders = {};

  // FormData가 아니면 JSON Content-Type 설정
  if (options.body && !(options.body instanceof FormData)) {
    defaultHeaders['Content-Type'] = 'application/json';
    if (typeof options.body === 'object') {
      options.body = JSON.stringify(options.body);
    }
  }

  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...(options.headers || {})
      }
    });

    // JSON 파싱 시도
    let data;
    const contentType = res.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      data = await res.json();
    } else {
      data = await res.text();
    }

    if (!res.ok) {
      const errMsg = (typeof data === 'object' && data.error) ? data.error : `요청 실패 (${res.status})`;
      throw new Error(errMsg);
    }

    return data;
  } catch (err) {
    console.error('[API Error]', url, err);
    throw err;
  }
}


/* ============================================================
   사이드바 토글
   ============================================================ */

function toggleSidebar() {
  const layout = document.getElementById('appLayout');
  if (!layout) return;

  layout.classList.toggle('sidebar-collapsed');

  // 상태 로컬스토리지 저장
  const collapsed = layout.classList.contains('sidebar-collapsed');
  localStorage.setItem('sidebar_collapsed', collapsed ? '1' : '0');

  // 토글 버튼 텍스트 업데이트
  const label = document.querySelector('.sidebar__toggle-label');
  if (label) {
    label.textContent = collapsed ? '펼치기' : '사이드바 접기';
  }

  // 차트 리사이즈 트리거
  setTimeout(() => {
    window.dispatchEvent(new Event('resize'));
  }, 400);
}

/** 사이드바 상태 복원 */
function restoreSidebarState() {
  const collapsed = localStorage.getItem('sidebar_collapsed');
  if (collapsed === '1') {
    const layout = document.getElementById('appLayout');
    if (layout) {
      layout.classList.add('sidebar-collapsed');
      const label = document.querySelector('.sidebar__toggle-label');
      if (label) label.textContent = '펼치기';
    }
  }
}

/** 모바일 사이드바 토글 */
function toggleMobileSidebar(open) {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  if (!sidebar || !overlay) return;

  if (open) {
    sidebar.classList.add('mobile-open');
    overlay.classList.add('active');
  } else {
    sidebar.classList.remove('mobile-open');
    overlay.classList.remove('active');
  }
}


/* ============================================================
   Lucide 아이콘 초기화
   ============================================================ */

function initLucideIcons() {
  if (window.lucide) {
    lucide.createIcons();
  }
}


/* ============================================================
   ECharts 앱 테마 등록
   ============================================================ */

function registerEChartsTheme() {
  if (typeof echarts === 'undefined') return;

  echarts.registerTheme('assetDark', {
    backgroundColor: 'transparent',
    textStyle: {
      fontFamily: 'Pretendard, sans-serif',
      color: '#475569'
    },
    title: {
      textStyle: { color: '#0f172a', fontWeight: 600 },
      subtextStyle: { color: '#64748b' }
    },
    legend: {
      textStyle: { color: '#475569' },
      pageTextStyle: { color: '#475569' },
      inactiveColor: '#cbd5e1'
    },
    tooltip: {
      backgroundColor: 'rgba(255, 255, 255, 0.98)',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      textStyle: {
        color: '#0f172a',
        fontSize: 13,
        fontFamily: 'Pretendard, sans-serif'
      },
      extraCssText: 'border-radius: 10px; box-shadow: 0 12px 30px rgba(15,23,42,0.12);'
    },
    xAxis: {
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisTick: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { color: '#64748b', fontSize: 11 },
      splitLine: { lineStyle: { color: '#eef2f7' } }
    },
    yAxis: {
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisTick: { show: false },
      axisLabel: { color: '#64748b', fontSize: 11 },
      splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } }
    },
    grid: {
      left: '3%',
      right: '3%',
      bottom: '8%',
      top: '12%',
      containLabel: true
    },
    categoryAxis: {
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisTick: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { color: '#64748b' },
      splitLine: { show: false }
    },
    valueAxis: {
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#64748b' },
      splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } }
    },
    color: [
      '#2563eb', '#0891b2', '#16a34a', '#dc2626', '#d97706',
      '#7c3aed', '#db2777', '#059669', '#ca8a04', '#0284c7'
    ]
  });
}


/* ============================================================
   차트 리사이즈 핸들러 (debounce)
   ============================================================ */

/** 등록된 ECharts 인스턴스 목록 */
const chartInstances = [];

/** 차트 인스턴스 등록 */
function registerChart(instance) {
  if (instance) chartInstances.push(instance);
}

/** 디바운스 유틸 */
function debounce(fn, delay = 200) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

/** 윈도우 리사이즈 시 모든 차트 리사이즈 */
const handleResize = debounce(() => {
  chartInstances.forEach(chart => {
    if (chart && !chart.isDisposed()) {
      chart.resize();
    }
  });
}, 250);

window.addEventListener('resize', handleResize);


/* ============================================================
   카운트업 애니메이션
   ============================================================ */

function animateCountUp(element, targetValue, duration = 800, formatter = formatCurrency) {
  if (!element) return;
  const start = 0;
  const startTime = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);

    // easeOutExpo
    const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
    const current = start + (targetValue - start) * eased;

    element.textContent = formatter(Math.round(current));

    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }

  requestAnimationFrame(update);
}


/* ============================================================
   모달 유틸
   ============================================================ */

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}


/* ============================================================
   DOMContentLoaded 초기화
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  // Lucide 아이콘 초기화
  initLucideIcons();

  // ECharts 앱 테마 등록
  registerEChartsTheme();

  // 사이드바 상태 복원
  restoreSidebarState();

  // 사이드바 토글 버튼
  const toggleBtn = document.getElementById('sidebarToggle');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', toggleSidebar);
  }

  // 모바일 메뉴 버튼
  const mobileBtn = document.getElementById('mobileMenuBtn');
  if (mobileBtn) {
    mobileBtn.addEventListener('click', () => toggleMobileSidebar(true));
  }

  // 오버레이 클릭 시 닫기
  const overlay = document.getElementById('sidebarOverlay');
  if (overlay) {
    overlay.addEventListener('click', () => toggleMobileSidebar(false));
  }

  // 모달 배경 클릭 시 닫기
  document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) {
        backdrop.classList.remove('active');
        document.body.style.overflow = '';
      }
    });
  });

  // 모달 닫기 버튼
  document.querySelectorAll('.modal__close').forEach(btn => {
    btn.addEventListener('click', () => {
      const backdrop = btn.closest('.modal-backdrop');
      if (backdrop) {
        backdrop.classList.remove('active');
        document.body.style.overflow = '';
      }
    });
  });
});
