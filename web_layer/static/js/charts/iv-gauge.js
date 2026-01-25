const ChartIVGauge = {
    chart: null,

    render(data) {
        const ctx = document.getElementById('chart-iv-gauge');
        if (!ctx) return;

        // Destroy previous instance
        if (this.chart) {
            this.chart.destroy();
        }

        const m23 = data.calculations?.module23_dynamic_iv_threshold;
        if (!m23) return;

        const currentIV = data.raw_data.implied_volatility * 100;
        const lowThreshold = m23.low_threshold * 100;
        const highThreshold = m23.high_threshold * 100;

        // Determine color based on regime
        let color = '#facc15'; // Normal (Yellow)
        if (m23.iv_regime === 'LOW') color = '#10b981'; // Emerald
        if (m23.iv_regime === 'HIGH') color = '#ef4444'; // Red

        // Gauge Data (Needle approach simulation with doughnut)
        // We will show 3 segments: Low, Normal, High

        this.chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Low', 'Normal', 'High'],
                datasets: [{
                    data: [33, 33, 33], // Equal segments for background
                    backgroundColor: [
                        'rgba(16, 185, 129, 0.2)', // Low bg
                        'rgba(250, 204, 21, 0.2)', // Normal bg
                        'rgba(239, 68, 68, 0.2)'   // High bg
                    ],
                    borderColor: [
                        'rgba(16, 185, 129, 0.5)',
                        'rgba(250, 204, 21, 0.5)',
                        'rgba(239, 68, 68, 0.5)'
                    ],
                    borderWidth: 1,
                    needleValue: this.calculateNeedlePosition(currentIV, lowThreshold, highThreshold),
                    cutout: '70%',
                    circumference: 180,
                    rotation: 270,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                },
                layout: { padding: 20 },
                animation: {
                    animateRotate: true,
                    animateScale: true
                }
            },
            plugins: [{
                id: 'gaugeNeedle',
                afterDatasetDraw(chart, args, options) {
                    const { ctx, config, data, chartArea: { top, bottom, left, right, width, height } } = chart;

                    ctx.save();

                    const needleValue = data.datasets[0].needleValue;
                    const dataTotal = data.datasets[0].data.reduce((a, b) => a + b, 0);
                    const angle = Math.PI + (1 / dataTotal * needleValue * Math.PI);

                    const cx = width / 2;
                    const cy = chart._metasets[0].data[0].y;

                    // Draw Needle
                    ctx.translate(cx, cy);
                    ctx.rotate(angle);
                    ctx.beginPath();
                    ctx.moveTo(0, -2);
                    ctx.lineTo(height / 2 - 20, 0); // Length
                    ctx.lineTo(0, 2);
                    ctx.fillStyle = color; // Dynamic color
                    ctx.fill();

                    // Draw pivot
                    ctx.rotate(-angle);
                    ctx.beginPath();
                    ctx.arc(0, 0, 5, 0, Math.PI * 2);
                    ctx.fillStyle = '#fff';
                    ctx.fill();

                    ctx.restore();

                    // Draw Text Value in Center
                    ctx.font = 'bold 24px Inter';
                    ctx.fillStyle = '#fff';
                    ctx.textAlign = 'center';
                    // ctx.fillText(currentIV.toFixed(1) + '%', cx, cy - 10);
                    // Let index.html handle text outside canvas for better layout
                }
            }]
        });
    },

    calculateNeedlePosition(current, low, high) {
        // Map current IV to 0-100 scale where:
        // 0-33: Low
        // 33-66: Normal
        // 66-100: High

        // Simple linear mapping for visualization
        // Assume Low range is 0 to lowThreshold
        // Normal range is low to high
        // High range is high to high*1.5

        if (current <= low) {
            return (current / low) * 33;
        } else if (current <= high) {
            return 33 + ((current - low) / (high - low)) * 33;
        } else {
            return 66 + Math.min(33, ((current - high) / (high * 0.5)) * 33);
        }
    }
};
