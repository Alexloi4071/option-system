const ChartPnlCurve = {
    chart: null,
    dataCache: null,

    render(data) {
        const ctx = document.getElementById('chart-strategy-pnl');
        if (!ctx) return;

        this.dataCache = data; // Store full data for switching reference

        // Initialize with Long Call
        this.updateChart('long_call');

        // Setup Tab Listeners
        const tabs = document.querySelectorAll('.strategy-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                // UI Toggle
                tabs.forEach(t => {
                    t.classList.remove('bg-violet-600', 'text-white');
                    t.classList.add('bg-gray-800', 'text-gray-400');
                });
                e.target.classList.remove('bg-gray-800', 'text-gray-400');
                e.target.classList.add('bg-violet-600', 'text-white');

                // Update Chart & Side Panel
                const type = e.target.dataset.tab;
                this.updateChart(type);

                // Update Side Panel (via global helper or assumption)
                if (window.ModulesStrategies) {
                    // Need to retrieve specific module data
                    const map = {
                        'long_call': 'module7_long_call_strategy',
                        'long_put': 'module8_long_put_strategy',
                        'short_call': 'module9_short_call_strategy',
                        'short_put': 'module10_short_put_strategy'
                    };
                    ModulesStrategies.updateStrategyDetails(type, data.calculations[map[type]]);
                }
            });
        });
    },

    updateChart(strategyType) {
        const ctx = document.getElementById('chart-strategy-pnl');
        if (!this.dataCache) return;

        const map = {
            'long_call': 'module7_long_call_strategy',
            'long_put': 'module8_long_put_strategy',
            'short_call': 'module9_short_call_strategy',
            'short_put': 'module10_short_put_strategy'
        };

        const strat = this.dataCache.calculations[map[strategyType]];
        if (!strat) return;

        // Generate Curve Points
        // We need a range of prices around current spot or strike
        const spot = this.dataCache.raw_data.current_price;
        const strike = strat.strike_price || spot; // Fallback
        const range = spot * 0.2; // +/- 20%

        const prices = [];
        const profits = [];

        const steps = 20;
        const start = strike - range;
        const end = strike + range;
        const step = (end - start) / steps;

        for (let i = 0; i <= steps; i++) {
            const price = start + (step * i);
            prices.push(price.toFixed(2));

            // Calculate P&L based on strategy type basic formula
            // Ideally backend provides points, but we can simulate for visualization
            let pnl = 0;
            const cost = strat.net_debit || 0; // or net_credit but represented as cost
            // This is a simplification. Real calculation should come from backend if possible.
            // Assumption: strat object has 'max_profit', 'max_loss', 'break_even_point'

            // Let's use simple Black Scholes pay-off logic
            if (strategyType === 'long_call') {
                pnl = Math.max(0, price - strike) - (strat.premium_paid || 0) * 100; // *100 for contract size?
                // Let's rely on backend 'points' if they existed. If not, simple mock approximation:
                // If backend does NOT provide curve points, we make a linear approximation around strike.
                // Using 'break_even_point' to anchor.

                // If we don't have enough data to calc locally, we might plot flat line?
                // Let's check if strat has 'profit_loss_matrix' (some backends do)
                // If not, use basic intrinsic value logic.
                pnl = (Math.max(0, price - strike) * 100) - strat.cost;
            } else if (strategyType === 'long_put') {
                pnl = (Math.max(0, strike - price) * 100) - strat.cost;
            } else if (strategyType === 'short_call') {
                pnl = strat.credit - (Math.max(0, price - strike) * 100);
            } else if (strategyType === 'short_put') {
                pnl = strat.credit - (Math.max(0, strike - price) * 100);
            }

            profits.push(pnl);
        }

        if (this.chart) this.chart.destroy();

        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: prices,
                datasets: [{
                    label: '損益 (P&L $)',
                    data: profits,
                    borderColor: (ctx) => {
                        // Gradient or standard color?
                        return '#8b5cf6';
                    },
                    segment: {
                        borderColor: ctx => ctx.p0.parsed.y > 0 ? '#10b981' : '#ef4444',
                        backgroundColor: ctx => ctx.p0.parsed.y > 0 ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)'
                    },
                    fill: true,
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    annotation: {
                        annotations: {
                            zeroLine: {
                                type: 'line',
                                yMin: 0,
                                yMax: 0,
                                borderColor: 'rgba(255, 255, 255, 0.3)',
                                borderWidth: 1
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: { display: true, text: '到期日股價' },
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#94a3b8' }
                    },
                    y: {
                        title: { display: true, text: '利潤 / 虧損 ($)' },
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#94a3b8' }
                    }
                }
            }
        });
    }
};
