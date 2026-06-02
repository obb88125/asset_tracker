let currentStockId = null;

document.addEventListener('DOMContentLoaded', () => {
  currentStockId = Number(window.location.pathname.split('/').pop());
  loadStockDetail();
});

async function loadStockDetail() {
  const [detailRes, flowRes, pnlRes] = await Promise.all([
    api(`/api/stocks/${currentStockId}`),
    api(`/api/stocks/${currentStockId}/timeline`),
    api(`/api/stocks/${currentStockId}/pnl-timeline`)
  ]);

  if (!detailRes.success) {
    showToast(detailRes.error || '종목 정보를 불러오지 못했습니다.', 'error');
    return;
  }

  renderStockDetail(detailRes.data);
  renderTradeTable(detailRes.data.trades || []);
  if (flowRes.success) renderStockFlowCharts(flowRes.data);
  if (pnlRes.success) renderPnlTimeline(pnlRes.data);
}

function renderStockDetail(data) {
  document.getElementById('stockName').textContent = data.name || '-';
  document.getElementById('stockCode').textContent = data.code || '코드 없음';
  document.getElementById('holdings').textContent = formatNumber(data.holdings || 0);
  document.getElementById('avgPrice').textContent = formatCurrency(data.avg_buy_price || 0);
  document.getElementById('totalBuy').textContent = formatCurrency(data.total_buy || 0);
  document.getElementById('totalSell').textContent = formatCurrency(data.total_sell || 0);
  document.getElementById('realizedPnl').textContent = formatCurrency(data.realized_pnl || 0);
}

function renderTradeTable(trades) {
  const tbody = document.querySelector('#tradeTable tbody');
  if (!tbody) return;

  if (!trades.length) {
    tbody.innerHTML = '<tr><td colspan="6"><div class="empty-inline">거래 내역이 없습니다.</div></td></tr>';
    return;
  }

  tbody.innerHTML = trades.map(trade => `
    <tr>
      <td>${formatDate(trade.date)}</td>
      <td><span class="badge ${trade.type === 'buy' ? 'badge--negative' : 'badge--positive'}">${trade.type === 'buy' ? '매수' : '매도'}</span></td>
      <td class="text-right">${formatNumber(trade.quantity)}</td>
      <td class="text-right">${formatCurrency(trade.price)}</td>
      <td class="text-right">${formatCurrency(trade.total)}</td>
      <td class="text-right ${(trade.realized_pnl || 0) >= 0 ? 'text-positive' : 'text-negative'}">${trade.type === 'sell' ? formatCurrency(trade.realized_pnl || 0) : '-'}</td>
    </tr>
  `).join('');
}

function renderPnlTimeline(data) {
  const el = document.getElementById('pnlTimelineChart');
  if (!el) return;

  if (!(data.dates || []).length) {
    renderStockDetailEmpty(el, '매도 내역이 생기면 이 종목의 누적 실현손익이 표시됩니다.');
    return;
  }

  const chart = echarts.init(el, 'assetDark');
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { data: ['누적 실현손익', '일별 확정 손익'] },
    grid: { left: 56, right: 28, top: 48, bottom: 36 },
    xAxis: { type: 'category', data: data.dates },
    yAxis: { type: 'value', axisLabel: { formatter: value => formatCurrencyShort(value).replace('₩', '') } },
    series: [
      {
        name: '일별 확정 손익',
        type: 'bar',
        data: data.daily_pnl,
        itemStyle: {
          color: params => params.value >= 0 ? '#16a34a' : '#dc2626',
          borderRadius: [4, 4, 0, 0]
        }
      },
      {
        name: '누적 실현손익',
        type: 'line',
        smooth: true,
        lineStyle: { color: '#2563eb', width: 3 },
        areaStyle: { color: 'rgba(37, 99, 235, 0.12)' },
        data: data.cumulative_pnl
      }
    ]
  });
  registerChart(chart);
}

function renderStockFlowCharts(data) {
  const dates = data.dates || [];
  const amounts = data.amounts || [];
  const holdings = data.holdings || [];

  const timelineEl = document.getElementById('timelineChart');
  const holdingsEl = document.getElementById('holdingsChart');
  if (!dates.length) {
    renderStockDetailEmpty(timelineEl, '거래 현금흐름 데이터가 없습니다.');
    renderStockDetailEmpty(holdingsEl, '보유량 변화 데이터가 없습니다.');
    return;
  }

  const timelineChart = echarts.init(timelineEl, 'assetDark');
  timelineChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { left: 48, right: 24, top: 24, bottom: 32 },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', axisLabel: { formatter: value => formatCurrencyShort(value).replace('₩', '') } },
    series: [{
      name: '거래 현금흐름',
      type: 'bar',
      data: amounts,
      itemStyle: {
        color: params => params.value >= 0 ? '#16a34a' : '#dc2626',
        borderRadius: [4, 4, 0, 0]
      }
    }]
  });
  registerChart(timelineChart);

  const holdingsChart = echarts.init(holdingsEl, 'assetDark');
  holdingsChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { left: 44, right: 24, top: 24, bottom: 32 },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value' },
    series: [{
      name: '보유량',
      type: 'line',
      smooth: true,
      areaStyle: { color: 'rgba(37, 99, 235, 0.12)' },
      lineStyle: { color: '#2563eb', width: 3 },
      data: holdings
    }]
  });
  registerChart(holdingsChart);
}

function renderStockDetailEmpty(el, message) {
  if (!el) return;
  el.innerHTML = `
    <div class="chart-empty">
      <i data-lucide="line-chart"></i>
      <span>${message}</span>
    </div>
  `;
  if (window.lucide) lucide.createIcons({ nodes: [el] });
}
