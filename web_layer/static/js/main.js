// web_layer/static/js/main.js

// ============================================================================
// MODERN UI INITIALIZATION
// ============================================================================

// Initialize all modern UI components when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('[Main] Initializing modern UI components...');
    
    // Initialize theme manager (already loaded)
    if (window.themeManager) {
        console.log('[Main] Theme Manager ready:', themeManager.getCurrentTheme());
    }
    
    // Initialize animation controller (already loaded)
    if (window.animationController) {
        console.log('[Main] Animation Controller ready. Reduced motion:', animationController.reducedMotion);
        
        // Apply staggered animations to initial cards
        const initialCards = document.querySelectorAll('.card');
        if (initialCards.length > 0) {
            animationController.applyStaggeredAnimation(initialCards);
        }
    }
    
    // Initialize module error handler (already loaded)
    if (window.ModuleErrorHandler) {
        console.log('[Main] Module Error Handler ready');
    }
    
    // Initialize CSS fallback handler (already loaded)
    if (window.CSSFallbackHandler) {
        console.log('[Main] CSS Fallback Handler ready');
    }
    
    // Initialize performance monitor if available
    if (window.PerformanceMonitor) {
        console.log('[Main] Performance Monitor ready');
        PerformanceMonitor.startMonitoring();
    }
    
    // Initialize lazy loader if available
    if (window.LazyLoader) {
        console.log('[Main] Lazy Loader ready');
        LazyLoader.init();
    }
    
    // Initialize virtual scroller if available
    if (window.VirtualScroller) {
        console.log('[Main] Virtual Scroller ready');
    }
    
    // Apply hover effects to interactive elements
    applyHoverEffects();
    
    // Apply button click feedback
    applyButtonFeedback();
    
    // Initialize accessibility manager (auto-initialized in accessibility-manager.js)
    if (window.accessibilityManager) {
        console.log('[Main] Accessibility Manager ready (includes keyboard shortcuts)');
    }
    
    console.log('[Main] Modern UI initialization complete');
    
    // Continue with existing initialization
    initializeAnalysisForm();
});

/**
 * Apply hover effects to interactive elements
 */
function applyHoverEffects() {
    if (!window.animationController) return;
    
    // Apply hover effects to cards
    document.querySelectorAll('.card').forEach(card => {
        animationController.applyHoverEffect(card, 'lift');
    });
    
    // Apply hover effects to buttons
    document.querySelectorAll('.btn').forEach(button => {
        animationController.applyHoverTransition(button, 'all');
    });
    
    // Apply hover effects to table rows
    document.querySelectorAll('table tbody tr').forEach(row => {
        animationController.applyHoverTransition(row, 'background-color');
    });
}

/**
 * Apply button click feedback to all buttons
 */
function applyButtonFeedback() {
    if (!window.animationController) return;
    
    document.querySelectorAll('button, .btn').forEach(button => {
        button.addEventListener('click', function(e) {
            // Don't apply feedback if button is disabled
            if (this.disabled) return;
            
            // Apply ripple effect for primary buttons
            if (this.classList.contains('btn-primary')) {
                animationController.applyButtonFeedback(this, 'ripple');
            } else {
                animationController.applyButtonFeedback(this, 'scale');
            }
        });
    });
}

/**
 * US-5: Validate ticker input
 * Task 4.1.1: Create validateTicker function
 * 
 * @param {string} ticker - The ticker symbol to validate
 * @returns {Object} - Validation result with isValid, ticker, and errors
 */
function validateTicker(ticker) {
    const validation = {
        isValid: false,
        ticker: ticker.toUpperCase(),
        errors: []
    };
    
    // Task 4.1.2: Check length (1-5 characters)
    if (ticker.length === 0) {
        validation.errors.push('股票代碼不能為空');
        return validation;
    }
    
    if (ticker.length > 5) {
        validation.errors.push('股票代碼不能超過5個字符');
        return validation;
    }
    
    // Task 4.1.3: Check characters (only letters, numbers, dots, hyphens)
    const validPattern = /^[A-Z0-9.-]+$/;
    if (!validPattern.test(validation.ticker)) {
        validation.errors.push('股票代碼只能包含字母、數字、點(.)和連字符(-)');
        return validation;
    }
    
    validation.isValid = true;
    return validation;
}

/**
 * Initialize analysis form and related functionality
 */
function initializeAnalysisForm() {
    const form = document.getElementById('analysisForm');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const loadingState = document.getElementById('loadingState');
    const resultsArea = document.getElementById('resultsArea');
    // US-2: 更新錯誤提示元素 ID
    const errorAlert = document.getElementById('error-alert');
    const errorMessage = document.getElementById('error-message');
    const errorDetails = document.getElementById('error-details');
    
    // Expiration Date Logic
    const tickerInput = document.getElementById('ticker');
    const expirationSelect = document.getElementById('expiration');
    const refreshDatesBtn = document.getElementById('refreshDatesBtn');
    const expirationStatus = document.getElementById('expirationStatus');
    
    // Multi-expiry elements
    const multiExpirySection = document.getElementById('multiExpirySection');
    const expirationCheckboxes = document.getElementById('expirationCheckboxes');
    const selectedExpCount = document.getElementById('selectedExpCount');
    const selectAllExp = document.getElementById('selectAllExp');
    const clearAllExp = document.getElementById('clearAllExp');
    
    let availableExpirations = []; // 存儲所有可用到期日

    // US-5 Task 4.1.5: Add real-time validation event listener
    tickerInput.addEventListener('input', function() {
        const ticker = this.value;
        const validation = validateTicker(ticker);
        
        // Task 4.1.4: Auto-convert to uppercase
        this.value = validation.ticker;
        
        // Display validation errors
        const tickerError = document.getElementById('ticker-error');
        if (!validation.isValid && ticker.length > 0) {
            tickerError.textContent = validation.errors.join(', ');
            tickerError.style.display = 'block';
            analyzeBtn.disabled = true;
        } else {
            tickerError.style.display = 'none';
            analyzeBtn.disabled = false;
        }
        
        // Continue with existing debounced fetch
        debouncedFetchExpirations(validation.ticker);
    });

    // Auto-fetch dates when ticker changes (debounced for performance)
    // Validates: Requirements 13.4
    const debouncedFetchExpirations = debounce(function(ticker) {
        if (ticker && ticker.length >= 1) {
            fetchExpirations(ticker);
        }
    }, 800);

    refreshDatesBtn.addEventListener('click', function() {
        const ticker = tickerInput.value.trim();
        if (ticker) {
            fetchExpirations(ticker);
        } else {
            expirationStatus.textContent = '請輸入股票代碼';
            expirationStatus.className = 'form-text text-danger';
        }
    });

    async function fetchExpirations(ticker) {
        expirationStatus.textContent = '正在獲取到期日...';
        expirationStatus.className = 'form-text text-info';
        refreshDatesBtn.disabled = true;
        
        try {
            const response = await fetch(`/api/expirations?ticker=${ticker}`);
            const data = await response.json();
            
            if (data.status === 'success' && data.expirations) {
                availableExpirations = data.expirations;
                
                // Clear existing options except the first one
                while (expirationSelect.options.length > 1) {
                    expirationSelect.remove(1);
                }
                
                data.expirations.forEach(date => {
                    const option = document.createElement('option');
                    option.value = date;
                    option.textContent = date;
                    expirationSelect.appendChild(option);
                });
                
                // 更新多選到期日區域
                updateMultiExpiryCheckboxes(data.expirations);
                multiExpirySection.style.display = 'block';
                
                expirationStatus.textContent = `已獲取 ${data.expirations.length} 個到期日`;
                expirationStatus.className = 'form-text text-success';
            } else {
                throw new Error(data.message || '無法獲取');
            }
        } catch (error) {
            console.error('Fetch expirations error:', error);
            expirationStatus.textContent = '無法獲取到期日 (可能代碼錯誤)';
            expirationStatus.className = 'form-text text-warning';
            multiExpirySection.style.display = 'none';
        } finally {
            refreshDatesBtn.disabled = false;
        }
    }
    
    // 更新多選到期日 checkboxes
    function updateMultiExpiryCheckboxes(expirations) {
        expirationCheckboxes.innerHTML = '';
        
        // 計算每個到期日距今天數
        const today = new Date();
        
        expirations.forEach((date, index) => {
            const expDate = new Date(date);
            const daysDiff = Math.ceil((expDate - today) / (1000 * 60 * 60 * 24));
            
            // 只顯示 90 天內的到期日（與 Module 27 邏輯一致）
            if (daysDiff > 0 && daysDiff <= 90) {
                const div = document.createElement('div');
                div.className = 'form-check form-check-inline';
                div.innerHTML = `
                    <input class="form-check-input exp-checkbox" type="checkbox" value="${date}" id="exp_${index}" ${index < 5 ? 'checked' : ''}>
                    <label class="form-check-label small" for="exp_${index}">
                        ${date} <span class="text-muted">(${daysDiff}天)</span>
                    </label>
                `;
                expirationCheckboxes.appendChild(div);
            }
        });
        
        updateSelectedCount();
    }
    
    // 更新已選數量
    function updateSelectedCount() {
        const checked = document.querySelectorAll('.exp-checkbox:checked').length;
        selectedExpCount.textContent = checked;
    }
    
    // 監聽 checkbox 變化
    expirationCheckboxes.addEventListener('change', updateSelectedCount);
    
    // 全選
    selectAllExp.addEventListener('click', function(e) {
        e.preventDefault();
        document.querySelectorAll('.exp-checkbox').forEach(cb => cb.checked = true);
        updateSelectedCount();
    });
    
    // 清除
    clearAllExp.addEventListener('click', function(e) {
        e.preventDefault();
        document.querySelectorAll('.exp-checkbox').forEach(cb => cb.checked = false);
        updateSelectedCount();
    });
    
    // 獲取選中的到期日
    function getSelectedExpirations() {
        const selected = [];
        document.querySelectorAll('.exp-checkbox:checked').forEach(cb => {
            selected.push(cb.value);
        });
        return selected;
    }

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // 獲取選中的多個到期日
        const selectedExpirations = getSelectedExpirations();

        // 1. 獲取表單數據
        const formData = {
            ticker: document.getElementById('ticker').value,
            expiration: document.getElementById('expiration').value || null,
            selected_expirations: selectedExpirations.length > 0 ? selectedExpirations : null,
            confidence: document.getElementById('confidence').value,
            use_ibkr: document.getElementById('useIbkr').checked,
            strike: document.getElementById('strike').value || null,
            premium: document.getElementById('premium').value || null,
            type: document.getElementById('optionType').value || null,
            total_capital: document.getElementById('totalCapital').value || 130000,
            currency: document.getElementById('currency').value || 'HKD',
            risk_level: document.getElementById('riskLevel').value || 'moderate',
            strategy_preference: document.getElementById('strategyPreference').value || 'long'
        };

        // 2. UI 狀態更新
        analyzeBtn.disabled = true;
        loadingState.classList.remove('d-none');
        resultsArea.classList.add('d-none');
        errorAlert.classList.add('d-none');

        try {
            // 3. 發送 API 請求
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            // US-2: 檢查後端返回的 success 標識
            if (data.success === false) {
                // 創建包含詳細錯誤信息的錯誤對象
                const error = new Error(data.error || '分析失敗');
                error.response = data;
                throw error;
            }

            if (!response.ok) {
                const error = new Error(data.message || '分析請求失敗');
                error.response = data;
                throw error;
            }

            // 4. 渲染數據
            renderResults(data);
            resultsArea.classList.remove('d-none');

        } catch (error) {
            console.error('Error:', error);
            
            // US-2: 增強錯誤處理 - 顯示友好的錯誤消息
            let errorMsg = error.message || '分析請求失敗';
            let detailsMsg = '';
            
            // 如果錯誤響應包含詳細信息
            if (error.response) {
                const errorData = error.response;
                
                // 根據錯誤類型顯示不同的消息
                if (errorData.error_type === 'no_data') {
                    errorMsg = `無法獲取 ${errorData.ticker} 的數據，請檢查股票代碼是否正確`;
                } else if (errorData.error_type === 'missing_price') {
                    errorMsg = `無法獲取 ${errorData.ticker} 的當前股價`;
                } else if (errorData.error_type === 'no_option_chain') {
                    errorMsg = `無法獲取 ${errorData.ticker} 的期權鏈數據`;
                    if (errorData.available_expirations && errorData.available_expirations.length > 0) {
                        detailsMsg = `可用的到期日: ${errorData.available_expirations.join(', ')}`;
                    }
                } else if (errorData.error_type === 'empty_options') {
                    errorMsg = `${errorData.ticker} 的期權數據為空（Call 和 Put 都無數據）`;
                    if (errorData.expiration) {
                        detailsMsg = `到期日: ${errorData.expiration}`;
                    }
                } else if (errorData.error) {
                    errorMsg = errorData.error;
                }
            }
            
            errorMessage.textContent = errorMsg;
            
            // 顯示詳細信息（如果有）
            if (detailsMsg && errorDetails) {
                errorDetails.textContent = detailsMsg;
                errorDetails.style.display = 'block';
            } else if (errorDetails) {
                errorDetails.style.display = 'none';
            }
            
            errorAlert.classList.remove('d-none');
        } finally {
            analyzeBtn.disabled = false;
            loadingState.classList.add('d-none');
        }
    });

    function renderResults(data) {
        const rawData = data.raw_data;
        const calcs = data.calculations;

        // --- 1. 核心概覽 ---
        document.getElementById('analysisDate').textContent = rawData.analysis_date;
        document.getElementById('currentPrice').textContent = `$${rawData.current_price.toFixed(2)}`;
        document.getElementById('impliedVolatility').textContent = `${rawData.implied_volatility.toFixed(2)}%`;
        
        // 支持/阻力位 (Module 1)
        const sr = calcs.module1_support_resistance;
        if (sr) {
            document.getElementById('supportLevel').textContent = `$${sr.support_level.toFixed(2)}`;
            document.getElementById('resistanceLevel').textContent = `$${sr.resistance_level.toFixed(2)}`;
        }

        // 健康評分 (Module 20)
        const health = calcs.module20_fundamental_health;
        if (health && health.status !== 'skipped') {
            document.getElementById('healthScore').textContent = health.health_score;
            document.getElementById('healthGrade').textContent = health.grade;
            
            // 顏色編碼
            const scoreEl = document.getElementById('healthScore');
            if (health.health_score >= 80) scoreEl.className = 'text-success fw-bold';
            else if (health.health_score >= 60) scoreEl.className = 'text-warning fw-bold';
            else scoreEl.className = 'text-danger fw-bold';
        } else {
            document.getElementById('healthScore').textContent = 'N/A';
            document.getElementById('healthGrade').textContent = '-';
        }

        // --- 2. 支持/阻力位表格 (Module 1 Multi) ---
        const srMulti = calcs.module1_support_resistance_multi;
        const srTableBody = document.querySelector('#srTable tbody');
        srTableBody.innerHTML = '';
        
        if (srMulti && srMulti.results) {
            Object.entries(srMulti.results).forEach(([conf, res]) => {
                const row = `
                    <tr>
                        <td>${conf}</td>
                        <td>${res.z_score}</td>
                        <td>$${res.price_move.toFixed(2)} (±${res.move_percentage}%)</td>
                        <td class="text-success fw-bold">$${res.support.toFixed(2)}</td>
                        <td class="text-danger fw-bold">$${res.resistance.toFixed(2)}</td>
                    </tr>
                `;
                srTableBody.innerHTML += row;
            });
        }

        // --- 3. 公允值 (Module 2) ---
        const fv = calcs.module2_fair_value;
        const fvList = document.getElementById('fairValueList');
        fvList.innerHTML = '';
        if (fv) {
            fvList.innerHTML = `
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    公允值 (Fair Value)
                    <span class="fw-bold">$${fv.fair_value.toFixed(2)}</span>
                </li>
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    無風險利率
                    <span>${(fv.risk_free_rate * 100).toFixed(2)}%</span>
                </li>
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    預期股息
                    <span>$${fv.expected_dividend.toFixed(2)}</span>
                </li>
            `;
        }

        // --- 4. 套戥水位 (Module 3) ---
        const arb = calcs.module3_arbitrage_spread;
        const arbContent = document.getElementById('arbitrageContent');
        if (arb && arb.status !== 'skipped' && arb.status !== 'error') {
            const isArb = arb.arbitrage_spread > 0;
            arbContent.innerHTML = `
                <div class="text-center mb-3">
                    <h3 class="${isArb ? 'text-success' : 'text-muted'}">${arb.arbitrage_spread.toFixed(2)}</h3>
                    <small class="text-muted">價差 (${arb.spread_percentage.toFixed(2)}%)</small>
                </div>
                <p class="mb-1"><strong>建議:</strong> ${arb.recommendation}</p>
                <p class="mb-0 small text-muted">理論價: $${arb.theoretical_price.toFixed(2)} vs 市場價: $${arb.market_price.toFixed(2)}</p>
                ${arb.note ? `<p class="mb-0 small text-info fst-italic">${arb.note}</p>` : ''}
            `;
        } else {
            arbContent.innerHTML = `<div class="alert alert-secondary mb-0">暫無套戥機會或數據不足</div>`;
        }

        // --- 5. Greeks (Module 15 & 16) ---
        const greeks = calcs.module16_greeks;
        const bs = calcs.module15_black_scholes;
        
        if (greeks) {
            document.getElementById('greeksSource').textContent = greeks.data_source || 'Unknown';
            
            // 獲取行使價信息
            let strikePrice = 'N/A';
            let strikeNote = '';
            
            // 優先使用 strike_selection 信息
            if (calcs.strike_selection) {
                strikePrice = calcs.strike_selection.strike_price;
                strikeNote = calcs.strike_selection.moneyness || '';
            } else if (bs && bs.parameters && bs.parameters.strike_price) {
                strikePrice = bs.parameters.strike_price;
            } else if (bs && bs.call && bs.call.strike_price) {
                strikePrice = bs.call.strike_price;
            }

            // 更新標題顯示行使價
            const greeksCardHeader = document.querySelector('#greeksCard .card-header');
            if (greeksCardHeader) {
                // 查找或創建標題元素
                let titleEl = greeksCardHeader.querySelector('h6');
                if (!titleEl) {
                    titleEl = document.createElement('h6');
                    titleEl.className = 'mb-0 fw-bold text-primary';
                    greeksCardHeader.prepend(titleEl);
                }
                
                titleEl.innerHTML = `
                    15 & 16. 期權定價與 Greeks
                    <span class="badge bg-warning text-dark ms-2">Strike: $${strikePrice}</span>
                    <span class="badge bg-info text-dark ms-1">現價: $${rawData.current_price.toFixed(2)}</span>
                    <small class="text-muted ms-2" style="font-size: 0.8em;">(${strikeNote || '自動選擇'})</small>
                `;
            }
            
            const renderGreeks = (type, data, priceData) => {
                if (!data) return '<p class="text-muted text-center">無數據</p>';
                const price = priceData ? priceData.option_price : 0;
                return `
                    <div class="text-center mb-2">
                        <span class="badge bg-light text-dark border">理論價: $${price.toFixed(2)}</span>
                    </div>
                    <div class="d-flex justify-content-between mb-1"><span class="text-muted">Delta</span> <span>${data.delta.toFixed(4)}</span></div>
                    <div class="d-flex justify-content-between mb-1"><span class="text-muted">Gamma</span> <span>${data.gamma.toFixed(4)}</span></div>
                    <div class="d-flex justify-content-between mb-1"><span class="text-muted">Theta</span> <span>${data.theta.toFixed(4)}</span></div>
                    <div class="d-flex justify-content-between mb-1"><span class="text-muted">Vega</span> <span>${data.vega.toFixed(4)}</span></div>
                    <div class="d-flex justify-content-between"><span class="text-muted">Rho</span> <span>${data.rho.toFixed(4)}</span></div>
                `;
            };

            // US-4: Mobile card view rendering for Greeks
            const renderGreeksCards = (type, data, priceData) => {
                if (!data) return '<p class="text-muted text-center">無數據</p>';
                const price = priceData ? priceData.option_price : 0;
                
                return `
                    <div class="data-card">
                        <div class="data-card-header">${type} Option Greeks</div>
                        <div class="data-card-row">
                            <span class="data-card-label">理論價</span>
                            <span class="data-card-value numeric">${price.toFixed(2)}</span>
                        </div>
                        <div class="data-card-row">
                            <span class="data-card-label">Delta</span>
                            <span class="data-card-value numeric">${data.delta.toFixed(4)}</span>
                        </div>
                        <div class="data-card-row">
                            <span class="data-card-label">Gamma</span>
                            <span class="data-card-value numeric">${data.gamma.toFixed(4)}</span>
                        </div>
                        <div class="data-card-row">
                            <span class="data-card-label">Theta</span>
                            <span class="data-card-value numeric ${data.theta < 0 ? 'negative' : 'positive'}">${data.theta.toFixed(4)}</span>
                        </div>
                        <div class="data-card-row">
                            <span class="data-card-label">Vega</span>
                            <span class="data-card-value numeric">${data.vega.toFixed(4)}</span>
                        </div>
                        <div class="data-card-row">
                            <span class="data-card-label">Rho</span>
                            <span class="data-card-value numeric">${data.rho.toFixed(4)}</span>
                        </div>
                    </div>
                `;
            };

            // Render both desktop and mobile views
            document.getElementById('callGreeks').innerHTML = renderGreeks('Call', greeks.call, bs?.call);
            document.getElementById('putGreeks').innerHTML = renderGreeks('Put', greeks.put, bs?.put);
            document.getElementById('callGreeksCards').innerHTML = renderGreeksCards('Call', greeks.call, bs?.call);
            document.getElementById('putGreeksCards').innerHTML = renderGreeksCards('Put', greeks.put, bs?.put);
        }

        // --- 6. 監察崗位 (Module 14) ---
        const posts = calcs.module14_monitoring_posts;
        const postsContainer = document.getElementById('monitoringPosts');
        postsContainer.innerHTML = '';
        
        if (posts && posts.post_details) {
            Object.entries(posts.post_details).forEach(([key, post]) => {
                // 狀態判斷邏輯調整：根據返回的 status 字符串判斷
                const isPass = post.status.includes('正常');
                const isFail = post.status.includes('警報');
                
                const statusClass = isPass ? 'status-pass' : (isFail ? 'status-fail' : 'status-warning');
                const icon = isPass ? 'fa-check-circle' : (isFail ? 'fa-exclamation-triangle' : 'fa-info-circle');
                
                const col = document.createElement('div');
                col.className = 'col-md-6 col-lg-4 mb-3';
                col.innerHTML = `
                    <div class="monitoring-item border rounded bg-white h-100">
                        <div class="d-flex align-items-center mb-2">
                            <i class="fas ${icon} ${statusClass} me-2"></i>
                            <span class="fw-bold">${post.name}</span>
                        </div>
                        <div class="d-flex justify-content-between small">
                            <span class="text-muted">當前: ${post.value !== undefined && typeof post.value === 'number' ? post.value.toFixed(2) : (post.value !== undefined ? post.value : 'N/A')}</span>
                            <span class="text-muted">標準: ${post.threshold !== undefined ? post.threshold : 'N/A'}</span>
                        </div>
                    </div>
                `;
                postsContainer.appendChild(col);
            });
        }

        // --- 7. 基本面健康 (Module 20) ---
        const healthDiv = document.getElementById('fundamentalHealth');
        if (health && health.status !== 'skipped') {
            let metricsHtml = '';
            if (health.metrics) {
                Object.entries(health.metrics).forEach(([key, m]) => {
                    const scoreColor = m.score >= 8 ? 'text-success' : (m.score >= 5 ? 'text-warning' : 'text-danger');
                    metricsHtml += `
                        <div class="d-flex justify-content-between align-items-center mb-2 border-bottom pb-1">
                            <span>${key}</span>
                            <div class="text-end">
                                <div class="fw-bold">${m.value !== null ? m.value : 'N/A'}</div>
                                <small class="${scoreColor}">評分: ${m.score}/10</small>
                            </div>
                        </div>
                    `;
                });
            }
            healthDiv.innerHTML = metricsHtml;
        } else {
            healthDiv.innerHTML = '<p class="text-muted">數據不足，無法進行健康檢查</p>';
        }

        // --- 8. PE 估值 (Module 4 & 5) ---
        const pe = calcs.module4_pe_valuation;
        const ratePe = calcs.module5_rate_pe_relation;
        const peDiv = document.getElementById('peValuation');
        
        let peHtml = '';
        if (pe) {
            peHtml += `
                <div class="mb-3">
                    <div class="d-flex justify-content-between"><span>當前 PE:</span> <strong>${pe.pe_multiple.toFixed(2)}</strong></div>
                    <div class="d-flex justify-content-between"><span>EPS:</span> <strong>$${pe.eps.toFixed(2)}</strong></div>
                    <div class="d-flex justify-content-between"><span>PEG:</span> <strong>${pe.peg_ratio || 'N/A'}</strong></div>
                    <div class="mt-1 small text-muted">${pe.peg_valuation || ''}</div>
                </div>
            `;
        }
        if (ratePe) {
            peHtml += `
                <div class="border-top pt-2">
                    <div class="d-flex justify-content-between"><span>利率基準 PE:</span> <strong>${ratePe.reasonable_pe.toFixed(2)}</strong></div>
                    <div class="d-flex justify-content-between"><span>行業 PE 範圍:</span> <strong>${ratePe.行業PE範圍 || 'N/A'}</strong></div>
                    <div class="mt-1 small text-info">${ratePe.行業比較 || ''}</div>
                </div>
            `;
        }
        peDiv.innerHTML = peHtml || '<p class="text-muted">無 PE 數據</p>';

        // --- 9. 倉位分析 (Module 13) ---
        const pos = calcs.module13_position_analysis;
        const posDiv = document.getElementById('positionAnalysis');
        if (pos) {
            posDiv.innerHTML = `
                <div class="mb-2">
                    <small class="text-muted">成交量/持倉量</small>
                    <div class="progress" style="height: 6px;">
                        <div class="progress-bar" role="progressbar" style="width: ${Math.min(100, (pos.volume/pos.open_interest)*100)}%"></div>
                    </div>
                    <div class="d-flex justify-content-between small mt-1">
                        <span>Vol: ${pos.volume}</span>
                        <span>OI: ${pos.open_interest}</span>
                    </div>
                </div>
                <div class="small border-top pt-2">
                    <div class="mb-1"><strong>機構持股:</strong> ${pos.institutional_ownership}% <span class="text-muted">(${pos.inst_note || ''})</span></div>
                    <div class="mb-1"><strong>內部人持股:</strong> ${pos.insider_ownership}% <span class="text-muted">(${pos.insider_note || ''})</span></div>
                    <div><strong>做空比例:</strong> ${pos.short_float}% <span class="text-muted">(${pos.short_note || ''})</span></div>
                </div>
            `;
        } else {
            posDiv.innerHTML = '<p class="text-muted">無倉位數據</p>';
        }

        // --- 10. 歷史波動率 (Module 18) ---
        const hv = calcs.module18_historical_volatility;
        const hvDiv = document.getElementById('hvAnalysis');
        if (hv && hv.hv_results) {
            let hvHtml = '<table class="table table-sm table-borderless mb-0"><tbody>';
            Object.entries(hv.hv_results).forEach(([window, res]) => {
                hvHtml += `
                    <tr>
                        <td>${window}日 HV</td>
                        <td class="text-end fw-bold">${(res.historical_volatility * 100).toFixed(2)}%</td>
                    </tr>
                `;
            });
            hvHtml += '</tbody></table>';
            
            if (hv.iv_hv_comparison) {
                const ratio = hv.iv_hv_comparison.iv_hv_ratio;
                const color = ratio > 1.2 ? 'text-danger' : (ratio < 0.8 ? 'text-success' : 'text-warning');
                hvHtml += `
                    <div class="border-top pt-2 mt-2 text-center">
                        <small class="text-muted">IV / HV (30日) 比率</small>
                        <div class="fw-bold ${color}">${ratio.toFixed(2)}</div>
                        <small class="text-muted">${hv.iv_hv_comparison.assessment}</small>
                    </div>
                `;
            }
            hvDiv.innerHTML = hvHtml;
        } else {
            hvDiv.innerHTML = '<p class="text-muted">無歷史波動率數據</p>';
        }

        // --- 11. 策略推薦 (New) ---
        const recs = calcs.strategy_recommendations;
        const recDiv = document.getElementById('strategyRecommendations');
        if (recDiv && recs && recs.length > 0) {
            let recHtml = '';
            recs.forEach((rec, index) => {
                const badgeClass = rec.direction === 'Bullish' ? 'bg-success' : (rec.direction === 'Bearish' ? 'bg-danger' : 'bg-secondary');
                const confidenceStars = '★'.repeat(rec.confidence === 'High' ? 3 : (rec.confidence === 'Medium' ? 2 : 1));
                
                recHtml += `
                    <div class="card mb-2 border-start border-4 ${rec.direction === 'Bullish' ? 'border-success' : (rec.direction === 'Bearish' ? 'border-danger' : 'border-secondary')}">
                        <div class="card-body p-2">
                            <div class="d-flex justify-content-between align-items-center mb-1">
                                <h6 class="mb-0 fw-bold">${rec.strategy_name}</h6>
                                <span class="badge ${badgeClass}">${rec.direction}</span>
                            </div>
                            <div class="small text-warning mb-1">${confidenceStars} 信心度: ${rec.confidence}</div>
                            <p class="small mb-1 text-muted">${rec.reasoning.join(' • ')}</p>
                            <div class="small bg-light p-1 rounded">
                                <strong>建議行使價:</strong> $${rec.suggested_strike ? rec.suggested_strike.toFixed(2) : 'N/A'}
                                ${rec.key_levels.stop_loss ? ` | <span class="text-danger">止損: $${rec.key_levels.stop_loss.toFixed(2)}</span>` : ''}
                                ${rec.key_levels.target ? ` | <span class="text-success">目標: $${rec.key_levels.target.toFixed(2)}</span>` : ''}
                            </div>
                        </div>
                    </div>
                `;
            });
            recDiv.innerHTML = recHtml;
        } else if (recDiv) {
            recDiv.innerHTML = '<p class="text-muted text-center">暫無明確策略建議</p>';
        }

        // --- 12. 單腿策略損益 (Module 7-10) ---
        const pnlTableBody = document.querySelector('#strategyPnLTable tbody');
        if (pnlTableBody) {
            pnlTableBody.innerHTML = '';
            const scenarios = [0, 1, 2]; // 假設後端返回3個場景: -10%, 0%, +10%
            
            // 獲取各策略數據
            const longCall = calcs.module7_long_call || [];
            const longPut = calcs.module8_long_put || [];
            const shortCall = calcs.module9_short_call || [];
            const shortPut = calcs.module10_short_put || [];

            if (longCall.length > 0) {
                scenarios.forEach(i => {
                    const price = longCall[i] ? longCall[i].stock_price_at_expiry : 0;
                    const lc = longCall[i] ? longCall[i].profit_loss : 0;
                    const lp = longPut[i] ? longPut[i].profit_loss : 0;
                    const sc = shortCall[i] ? shortCall[i].profit_loss : 0;
                    const sp = shortPut[i] ? shortPut[i].profit_loss : 0;

                    const formatPnL = (val) => {
                        const color = val > 0 ? 'text-success' : (val < 0 ? 'text-danger' : 'text-muted');
                        return `<span class="${color} fw-bold">${val > 0 ? '+' : ''}${val.toFixed(2)}</span>`;
                    };

                    const row = `
                        <tr>
                            <td>$${price.toFixed(2)}</td>
                            <td>${formatPnL(lc)}</td>
                            <td>${formatPnL(lp)}</td>
                            <td>${formatPnL(sc)}</td>
                            <td>${formatPnL(sp)}</td>
                        </tr>
                    `;
                    pnlTableBody.innerHTML += row;
                });
            } else {
                pnlTableBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">無策略損益數據 (需選擇行使價)</td></tr>';
            }
        }

        // --- 13. 對沖量 (Module 6) ---
        const hedge = calcs.module6_hedge_quantity;
        const hedgeDiv = document.getElementById('hedgeQuantity');
        if (hedgeDiv) {
            if (hedge) {
                hedgeDiv.innerHTML = `
                    <div class="d-flex justify-content-between mb-2">
                        <span>正股數量:</span> <strong>${hedge.stock_quantity} 股</strong>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span>持倉市值:</span> <strong>$${hedge.portfolio_value.toFixed(2)}</strong>
                    </div>
                    <div class="alert alert-info mb-0 py-2 text-center">
                        需 <strong>${hedge.hedge_contracts}</strong> 張 Put 合約對沖
                        <div class="small mt-1">覆蓋率: ${hedge.coverage_percentage.toFixed(1)}%</div>
                    </div>
                `;
            } else {
                hedgeDiv.innerHTML = '<p class="text-muted">無對沖數據</p>';
            }
        }

        // --- 14. 合成正股 (Module 11) ---
        const synth = calcs.module11_synthetic_stock;
        const synthDiv = document.getElementById('syntheticStock');
        if (synthDiv) {
            if (synth) {
                const isArb = synth.arbitrage_opportunity;
                synthDiv.innerHTML = `
                    <div class="d-flex justify-content-between mb-1">
                        <span>合成價格:</span> <strong>$${synth.synthetic_price.toFixed(2)}</strong>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span>實際股價:</span> <strong>$${synth.current_stock_price.toFixed(2)}</strong>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span>價差:</span> <span class="${isArb ? 'text-danger fw-bold' : 'text-muted'}">$${synth.difference.toFixed(2)}</span>
                    </div>
                    <div class="small text-muted border-top pt-2">
                        <strong>策略:</strong> ${synth.strategy}
                    </div>
                `;
            } else {
                synthDiv.innerHTML = '<p class="text-muted">無合成正股數據 (需 Call & Put 價格)</p>';
            }
        }

        // --- 15. 年息收益率 (Module 12) ---
        const yieldData = calcs.module12_annual_yield;
        const yieldDiv = document.getElementById('annualYield');
        if (yieldDiv) {
            if (yieldData) {
                yieldDiv.innerHTML = `
                    <div class="text-center mb-3">
                        <h3 class="text-success">${yieldData.annual_yield.toFixed(2)}%</h3>
                        <small class="text-muted">總年化收益率</small>
                    </div>
                    <div class="d-flex justify-content-between small mb-1">
                        <span>派息收益:</span> <span>${yieldData.dividend_yield.toFixed(2)}%</span>
                    </div>
                    <div class="d-flex justify-content-between small">
                        <span>期權收益:</span> <span>${yieldData.option_yield.toFixed(2)}%</span>
                    </div>
                `;
            } else {
                yieldDiv.innerHTML = '<p class="text-muted">無收益率數據</p>';
            }
        }

        // --- 16. Put-Call Parity (Module 19) ---
        const parity = calcs.module19_put_call_parity;
        const parityDiv = document.getElementById('parityCheck');
        if (parityDiv) {
            if (parity && parity.market_prices) {
                const mp = parity.market_prices;
                const isArb = mp.arbitrage_opportunity;
                parityDiv.innerHTML = `
                    <div class="d-flex justify-content-between mb-1">
                        <span>偏離度:</span>
                        <span class="${isArb ? 'text-danger fw-bold' : 'text-success'}">$${mp.deviation.toFixed(2)}</span>
                    </div>
                    <div class="progress mb-2" style="height: 6px;">
                        <div class="progress-bar ${isArb ? 'bg-danger' : 'bg-success'}" role="progressbar" style="width: ${Math.min(100, Math.abs(mp.deviation_percentage))}%"></div>
                    </div>
                    <div class="small text-muted">
                        ${mp.strategy}
                    </div>
                `;
            } else {
                parityDiv.innerHTML = '<p class="text-muted">無 Parity 數據</p>';
            }
        }

        // 調用新增模塊渲染函數
        renderAdditionalModules(calcs);
        
        // Initialize lazy loading for dynamically rendered content
        initializeLazyLoading();
    }
});

} // End of initializeAnalysisForm


// ========== 新增模塊渲染函數 ==========

function renderAdditionalModules(calcs) {
    // --- 動量過濾器 (Module 21) ---
    const momentum = calcs.module21_momentum_filter;
    const momentumDiv = document.getElementById('momentumFilter');
    if (momentumDiv) {
        if (momentum && momentum.status !== 'skipped' && momentum.status !== 'error') {
            const score = momentum.momentum_score || 0.5;
            const scoreColor = score >= 0.7 ? 'text-success' : (score <= 0.3 ? 'text-danger' : 'text-warning');
            const direction = score >= 0.7 ? '強勢上漲' : (score <= 0.3 ? '弱勢下跌' : '中性震盪');
            
            momentumDiv.innerHTML = `
                <div class="text-center mb-3">
                    <h3 class="${scoreColor}">${(score * 100).toFixed(0)}%</h3>
                    <small class="text-muted">動量得分</small>
                </div>
                <div class="d-flex justify-content-between mb-2">
                    <span>趨勢方向:</span>
                    <span class="${scoreColor} fw-bold">${direction}</span>
                </div>
                ${momentum.recommendation ? `<div class="alert alert-${score >= 0.7 ? 'success' : (score <= 0.3 ? 'danger' : 'warning')} mb-0 py-2 small">${momentum.recommendation}</div>` : ''}
            `;
        } else {
            momentumDiv.innerHTML = `<p class="text-muted">${momentum?.reason || '動量數據不足'}</p>`;
        }
    }

    // --- 動態 IV 閾值 (Module 23) ---
    const ivThreshold = calcs.module23_dynamic_iv_threshold;
    const ivThresholdDiv = document.getElementById('dynamicIVThreshold');
    if (ivThresholdDiv) {
        if (ivThreshold && ivThreshold.status !== 'skipped' && ivThreshold.status !== 'error') {
            const currentIV = ivThreshold.current_iv || 0;
            const threshold = ivThreshold.threshold || 0;
            const isHigh = currentIV > threshold;
            
            ivThresholdDiv.innerHTML = `
                <div class="text-center mb-3">
                    <h4 class="${isHigh ? 'text-danger' : 'text-success'}">${(currentIV * 100).toFixed(1)}%</h4>
                    <small class="text-muted">當前 IV</small>
                </div>
                <div class="d-flex justify-content-between mb-2">
                    <span>動態閾值:</span>
                    <span class="fw-bold">${(threshold * 100).toFixed(1)}%</span>
                </div>
                <div class="d-flex justify-content-between mb-2">
                    <span>IV Rank:</span>
                    <span class="fw-bold">${ivThreshold.iv_rank ? ivThreshold.iv_rank.toFixed(1) + '%' : 'N/A'}</span>
                </div>
                <div class="alert alert-${isHigh ? 'warning' : 'info'} mb-0 py-2 small">
                    ${isHigh ? '⚠️ IV 偏高，適合賣方策略' : '✓ IV 正常，可考慮買方策略'}
                </div>
            `;
        } else {
            ivThresholdDiv.innerHTML = `<p class="text-muted">${ivThreshold?.reason || '無動態 IV 閾值數據'}</p>`;
        }
    }

    // --- 資金倉位計算器 (Module 28) ---
    const posCalc = calcs.module28_position_calculator;
    const posCalcDiv = document.getElementById('positionCalculator');
    if (posCalcDiv) {
        if (posCalc && posCalc.status === 'success') {
            const posRec = posCalc.position_recommendation || {};
            const riskAna = posCalc.risk_analysis || {};
            const capSum = posCalc.capital_summary || {};
            
            posCalcDiv.innerHTML = `
                <div class="text-center mb-3">
                    <h3 class="text-primary">${posRec.recommended_contracts || 0} 張</h3>
                    <small class="text-muted">建議合約數量</small>
                </div>
                <div class="d-flex justify-content-between mb-1">
                    <span>總資金:</span>
                    <span class="fw-bold">${capSum.currency || 'HKD'} ${(capSum.total_capital || 0).toLocaleString()}</span>
                </div>
                <div class="d-flex justify-content-between mb-1">
                    <span>投入金額:</span>
                    <span class="fw-bold">$${(posRec.actual_investment_usd || 0).toFixed(0)}</span>
                </div>
                <div class="d-flex justify-content-between mb-1">
                    <span>最大虧損:</span>
                    <span class="text-danger fw-bold">$${(riskAna.max_loss_usd || 0).toFixed(0)} (${riskAna.max_loss_pct || 0}%)</span>
                </div>
                <div class="d-flex justify-content-between mb-2">
                    <span>風險評級:</span>
                    <span class="badge ${riskAna.risk_rating === '低' ? 'bg-success' : (riskAna.risk_rating === '高' ? 'bg-danger' : 'bg-warning')}">${riskAna.risk_rating || 'N/A'}</span>
                </div>
            `;
        } else {
            posCalcDiv.innerHTML = `<p class="text-muted">${posCalc?.reason || '無倉位計算數據'}</p>`;
        }
    }

    // --- 最佳行使價分析 (Module 22) ---
    const optStrike = calcs.module22_optimal_strike;
    const optStrikeDiv = document.getElementById('optimalStrike');
    if (optStrikeDiv) {
        if (optStrike && optStrike.status !== 'skipped' && optStrike.status !== 'error') {
            let html = '<div class="row">';
            const strategies = ['long_call', 'long_put', 'short_call', 'short_put'];
            const strategyNames = {'long_call': 'Long Call', 'long_put': 'Long Put', 'short_call': 'Short Call', 'short_put': 'Short Put'};
            const strategyColors = {'long_call': 'success', 'long_put': 'danger', 'short_call': 'warning', 'short_put': 'info'};
            
            strategies.forEach(strategy => {
                const data = optStrike[strategy];
                if (data && data.optimal_strike) {
                    html += `
                        <div class="col-md-3 mb-3">
                            <div class="card h-100 border-${strategyColors[strategy]}">
                                <div class="card-header bg-${strategyColors[strategy]} text-white py-2">
                                    <h6 class="mb-0">${strategyNames[strategy]}</h6>
                                </div>
                                <div class="card-body py-2">
                                    <div class="text-center mb-2">
                                        <h4 class="mb-0">$${data.optimal_strike.toFixed(2)}</h4>
                                        <small class="text-muted">最佳行使價</small>
                                    </div>
                                    <div class="small">
                                        <div class="d-flex justify-content-between"><span>評分:</span><span class="fw-bold">${data.score?.toFixed(1) || 'N/A'}</span></div>
                                        <div class="d-flex justify-content-between"><span>Delta:</span><span>${data.delta?.toFixed(3) || 'N/A'}</span></div>
                                        <div class="d-flex justify-content-between"><span>權利金:</span><span>$${data.premium?.toFixed(2) || 'N/A'}</span></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                }
            });
            html += '</div>';
            if (optStrike.recommendation) {
                html += `<div class="alert alert-info mt-2 mb-0"><i class="fas fa-lightbulb me-2"></i>${optStrike.recommendation}</div>`;
            }
            optStrikeDiv.innerHTML = html;
        } else {
            optStrikeDiv.innerHTML = `<p class="text-muted text-center">${optStrike?.reason || '無最佳行使價數據'}</p>`;
        }
    }

    // --- 技術方向分析 (Module 24) ---
    const techDir = calcs.module24_technical_direction;
    const techDirDiv = document.getElementById('technicalDirection');
    if (techDirDiv) {
        if (techDir && techDir.status !== 'skipped' && techDir.status !== 'error') {
            const direction = techDir.combined_direction || 'Neutral';
            const confidence = techDir.confidence || 'Low';
            const dirColor = direction === 'Bullish' ? 'success' : (direction === 'Bearish' ? 'danger' : 'secondary');
            
            let html = `
                <div class="text-center mb-3">
                    <span class="badge bg-${dirColor} fs-5 px-3 py-2">${direction}</span>
                    <div class="mt-1"><small class="text-muted">信心度: </small><span class="badge bg-${confidence === 'High' ? 'success' : (confidence === 'Medium' ? 'warning' : 'secondary')}">${confidence}</span></div>
                </div>
            `;
            if (techDir.daily_trend) {
                const dt = techDir.daily_trend;
                html += `<div class="border-top pt-2"><h6 class="small fw-bold mb-2">日線趨勢</h6>
                    <div class="d-flex justify-content-between small mb-1"><span>趨勢:</span><span class="text-${dt.trend === 'Bullish' ? 'success' : (dt.trend === 'Bearish' ? 'danger' : 'muted')}">${dt.trend}</span></div>
                    ${dt.ma_20 ? `<div class="d-flex justify-content-between small mb-1"><span>MA20:</span><span>$${dt.ma_20.toFixed(2)}</span></div>` : ''}
                    ${dt.ma_50 ? `<div class="d-flex justify-content-between small mb-1"><span>MA50:</span><span>$${dt.ma_50.toFixed(2)}</span></div>` : ''}
                </div>`;
            }
            techDirDiv.innerHTML = html;
        } else {
            techDirDiv.innerHTML = `<p class="text-muted">${techDir?.reason || '無技術方向數據'}</p>`;
        }
    }

    // --- 波動率微笑分析 (Module 25) ---
    const volSmile = calcs.module25_volatility_smile;
    const volSmileDiv = document.getElementById('volatilitySmile');
    if (volSmileDiv) {
        if (volSmile && volSmile.status !== 'skipped' && volSmile.status !== 'error') {
            const atmIV = volSmile.atm_iv || 0;
            const skew = volSmile.skew || 0;
            const skewType = volSmile.skew_type || 'Normal';
            const ivEnv = volSmile.iv_environment || 'Normal';
            
            volSmileDiv.innerHTML = `
                <div class="text-center mb-3"><h4 class="mb-0">${(atmIV * 100).toFixed(1)}%</h4><small class="text-muted">ATM IV</small></div>
                <div class="d-flex justify-content-between mb-2"><span>Skew:</span><span class="${skew > 0 ? 'text-danger' : 'text-success'} fw-bold">${(skew * 100).toFixed(2)}%</span></div>
                <div class="d-flex justify-content-between mb-2"><span>Skew 類型:</span><span class="badge bg-${skewType === 'Put Skew' ? 'danger' : (skewType === 'Call Skew' ? 'success' : 'secondary')}">${skewType}</span></div>
                <div class="d-flex justify-content-between mb-2"><span>IV 環境:</span><span class="badge bg-${ivEnv === 'High' ? 'danger' : (ivEnv === 'Low' ? 'success' : 'warning')}">${ivEnv}</span></div>
                ${volSmile.anomaly_count > 0 ? `<div class="alert alert-warning mb-0 py-2 small"><i class="fas fa-exclamation-triangle me-1"></i>發現 ${volSmile.anomaly_count} 個定價異常</div>` : ''}
            `;
        } else {
            volSmileDiv.innerHTML = `<p class="text-muted">${volSmile?.reason || '無波動率微笑數據'}</p>`;
        }
    }

    // --- Long 期權成本效益分析 (Module 26) ---
    const longOpt = calcs.module26_long_option_analysis;
    const longOptDiv = document.getElementById('longOptionAnalysis');
    if (longOptDiv) {
        if (longOpt && longOpt.status !== 'skipped' && longOpt.status !== 'error') {
            let html = '<div class="row">';
            if (longOpt.long_call) {
                const lc = longOpt.long_call;
                const score = lc.score || {};
                html += `<div class="col-md-6 mb-3"><div class="card h-100 border-success"><div class="card-header bg-success text-white py-2"><h6 class="mb-0">Long Call</h6></div>
                    <div class="card-body py-2"><div class="text-center mb-2"><h4 class="mb-0">${score.total_score || 'N/A'}</h4><span class="badge bg-${score.grade === 'A' || score.grade === 'B' ? 'success' : 'warning'}">${score.grade || 'N/A'}</span></div>
                    <div class="small"><div class="d-flex justify-content-between mb-1"><span>行使價:</span><span>$${lc.strike?.toFixed(2) || 'N/A'}</span></div>
                    <div class="d-flex justify-content-between mb-1"><span>權利金:</span><span>$${lc.premium?.toFixed(2) || 'N/A'}</span></div>
                    <div class="d-flex justify-content-between"><span>槓桿:</span><span>${lc.leverage?.toFixed(1) || 'N/A'}x</span></div></div></div></div></div>`;
            }
            if (longOpt.long_put) {
                const lp = longOpt.long_put;
                const score = lp.score || {};
                html += `<div class="col-md-6 mb-3"><div class="card h-100 border-danger"><div class="card-header bg-danger text-white py-2"><h6 class="mb-0">Long Put</h6></div>
                    <div class="card-body py-2"><div class="text-center mb-2"><h4 class="mb-0">${score.total_score || 'N/A'}</h4><span class="badge bg-${score.grade === 'A' || score.grade === 'B' ? 'success' : 'warning'}">${score.grade || 'N/A'}</span></div>
                    <div class="small"><div class="d-flex justify-content-between mb-1"><span>行使價:</span><span>$${lp.strike?.toFixed(2) || 'N/A'}</span></div>
                    <div class="d-flex justify-content-between mb-1"><span>權利金:</span><span>$${lp.premium?.toFixed(2) || 'N/A'}</span></div>
                    <div class="d-flex justify-content-between"><span>槓桿:</span><span>${lp.leverage?.toFixed(1) || 'N/A'}x</span></div></div></div></div></div>`;
            }
            html += '</div>';
            if (longOpt.comparison) {
                html += `<div class="alert alert-info mb-0"><i class="fas fa-balance-scale me-2"></i><strong>推薦:</strong> ${longOpt.comparison.better_choice || 'N/A'}</div>`;
            }
            longOptDiv.innerHTML = html;
        } else {
            longOptDiv.innerHTML = `<p class="text-muted text-center">${longOpt?.reason || '無 Long 期權分析數據'}</p>`;
        }
    }

    // --- 多到期日比較 (Module 27) ---
    const multiExp = calcs.module27_multi_expiry_comparison;
    const multiExpDiv = document.getElementById('multiExpiryComparison');
    if (multiExpDiv) {
        if (multiExp && multiExp.status === 'success') {
            let html = `
                <div class="mb-3 d-flex justify-content-between align-items-center">
                    <small class="text-muted">
                        <i class="fas fa-calendar-check me-1"></i>
                        分析了 <strong>${multiExp.expirations_analyzed || 0}</strong> 個到期日 
                        (共 ${multiExp.total_expirations_available || 0} 個可用)
                    </small>
                </div>
            `;
            
            // 策略推薦卡片
            html += '<div class="row mb-3">';
            const strategyResults = multiExp.strategy_results || {};
            const strategyNames = {'long_call': 'Long Call', 'long_put': 'Long Put', 'short_call': 'Short Call', 'short_put': 'Short Put'};
            const strategyColors = {'long_call': 'success', 'long_put': 'danger', 'short_call': 'warning', 'short_put': 'info'};
            const strategyIcons = {'long_call': 'fa-arrow-up', 'long_put': 'fa-arrow-down', 'short_call': 'fa-level-down-alt', 'short_put': 'fa-level-up-alt'};
            
            Object.entries(strategyResults).forEach(([strategy, result]) => {
                if (result && result.status === 'success') {
                    const rec = result.recommendation || {};
                    const reasons = rec.reasons || [];
                    html += `
                        <div class="col-md-3 mb-3">
                            <div class="card h-100 border-${strategyColors[strategy]}">
                                <div class="card-header bg-${strategyColors[strategy]} text-white py-2">
                                    <h6 class="mb-0 small"><i class="fas ${strategyIcons[strategy]} me-1"></i>${strategyNames[strategy]}</h6>
                                </div>
                                <div class="card-body py-2">
                                    <div class="text-center mb-2">
                                        <div class="fw-bold">${rec.best_expiration || 'N/A'}</div>
                                        <small class="text-muted">${rec.best_days || 0} 天</small>
                                    </div>
                                    <div class="small">
                                        <div class="d-flex justify-content-between mb-1">
                                            <span>評分:</span>
                                            <span class="fw-bold">${rec.best_score || 'N/A'}</span>
                                        </div>
                                        <div class="d-flex justify-content-between mb-1">
                                            <span>等級:</span>
                                            <span class="badge bg-${rec.best_grade === 'A' || rec.best_grade === 'B' ? 'success' : 'secondary'}">${rec.best_grade || 'N/A'}</span>
                                        </div>
                                        <div class="d-flex justify-content-between">
                                            <span>權利金:</span>
                                            <span>${rec.best_premium?.toFixed(2) || 'N/A'}</span>
                                        </div>
                                    </div>
                                    ${reasons.length > 0 ? `<div class="mt-2 small text-muted border-top pt-1">${reasons[0]}</div>` : ''}
                                </div>
                            </div>
                        </div>
                    `;
                }
            });
            html += '</div>';
            
            // 詳細比較表格（如果有多個到期日）
            if (multiExp.expirations_analyzed > 1) {
                // 取第一個策略的詳細數據來顯示表格
                const firstStrategy = Object.values(strategyResults).find(r => r && r.status === 'success');
                if (firstStrategy && firstStrategy.comparison_table && firstStrategy.comparison_table.length > 0) {
                    html += `
                        <div class="table-responsive mt-3">
                            <table class="table table-sm table-hover">
                                <thead class="table-light">
                                    <tr>
                                        <th>到期日</th>
                                        <th>天數</th>
                                        <th>權利金</th>
                                        <th>IV</th>
                                        <th>Theta/日</th>
                                        <th>年化收益</th>
                                        <th>評分</th>
                                    </tr>
                                </thead>
                                <tbody>
                    `;
                    firstStrategy.comparison_table.forEach(row => {
                        const gradeColor = row.grade === 'A' ? 'success' : (row.grade === 'B' ? 'primary' : (row.grade === 'C' ? 'warning' : 'secondary'));
                        html += `
                            <tr>
                                <td><strong>${row.expiration || 'N/A'}</strong></td>
                                <td>${row.days || 0}</td>
                                <td>${row.premium?.toFixed(2) || 'N/A'}</td>
                                <td>${row.iv?.toFixed(1) || 'N/A'}%</td>
                                <td class="${row.theta_pct > 3 ? 'text-danger' : ''}">${row.theta_pct?.toFixed(2) || 'N/A'}%</td>
                                <td>${row.annualized_return?.toFixed(1) || 'N/A'}%</td>
                                <td><span class="badge bg-${gradeColor}">${row.score || 0} (${row.grade || 'N/A'})</span></td>
                            </tr>
                        `;
                    });
                    html += '</tbody></table></div>';
                }
            }
            
            // 已分析的到期日列表
            if (multiExp.expiration_list && multiExp.expiration_list.length > 0) {
                html += `
                    <div class="mt-3 p-2 bg-light rounded small">
                        <strong><i class="fas fa-list me-1"></i>已分析到期日:</strong> 
                        ${multiExp.expiration_list.map(exp => `<span class="badge bg-secondary me-1">${exp}</span>`).join('')}
                    </div>
                `;
            }
            
            // Theta 分析建議
            const thetaAnalysis = Object.values(strategyResults).find(r => r && r.theta_analysis);
            if (thetaAnalysis && thetaAnalysis.theta_analysis && thetaAnalysis.theta_analysis.suggestion) {
                html += `
                    <div class="alert alert-info mt-3 mb-0 py-2">
                        <i class="fas fa-clock me-2"></i>
                        <strong>Theta 建議:</strong> ${thetaAnalysis.theta_analysis.suggestion}
                    </div>
                `;
            }
            
            multiExpDiv.innerHTML = html;
        } else {
            multiExpDiv.innerHTML = `<p class="text-muted text-center">${multiExp?.reason || '無多到期日比較數據'}</p>`;
        }
    }
}


// ========== Lazy Loading Integration ==========

/**
 * Mark non-critical module cards for lazy loading
 * This function adds data-lazy-load attributes to module cards
 * that are below the fold for performance optimization
 */
function setupLazyLoadingForModules() {
    // Get all module cards
    const moduleCards = document.querySelectorAll('.card');
    
    // Mark cards below the fold for lazy loading
    moduleCards.forEach((card, index) => {
        // Load first 3 cards immediately (above the fold)
        // Lazy load the rest
        if (index >= 3) {
            card.setAttribute('data-lazy-load', 'module');
        }
    });
    
    // Refresh lazy loader to observe new elements
    if (window.lazyLoader) {
        window.lazyLoader.refresh();
    }
}

/**
 * Add loading="lazy" attribute to dynamically created images
 * This ensures all images use native lazy loading when supported
 */
function addLazyLoadingToImages() {
    const images = document.querySelectorAll('img:not([loading])');
    images.forEach(img => {
        // Add native lazy loading attribute
        img.setAttribute('loading', 'lazy');
    });
}

/**
 * Initialize lazy loading after results are rendered
 */
function initializeLazyLoading() {
    // Add lazy loading to images
    addLazyLoadingToImages();
    
    // Setup lazy loading for module cards
    setupLazyLoadingForModules();
    
    // Refresh the lazy loader
    if (window.lazyLoader) {
        window.lazyLoader.refresh();
    }
}

// Call lazy loading initialization after DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize lazy loading for existing content
    initializeLazyLoading();
});
