const ModulesGreeks = {
    render(data) {
        const calcs = data.calculations;
        const get = (key) => calcs[key] ? calcs[key] : null;

        // --- Module 13: Position Analysis ---
        this.renderModule13(get('module13_position_analysis'));

        // --- Module 14: Monitoring ---
        this.renderModule14(get('module14_monitoring_post'));

        // --- Module 16 (and 15): Greeks & BS Model ---
        // Merging BS model data into Greeks display for efficiency
        this.renderModule16(get('module16_greeks_sensitivity'), get('module15_black_scholes_pricing'));

        // --- Module 18: Historical Volatility (Summary) ---
        // Detailed chart handled in separate file
    },

    renderModule13(data) {
        const container = document.getElementById('module-13');
        if (!container || !data) return;

        const sentimentScale = (data.put_call_ratio_oi < 0.7) ? '看漲 (Bullish)' : (data.put_call_ratio_oi > 1.0 ? '看跌 (Bearish)' : '中性 (Neutral)');
        const sentimentColor = data.put_call_ratio_oi < 0.7 ? 'text-emerald-400' : (data.put_call_ratio_oi > 1.0 ? 'text-red-400' : 'text-gray-400');

        container.innerHTML = `
            <div class="glass-card p-5 rounded-xl">
                 <div class="flex justify-between items-center mb-4">
                    <h3 class="font-semibold text-gray-200">市場倉位分析</h3>
                    <span class="text-xs bg-gray-800 px-2 py-1 rounded text-gray-400">M13</span>
                </div>
                <div class="grid grid-cols-2 gap-4 text-center">
                    <div>
                        <div class="text-xs text-gray-500">P/C Ratio (OI)</div>
                        <div class="font-mono text-xl text-white font-bold">${data.put_call_ratio_oi?.toFixed(2)}</div>
                    </div>
                    <div>
                        <div class="text-xs text-gray-500">情緒指標</div>
                        <div class="font-bold ${sentimentColor}">${sentimentScale}</div>
                    </div>
                </div>
                <div class="mt-4 pt-3 border-t border-gray-700">
                    <div class="flex justify-between text-xs mb-1">
                        <span class="text-gray-400">Call 總量</span>
                        <span class="text-emerald-300 font-mono">${data.call_volume_total?.toLocaleString()}</span>
                    </div>
                     <div class="flex justify-between text-xs">
                        <span class="text-gray-400">Put 總量</span>
                        <span class="text-red-300 font-mono">${data.put_volume_total?.toLocaleString()}</span>
                    </div>
                </div>
            </div>
        `;
    },

    renderModule14(data) {
        const container = document.getElementById('module-14');
        if (!container || !data) return;

        container.innerHTML = `
             <div class="glass-card p-5 rounded-xl">
                 <div class="flex justify-between items-center mb-4">
                    <h3 class="font-semibold text-gray-200">風險監察崗位</h3>
                    <span class="text-xs bg-gray-800 px-2 py-1 rounded text-gray-400">M14</span>
                </div>
                <div class="space-y-3">
                    <div class="flex justify-between items-center">
                        <span class="text-sm text-gray-400">ATR (14天)</span>
                        <span class="font-mono text-white">$${data.atr?.toFixed(2)}</span>
                    </div>
                     <div class="flex justify-between items-center">
                        <span class="text-sm text-gray-400">建議止損位</span>
                        <span class="font-mono text-red-300">$${data.suggested_stop_loss?.toFixed(2)}</span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-sm text-gray-400">建議止盈位</span>
                        <span class="font-mono text-emerald-300">$${data.suggested_take_profit?.toFixed(2)}</span>
                    </div>
                </div>
            </div>
        `;
    },

    renderModule16(greeks, bs) {
        const container = document.getElementById('module-16');
        if (!container || !greeks) return;

        // Format Greek value with color
        const fmtG = (val, type, isCall) => {
            if (val == null) return '-';
            let color = 'text-gray-300';

            // Basic color logic for Greeks
            if (type === 'Delta') color = isCall ? 'text-emerald-400' : 'text-red-400';
            if (type === 'Theta') color = 'text-red-400'; // Theta decay usually negative
            if (type === 'Gamma') color = 'text-blue-400';

            return `<span class="${color} font-mono font-bold">${val.toFixed(3)}</span>`;
        };

        container.innerHTML = `
            <div class="mb-4 flex items-center justify-between">
                <h3 class="font-semibold text-white">希臘字母 (Greeks)</h3>
                <div class="text-xs font-mono text-gray-500">ATM 敏感度</div>
            </div>
            
            <!-- Greeks Grid -->
            <div class="grid grid-cols-3 gap-2 text-sm">
                <!-- Header -->
                <div class="text-xs text-gray-500 font-bold uppercase pb-2 border-b border-gray-700">指標</div>
                <div class="text-xs text-center text-emerald-500 font-bold uppercase pb-2 border-b border-gray-700">Call</div>
                <div class="text-xs text-center text-red-500 font-bold uppercase pb-2 border-b border-gray-700">Put</div>
                
                <!-- Delta -->
                <div class="py-2 border-b border-gray-800 text-gray-400">Delta</div>
                <div class="py-2 border-b border-gray-800 text-right pr-4">${fmtG(greeks.call_delta, 'Delta', true)}</div>
                <div class="py-2 border-b border-gray-800 text-right pr-4">${fmtG(greeks.put_delta, 'Delta', false)}</div>
                
                 <!-- Gamma -->
                <div class="py-2 border-b border-gray-800 text-gray-400">Gamma</div>
                <div class="py-2 border-b border-gray-800 text-right pr-4">${fmtG(greeks.gamma, 'Gamma', true)}</div>
                <div class="py-2 border-b border-gray-800 text-right pr-4">${fmtG(greeks.gamma, 'Gamma', false)}</div>
                
                <!-- Theta -->
                <div class="py-2 border-b border-gray-800 text-gray-400">Theta</div>
                <div class="py-2 border-b border-gray-800 text-right pr-4">${fmtG(greeks.call_theta, 'Theta', true)}</div>
                <div class="py-2 border-b border-gray-800 text-right pr-4">${fmtG(greeks.put_theta, 'Theta', false)}</div>
                
                <!-- Vega -->
                <div class="py-2 text-gray-400">Vega</div>
                <div class="py-2 text-right pr-4">${fmtG(greeks.vega, 'Vega', true)}</div>
                <div class="py-2 text-right pr-4">${fmtG(greeks.vega, 'Vega', false)}</div>
            </div>
        `;

        // If BS data exists, append a small footer
        if (bs) {
            container.innerHTML += `
                <div class="mt-4 pt-3 border-t border-gray-700 text-center">
                    <span class="text-xs text-gray-500 mr-2">BS 理論價格:</span>
                    <span class="text-xs text-white font-mono">C $${bs.call_price.toFixed(2)} / P $${bs.put_price.toFixed(2)}</span>
                </div>
            `;
        }
    }
};
