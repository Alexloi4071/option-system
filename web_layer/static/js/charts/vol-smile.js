const ChartVolSmile = {
    chart: null,

    render(data) {
        const ctx = document.getElementById('chart-vol-smile');
        if (!ctx) return;

        // Attempt to get Smile data from Module 25
        const m25 = data.calculations?.module25_volatility_smile;
        const chain = data.raw_data?.option_chain;

        // Data Prep
        let strikes = [];
        let ivs = [];

        // If we have full raw chain data, we can plot a real smile
        if (chain && (chain.calls || chain.puts)) {
            // Combine Calls and Puts to get best IV for each strike
            // For simplicity, let's use Calls for OTM/ATM calls and Puts for OTM puts logic, 
            // OR just plot all IVs available.

            // Simplest: use Calls IV
            const calls = chain.calls || [];
            // Filter for reasonable range +/- 20% of spot
            const spot = data.raw_data.current_price;
            const relevant = calls
                .filter(c => c.strike > spot * 0.8 && c.strike < spot * 1.2)
                .sort((a, b) => a.strike - b.strike);

            strikes = relevant.map(c => c.strike);
            ivs = relevant.map(c => c.impliedVolatility * 100); // to percent
        } else if (m25 && m25.smile_curve_points) {
            // Fallback if pre-calculated points exist in module output (hypothetically)
            strikes = m25.smile_curve_points.map(p => p.strike);
            ivs = m25.smile_curve_points.map(p => p.iv);
        } else {
            // Mock data or failure
            return;
        }

        if (this.chart) this.chart.destroy();

        const spot = data.raw_data.current_price;

        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: strikes,
                datasets: [{
                    label: '隱含波動率 (IV %)',
                    data: ivs,
                    borderColor: '#06b6d4', // Cyan 500
                    backgroundColor: 'rgba(6, 182, 212, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 2,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: { display: false },
                    annotation: {
                        annotations: {
                            line1: {
                                type: 'line',
                                xMin: strikes.findIndex(s => s >= spot), // Approximate index
                                xMax: strikes.findIndex(s => s >= spot),
                                borderColor: '#ffffff',
                                borderDash: [2, 2],
                                borderWidth: 1,
                                label: { content: '現價 (Spot)', enabled: true, position: 'bottom' }
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: { display: true, text: '行使價 (Strike)' },
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#94a3b8' }
                    },
                    y: {
                        title: { display: true, text: 'IV %' },
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#94a3b8' }
                    }
                }
            }
        });
    }
};
