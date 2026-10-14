/**
 * 主应用逻辑 - 大乐透版本
 */

// 全局状态
let appData = {
    lotteryHistory: null,
    aiPredictions: null,
    predictionsHistory: null
};

// 大乐透配置
const LOTTERY_CONFIG = {
    frontCount: 5,       // 前区选5个
    frontMax: 35,        // 前区1-35
    backCount: 2,        // 后区选2个
    backMax: 12,         // 后区1-12
    sumMin: 60,          // 和值范围
    sumMax: 120,
    zones: [[1, 12], [13, 24], [25, 35]]  // 三区划分
};

// 初始化应用
async function initApp() {
    try {
        await loadAllData();
        renderHeroBanner();
        renderModelsGrid();
        renderHistoryTab();
        setupEventListeners();
        hideLoadingScreen();
    } catch (error) {
        console.error('初始化失败:', error);
        alert('数据加载失败，请刷新页面重试');
    }
}

// 加载所有数据
async function loadAllData() {
    try {
        const [lotteryHistory, aiPredictions, predictionsHistory] = await Promise.all([
            DataLoader.loadLotteryHistory(),
            DataLoader.loadPredictions(),
            DataLoader.loadPredictionsHistory()
        ]);

        appData.lotteryHistory = lotteryHistory;
        appData.aiPredictions = aiPredictions;
        appData.predictionsHistory = predictionsHistory;
    } catch (error) {
        console.error('数据加载失败:', error);
        throw error;
    }
}

// 渲染Hero Banner
function renderHeroBanner() {
    if (!appData.lotteryHistory || !appData.aiPredictions) return;

    const nextDraw = appData.lotteryHistory.next_draw;
    const heroPeriodEl = document.getElementById('heroPeriod');
    if (heroPeriodEl) heroPeriodEl.textContent = nextDraw.next_period;

    const heroDateDisplayEl = document.getElementById('heroDateDisplay');
    if (heroDateDisplayEl) heroDateDisplayEl.textContent = nextDraw.next_date_display;

    const heroDrawTimeEl = document.getElementById('heroDrawTime');
    if (heroDrawTimeEl) heroDrawTimeEl.textContent = `${nextDraw.draw_time} 开奖`;

    const heroPredictionDateEl = document.getElementById('heroPredictionDate');
    if (heroPredictionDateEl) heroPredictionDateEl.textContent = appData.aiPredictions.prediction_date;

    const heroCountdownEl = document.getElementById('heroCountdown');
    if (heroCountdownEl) {
        const daysUntil = calculateDaysUntil(nextDraw.next_date);
        heroCountdownEl.textContent = daysUntil > 0 ? `距离开奖仅剩 ${daysUntil} 天` : '即将开奖';
    }
}

// 渲染模型网格
function renderModelsGrid() {
    if (!appData.aiPredictions) return;

    const modelsGridEl = document.getElementById('modelsGrid');
    if (!modelsGridEl) return;

    modelsGridEl.innerHTML = '';

    const targetPeriod = appData.aiPredictions.target_period;
    const latestDraw = appData.lotteryHistory?.data?.[0];
    let actualResult = null;

    if (latestDraw && parseInt(targetPeriod) <= parseInt(latestDraw.period)) {
        actualResult = appData.lotteryHistory.data.find(draw => draw.period === targetPeriod);
        if (actualResult) {
            const statusBanner = createDrawnStatusBanner(actualResult);
            modelsGridEl.appendChild(statusBanner);
        }
    }

    appData.aiPredictions.models.forEach(model => {
        const modelCard = Components.createModelCard(model, actualResult);
        modelsGridEl.appendChild(modelCard);
    });
}

// 创建已开奖状态横幅
function createDrawnStatusBanner(actualResult) {
    const banner = document.createElement('div');
    banner.className = 'drawn-status-banner';
    banner.innerHTML = `
        <div class="drawn-status-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
        </div>
        <div class="drawn-status-content">
            <h3 class="drawn-status-title">第 ${actualResult.period} 期已开奖</h3>
            <p class="drawn-status-subtitle">以下为预测命中情况对比</p>
        </div>
        <div class="drawn-status-balls">
            ${actualResult.front_balls.map(num => `<span class="mini-result-ball red">${num}</span>`).join('')}
            <span class="mini-result-ball-divider"></span>
            ${actualResult.back_balls.map(num => `<span class="mini-result-ball blue">${num}</span>`).join('')}
        </div>
    `;
    return banner;
}

// 渲染历史标签页
function renderHistoryTab() {
    renderAccuracyChart();
    renderAccuracyCards();
    renderHistoryTable();
}

// 渲染准确度图表
function renderAccuracyChart() {
    if (!appData.predictionsHistory) return;

    const chartEl = document.getElementById('accuracyChart');
    if (!chartEl) return;

    const chartData = prepareChartData();
    const fontFamily = getComputedStyle(chartEl).fontFamily;
    document.getElementById('accuracyChartCount').textContent = `${chartData.labels.length} 期记录`;
    document.getElementById('accuracyChartRange').textContent = chartData.labels.length
        ? `${chartData.labels[0]} — ${chartData.labels.at(-1)} 期`
        : '暂无历史记录';

    Chart.getChart(chartEl)?.destroy();
    const chart = Chart.getChart(chartEl)?.destroy();
    new Chart(chartEl, {
        type: 'line',
        data: {
            labels: chartData.labels,
            datasets: chartData.datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            onResize: (chart, size) => {
                chart.options.scales.x.ticks.maxTicksLimit = size.width < 600 ? 5 : 10;
            },
            animation: window.matchMedia('(prefers-reduced-motion: reduce)').matches
                ? false : { duration: 500 },
            interaction: { mode: 'index', intersect: false },
            layout: { padding: { top: 8, right: 8 } },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.98)',
                    titleColor: '#1e293b',
                    bodyColor: '#475569',
                    borderColor: '#e0e7ff',
                    borderWidth: 1,
                    cornerRadius: 12,
                    padding: 14,
                    titleFont: { family: fontFamily, size: 13, weight: '600' },
                    bodyFont: { family: fontFamily, size: 12 },
                    titleMarginBottom: 10,
                    bodySpacing: 8,
                    boxWidth: 7,
                    boxHeight: 7,
                    boxPadding: 6,
                    usePointStyle: true,
                    callbacks: {
                        title: items => `第 ${items[0].label} 期`,
                        label: item => ` ${item.dataset.label}   ${item.parsed.y} 球`,
                        labelColor: item => ({
                            borderColor: item.dataset.borderColor,
                            backgroundColor: item.dataset.borderColor
                        })
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    border: { display: false },
                    ticks: {
                        color: '#94a3b8',
                        font: { family: fontFamily, size: 11 },
                        maxRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 10,
                        padding: 12
                    }
                },
                y: {
                    beginAtZero: true,
                    max: 7,  // 5前区 + 2后区 = 7
                    border: { display: false, dash: [4, 5] },
                    grid: { color: '#edf0f7', drawTicks: false },
                    ticks: {
                        stepSize: 1,
                        color: '#94a3b8',
                        font: { family: fontFamily, size: 11 },
                        padding: 12
                    }
                }
            }
        },
        plugins: [{
            id: 'accuracyHoverGuide',
            beforeDatasetsDraw(chart) {
                const [active] = chart.tooltip?.getActiveElements() || [];
                if (!active || chart.tooltip.opacity === 0) return;
                const { ctx, chartArea } = chart;
                ctx.save();
                ctx.beginPath();
                ctx.moveTo(active.element.x, chartArea.top);
                ctx.lineTo(active.element.x, chartArea.bottom);
                ctx.strokeStyle = '#c7d2fe';
                ctx.lineWidth = 1;
                ctx.setLineDash([4, 4]);
                ctx.stroke();
                ctx.restore();
            }
        }]
    });

    const legend = document.getElementById('accuracyChartLegend');
    legend.replaceChildren();
    chart.data.datasets.forEach((dataset, index) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = dataset.label;
        button.style.setProperty('--series-color', dataset.borderColor);
        button.setAttribute('aria-pressed', 'true');
        button.setAttribute('aria-controls', 'accuracyChart');
        button.addEventListener('click', () => {
            const visible = !chart.isDatasetVisible(index);
            chart.setDatasetVisibility(index, visible);
            button.setAttribute('aria-pressed', String(visible));
            chart.update();
        });
        legend.appendChild(button);
    });
}

// 准备图表数据
function prepareChartData() {
    const history = appData.predictionsHistory.predictions_history;
    const reversedHistory = [...history].reverse();
    const labels = reversedHistory.map(record => record.target_period);
    const series = new Map();

    reversedHistory.forEach((record, periodIndex) => {
        const isSimulation = record.data_source === 'random_simulation';
        record.models.forEach(model => {
            const key = JSON.stringify([isSimulation, model.model_name]);
            if (!series.has(key)) {
                series.set(key, {
                    modelName: model.model_name,
                    isSimulation,
                    data: Array(labels.length).fill(null)
                });
            }
            const bestHit = Math.max(...model.predictions.map(p => p.hit_result?.total_hits || 0));
            series.get(key).data[periodIndex] = bestHit;
        });
    });

    const colors = {
        'GPT-5': '#10b981',
        'Claude 4.5': '#8b5cf6',
        'Gemini 2.5 Pro': '#06b6d4',
        'Gemini 2.5': '#3b82f6',
        'DeepSeek R1': '#f59e0b',
        'GPT5': '#f43f5e',
        '历史补录': '#6366f1'
    };

    const palette = Object.values(colors);
    const datasets = [...series.values()].map(({ modelName, isSimulation, data }, index) => {
        const color = colors[modelName] || palette[index % palette.length];
        return {
            label: isSimulation ? `${modelName}（非实测）` : modelName,
            data,
            borderColor: color,
            backgroundColor: context => {
                const { ctx, chartArea } = context.chart;
                if (!chartArea) return `${color}0a`;
                const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                gradient.addColorStop(0, `${color}24`);
                gradient.addColorStop(1, `${color}00`);
                return gradient;
            },
            fill: 'origin',
            spanGaps: false,
            borderWidth: 2,
            borderCapStyle: 'round',
            borderJoinStyle: 'round',
            pointBackgroundColor: color,
            pointBorderColor: '#ffffff',
            pointBorderWidth: 1.5,
            pointRadius: context => {
                const i = context.dataIndex;
                if (data[i - 1] == null && data[i + 1] == null) return 3.5;
                return context.chart.width < 600 ? 0 : 2;
            },
            pointHoverRadius: 5,
            pointHoverBorderWidth: 2.5,
            pointHitRadius: 10,
            cubicInterpolationMode: 'monotone',
            tension: 0.25
        };
    });

    return { labels, datasets };
}

// 渲染准确度卡片
function renderAccuracyCards() {
    if (!appData.predictionsHistory) return;

    const containerEl = document.getElementById('accuracyCardsContainer');
    if (!containerEl) return;

    containerEl.innerHTML = '';

    appData.predictionsHistory.predictions_history.forEach(record => {
        const card = Components.createAccuracyCard(record);
        containerEl.appendChild(card);
    });
}

// 渲染历史表格
function renderHistoryTable() {
    if (!appData.lotteryHistory) return;

    const tableBodyEl = document.getElementById('historyTableBody');
    if (!tableBodyEl) return;

    tableBodyEl.innerHTML = '';

    appData.lotteryHistory.data.forEach(draw => {
        const row = Components.createHistoryTableRow(draw);
        tableBodyEl.appendChild(row);
    });
}

// 渲染前区频率图表
function renderFrequencyChart() {
    if (!appData.lotteryHistory) return;

    const chartEl = document.getElementById('frequencyChart');
    if (!chartEl) return;

    // 前区1-35
    const frequency = {};
    for (let i = 1; i <= LOTTERY_CONFIG.frontMax; i++) {
        frequency[i.toString().padStart(2, '0')] = 0;
    }

    appData.lotteryHistory.data.forEach(draw => {
        if (!draw.front_balls || !draw.back_balls) return;
        draw.front_balls.forEach(ball => {
            frequency[ball] = (frequency[ball] || 0) + 1;
        });
    });

    const labels = Object.keys(frequency).sort();
    const data = labels.map(label => frequency[label]);

    Chart.getChart(chartEl)?.destroy();
    new Chart(chartEl, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '出现次数',
                data: data,
                backgroundColor: '#fca5a5',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, ticks: { stepSize: 1 } }
            }
        }
    });
}

// 渲染统计卡片
function renderStatisticsCards() {
    if (!appData.lotteryHistory) return;

    // 前区频率
    const frontFrequency = {};
    for (let i = 1; i <= LOTTERY_CONFIG.frontMax; i++) {
        frontFrequency[i.toString().padStart(2, '0')] = 0;
    }

    // 后区频率
    const backFrequency = {};
    for (let i = 1; i <= LOTTERY_CONFIG.backMax; i++) {
        backFrequency[i.toString().padStart(2, '0')] = 0;
    }

    let totalSum = 0;

    appData.lotteryHistory.data.forEach(draw => {
        if (!draw.front_balls || !draw.back_balls) return;
        draw.front_balls.forEach(ball => {
            frontFrequency[ball] = (frontFrequency[ball] || 0) + 1;
        });
        draw.back_balls.forEach(ball => {
            backFrequency[ball] = (backFrequency[ball] || 0) + 1;
        });
        const sum = draw.front_balls.reduce((acc, ball) => acc + parseInt(ball), 0);
        totalSum += sum;
    });

    const hottestFront = Object.entries(frontFrequency).sort((a, b) => b[1] - a[1])[0];
    const hottestBack = Object.entries(backFrequency).sort((a, b) => b[1] - a[1])[0];
    const avgSum = Math.round(totalSum / appData.lotteryHistory.data.length);

    const totalDrawsEl = document.getElementById('statTotalDraws');
    if (totalDrawsEl) totalDrawsEl.textContent = `${appData.lotteryHistory.data.length} 期`;

    const hottestFrontEl = document.getElementById('statHottestRed');
    if (hottestFrontEl) hottestFrontEl.textContent = `${hottestFront[0]} (${hottestFront[1]}次)`;

    const hottestBackEl = document.getElementById('statHottestBlue');
    if (hottestBackEl) hottestBackEl.textContent = `${hottestBack[0]} (${hottestBack[1]}次)`;

    const avgSumEl = document.getElementById('statAvgSum');
    if (avgSumEl) avgSumEl.textContent = avgSum;
}

// 渲染后区频率图表
function renderBlueFrequencyChart() {
    if (!appData.lotteryHistory) return;

    const chartEl = document.getElementById('blueFrequencyChart');
    if (!chartEl) return;

    const frequency = {};
    for (let i = 1; i <= LOTTERY_CONFIG.backMax; i++) {
        frequency[i.toString().padStart(2, '0')] = 0;
    }

    appData.lotteryHistory.data.forEach(draw => {
        if (!draw.front_balls || !draw.back_balls) return;
        draw.back_balls.forEach(ball => {
            frequency[ball] = (frequency[ball] || 0) + 1;
        });
    });

    const labels = Object.keys(frequency).sort();
    const data = labels.map(label => frequency[label]);

    Chart.getChart(chartEl)?.destroy();
    new Chart(chartEl, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '出现次数',
                data: data,
                backgroundColor: '#93c5fd',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, ticks: { stepSize: 1 } }
            }
        }
    });
}

// 渲染奇偶比图表
function renderOddEvenChart() {
    if (!appData.lotteryHistory) return;

    const chartEl = document.getElementById('oddEvenChart');
    if (!chartEl) return;

    const ratioCount = {};
    const frontCount = LOTTERY_CONFIG.frontCount;

    appData.lotteryHistory.data.forEach(draw => {
        const oddCount = draw.front_balls.filter(ball => parseInt(ball) % 2 === 1).length;
        const evenCount = frontCount - oddCount;
        const ratio = `${oddCount}:${evenCount}`;
        ratioCount[ratio] = (ratioCount[ratio] || 0) + 1;
    });

    // 大乐透5个号的奇偶比
    const commonRatios = ['0:5', '1:4', '2:3', '3:2', '4:1', '5:0'];
    const labels = commonRatios.filter(r => ratioCount[r]);
    const data = labels.map(label => ratioCount[label] || 0);

    Chart.getChart(chartEl)?.destroy();
    new Chart(chartEl, {
        type: 'doughnut',
        data: {
            labels: labels.map(l => `${l} (奇:偶)`),
            datasets: [{
                data: data,
                backgroundColor: [
                    '#ef4444', '#f97316', '#f59e0b',
                    '#10b981', '#3b82f6', '#8b5cf6'
                ],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { padding: 15, font: { size: 11 } }
                }
            }
        }
    });
}

// 渲染和值走势图表
function renderSumTrendChart() {
    if (!appData.lotteryHistory) return;

    const chartEl = document.getElementById('sumTrendChart');
    if (!chartEl) return;

    const recentDraws = appData.lotteryHistory.data.slice(0, 30).reverse();

    const labels = recentDraws.map(draw => draw.period);
    const sums = recentDraws.map(draw =>
        draw.front_balls.reduce((acc, ball) => acc + parseInt(ball), 0)
    );

    const avgSum = sums.reduce((a, b) => a + b, 0) / sums.length;

    Chart.getChart(chartEl)?.destroy();
    new Chart(chartEl, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '前区和值',
                    data: sums,
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    borderWidth: 3,
                    pointRadius: 4,
                    pointHoverRadius: 7,
                    tension: 0.3,
                    fill: true
                },
                {
                    label: '平均值',
                    data: Array(sums.length).fill(avgSum),
                    borderColor: '#94a3b8',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    pointRadius: 0,
                    tension: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'top' } },
            scales: {
                y: {
                    beginAtZero: false,
                    min: 30,
                    max: 150
                }
            }
        }
    });
}

// 渲染区间分布图表
function renderZoneDistributionChart() {
    if (!appData.lotteryHistory) return;

    const chartEl = document.getElementById('zoneDistributionChart');
    if (!chartEl) return;

    // 大乐透三区：01-12, 13-24, 25-35
    const zoneNames = ['01-12', '13-24', '25-35'];
    const zones = { '01-12': 0, '13-24': 0, '25-35': 0 };

    appData.lotteryHistory.data.forEach(draw => {
        if (!draw.front_balls || !draw.back_balls) return;
        draw.front_balls.forEach(ball => {
            const num = parseInt(ball);
            if (num >= 1 && num <= 12) zones['01-12']++;
            else if (num >= 13 && num <= 24) zones['13-24']++;
            else if (num >= 25 && num <= 35) zones['25-35']++;
        });
    });

    const labels = Object.keys(zones);
    const data = Object.values(zones);

    Chart.getChart(chartEl)?.destroy();
    new Chart(chartEl, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '出现次数',
                data: data,
                backgroundColor: ['#fca5a5', '#93c5fd', '#d8b4fe'],
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, ticks: { stepSize: 10 } }
            }
        }
    });
}

// 渲染所有分析图表
function renderAllAnalysisCharts() {
    renderStatisticsCards();
    renderFrequencyChart();
    renderBlueFrequencyChart();
    renderOddEvenChart();
    renderSumTrendChart();
    renderZoneDistributionChart();
}

// 设置事件监听
function setupEventListeners() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', () => handleTabSwitch(item.dataset.tab, navItems));
    });

    const mobileNavItems = document.querySelectorAll('.mobile-nav-item');
    mobileNavItems.forEach(item => {
        item.addEventListener('click', () => handleTabSwitch(item.dataset.tab, mobileNavItems));
    });
}

// 处理Tab切换
function handleTabSwitch(tabName, navItems) {
    navItems.forEach(item => {
        if (item.dataset.tab === tabName) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    const allNavItems = document.querySelectorAll('.nav-item, .mobile-nav-item');
    allNavItems.forEach(item => {
        if (item.dataset.tab === tabName) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => {
        if (content.dataset.tab === tabName) {
            content.classList.add('active');
        } else {
            content.classList.remove('active');
        }
    });

    if (tabName === 'analysis') {
        setTimeout(() => renderAllAnalysisCharts(), 100);
    }
}

// 隐藏加载屏幕
function hideLoadingScreen() {
    const loadingScreen = document.getElementById('loadingScreen');
    const mainApp = document.getElementById('mainApp');

    if (loadingScreen) {
        loadingScreen.style.display = 'none';
    }

    if (mainApp) {
        mainApp.style.display = 'block';
    }
}

// 计算距离目标日期的天数
function calculateDaysUntil(targetDateStr) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const targetDate = new Date(targetDateStr);
    targetDate.setHours(0, 0, 0, 0);

    const diffTime = targetDate - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    return diffDays;
}

// 页面加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}

