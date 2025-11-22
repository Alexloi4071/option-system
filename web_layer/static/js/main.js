// web_layer/static/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('analysisForm');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const loadingState = document.getElementById('loadingState');
    const resultsArea = document.getElementById('resultsArea');
    const errorAlert = document.getElementById('errorAlert');
    const errorMessage = document.getElementById('errorMessage');
    
    // Expiration Date Logic
    const tickerInput = document.getElementById('ticker');
    const expirationSelect = document.getElementById('expiration');
    const refreshDatesBtn = document.getElementById('refreshDatesBtn');
    const expirationStatus = document.getElementById('expirationStatus');
    
    let fetchTimeout;

    // Auto-fetch dates when ticker changes
    tickerInput.addEventListener('input', function() {
        clearTimeout(fetchTimeout);
        const ticker = this.value.trim();
        if (ticker.length >= 1) {
            fetchTimeout = setTimeout(() => fetchExpirations(ticker), 800);
        }
    });

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
                
                expirationStatus.textContent = `已獲取 ${data.expirations.length} 個到期日`;
                expirationStatus.className = 'form-text text-success';
            } else {
                throw new Error(data.message || '無法獲取');
            }
        } catch (error) {
            console.error('Fetch expirations error:', error);
            expirationStatus.textContent = '無法獲取到期日 (可能代碼錯誤)';
            expirationStatus.className = 'form-text text-warning';
        } finally {
            refreshDatesBtn.disabled = false;
        }
    }

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        // 1. 獲取表單數據
        const formData = {
            ticker: document.getElementById('ticker').value,
            expiration: document.getElementById('expiration').value || null,
            confidence: document.getElementById('confidence').value,
            use_ibkr: document.getElementById('useIbkr').checked,
            strike: document.getElementById('strike').value || null,
            premium: document.getElementById('premium').value || null,
            type: document.getElementById('optionType').value || null
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

            if (!response.ok) {
                throw new Error(data.message || '分析請求失敗');
            }

            // 4. 渲染數據
            renderResults(data);
            resultsArea.classList.remove('d-none');

        } catch (error) {
            console.error('Error:', error);
            errorMessage.textContent = error.message;
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

            document.getElementById('callGreeks').innerHTML = renderGreeks('Call', greeks.call, bs?.call);
            document.getElementById('putGreeks').innerHTML = renderGreeks('Put', greeks.put, bs?.put);
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
    }
});