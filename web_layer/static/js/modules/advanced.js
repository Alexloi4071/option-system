const ModulesAdvanced = {
    render(data) {
        const calcs = data.calculations;
        const get = (key) => calcs[key] ? calcs[key] : null;

        this.renderSimpleCard('module-20', '基本面健康度', 'M20', get('module20_fundamental_health'), (d) => `
            <div class="space-y-2 text-sm">
                <div class="flex justify-between"><span class="text-gray-400">總評分</span><span class="font-bold text-white">${d.overall_score}/10</span></div>
                <div class="flex justify-between"><span class="text-gray-400">盈利趨勢</span><span class="${d.earnings_trend === 'Growing' ? 'text-emerald-400' : 'text-orange-400'}">${d.earnings_trend}</span></div>
            </div>
        `);

        this.renderSimpleCard('module-21', '動量過濾器', 'M21', get('module21_momentum_filter'), (d) => `
             <div class="text-center py-2">
                <div class="${d.short_term_momentum === 'Positive' ? 'text-emerald-400' : 'text-red-400'} text-lg font-bold mb-1">${d.short_term_momentum === 'Positive' ? '正向動能' : '負向動能'}</div>
                <div class="text-xs text-gray-500">RSI 指標: ${d.rsi.toFixed(1)}</div>
            </div>
        `);

        this.renderSimpleCard('module-22', '最佳行使價 (Strike)', 'M22', get('module22_best_strike_price'), (d) => `
             <div class="flex justify-between items-center mb-2">
                <div class="text-xs text-gray-400">Call 行使價</div>
                <div class="font-mono text-emerald-300 font-bold">$${d.best_call_strike}</div>
            </div>
            <div class="flex justify-between items-center">
                <div class="text-xs text-gray-400">Put 行使價</div>
                <div class="font-mono text-red-300 font-bold">$${d.best_put_strike}</div>
            </div>
        `);

        // Module 23 handled by Gauge Chart mainly, but text updated here
        const m23 = get('module23_dynamic_iv_threshold');
        if (m23) {
            const regimeText = document.getElementById('iv-regime-text');
            if (regimeText) {
                regimeText.textContent = m23.iv_regime;
                regimeText.className = `font-bold text-lg ${m23.iv_regime === 'HIGH' ? 'text-red-400' : (m23.iv_regime === 'LOW' ? 'text-emerald-400' : 'text-yellow-400')}`;
            }
        }

        this.renderSimpleCard('module-24', '技術分析方向', 'M24', get('module24_technical_direction'), (d) => `
             <div class="grid grid-cols-2 gap-2 text-center text-xs">
                <div class="bg-gray-900/40 rounded p-1">
                    <div class="text-gray-500">日線</div>
                    <div class="font-bold ${d.daily_trend.includes('Bull') ? 'text-emerald-400' : 'text-red-400'}">${d.daily_trend}</div>
                </div>
                 <div class="bg-gray-900/40 rounded p-1">
                    <div class="text-gray-500">日內</div>
                    <div class="font-bold ${d.intraday_trend.includes('Bull') ? 'text-emerald-400' : 'text-red-400'}">${d.intraday_trend}</div>
                </div>
            </div>
             <div class="mt-2 text-xs text-center text-gray-400">關鍵位: $${d.key_level.toFixed(2)}</div>
        `);

        this.renderSimpleCard('module-26', 'Long 期權分析', 'M26', get('module26_long_option_analysis'), (d) => `
             <div class="flex justify-between items-center bg-gray-900/30 p-2 rounded mb-2">
                <span class="text-xs text-gray-400">凱利公式</span>
                <span class="font-mono text-white text-sm">${(d.kelley_criterion_pct * 100).toFixed(1)}%</span>
            </div>
             <div class="text-xs text-gray-500 text-center">
                預估槓桿: ${d.leverage_ratio.toFixed(1)}x
            </div>
        `);

        this.renderSimpleCard('module-27', '期限結構 (Term Structure)', 'M27', get('module27_multi_expiry_comparison'), (d) => `
             <div class="text-sm space-y-2">
                <div class="flex justify-between">
                    <span class="text-gray-400">下月 IV</span>
                    <span class="text-white mono">${d.next_month_iv?.toFixed(1)}%</span>
                </div>
                 <div class="flex justify-between">
                    <span class="text-gray-400">結構</span>
                    <span class="${d.term_structure_skew === 'Contango' ? 'text-emerald-400' : 'text-orange-400'} font-bold">${d.term_structure_skew}</span>
                </div>
            </div>
        `);

        this.renderSimpleCard('module-28', '資金倉位管理', 'M28', get('module28_capital_position_calculator'), (d) => `
             <div class="flex justify-between items-center mb-2">
                <span class="text-xs text-gray-400">保守</span>
                <span class="font-mono text-emerald-300 font-bold">${d.conservative_position_size}%</span>
            </div>
            <div class="flex justify-between items-center">
                <span class="text-xs text-gray-400">激進</span>
                <span class="font-mono text-orange-300 font-bold">${d.aggressive_position_size}%</span>
            </div>
        `);
    },

    renderSimpleCard(elementId, title, badge, data, contentFn) {
        const container = document.getElementById(elementId);
        if (!container) return;

        if (!data) {
            container.innerHTML = `<div class="glass-card p-4 rounded text-gray-500 text-xs">無 ${badge} 數據</div>`;
            return;
        }

        container.innerHTML = `
            <div class="glass-card p-4 rounded-xl h-full flex flex-col justify-between">
                 <div class="flex justify-between items-center mb-3 border-b border-gray-800 pb-2">
                    <h4 class="font-semibold text-gray-300 text-sm">${title}</h4>
                    <span class="text-[10px] bg-gray-800 px-1.5 py-0.5 rounded text-gray-400">${badge}</span>
                </div>
                <div>${contentFn(data)}</div>
            </div>
        `;
    }
};
