/**
 * CSS Fallback Handler
 * Handles CSS loading failures and provides fallback mechanisms
 * 
 * Features:
 * - Detects CSS loading failures
 * - Provides CDN fallback URLs
 * - Displays warning banner for users
 * - Ensures critical CSS is always available
 */

(function() {
    'use strict';

    const CSSFallbackHandler = {
        // CDN fallback URLs
        fallbacks: {
            bootstrap: [
                'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
                'https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css',
                'https://unpkg.com/bootstrap@5.3.0/dist/css/bootstrap.min.css'
            ],
            fontawesome: [
                'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
                'https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.0.0/css/all.min.css',
                'https://unpkg.com/@fortawesome/fontawesome-free@6.0.0/css/all.min.css'
            ]
        },

        // Track loaded stylesheets
        loadedStylesheets: new Set(),
        failedStylesheets: new Set(),
        warningDisplayed: false,

        /**
         * Initialize CSS fallback handler
         */
        init: function() {
            // Wait for DOM to be ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.checkStylesheets());
            } else {
                this.checkStylesheets();
            }

            // Also check after window load (all resources loaded)
            window.addEventListener('load', () => {
                setTimeout(() => this.verifyStyles(), 1000);
            });
        },

        /**
         * Check all link elements for CSS loading
         */
        checkStylesheets: function() {
            const links = document.querySelectorAll('link[rel="stylesheet"], link[rel="preload"][as="style"]');
            
            links.forEach(link => {
                // Add load event listener
                link.addEventListener('load', () => {
                    this.loadedStylesheets.add(link.href);
                });

                // Add error event listener
                link.addEventListener('error', () => {
                    this.handleStylesheetError(link);
                });

                // Check if already loaded
                if (link.sheet) {
                    this.loadedStylesheets.add(link.href);
                }
            });
        },

        /**
         * Handle stylesheet loading error
         * @param {HTMLLinkElement} link - Failed link element
         */
        handleStylesheetError: function(link) {
            const href = link.href;
            this.failedStylesheets.add(href);

            console.warn(`[CSS Fallback] Failed to load stylesheet: ${href}`);

            // Try to load from fallback CDN
            if (href.includes('bootstrap')) {
                this.loadFallbackCSS('bootstrap', link);
            } else if (href.includes('font-awesome') || href.includes('fontawesome')) {
                this.loadFallbackCSS('fontawesome', link);
            } else if (href.includes('/static/css/main.css')) {
                // Main CSS failed - show warning but continue
                console.error('[CSS Fallback] Main CSS failed to load. Using inline critical CSS only.');
                this.showWarningBanner('部分樣式文件載入失敗，界面可能顯示不完整。');
            }
        },

        /**
         * Load fallback CSS from alternative CDN
         * @param {string} type - Type of CSS (bootstrap, fontawesome)
         * @param {HTMLLinkElement} originalLink - Original failed link
         */
        loadFallbackCSS: function(type, originalLink) {
            const fallbackUrls = this.fallbacks[type];
            if (!fallbackUrls || fallbackUrls.length === 0) {
                return;
            }

            // Find the next fallback URL that hasn't been tried
            const originalUrl = originalLink.href;
            let fallbackIndex = 0;

            // Find which fallback to try
            for (let i = 0; i < fallbackUrls.length; i++) {
                if (originalUrl.includes(new URL(fallbackUrls[i]).hostname)) {
                    fallbackIndex = i + 1;
                    break;
                }
            }

            if (fallbackIndex >= fallbackUrls.length) {
                // All fallbacks exhausted
                console.error(`[CSS Fallback] All fallbacks exhausted for ${type}`);
                this.showWarningBanner('無法載入必要的樣式文件，請檢查網絡連接。');
                return;
            }

            const fallbackUrl = fallbackUrls[fallbackIndex];
            console.log(`[CSS Fallback] Trying fallback for ${type}: ${fallbackUrl}`);

            // Create new link element
            const newLink = document.createElement('link');
            newLink.rel = 'stylesheet';
            newLink.href = fallbackUrl;
            newLink.crossOrigin = 'anonymous';

            // Add load handler
            newLink.addEventListener('load', () => {
                console.log(`[CSS Fallback] Successfully loaded fallback: ${fallbackUrl}`);
                this.loadedStylesheets.add(fallbackUrl);
                // Remove original failed link
                if (originalLink.parentNode) {
                    originalLink.parentNode.removeChild(originalLink);
                }
            });

            // Add error handler for fallback
            newLink.addEventListener('error', () => {
                console.warn(`[CSS Fallback] Fallback also failed: ${fallbackUrl}`);
                this.loadFallbackCSS(type, newLink); // Try next fallback
            });

            // Insert into document
            document.head.appendChild(newLink);
        },

        /**
         * Verify that styles are actually applied
         */
        verifyStyles: function() {
            // Check if Bootstrap is loaded by testing a known Bootstrap class
            const testElement = document.createElement('div');
            testElement.className = 'container';
            testElement.style.display = 'none';
            document.body.appendChild(testElement);

            const computedStyle = window.getComputedStyle(testElement);
            const hasBootstrap = computedStyle.maxWidth !== 'none' && computedStyle.maxWidth !== '';

            document.body.removeChild(testElement);

            if (!hasBootstrap && !this.warningDisplayed) {
                console.warn('[CSS Fallback] Bootstrap styles not detected');
                this.showWarningBanner('樣式載入異常，界面可能顯示不正常。');
            }

            // Check Font Awesome by testing icon rendering
            const iconTest = document.createElement('i');
            iconTest.className = 'fas fa-check';
            iconTest.style.display = 'none';
            document.body.appendChild(iconTest);

            const iconStyle = window.getComputedStyle(iconTest, ':before');
            const hasFontAwesome = iconStyle.fontFamily && iconStyle.fontFamily.includes('Font Awesome');

            document.body.removeChild(iconTest);

            if (!hasFontAwesome && !this.warningDisplayed) {
                console.warn('[CSS Fallback] Font Awesome not detected');
            }
        },

        /**
         * Show warning banner to user
         * @param {string} message - Warning message
         */
        showWarningBanner: function(message) {
            if (this.warningDisplayed) {
                return; // Don't show multiple warnings
            }

            this.warningDisplayed = true;

            const banner = document.createElement('div');
            banner.id = 'css-fallback-warning';
            banner.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                background-color: #fff3cd;
                border-bottom: 2px solid #ffc107;
                color: #856404;
                padding: 12px 20px;
                text-align: center;
                z-index: 9999;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 14px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            `;

            banner.innerHTML = `
                <strong>⚠️ 警告：</strong> ${message}
                <button onclick="this.parentElement.remove()" style="
                    background: none;
                    border: none;
                    color: #856404;
                    font-size: 18px;
                    font-weight: bold;
                    cursor: pointer;
                    float: right;
                    padding: 0;
                    margin-left: 15px;
                ">&times;</button>
            `;

            document.body.insertBefore(banner, document.body.firstChild);

            // Auto-dismiss after 10 seconds
            setTimeout(() => {
                if (banner.parentNode) {
                    banner.style.transition = 'opacity 0.5s';
                    banner.style.opacity = '0';
                    setTimeout(() => banner.remove(), 500);
                }
            }, 10000);
        },

        /**
         * Get loading status report
         * @returns {Object} Status report
         */
        getStatus: function() {
            return {
                loaded: Array.from(this.loadedStylesheets),
                failed: Array.from(this.failedStylesheets),
                warningDisplayed: this.warningDisplayed
            };
        }
    };

    // Auto-initialize
    CSSFallbackHandler.init();

    // Expose to global scope for debugging
    window.CSSFallbackHandler = CSSFallbackHandler;

})();
