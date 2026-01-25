const ModulesSignals = {
    render(data) {
        const calcs = data.calculations;
        const get = (key) => calcs[key] ? calcs[key] : null;

        // --- Module 30: Unusual Activity ---
        this.renderModule30(get('module30_unusual_activity'));
        
        // --- Module 31: Advanced Indicators ---
        // GEX/OI Chart handled separately, this renders summaries (Max Pain etc)
        this.renderModule31(get('module31_advanced_market_indicators'));
        
        // --- Module 32: Complex Strategies ---
        this.renderModule32(get('module32_complex_strategy_analysis'));
    },
    
    renderModule30(data) {
        const container = document.getElementById('module-30');
        if(!container) return;
        
        // If no signals, don't show empty box or show "None"
        const signals = data && data.signals ? data.signals : [];
        const count = signals.length;
        
        if (count === 0) {
             container.innerHTML = `
                <div class="glass-card p-4 rounded-xl h-full flex items-center justify-center text-gray-500 text-sm">
                    未偵測到異常異動
                </div>
            `;
            return;
        }

        let listHtml = signals.slice(0, 3).map(sig => `
            <div class="bg-gray-900/40 p-2 rounded mb-2 border-l-2 ${sig.type === 'CALL' ? 'border-emerald-500' : 'border-red-500'}">
                <div class="flex justify-between text-xs">
                    <span class="font-bold text-white">${sig.description}</span>
                    <span class="text-gray-400 font-mono">${sig.volume} Vol</span>
                </div>
            </div>
        `).join('');

        container.innerHTML = `
            <div class="glass-card p-4 rounded-xl h-full">
                 <div class="flex justify-between items-center mb-3">
                    <h4 class="font-semibold text-gray-200 text-sm">期權異動監控 (M30)</h4>
                    <span class="text-xs bg-red-500/20 text-red-300 px-2 py-0.5 rounded border border-red-500/30 animate-pulse">${count} 訊號</span>
                </div>
                <div class="overflow-y-auto max-h-[150px] custom-scrollbar">
                    ${listHtml}
                </div>
            </div>
        `;
    },
    
    renderModule31(data) {
        const container = document.getElementById('module-31');
        if(!container || !data) return;
        
        // Just inject the summary statistics into the chart card header area or overlay
        // For now, we'll append a stats row at the bottom of the container if it's the right one, 
        // OR if this function refers to a separate text container.
        
        // In index.html, module-31 is the chart card container. We can append data there or expect separate.
        // Let's assume we want to overlay max pain data.
        
        const existingCanvas = container.querySelector('canvas');
        if (existingCanvas) {
            // Check if we already appended stats
            if (!container.querySelector('.m31-stats')) {
                const statsDiv = document.createElement('div');
                statsDiv.className = 'm31-stats grid grid-cols-2 gap-4 mt-4 pt-4 border-t border-gray-800 text-sm';
                statsDiv.innerHTML = `
                    <div class="flex justify-between">
                        <span class="text-gray-400">Max Pain 痛點</span>
                        <span class="font-mono text-orange-400 font-bold">$${data.max_pain_price}</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-gray-400">Net GEX (伽瑪)</span>
                        <span class="font-mono ${data.net_gex > 0 ? 'text-emerald-400' : 'text-red-400'} font-bold">$${(data.net_gex / 1000000).toFixed(1)}M</span>
                    </div>
                `;
                container.appendChild(statsDiv);
            }
        }
    },
    
    renderModule32(data) {
         const container = document.getElementById('module-32');
         if(!container) return;
         
         if(!data || !data.recommended_strategies || data.recommended_strategies.length === 0) {
              container.innerHTML = `<div class="glass-card p-4 rounded text-gray-500 text-sm">無複雜策略推薦</div>`;
              return;
         }
         
         const topStrat = data.recommended_strategies[0];
         
         container.innerHTML = `
            <div class="glass-card p-4 rounded-xl h-full">
                 <div class="flex justify-between items-center mb-3">
                    <h4 class="font-semibold text-gray-200 text-sm">複雜策略分析</h4>
                    <span class="text-[10px] bg-violet-600 px-1.5 py-0.5 rounded text-white">M32</span>
                </div>
                <div class="bg-gray-900/50 p-3 rounded-lg border border-gray-700">
                    <div class="text-violet-300 font-bold text-sm mb-1">${topStrat.name}</div>
                    <div class="text-xs text-gray-400 mb-2">${topStrat.description}</div>
                    
                    <div class="flex justify-between text-xs border-t border-gray-700 pt-2">
                        <span class="text-gray-500">最大利潤:</span>
                        <span class="text-emerald-400">$${topStrat.max_profit}</span>
                    </div>
                     <div class="flex justify-between text-xs mt-1">
                        <span class="text-gray-500">最大風險:</span>
                        <span class="text-red-400">$${topStrat.max_risk}</span>
                    </div>
                </div>
            </div>
         `;
    }
};
