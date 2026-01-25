const ChartHvTrend = {
    chart: null,

    render(data) {
        const ctx = document.getElementById('chart-hv-trend');
        if (!ctx) return;

        const m18 = data.calculations?.module18_historical_volatility;
        if (!m18) return;

        // We need time series data for HV.
        // If the backend only provides current values (hv_10, hv_20 etc), we can show a Bar Comparison.
        // If backend provides 'hv_history', we plot trend line.

        // Assuming current snapshot for now: [HV10, HV20, HV30, HV60, IV]

        const labels = ['10日 HV', '20日 HV', '30日 HV', '60日 HV', '90日 HV', '當前 IV'];
        const values = [
            m18.hv_10 * 100,
            m18.hv_20 * 100,
            m18.hv_30 * 100,
            m18.hv_60 * 100,
            m18.hv_90 * 100,
            data.raw_data.implied_volatility // Already % or number? Raw data usually IV is around 0.20 or 20. 
        ];
        // Check IV scaling in raw_data. JSON sample showed "7409.69"?? Likely annual %. 
        // Code usually: IV 0.20 -> 20%. 
        // If logic is consistently %, use as is.

        if (this.chart) this.chart.destroy();

        this.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: '波動率 (%)',
                    data: values,
                    backgroundColor: [
                        'rgba(99, 102, 241, 0.5)',
                        'rgba(99, 102, 241, 0.5)',
                        'rgba(99, 102, 241, 0.5)',
                        'rgba(99, 102, 241, 0.5)',
                        'rgba(99, 102, 241, 0.5)',
                        'rgba(16, 185, 129, 0.8)' // IV Highlight
                    ],
                    borderColor: [
                        'transparent', 'transparent', 'transparent', 'transparent', 'transparent', '#10b981'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: '歷史波動率 vs 隱含波動率 (HV vs IV)' }
                },
                scales: {
                    y: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#94a3b8' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#94a3b8' }
                    }
                }
            }
        });
    }
};
