document.addEventListener('DOMContentLoaded', () => {
    loadSummary();
    loadCharts();
});

async function loadSummary() {
    const res = await api('/api/dashboard/summary');
    if (res.success && res.data) {
        document.getElementById('totalDeposit').textContent = formatCurrency(res.data.total_deposit || 0);
        document.getElementById('totalWithdrawal').textContent = formatCurrency(res.data.total_withdrawal || 0);
        document.getElementById('netAmount').textContent = formatCurrency((res.data.total_deposit || 0) - (res.data.total_withdrawal || 0));
        document.getElementById('personCount').textContent = formatNumber(res.data.person_count || 0) + '명';
        document.getElementById('txCount').textContent = formatNumber(res.data.tx_count || 0) + '건';
        document.getElementById('stockPnl').textContent = formatCurrency(res.data.stock_pnl || 0);
    }
}

async function loadCharts() {
    // 월별 추이
    const monthlyRes = await api('/api/dashboard/monthly');
    if (monthlyRes.success) initMonthlyChart(monthlyRes.data);

    // 인물별 비중
    const peopleRes = await api('/api/dashboard/people-share');
    if (peopleRes.success) initPeopleShareChart(peopleRes.data);

    // 누적 흐름
    const cumRes = await api('/api/dashboard/cumulative');
    if (cumRes.success) initCumulativeChart(cumRes.data);

    // 계좌별
    const accRes = await api('/api/dashboard/account-comparison');
    if (accRes.success) initAccountChart(accRes.data);

    // 히트맵
    const heatRes = await api('/api/dashboard/heatmap');
    if (heatRes.success) initHeatmapChart(heatRes.data);
}

function initMonthlyChart(data) {
    const chart = echarts.init(document.getElementById('chartMonthly'), 'dark');
    chart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis' },
        legend: { data: ['입금', '출금'] },
        xAxis: { data: data.labels },
        yAxis: {},
        series: [
            { name: '입금', type: 'bar', stack: 'total', data: data.deposits, itemStyle: { color: 'var(--color-positive)' } },
            { name: '출금', type: 'bar', stack: 'total', data: data.withdrawals, itemStyle: { color: 'var(--color-negative)' } }
        ]
    });
    window.addEventListener('resize', () => chart.resize());
}

function initPeopleShareChart(data) {
    const chart = echarts.init(document.getElementById('chartPeopleShare'), 'dark');
    chart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item' },
        series: [{
            type: 'pie',
            radius: ['40%', '70%'],
            data: data.map(d => ({name: d.name, value: d.amount}))
        }]
    });
    window.addEventListener('resize', () => chart.resize());
}

function initCumulativeChart(data) {
    const chart = echarts.init(document.getElementById('chartCumulative'), 'dark');
    chart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: data.dates },
        yAxis: { type: 'value' },
        series: [{
            data: data.amounts,
            type: 'line',
            areaStyle: {},
            itemStyle: { color: 'var(--accent-primary)' }
        }]
    });
    window.addEventListener('resize', () => chart.resize());
}

function initAccountChart(data) {
    const chart = echarts.init(document.getElementById('chartAccount'), 'dark');
    chart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis' },
        legend: { data: ['입금', '출금'] },
        xAxis: { type: 'category', data: data.map(d => d.account_name) },
        yAxis: { type: 'value' },
        series: [
            { name: '입금', type: 'bar', data: data.map(d => d.deposits), itemStyle: { color: 'var(--color-positive)' } },
            { name: '출금', type: 'bar', data: data.map(d => d.withdrawals), itemStyle: { color: 'var(--color-negative)' } }
        ]
    });
    window.addEventListener('resize', () => chart.resize());
}

function initHeatmapChart(data) {
    const chart = echarts.init(document.getElementById('chartHeatmap'), 'dark');
    // 간단한 캘린더 히트맵 구현
    const year = new Date().getFullYear();
    chart.setOption({
        backgroundColor: 'transparent',
        tooltip: { position: 'top' },
        visualMap: {
            min: 0,
            max: 10,
            calculable: true,
            orient: 'horizontal',
            left: 'center',
            bottom: '15%'
        },
        calendar: [{
            range: year,
            cellSize: ['auto', 20]
        }],
        series: [{
            type: 'heatmap',
            coordinateSystem: 'calendar',
            data: data.map(d => [d.date, d.count])
        }]
    });
    window.addEventListener('resize', () => chart.resize());
}
