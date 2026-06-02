const chartColors = {
  asset: '#2563eb',
  cash: '#0891b2',
  stock: '#7c3aed',
  buy: '#dc2626',
  sell: '#16a34a',
  grid: '#e2e8f0',
  text: '#64748b'
};

document.addEventListener('DOMContentLoaded', () => {
  loadDashboard();
});

async function loadDashboard() {
  try {
    await Promise.all([
      loadSummary(),
      loadAssetTimeline(),
      loadSupportingCharts()
    ]);
  } catch (err) {
    showToast(`대시보드 로딩 실패: ${err.message}`, 'error');
  }
}

async function loadSummary() {
  const res = await api('/api/dashboard/summary');
  if (!res.success || !res.data) return;

  const data = res.data;
  setText('totalDeposit', formatCurrency(data.total_deposit || 0));
  setText('totalWithdrawal', formatCurrency(data.total_withdrawal || 0));
  setText('netAmount', formatCurrency(data.net_amount || 0));
  setText('personCount', `${formatNumber(data.person_count || 0)}명`);
  setText('txCount', `${formatNumber(data.transaction_count || 0)}건`);
  setText('stockPnl', formatCurrency(data.stock_realized_pnl || 0));
}

async function loadAssetTimeline() {
  const res = await api('/api/dashboard/asset-timeline');
  if (!res.success || !res.data) return;

  const data = res.data;
  setText('totalAsset', formatCurrency(data.latest_asset_value || 0));
  setText('cashValue', formatCurrency(data.latest_cash_value || 0));
  setText('stockBookValue', formatCurrency(data.latest_stock_book_value || 0));
  setText('realizedPnlValue', formatCurrency(data.latest_realized_pnl || 0));

  renderStockEvents(data.events || []);
  initAssetTimelineChart(data);
}

async function loadSupportingCharts() {
  const [monthlyRes, peopleRes, accountRes, heatRes] = await Promise.all([
    api('/api/dashboard/monthly'),
    api('/api/dashboard/people-share'),
    api('/api/dashboard/account-comparison'),
    api('/api/dashboard/heatmap')
  ]);

  if (monthlyRes.success) initMonthlyChart(monthlyRes.data);
  if (peopleRes.success) initPeopleShareChart(peopleRes.data);
  if (accountRes.success) initAccountChart(accountRes.data);
  if (heatRes.success) initHeatmapChart(heatRes.data);
}

function initAssetTimelineChart(data) {
  const el = document.getElementById('assetTimelineChart');
  if (!el) return;

  const dates = data.dates || [];
  const assetValues = data.asset_values || [];
  if (!dates.length) {
    renderChartEmpty(el, '거래 데이터를 업로드하면 자산 변화가 여기에 그려집니다.');
    return;
  }
  const dateToAsset = new Map(dates.map((date, index) => [date, assetValues[index] || 0]));
  const buyEvents = [];
  const sellEvents = [];

  (data.events || []).forEach(event => {
    const value = dateToAsset.get(event.date) || assetValues[assetValues.length - 1] || 0;
    const point = [
      event.date,
      value,
      `${event.stock_name} ${event.type === 'buy' ? '매수' : '매도'} ${formatNumber(event.quantity)}주`,
      event
    ];
    if (event.type === 'buy') buyEvents.push(point);
    if (event.type === 'sell') sellEvents.push(point);
  });

  const chart = echarts.init(el, 'assetDark');
  chart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 48, right: 28, top: 36, bottom: 56 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter(params) {
        const lines = [];
        params.forEach(param => {
          if (param.seriesType === 'scatter') {
            const event = param.value[3];
            lines.push(
              `<strong>${event.stock_name}</strong> ${event.type === 'buy' ? '매수' : '매도'} ` +
              `${formatNumber(event.quantity)}주 · ${formatCurrency(event.amount)}`
            );
          } else {
            lines.push(`${param.marker}${param.seriesName}: ${formatCurrency(param.value)}`);
          }
        });
        return `<div>${params[0]?.axisValue || ''}</div>${lines.join('<br>')}`;
      }
    },
    legend: {
      top: 0,
      data: ['추정 자산', '현금', '주식 장부가', '매수', '매도']
    },
    dataZoom: [
      { type: 'inside', filterMode: 'none' },
      { type: 'slider', height: 20, bottom: 10, borderColor: 'rgba(148,163,184,0.2)' }
    ],
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
      axisLine: { lineStyle: { color: chartColors.grid } },
      axisLabel: { color: chartColors.text }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        color: chartColors.text,
        formatter: value => formatCurrencyShort(value).replace('₩', '')
      },
      splitLine: { lineStyle: { color: chartColors.grid } }
    },
    series: [
      {
        name: '추정 자산',
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 3, color: chartColors.asset },
        areaStyle: { color: 'rgba(59, 130, 246, 0.14)' },
        data: assetValues
      },
      {
        name: '현금',
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: chartColors.cash },
        data: data.cash_values || []
      },
      {
        name: '주식 장부가',
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: chartColors.stock },
        data: data.stock_book_values || []
      },
      {
        name: '매수',
        type: 'scatter',
        symbol: 'triangle',
        symbolSize: 13,
        itemStyle: { color: chartColors.buy },
        data: buyEvents
      },
      {
        name: '매도',
        type: 'scatter',
        symbol: 'diamond',
        symbolSize: 13,
        itemStyle: { color: chartColors.sell },
        data: sellEvents
      }
    ]
  });
  registerChart(chart);
}

function initMonthlyChart(data) {
  const el = document.getElementById('chartMonthly');
  if (!(data.labels || []).length) {
    renderChartEmpty(el, '월별 입출금 데이터가 없습니다.');
    return;
  }
  const chart = echarts.init(el, 'assetDark');
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { data: ['입금', '출금'] },
    grid: { left: 48, right: 20, top: 44, bottom: 32 },
    xAxis: { type: 'category', data: data.labels || [] },
    yAxis: { type: 'value', axisLabel: { formatter: value => formatCurrencyShort(value).replace('₩', '') } },
    series: [
      { name: '입금', type: 'bar', data: data.deposits || [], itemStyle: { color: chartColors.sell, borderRadius: [4, 4, 0, 0] } },
      { name: '출금', type: 'bar', data: data.withdrawals || [], itemStyle: { color: chartColors.buy, borderRadius: [4, 4, 0, 0] } }
    ]
  });
  registerChart(chart);
}

function initPeopleShareChart(data) {
  const el = document.getElementById('chartPeopleShare');
  if (!(data || []).length) {
    renderChartEmpty(el, '인물별 거래 데이터가 없습니다.');
    return;
  }
  const chart = echarts.init(el, 'assetDark');
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: p => `${p.name}: ${formatCurrency(p.value)}` },
    series: [{
      type: 'pie',
      radius: ['48%', '72%'],
      center: ['50%', '52%'],
      label: { color: chartColors.text },
      data: (data || []).map(d => ({ name: d.name, value: d.total_amount || 0 }))
    }]
  });
  registerChart(chart);
}

function initAccountChart(data) {
  const el = document.getElementById('chartAccount');
  if (!(data || []).length) {
    renderChartEmpty(el, '계좌별 거래 데이터가 없습니다.');
    return;
  }
  const chart = echarts.init(el, 'assetDark');
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { data: ['입금', '출금'] },
    grid: { left: 48, right: 20, top: 44, bottom: 32 },
    xAxis: { type: 'category', data: (data || []).map(d => d.account_name) },
    yAxis: { type: 'value', axisLabel: { formatter: value => formatCurrencyShort(value).replace('₩', '') } },
    series: [
      { name: '입금', type: 'bar', data: (data || []).map(d => d.deposits), itemStyle: { color: chartColors.sell, borderRadius: [4, 4, 0, 0] } },
      { name: '출금', type: 'bar', data: (data || []).map(d => d.withdrawals), itemStyle: { color: chartColors.buy, borderRadius: [4, 4, 0, 0] } }
    ]
  });
  registerChart(chart);
}

function initHeatmapChart(data) {
  const el = document.getElementById('chartHeatmap');
  if (!(data || []).length) {
    renderChartEmpty(el, '거래 빈도 데이터가 없습니다.');
    return;
  }
  const chart = echarts.init(el, 'assetDark');
  const dates = (data || []).map(d => d.date);
  const year = dates[0] ? dates[0].slice(0, 4) : new Date().getFullYear();
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { position: 'top' },
    visualMap: {
      min: 0,
      max: Math.max(1, ...(data || []).map(d => d.count)),
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      textStyle: { color: chartColors.text }
    },
    calendar: [{
      range: year,
      top: 24,
      left: 24,
      right: 24,
      cellSize: ['auto', 18],
      itemStyle: { borderColor: 'rgba(148,163,184,0.14)' },
      dayLabel: { color: chartColors.text },
      monthLabel: { color: chartColors.text },
      yearLabel: { show: false }
    }],
    series: [{
      type: 'heatmap',
      coordinateSystem: 'calendar',
      data: (data || []).map(d => [d.date, d.count])
    }]
  });
  registerChart(chart);
}

function renderStockEvents(events) {
  const list = document.getElementById('stockEventList');
  if (!list) return;

  const recent = events.slice(-6).reverse();
  if (!recent.length) {
    list.innerHTML = '<div class="empty-inline">아직 주식 매수/매도 기록이 없습니다.</div>';
    return;
  }

  list.innerHTML = recent.map(event => `
    <div class="event-item">
      <span class="event-item__dot event-item__dot--${event.type}"></span>
      <div>
        <strong>${escapeHtml(event.stock_name || '-')}</strong>
        <span>${event.type === 'buy' ? '매수' : '매도'} · ${formatNumber(event.quantity || 0)}주</span>
      </div>
      <em>${formatDate(event.date)}</em>
    </div>
  `).join('');
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function renderChartEmpty(el, message) {
  if (!el) return;
  el.innerHTML = `
    <div class="chart-empty">
      <i data-lucide="line-chart"></i>
      <span>${escapeHtml(message)}</span>
    </div>
  `;
  if (window.lucide) lucide.createIcons({ nodes: [el] });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}
