const ModulesStrategies = {
    render(data) {
        const calcs = data.calculations;
        const get = (key) => calcs[key] ? calcs[key] : null;

        // --- Module 6: Portfolio Hedging ---
        this.renderModule6(get('module6_portfolio_hedging'));

        // --- Module 7-10: Strategy Details (Side Panel) ---
        this.renderStrategiesSidePanel(get('module7_long_call_strategy'), get('module8_long_put_strategy'), get('module9_short_call_strategy'), get('module10_short_put_strategy'));

        // --- Module 11: Synthetic Stock ---
        this.renderModule11(get('module11_synthetic_stock'));

        // --- Module 12: Annual Yield ---
        this.renderModule12(get('module12_annualized_return'));
    },

    renderModule6(data) {
        const container = document.getElementById('module-6');
        if (!container) return;

        if (!data) {
            container.innerHTML = '<div class="glass-card p-4 rounded text-gray-500">無對沖計算數據</div>';
            return;
        }

        container.innerHTML = `
            <div class="glass-card p-5 rounded-xl h-full flex flex-col justify-between">
                <div>
                     <div class="flex justify-between items-center mb-4">
                        <h3 class="font-semibold text-gray-200">投資組合對沖 (Hedging)</h3>
                        <span class="text-xs bg-gray-800 px-2 py-1 rounded text-gray-400">M6</span>
                    </div>
                    <div class="space-y-3 text-sm">
                        <div class="flex justify-between items-center bg-gray-900/40 p-2 rounded">
                            <span class="text-gray-400">所需 PUT 合約</span>
                            <span class="font-mono text-cyan-300 font-bold">${data.put_options_needed} 張</span>
                        </div>
                        <div class="flex justify-between items-center bg-gray-900/40 p-2 rounded">
                            <span class="text-gray-400">總保護成本</span>
                            <span class="font-mono text-orange-300">$${data.cost_of_protection?.toFixed(2)}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    renderStrategiesSidePanel(m7, m8, m9, m10) {
        const container = document.getElementById('strategy-details');
        if (!container) return;

        const strats = { 'long_call': m7, 'long_put': m8, 'short_call': m9, 'short_put': m10 };

        // 存儲數據供圖表交互使用
        container.dataset.strategies = JSON.stringify(strats);

        // 預設渲染 Long Call
        this.updateStrategyDetails('long_call', m7);
    },

    updateStrategyDetails(type, data) {
        const container = document.getElementById('strategy-details');
        if (!data) {
            container.innerHTML = '<div class="text-gray-500">此策略無數據</div>';
            return;
        }

        const titles = {
            'long_call': '買入看漲 (Long Call)',
            'long_put': '買入看跌 (Long Put)',
            'short_call': '賣出看漲 (Short Call)',
            'short_put': '賣出看跌 (Short Put)'
        };

        const isProfitable = data.max_profit > 0 || data.max_profit === 'Unlimited';
        const maxProfitText = typeof data.max_profit === 'number' ? '$' + data.max_profit.toFixed(0) : (data.max_profit === 'Unlimited' ? '無限' : data.max_profit);
        const maxLossText = typeof data.max_loss === 'number' ? '$' + data.max_loss.toFixed(0) : (data.max_loss === 'Unlimited' ? '無限' : data.max_loss);

        container.innerHTML = `
            <div class="bg-gray-800/50 p-4 rounded-lg border border-gray-700 h-full flex flex-col justify-between">
                <div>
                    <h4 class="text-violet-300 font-bold mb-4 uppercase tracking-wider">${titles[type] || type}</h4>
                    
                    <div class="grid grid-cols-2 gap-4 mb-4">
                         <div>
                            <div class="text-xs text-gray-500">最大利潤</div>
                            <div class="font-mono text-emerald-400 font-bold">${maxProfitText}</div>
                        </div>
                        <div>
                            <div class="text-xs text-gray-500">最大損失</div>
                            <div class="font-mono text-red-400 font-bold">${maxLossText}</div>
                        </div>
                    </div>
                    
                     <div class="space-y-2 text-sm border-t border-gray-700 pt-3">
                        <div class="flex justify-between">
                            <span class="text-gray-400">盈虧平衡點</span>
                            <span class="text-white font-mono">$${data.break_even_point?.toFixed(2)}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-400">獲利機率 (Win Prob)</span>
                            <span class="text-white font-mono">${(data.probability_of_profit * 100).toFixed(1)}%</span>
                        </div>
                         <div class="flex justify-between">
                            <span class="text-gray-400">回報率 (ROI)</span>
                            <span class="${data.roi > 0 ? 'text-emerald-400' : 'text-red-400'} font-mono">${(data.roi * 100).toFixed(1)}%</span>
                        </div>
                    </div>
                </div>
                
                <div class="mt-4 pt-3 border-t border-gray-700">
                     <div class="text-xs text-gray-500 mb-1">AI 建議</div>
                     <div class="text-sm italic text-gray-300">"${data.description || '無具體建議'}"</div>
                </div>
            </div>
        `;
    },

    renderModule11(data) {
        const container = document.getElementById('module-11');
        if (!container) return;

        if (!data) {
            container.innerHTML = '<div class="glass-card p-4 rounded text-gray-500">無合成股票數據</div>';
            return;
        }

        const costDiff = data.stock_price - data.net_cost;

        container.innerHTML = `
            <div class="glass-card p-5 rounded-xl h-full flex flex-col justify-between">
                 <div>
                     <div class="flex justify-between items-center mb-4">
                        <h3 class="font-semibold text-gray-200">合成股票 (Synthetic)</h3>
                        <span class="text-xs bg-gray-800 px-2 py-1 rounded text-gray-400">M11</span>
                    </div>
                    <div class="grid grid-cols-2 gap-3 text-sm mb-3">
                        <div class="bg-gray-900/40 p-2 rounded">
                            <span class="block text-xs text-gray-500">淨成本</span>
                            <span class="font-bold text-white">$${data.net_cost?.toFixed(2)}</span>
                        </div>
                        <div class="bg-gray-900/40 p-2 rounded">
                            <span class="block text-xs text-gray-500">套戥差價</span>
                            <span class="font-bold ${costDiff > 0 ? 'text-emerald-400' : 'text-red-400'}">$${costDiff.toFixed(2)}</span>
                        </div>
                    </div>
                 </div>
                 <div class="text-xs text-gray-400 border-t border-gray-800/50 pt-2">
                    組合: Long Call + Short Put @ 相同行權價
                </div>
            </div>
        `;
    },

    renderModule12(data) {
        const container = document.getElementById('module-12');
        if (!container) return;

        if (!data) return;

        container.innerHTML = `
            <div class="glass-card p-5 rounded-xl h-full flex flex-col justify-between">
                 <div>
                     <div class="flex justify-between items-center mb-4">
                        <h3 class="font-semibold text-gray-200">年化收益率 (Yields)</h3>
                        <span class="text-xs bg-gray-800 px-2 py-1 rounded text-gray-400">M12</span>
                    </div>
                     <div class="space-y-3">
                        <div class="flex justify-between items-center border-b border-gray-800 pb-2">
                            <span class="text-gray-400 text-sm">Covered Call</span>
                            <span class="font-mono text-emerald-400 font-bold">${(data.covered_call_yield * 100).toFixed(1)}%</span>
                        </div>
                        <div class="flex justify-between items-center border-b border-gray-800 pb-2">
                            <span class="text-gray-400 text-sm">Cash Secured Put</span>
                            <span class="font-mono text-emerald-400 font-bold">${(data.cash_secured_put_yield * 100).toFixed(1)}%</span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="text-gray-400 text-sm">風險調整後回報</span>
                            <span class="font-mono text-blue-400 font-bold">${(data.risk_adjusted_return * 100).toFixed(1)}%</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
};
