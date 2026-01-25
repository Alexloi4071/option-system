const ChartGexOi = {
    chart: null,

    render(data) {
        const ctx = document.getElementById('chart-gex-oi');
        if (!ctx) return;

        const m31 = data.calculations?.module31_advanced_market_indicators;
        if (!m31) return;

        // We need distribution data.
        // Assuming m31 contains 'gex_profile' or we can derive from option chain if available.
        // If m31 has 'gex_by_strike' or similar:
        // Let's assume the backend provides 'strike_data': [{strike, call_gex, put_gex, call_oi, put_oi}, ...]

        // Fallback: If M31 doesn't have detailed arrays, we might need to process option_chain Raw Data.
        let strikes = [];
        let callOi = [];
        let putOi = [];
        let callGex = [];
        let putGex = [];

        // Use Option Chain to build distribution
        const chain = data.raw_data.option_chain;
        if (chain && (chain.calls || chain.puts)) {
            // Processing logic (simplified for visualization)
            // Group by Strike
            const map = {};

            [...(chain.calls || []), ...(chain.puts || [])].forEach(opt => {
                if (!map[opt.strike]) map[opt.strike] = { call_oi: 0, put_oi: 0, call_gex: 0, put_gex: 0 };
                // OI
                if (opt.contractSymbol.includes('C')) map[opt.strike].call_oi += opt.openInterest;
                else map[opt.strike].put_oi += opt.openInterest;

                // GEX (Gamma * Price * OI * 100 * Spot * 0.01 ish approximation)
                // If we don't have Gamma in raw data, we can't calc GEX accurately. 
                // Let's stick to OI for now if GEX missing, or use placeholders.
                // Assuming we just plot OI distribution.
            });

            strikes = Object.keys(map).map(Number).sort((a, b) => a - b);
            // Filter outlier strikes
            const spot = data.raw_data.current_price;
            strikes = strikes.filter(s => s > spot * 0.7 && s < spot * 1.3);

            callOi = strikes.map(s => map[s].call_oi);
            putOi = strikes.map(s => map[s].put_oi); // Negative for visual split?
        }

        if (this.chart) this.chart.destroy();

        const spot = data.raw_data.current_price;
        const maxPain = m31.max_pain_price;

        this.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: strikes,
                datasets: [
                    {
                        label: 'Call OI (未平倉)',
                        data: callOi,
                        backgroundColor: 'rgba(16, 185, 129, 0.6)', // Emerald
                        borderColor: '#10b981',
                        borderWidth: 1
                    },
                    {
                        label: 'Put OI (未平倉)',
                        data: putOi,
                        backgroundColor: 'rgba(239, 68, 68, 0.6)', // Red
                        borderColor: '#ef4444',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        stacked: true,
                        grid: { display: false },
                        ticks: { color: '#94a3b8' }
                    },
                    y: {
                        stacked: true,
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#94a3b8' }
                    }
                },
                plugins: {
                    annotation: {
                        annotations: {
                            line1: {
                                type: 'line',
                                xMin: strikes.findIndex(s => s >= spot),
                                xMax: strikes.findIndex(s => s >= spot),
                                borderColor: 'white',
                                borderDash: [5, 5],
                                borderWidth: 2,
                                label: { content: '現價', enabled: true, position: 'top' }
                            },
                            line2: {
                                type: 'line',
                                xMin: strikes.findIndex(s => s >= maxPain),
                                xMax: strikes.findIndex(s => s >= maxPain),
                                borderColor: 'orange',
                                borderWidth: 2,
                                label: { content: '最大痛點 (Max Pain)', enabled: true, position: 'top', yAdjust: 20 }
                            }
                        }
                    }
                }
            }
        });
    }
};
