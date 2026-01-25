document.addEventListener('alpine:init', () => {
    Alpine.data('app', () => ({
        // 狀態管理
        isLoading: false,
        error: null,
        results: null,
        expirations: [],
        showAdvanced: false, // 控制高級設置顯示
        form: {
            ticker: 'NOW',
            target_date: '',
            use_ibkr: false,
            // 高級設置
            confidence_level: 0.68,
            direction: '',     // "" means Auto
            strike_price: null, // null means Auto
            risk_free_rate: 0.045,
            // Custom Overrides
            iv: null,
            delta: null,
            gamma: null,
            theta: null,
            vega: null,
            rho: null
        },
        status: {
            ibkr: false,
            api: true
        },
        progress: {
            percent: 0,
            status: '準備就緒'
        },

        // 輪詢計時器
        statusTimer: null,

        // 生命周期
        async init() {
            this.checkSystemStatus();
            this.statusTimer = setInterval(() => this.checkSystemStatus(), 30000);

            // 如果預填了股票代碼，初始加載到期日
            if (this.form.ticker) {
                await this.fetchExpirations();
            }

            // 監聽代碼變化
            this.$watch('form.ticker', (value) => {
                if (value && value.length >= 2) {
                    this.fetchExpirations();
                }
            });
        },

        // 系統動作
        async checkSystemStatus() {
            try {
                const res = await fetch('/api/system_status');
                const data = await res.json();
                // 使用後端返回的真實連接狀態
                this.status.ibkr = data.ibkr_connected;
                this.status.api = true;
            } catch (e) {
                console.error('狀態檢查失敗:', e);
                this.status.api = false;
                this.status.ibkr = false;
            }
        },

        async fetchExpirations() {
            if (!this.form.ticker) return;
            try {
                // 重置
                this.expirations = [];

                const res = await fetch(`/api/expirations?ticker=${this.form.ticker}`);
                const data = await res.json();

                // 修正：檢查 data.status === 'success' 而非 data.success
                if (data.status === 'success' && data.expirations && data.expirations.length > 0) {
                    this.expirations = data.expirations;
                    // 自動選擇第一個到期日
                    if (!this.form.target_date) {
                        this.form.target_date = data.expirations[0];
                    }
                } else {
                    console.warn('未找到到期日:', data.message);
                }
            } catch (e) {
                console.error('獲取到期日失敗:', e);
            }
        },

        async runAnalysis() {
            if (!this.form.ticker || !this.form.target_date) {
                this.error = "請輸入股票代碼並選擇目標日期";
                return;
            }

            this.isLoading = true;
            this.error = null;
            this.results = null;
            this.progress = { percent: 0, status: '初始化中...' };

            try {
                // 生成任務 ID (簡單時間戳)
                const taskId = `${this.form.ticker}_${Date.now()}`;

                // 開始進度追蹤 (SSE)
                const eventSource = new EventSource(`/api/progress/stream/${taskId}`);

                eventSource.onmessage = (e) => {
                    const data = JSON.parse(e.data);
                    // 翻譯狀態文本 (如果後端傳回英文)
                    this.progress = data;
                    if (data.percent >= 100) {
                        eventSource.close();
                    }
                };

                eventSource.onerror = (e) => {
                    eventSource.close();
                };

                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        task_id: taskId,
                        ...this.form
                    })
                });

                const data = await response.json();
                console.log("DEBUG: Received Response Payload:", data); // Log full response

                if (data.status === 'success') {
                    // 修正: app.py 直接返回了 serializable_results，其中包含 status: 'success'
                    // 所以 data 本身就是結果對象，不需要 .data
                    this.results = data;
                    console.log("DEBUG: Setting this.results =", this.results);


                    this.$nextTick(() => {
                        this.renderAllModules();
                    });
                } else {
                    this.error = data.message || "分析失敗";
                }

            } catch (e) {
                this.error = "分析過程中發生網絡錯誤";
                console.error(e);
            } finally {
                this.isLoading = false;
            }
        },

        // 渲染協調器
        renderAllModules() {
            const data = this.results;
            if (!data) return;

            console.log("開始渲染模塊...", data);

            try {
                // 核心模塊 1-5
                if (window.ModulesCore) ModulesCore.render(data);

                // 策略模塊 6-12
                if (window.ModulesStrategies) ModulesStrategies.render(data);

                // Greeks 模塊 13-19
                if (window.ModulesGreeks) ModulesGreeks.render(data);

                // 高級模塊 20-28
                if (window.ModulesAdvanced) ModulesAdvanced.render(data);

                // 信號模塊 30-32
                if (window.ModulesSignals) ModulesSignals.render(data);

                // 圖表
                if (window.ChartPriceRange) ChartPriceRange.render(data);
                if (window.ChartVolSmile) ChartVolSmile.render(data);
                if (window.ChartPnlCurve) ChartPnlCurve.render(data);
                if (window.ChartGexOi) ChartGexOi.render(data);
                if (window.ChartHvTrend) ChartHvTrend.render(data);
                if (window.ChartIVGauge) ChartIVGauge.render(data);

            } catch (e) {
                console.error("渲染錯誤:", e);
                this.error = "顯示結果時發生錯誤: " + e.message;
            }
        },

        // 工具函數
        formatNum(v, decimals = 2) {
            return v != null ? Number(v).toFixed(decimals) : '-';
        }
    }));
});
