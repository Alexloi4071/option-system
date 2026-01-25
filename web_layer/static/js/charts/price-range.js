const ChartPriceRange = {
    chart: null,

    render(data) {
        const ctx = document.getElementById('chart-price-range');
        if (!ctx) return;

        const m1 = data.calculations?.module1_iv_price_range;
        if (!m1) return;

        const currentPrice = data.raw_data.current_price;

        // Prepare Datasets for Horizontal Bar
        // We want bars spanning from Low to High for each confidence level
        const intervals = m1.confidence_intervals.sort((a, b) => b.confidence_level - a.confidence_level); // Largest first

        const labels = intervals.map(i => `${(i.confidence_level * 100).toFixed(0)}%`);

        // Construct Floating Bars data: [min, max]
        const barData = intervals.map(i => [
            i.price_range.min_price,
            i.price_range.max_price
        ]);

        // Colors based on confidence (darker for wider/higher confidence)
        const bgColors = [
            'rgba(139, 92, 246, 0.2)', // 99%
            'rgba(139, 92, 246, 0.4)', // 95%
            'rgba(139, 92, 246, 0.6)', // 90%
            'rgba(139, 92, 246, 0.8)', // 80%
            'rgba(139, 92, 246, 1.0)'  // 68%
        ];

        if (this.chart) this.chart.destroy();

        this.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: '預期區間 (Expected Range)',
                    data: barData,
                    backgroundColor: bgColors,
                    borderWidth: 0,
                    barPercentage: 0.6
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const v = ctx.raw;
                                return `$${v[0].toFixed(2)} - $${v[1].toFixed(2)}`;
                            }
                        }
                    },
                    annotation: {
                        annotations: {
                            line1: {
                                type: 'line',
                                xMin: currentPrice,
                                xMax: currentPrice,
                                borderColor: '#10b981', // Emerald 500
                                borderWidth: 2,
                                borderDash: [5, 5],
                                label: {
                                    content: '現價',
                                    enabled: true,
                                    position: 'top'
                                }
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#94a3b8' }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: '#e2e8f0', font: { family: 'Inter' } }
                    }
                }
            }
        });
    }
};
