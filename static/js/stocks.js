const stockChartColors = {
  pnl: '#2563eb',
  positive: '#16a34a',
  negative: '#dc2626',
  grid: '#e5e7eb',
  text: '#64748b'
};

document.addEventListener('DOMContentLoaded', () => {
  loadStocks();
});

async function loadStocks() {
  const [portfolioRes, pnlRes] = await Promise.all([
    api('/api/stocks'),
    api('/api/stocks/pnl-timeline')
  ]);

  if (!portfolioRes.success) {
    showToast(portfolioRes.error || '주식 데이터를 불러오지 못했습니다.', 'error');
    return;
  }

  const portfolio = portfolioRes.data || [];
  const pnlTimeline = pnlRes.success ? pnlRes.data : null;

  renderStockSummary(portfolio, pnlTimeline);
  renderStockPnlTimeline(pnlTimeline);
  renderStockTable(portfolio);
}

function renderStockSummary(portfolio, pnlTimeline) {
  const summary = document.getElementById('stockSummary');
  if (!summary) return;

  const totalBuy = pnlTimeline?.total_buy ?? portfolio.reduce((sum, row) => sum + (row.total_buy || 0), 0);
  const totalSell = pnlTimeline?.total_sell ?? portfolio.reduce((sum, row) => sum + (row.total_sell || 0), 0);
  const realizedPnl = pnlTimeline?.realized_pnl ?? portfolio.reduce((sum, row) => sum + (row.realized_pnl || 0), 0);
  const cashBasis = pnlTimeline?.cash_basis_result ?? (totalSell - totalBuy);
  const openCostBasis = pnlTimeline?.open_cost_basis ?? 0;
  const holdings = portfolio.filter(row => (row.holdings || 0) > 0).length;

  summary.className = 'stat-cards';
  summary.innerHTML = `
    <article class="stat-card stat-card--hero">
      <div class="stat-card__value ${realizedPnl >= 0 ? 'text-positive' : 'text-negative'}">${formatCurrency(realizedPnl)}</div>
      <div class="stat-card__label">누적 실현손익</div>
    </article>
    <article class="stat-card">
      <div class="stat-card__value ${cashBasis >= 0 ? 'text-positive' : 'text-negative'}">${formatCurrency(cashBasis)}</div>
      <div class="stat-card__label">현금흐름 결과 (보유분 미반영)</div>
    </article>
    <article class="stat-card">
      <div class="stat-card__value">${formatCurrency(totalBuy)}</div>
      <div class="stat-card__label">누적 넣은 돈</div>
    </article>
    <article class="stat-card">
      <div class="stat-card__value">${formatCurrency(totalSell)}</div>
      <div class="stat-card__label">누적 뺀 돈</div>
    </article>
    <article class="stat-card">
      <div class="stat-card__value">${formatCurrency(openCostBasis)}</div>
      <div class="stat-card__label">아직 보유 중인 취득원가</div>
    </article>
    <article class="stat-card">
      <div class="stat-card__value">${formatNumber(holdings)}</div>
      <div class="stat-card__label">보유 종목</div>
    </article>
  `;
}

function renderStockPnlTimeline(data) {
  const el = document.getElementById('stockPnlTimelineChart');
  if (!el) return;

  if (!data || !(data.dates || []).length) {
    renderStockChartEmpty(el, '주식 거래내역을 업로드하면 누적 손익 그래프가 표시됩니다.');
    return;
  }

  const chart = echarts.init(el, 'assetDark');
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      formatter(params) {
        return params.map(param => {
          const value = Array.isArray(param.value) ? param.value[1] : param.value;
          return `${param.marker}${param.seriesName}: ${formatCurrency(value)}`;
        }).join('<br>');
      }
    },
    legend: { data: ['누적 실현손익', '일별 확정 손익'] },
    grid: { left: 56, right: 28, top: 48, bottom: 42 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: data.dates,
      axisLine: { lineStyle: { color: stockChartColors.grid } },
      axisLabel: { color: stockChartColors.text }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        color: stockChartColors.text,
        formatter: value => formatCurrencyShort(value).replace('₩', '')
      },
      splitLine: { lineStyle: { color: stockChartColors.grid } }
    },
    series: [
      {
        name: '일별 확정 손익',
        type: 'bar',
        data: data.daily_pnl,
        itemStyle: {
          color: params => params.value >= 0 ? stockChartColors.positive : stockChartColors.negative,
          borderRadius: [4, 4, 0, 0]
        }
      },
      {
        name: '누적 실현손익',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: stockChartColors.pnl, width: 3 },
        areaStyle: { color: 'rgba(37, 99, 235, 0.12)' },
        data: data.cumulative_pnl
      }
    ]
  });
  registerChart(chart);
}

function renderStockTable(portfolio) {
  const tbody = document.querySelector('#stockTable tbody');
  if (!tbody) return;

  if (!portfolio.length) {
    tbody.innerHTML = '<tr><td colspan="6"><div class="empty-inline">주식 거래 데이터가 없습니다.</div></td></tr>';
    return;
  }

  tbody.innerHTML = portfolio.map(row => `
    <tr class="clickable" onclick="window.location.href='/stocks/${row.stock_id}'">
      <td><strong>${escapeHtml(row.stock_name)}</strong></td>
      <td class="font-mono">${escapeHtml(row.stock_code || '-')}</td>
      <td class="text-right">${formatNumber(row.holdings || 0)}</td>
      <td class="text-right">${formatCurrency(row.total_buy || 0)}</td>
      <td class="text-right">${formatCurrency(row.total_sell || 0)}</td>
      <td class="text-right ${(row.realized_pnl || 0) >= 0 ? 'text-positive' : 'text-negative'}">${formatCurrency(row.realized_pnl || 0)}</td>
    </tr>
  `).join('');
}

function renderStockChartEmpty(el, message) {
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
