const ModulesCore = {
    render(data) {
        const calcs = data.calculations;

        // Helper: safe get
        const get = (path) => path ? path : null;

        // --- Module 1: Support/Resistance Stats ---
        this.renderModule1(get(calcs?.module1_support_resistance_multi));

        // --- Module 2: Fair Value ---
        this.renderModule2(get(calcs?.module2_fair_value));

        // --- Module 3: Arbitrage ---
        this.renderModule3(get(calcs?.module3_arbitrage_spread));

        // --- Module 4 & 5: PE Valuation ---
        this.renderModule45(get(calcs?.module4_pe_valuation));
    },

    renderModule1(m1) {
        const container = document.getElementById('module-1-stats');
        if (!m1 || !container) return;

        // 新的數據結構處理
        const conf90 = m1.results?.['90%'];
        const currentPrice = m1.stock_price;

        let html = `
            <div class="bg-gray-900/50 p-3 rounded-lg border border-gray-700">
                <div class="text-xs text-gray-500 uppercase">當前股價</div>
                <div class="font-bold text-lg text-white">$${currentPrice ? currentPrice.toFixed(2) : 'N/A'}</div>
            </div>
        `;

        if (conf90) {
            html += `
                <div class="bg-gray-900/50 p-3 rounded-lg border border-gray-700">
                    <div class="text-xs text-gray-500 uppercase">90% 阻力位</div>
                    <div class="font-bold text-lg text-orange-400">$${conf90.resistance ? conf90.resistance.toFixed(2) : 'N/A'}</div>
                </div>
                <div class="bg-gray-900/50 p-3 rounded-lg border border-gray-700">
                    <div class="text-xs text-gray-500 uppercase">90% 支持位</div>
                    <div class="font-bold text-lg text-blue-400">$${conf90.support ? conf90.support.toFixed(2) : 'N/A'}</div>
                </div>
            `;
        }

        container.innerHTML = html;
    },

    renderModule2(m2) {
        const container = document.getElementById('module-2');
        if (!container) return;

        if (!m2) {
            container.innerHTML = '<div class="text-gray-500 text-sm">無公允價值數據</div>';
            return;
        }

        // 轉換新的數據結構
        const fairValue = m2.forward_price || m2.theoretical_price;
        const marketPrice = m2.spot_price || m2.stock_price;
        
        if (!fairValue || !marketPrice) {
            container.innerHTML = '<div class="text-gray-500 text-sm">公允價值數據不完整</div>';
            return;
        }

        const gap = marketPrice - fairValue;
        const gapColor = gap > 0 ? 'text-red-400' : 'text-emerald-400';
        const gapText = gap > 0 ? '高估 (Overvalued)' : '低估 (Undervalued)';

        container.innerHTML = `
            <div class="h-full flex flex-col justify-between">
                <div>
                     <div class="flex justify-between mb-4">
                        <h4 class="font-semibold text-gray-200">公允價值模型</h4>
                        <span class="text-xs bg-gray-800 px-2 py-1 rounded text-gray-400">M2</span>
                    </div>
                    <div class="flex justify-between items-end mb-4">
                        <div>
                            <div class="text-xs text-gray-500">合理價格</div>
                            <div class="text-2xl font-bold text-white">$${fairValue.toFixed(2)}</div>
                        </div>
                        <div class="text-right">
                            <div class="text-xs text-gray-500">市場價格</div>
                            <div class="font-mono text-gray-300">$${marketPrice.toFixed(2)}</div>
                        </div>
                    </div>
                </div>
                <div class="p-3 bg-gray-900/50 rounded-lg border border-gray-700 flex justify-between items-center">
                    <span class="text-sm text-gray-400">狀態</span>
                    <span class="font-bold ${gapColor}">${gapText}</span>
                </div>
            </div>
        `;
    },

    renderModule3(m3) {
        const container = document.getElementById('module-3');
        if (!container) return;

        if (!m3) {
            container.innerHTML = '<div class="text-gray-500 text-sm">無套戥數據</div>';
            return;
        }

        // 轉換新的數據結構
        const callSpread = m3.call_parity_deviation || m3.call_spread || 0;
        const putSpread = m3.put_parity_deviation || m3.put_spread || 0;
        const threshold = m3.deviation_threshold || 0.01;

        container.innerHTML = `
             <div class="h-full flex flex-col justify-between">
                <div>
                    <div class="flex justify-between mb-4">
                        <h4 class="font-semibold text-gray-200">期權套戥偏離 (Arbitrage)</h4>
                        <span class="text-xs bg-gray-800 px-2 py-1 rounded text-gray-400">M3</span>
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div class="bg-gray-900/30 p-2 rounded text-center">
                            <div class="text-xs text-gray-500">Call Spread</div>
                            <div class="font-mono font-bold text-lg text-emerald-400">${(callSpread * 100).toFixed(2)}%</div>
                        </div>
                        <div class="bg-gray-900/30 p-2 rounded text-center">
                            <div class="text-xs text-gray-500">Put Spread</div>
                            <div class="font-mono font-bold text-lg text-emerald-400">${(putSpread * 100).toFixed(2)}%</div>
                        </div>
                    </div>
                </div>
                <div class="mt-3 text-xs text-gray-400 text-center border-t border-gray-800/50 pt-2">
                    偏離閾值: ${(threshold * 100).toFixed(1)}%
                </div>
            </div>
        `;
    },

    renderModule45(m4) {
        const container = document.getElementById('module-4');
        if (!container) return;

        if (!m4) {
            container.innerHTML = '<div class="text-gray-500 text-sm">無 PE 分析數據</div>';
            return;
        }

        // 轉換新的數據結構
        const currentPE = m4.forward_pe || m4.pe_ratio || m4.current_pe;
        const industryPE = m4.industry_pe_range ? 
            (typeof m4.industry_pe_range === 'string' ? m4.industry_pe_range : 'N/A') : 
            m4.industry_average_pe;
        
        let valuation = m4.peg_valuation || m4.valuation_status || 'N/A';
        
        // 翻譯估值狀態
        let statusText = valuation;
        if (valuation === 'Undervalued') statusText = '低估';
        else if (valuation === 'Overvalued') statusText = '高估';
        else if (valuation === 'Fair Value' || valuation === '合理') statusText = '合理';

        const isUndervalued = valuation.includes('低估') || valuation.includes('Undervalued');

        container.innerHTML = `
            <div class="h-full flex flex-col">
                <div class="flex justify-between mb-4">
                    <h4 class="font-semibold text-gray-200">PE 估值分析</h4>
                    <span class="text-xs bg-gray-800 px-2 py-1 rounded text-gray-400">M4-5</span>
                </div>
                <div class="space-y-3 font-mono text-sm flex-1">
                    <div class="flex justify-between border-b border-gray-800 pb-2">
                        <span class="text-gray-500">當前 PE</span>
                        <span class="text-white">${currentPE ? currentPE.toFixed(2) : 'N/A'}</span>
                    </div>
                    <div class="flex justify-between border-b border-gray-800 pb-2">
                        <span class="text-gray-500">行業範圍</span>
                        <span class="text-gray-300">${industryPE || 'N/A'}</span>
                    </div>
                    <div class="flex justify-between pt-1">
                        <span class="text-gray-500">評估結果</span>
                        <span class="${isUndervalued ? 'text-emerald-400' : 'text-orange-400'} font-bold">
                            ${statusText}
                        </span>
                    </div>
                </div>
            </div>
        `;
    }
};
