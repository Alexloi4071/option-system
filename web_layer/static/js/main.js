/**
 * Main Controller for Option Analysis System
 * Coordinates UI, Data Fetching, and Module Rendering
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log("OPTIQ System Initialized");
    const renderer = new ModuleRenderer();

    // UI Elements
    const form = document.getElementById('analysisForm');
    const loadingState = document.getElementById('loadingState');
    const resultsArea = document.getElementById('resultsArea');
    const errorAlert = document.getElementById('errorAlert');
    const analyzeBtn = form.querySelector('button[type="submit"]');

    // Ticker Blur Event - Fetch Expirations
    const tickerInput = document.getElementById('ticker');
    tickerInput.addEventListener('blur', async () => {
        const ticker = tickerInput.value.trim().toUpperCase();
        if (!ticker || ticker === 'MOCK' || ticker === 'TEST') return;

        const expirationSelect = document.getElementById('expiration');

        try {
            // Show loading state in dropdown
            expirationSelect.innerHTML = '<option>Loading expirations...</option>';
            expirationSelect.disabled = true;

            const response = await fetch(`/api/expirations?ticker=${ticker}`);
            const result = await response.json();

            if (result.status === 'success' && result.expirations.length > 0) {
                expirationSelect.innerHTML = '<option value="" selected>Auto-Select Smart Expiry</option>';
                result.expirations.forEach(date => {
                    const opt = document.createElement('option');
                    opt.value = date;
                    opt.textContent = date;
                    expirationSelect.appendChild(opt);
                });
                expirationSelect.disabled = false;
            } else {
                throw new Error("No expirations found");
            }
        } catch (e) {
            console.warn("Failed to fetch expirations:", e);
            expirationSelect.innerHTML = '<option value="">Auto-Select (Fetch Failed)</option>';
            expirationSelect.disabled = false;
        }
    });

    // Form Submit Handler
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Reset UI
        resultsArea.classList.add('d-none');
        loadingState.classList.remove('d-none');
        errorAlert.classList.add('d-none');
        analyzeBtn.disabled = true;

        const ticker = document.getElementById('ticker').value.toUpperCase();
        const expiration = document.getElementById('expiration').value;
        const useIbkr = document.getElementById('useIbkr').checked;

        // Advanced Settings
        const strike = document.getElementById('strike').value;
        const type = document.getElementById('type').value;
        const premium = document.getElementById('premium').value;
        const iv = document.getElementById('iv').value;
        const stockPrice = document.getElementById('stockPrice').value;
        const riskFreeRate = document.getElementById('riskFreeRate').value;

        // Mock Mode Check
        const isMock = ticker === 'MOCK' || ticker === 'DEMO' || ticker === 'TEST';
        const apiUrl = isMock ? '/api/analyze?mock=true' : '/api/analyze';

        try {
            // Simulated Progress (visual only)
            updateProgress(10, "Initializing...");

            const payload = {
                ticker: ticker,
                expiration: expiration || null,
                use_ibkr: useIbkr,
                // Advanced Overrides
                strike: strike ? parseFloat(strike) : null,
                type: type,
                premium: premium ? parseFloat(premium) : null,
                iv: iv ? parseFloat(iv) : null,
                stock_price: stockPrice ? parseFloat(stockPrice) : null,
                risk_free_rate: riskFreeRate ? parseFloat(riskFreeRate) : null,

                // Default settings
                confidence: 1.0,
                risk_level: 'moderate',
                total_capital: 100000
            };

            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            updateProgress(50, "Processing Options Chain...");

            if (result.status === 'error' || (result.success === false)) {
                throw new Error(result.message || result.error || "Analysis Failed");
            }

            // Render Results
            updateProgress(80, "Rendering Modules...");
            renderAll(result.data || result); // Handle wrapped or direct data

            // Finalize
            setTimeout(() => {
                loadingState.classList.add('d-none');
                resultsArea.classList.remove('d-none');
                analyzeBtn.disabled = false;
            }, 500);

        } catch (err) {
            console.error(err);
            loadingState.classList.add('d-none');
            errorAlert.classList.remove('d-none');
            document.getElementById('errorMessage').textContent = err.message;
            analyzeBtn.disabled = false;
        }
    });

    // Helper: Update Progress Bar
    function updateProgress(percent, msg) {
        const bar = document.getElementById('progressBar');
        const txt = document.getElementById('progressMessage');
        if (bar) bar.style.width = percent + '%';
        if (txt) txt.textContent = msg;
    }

    // Helper: Render All Modules
    function renderAll(data) {
        const raw = data.raw_data || {};
        const calcs = data.calculations || {};

        // 1. Header Stats
        document.getElementById('currentPrice').innerHTML = `$${Number(raw.current_price).toFixed(2)}`;
        document.getElementById('impliedVolatility').innerHTML = `${Number(raw.implied_volatility).toFixed(2)}%`;
        document.getElementById('analysisDate').textContent = raw.analysis_date;

        // Health Score (Module 20)
        const health = calcs.module20_fundamental_health;
        const healthEl = document.getElementById('healthScore');
        if (health && health.health_score) {
            healthEl.innerHTML = `${health.health_score} <span class="badge bg-dark border border-secondary text-muted small">${health.grade}</span>`;
            if (health.health_score > 70) healthEl.className = "stat-value text-neon-green";
            else if (health.health_score < 40) healthEl.className = "stat-value text-neon-red";
            else healthEl.className = "stat-value text-neon-warning";
        }

        // 2. Modules
        // We select containers using our new IDs from index.html

        // Module 1: Support/Resistance (Table)
        // We changed renderModule1 to accept a container. In index.html, we have a table with id 'srTable'
        // The renderer expects a container to write tbody into.
        const srTable = document.getElementById('srTable');
        if (calcs.module1_support_resistance_multi) {
            // New Multi-mode
            renderer.renderModule1(calcs.module1_support_resistance_multi, srTable);

            // Also update the big display numbers if available
            const srMulti = calcs.module1_support_resistance_multi.results;
            if (srMulti && srMulti['90%']) { // Default to 90%
                document.getElementById('supportLevel').textContent = '$' + Number(srMulti['90%'].support).toFixed(2);
                document.getElementById('resistanceLevel').textContent = '$' + Number(srMulti['90%'].resistance).toFixed(2);
            }
        } else if (calcs.module1_support_resistance) {
            // Legacy Single Mode - Adapter might be needed or renderer handles it?
            // renderModule1 supports 'results' object. Single mode returns similar but simple.
            // Let's rely on Mock Data structure which is 'multi'.
            // If single, manually populate:
            document.getElementById('supportLevel').textContent = '$' + Number(calcs.module1_support_resistance.support_level).toFixed(2);
            document.getElementById('resistanceLevel').textContent = '$' + Number(calcs.module1_support_resistance.resistance_level).toFixed(2);
        }

        // Module 15/16: Greeks
        // ID: callGreeks, putGreeks (Handled in renderer if we pass specific elements, or here)
        // Note: New renderer renderModule15_16 logic was specific.
        // Let's call it manually for clarity
        const greeksDiv = document.getElementById('resultsArea'); // Just a dummy, we call internal renderers
        // Actually, let's look at my renderer code. It expects (bs, greeks, container).
        // And checks if container is HTMLElement.
        // It tries to find #callGreeks inside container or uses container.
        // So passing document.body or resultsArea is safe.
        renderer.renderModule15_16(
            calcs.module15_black_scholes || calcs.module15_16_black_scholes_greeks?.bs_data, // Handle both structures
            calcs.module16_greeks || calcs.module15_16_black_scholes_greeks?.greeks_data,
            document.getElementById('resultsArea')
        );

        // Module 2: Fair Value
        renderer.renderModule2(calcs.module2_fair_value, document.getElementById('fairValueList'));

        // Module 4: PE
        renderer.renderModule4(calcs.module4_pe_valuation, document.getElementById('peValuation'));

        // Module 7-10: PnL
        renderer.renderStrategyPnL(
            calcs.module7_long_call?.scenarios, // Ensure we pass the array
            calcs.module8_long_put?.scenarios,
            calcs.module9_short_call?.scenarios,
            calcs.module10_short_put?.scenarios,
            document.getElementById('strategyPnLTable')
        );

        // Strategy Recommendations
        // Mock data might not have it, handles gracefully
    }

});
