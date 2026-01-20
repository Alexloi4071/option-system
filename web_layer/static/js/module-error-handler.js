/**
 * Module Error Handler
 * Provides comprehensive error handling for module rendering
 * 
 * Features:
 * - Try-catch wrappers for module rendering
 * - Graceful error state display
 * - Error logging and tracking
 * - Recovery mechanisms
 */

(function() {
    'use strict';

    const ModuleErrorHandler = {
        // Track errors by module
        errors: {},
        errorCount: 0,
        maxErrorsPerModule: 3,

        /**
         * Wrap a module rendering function with error handling
         * @param {Function} renderFn - Module rendering function
         * @param {string} moduleName - Name of the module
         * @param {HTMLElement} container - Container element for the module
         * @param {*} data - Data to pass to rendering function
         * @returns {boolean} Success status
         */
        safeRender: function(renderFn, moduleName, container, data) {
            try {
                // Validate inputs
                if (typeof renderFn !== 'function') {
                    throw new Error('renderFn must be a function');
                }
                if (!container) {
                    throw new Error('Container element not found');
                }

                // Initialize error tracking for this module
                if (!this.errors[moduleName]) {
                    this.errors[moduleName] = [];
                }

                // Check if module has exceeded error limit
                if (this.errors[moduleName].length >= this.maxErrorsPerModule) {
                    console.error(`[Module Error Handler] Module ${moduleName} has exceeded error limit`);
                    this.renderPermanentError(container, moduleName);
                    return false;
                }

                // Execute rendering function
                renderFn(data);
                return true;

            } catch (error) {
                this.handleRenderError(error, moduleName, container, data);
                return false;
            }
        },

        /**
         * Handle rendering error
         * @param {Error} error - Error object
         * @param {string} moduleName - Module name
         * @param {HTMLElement} container - Container element
         * @param {*} data - Module data
         */
        handleRenderError: function(error, moduleName, container, data) {
            // Log error
            console.error(`[Module Error Handler] Error rendering ${moduleName}:`, error);
            
            // Track error
            this.errors[moduleName] = this.errors[moduleName] || [];
            this.errors[moduleName].push({
                timestamp: Date.now(),
                error: error.message,
                stack: error.stack
            });
            this.errorCount++;

            // Display error state
            this.renderErrorState(container, moduleName, error, data);

            // Send error report if available
            this.reportError(moduleName, error);
        },

        /**
         * Render error state in container
         * @param {HTMLElement} container - Container element
         * @param {string} moduleName - Module name
         * @param {Error} error - Error object
         * @param {*} data - Module data
         */
        renderErrorState: function(container, moduleName, error, data) {
            if (!container) return;

            const errorCount = this.errors[moduleName]?.length || 0;
            const canRetry = errorCount < this.maxErrorsPerModule;

            container.innerHTML = `
                <div class="module-error-state" style="
                    padding: 1.5rem;
                    background-color: #fff3cd;
                    border: 1px solid #ffc107;
                    border-radius: 0.5rem;
                    text-align: center;
                ">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">⚠️</div>
                    <h6 style="color: #856404; margin-bottom: 0.5rem;">模塊渲染錯誤</h6>
                    <p style="color: #856404; font-size: 0.875rem; margin-bottom: 1rem;">
                        ${moduleName} 無法正常顯示
                    </p>
                    ${canRetry ? `
                        <button 
                            class="btn btn-sm btn-warning" 
                            onclick="ModuleErrorHandler.retryRender('${moduleName}', this)"
                            style="margin-right: 0.5rem;"
                        >
                            <i class="fas fa-redo"></i> 重試
                        </button>
                    ` : ''}
                    <button 
                        class="btn btn-sm btn-outline-secondary" 
                        onclick="ModuleErrorHandler.showErrorDetails('${moduleName}')"
                    >
                        <i class="fas fa-info-circle"></i> 詳情
                    </button>
                    ${this.hasValidData(data) ? `
                        <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #ffc107;">
                            <small style="color: #856404;">
                                <i class="fas fa-database"></i> 數據已接收，但顯示失敗
                            </small>
                        </div>
                    ` : ''}
                </div>
            `;
        },

        /**
         * Render permanent error state (max errors exceeded)
         * @param {HTMLElement} container - Container element
         * @param {string} moduleName - Module name
         */
        renderPermanentError: function(container, moduleName) {
            if (!container) return;

            container.innerHTML = `
                <div class="module-error-state" style="
                    padding: 1.5rem;
                    background-color: #f8d7da;
                    border: 1px solid #dc3545;
                    border-radius: 0.5rem;
                    text-align: center;
                ">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">❌</div>
                    <h6 style="color: #721c24; margin-bottom: 0.5rem;">模塊已停用</h6>
                    <p style="color: #721c24; font-size: 0.875rem; margin-bottom: 0;">
                        ${moduleName} 多次渲染失敗，已暫時停用
                    </p>
                    <small style="color: #721c24; display: block; margin-top: 0.5rem;">
                        請刷新頁面或聯繫技術支持
                    </small>
                </div>
            `;
        },

        /**
         * Render no-data state
         * @param {HTMLElement} container - Container element
         * @param {string} moduleName - Module name
         * @param {string} reason - Reason for no data
         */
        renderNoDataState: function(container, moduleName, reason) {
            if (!container) return;

            container.innerHTML = `
                <div class="module-no-data-state" style="
                    padding: 1.5rem;
                    background-color: #e7f3ff;
                    border: 1px solid #b3d9ff;
                    border-radius: 0.5rem;
                    text-align: center;
                ">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">📊</div>
                    <h6 style="color: #004085; margin-bottom: 0.5rem;">暫無數據</h6>
                    <p style="color: #004085; font-size: 0.875rem; margin-bottom: 0;">
                        ${reason || '此模塊當前沒有可顯示的數據'}
                    </p>
                </div>
            `;
        },

        /**
         * Render skipped state
         * @param {HTMLElement} container - Container element
         * @param {string} moduleName - Module name
         * @param {string} reason - Reason for skipping
         */
        renderSkippedState: function(container, moduleName, reason) {
            if (!container) return;

            container.innerHTML = `
                <div class="module-skipped-state" style="
                    padding: 1.5rem;
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 0.5rem;
                    text-align: center;
                ">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">⏭️</div>
                    <h6 style="color: #6c757d; margin-bottom: 0.5rem;">模塊已跳過</h6>
                    <p style="color: #6c757d; font-size: 0.875rem; margin-bottom: 0;">
                        ${reason || '此模塊在當前分析中被跳過'}
                    </p>
                </div>
            `;
        },

        /**
         * Check if data is valid
         * @param {*} data - Data to check
         * @returns {boolean} Whether data is valid
         */
        hasValidData: function(data) {
            if (!data) return false;
            if (typeof data !== 'object') return false;
            if (data.status === 'error' || data.status === 'skipped') return false;
            return Object.keys(data).length > 0;
        },

        /**
         * Retry rendering a module
         * @param {string} moduleName - Module name
         * @param {HTMLElement} button - Retry button element
         */
        retryRender: function(moduleName, button) {
            console.log(`[Module Error Handler] Retrying render for ${moduleName}`);
            
            // Disable button
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 重試中...';
            }

            // Dispatch retry event
            const event = new CustomEvent('moduleRetry', {
                detail: { moduleName }
            });
            document.dispatchEvent(event);

            // Re-enable button after delay
            setTimeout(() => {
                if (button) {
                    button.disabled = false;
                    button.innerHTML = '<i class="fas fa-redo"></i> 重試';
                }
            }, 2000);
        },

        /**
         * Show error details
         * @param {string} moduleName - Module name
         */
        showErrorDetails: function(moduleName) {
            const errors = this.errors[moduleName] || [];
            if (errors.length === 0) {
                alert('沒有錯誤詳情');
                return;
            }

            const latestError = errors[errors.length - 1];
            const details = `
模塊: ${moduleName}
錯誤次數: ${errors.length}
最新錯誤: ${latestError.error}
時間: ${new Date(latestError.timestamp).toLocaleString()}

請將此信息提供給技術支持。
            `.trim();

            alert(details);
            console.log(`[Module Error Handler] Error details for ${moduleName}:`, errors);
        },

        /**
         * Report error to analytics/logging service
         * @param {string} moduleName - Module name
         * @param {Error} error - Error object
         */
        reportError: function(moduleName, error) {
            // This could send to an analytics service
            // For now, just log to console
            console.log('[Module Error Handler] Error report:', {
                module: moduleName,
                error: error.message,
                timestamp: Date.now(),
                userAgent: navigator.userAgent
            });
        },

        /**
         * Get error statistics
         * @returns {Object} Error statistics
         */
        getStats: function() {
            return {
                totalErrors: this.errorCount,
                moduleErrors: Object.keys(this.errors).map(module => ({
                    module,
                    count: this.errors[module].length
                })),
                errors: this.errors
            };
        },

        /**
         * Clear errors for a module
         * @param {string} moduleName - Module name
         */
        clearErrors: function(moduleName) {
            if (moduleName) {
                delete this.errors[moduleName];
            } else {
                this.errors = {};
                this.errorCount = 0;
            }
        },

        /**
         * Render module with automatic error handling
         * @param {Object} options - Rendering options
         * @returns {boolean} Success status
         */
        renderModule: function(options) {
            const {
                moduleName,
                containerId,
                data,
                renderFn,
                fallbackMessage
            } = options;

            const container = document.getElementById(containerId);
            if (!container) {
                console.warn(`[Module Error Handler] Container not found: ${containerId}`);
                return false;
            }

            // Check data status
            if (!data) {
                this.renderNoDataState(container, moduleName, fallbackMessage || '無數據');
                return false;
            }

            if (data.status === 'skipped') {
                this.renderSkippedState(container, moduleName, data.reason || fallbackMessage);
                return false;
            }

            if (data.status === 'error') {
                this.renderErrorState(container, moduleName, new Error(data.error || 'Unknown error'), data);
                return false;
            }

            // Render with error handling
            return this.safeRender(renderFn, moduleName, container, data);
        }
    };

    // Expose to global scope
    window.ModuleErrorHandler = ModuleErrorHandler;

})();
