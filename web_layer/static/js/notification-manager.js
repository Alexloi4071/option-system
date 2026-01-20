/**
 * Notification Manager
 * Handles toast notifications, loading spinners, and clipboard confirmations
 * Requirements: 11.2, 11.3, 11.4, 11.5
 * 
 * @module NotificationManager
 */

(function(global) {
  'use strict';

  // Default configuration
  const DEFAULT_CONFIG = {
    position: 'top-right',
    autoDismiss: true,
    dismissTimeout: 5000,
    maxToasts: 5,
    animationDuration: 300,
    spinnerThreshold: 500, // Show spinner after 500ms
    clipboardConfirmDuration: 2000
  };

  // Toast types with their icons
  const TOAST_TYPES = {
    success: {
      icon: 'fa-check-circle',
      className: 'toast-success'
    },
    error: {
      icon: 'fa-exclamation-circle',
      className: 'toast-error'
    },
    warning: {
      icon: 'fa-exclamation-triangle',
      className: 'toast-warning'
    },
    info: {
      icon: 'fa-info-circle',
      className: 'toast-info'
    }
  };

  /**
   * NotificationManager class
   * Manages toast notifications, loading spinners, and clipboard confirmations
   */
  class NotificationManager {
    /**
     * Create a NotificationManager instance
     * @param {Object} options - Configuration options
     */
    constructor(options = {}) {
      this.config = { ...DEFAULT_CONFIG, ...options };
      this.toasts = [];
      this.toastIdCounter = 0;
      this.container = null;
      this.spinnerContainer = null;
      this.activeSpinners = new Map();
      this.reducedMotion = this._detectReducedMotion();
      
      // Initialize container when DOM is ready
      if (typeof document !== 'undefined') {
        if (document.readyState === 'loading') {
          document.addEventListener('DOMContentLoaded', () => this._initContainer());
        } else {
          this._initContainer();
        }
      }
    }

    /**
     * Detect if user prefers reduced motion
     * @private
     * @returns {boolean}
     */
    _detectReducedMotion() {
      if (typeof window !== 'undefined' && window.matchMedia) {
        return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      }
      return false;
    }

    /**
     * Initialize the toast container
     * @private
     */
    _initContainer() {
      // Create toast container if it doesn't exist
      this.container = document.querySelector('.toast-container');
      if (!this.container) {
        this.container = document.createElement('div');
        this.container.className = `toast-container toast-${this.config.position}`;
        this.container.setAttribute('role', 'alert');
        this.container.setAttribute('aria-live', 'polite');
        this.container.setAttribute('aria-atomic', 'true');
        document.body.appendChild(this.container);
      }
      
      // Create spinner container if it doesn't exist
      this.spinnerContainer = document.querySelector('.spinner-overlay');
      if (!this.spinnerContainer) {
        this.spinnerContainer = document.createElement('div');
        this.spinnerContainer.className = 'spinner-overlay';
        this.spinnerContainer.setAttribute('role', 'status');
        this.spinnerContainer.setAttribute('aria-live', 'polite');
        this.spinnerContainer.style.display = 'none';
        document.body.appendChild(this.spinnerContainer);
      }
    }

    /**
     * Show a toast notification
     * @param {Object} options - Toast options
     * @param {string} options.type - Toast type (success, error, warning, info)
     * @param {string} options.title - Toast title
     * @param {string} [options.message] - Toast message
     * @param {number} [options.duration] - Auto-dismiss duration in ms
     * @param {boolean} [options.dismissible] - Whether toast can be dismissed
     * @param {Array} [options.actions] - Action buttons
     * @returns {number} Toast ID
     */
    show(options) {
      const {
        type = 'info',
        title,
        message = '',
        duration = this.config.dismissTimeout,
        dismissible = true,
        actions = []
      } = options;

      if (!title) {
        console.warn('NotificationManager: Toast title is required');
        return -1;
      }

      const id = ++this.toastIdCounter;
      const typeConfig = TOAST_TYPES[type] || TOAST_TYPES.info;
      
      // Create toast element
      const toast = this._createToastElement({
        id,
        type,
        typeConfig,
        title,
        message,
        dismissible,
        actions
      });

      // Add to container
      if (this.container) {
        this.container.appendChild(toast);
      }

      // Track toast
      const toastData = {
        id,
        element: toast,
        type,
        title,
        message,
        timestamp: Date.now(),
        timeoutId: null
      };
      this.toasts.push(toastData);

      // Trigger entrance animation
      if (typeof requestAnimationFrame !== 'undefined') {
        requestAnimationFrame(() => {
          toast.classList.add('toast-visible');
        });
      } else {
        // Fallback for environments without requestAnimationFrame
        setTimeout(() => {
          toast.classList.add('toast-visible');
        }, 0);
      }

      // Set up auto-dismiss
      if (this.config.autoDismiss && duration > 0) {
        toastData.timeoutId = setTimeout(() => {
          this.dismiss(id);
        }, duration);
      }

      // Enforce max toasts limit
      this._enforceMaxToasts();

      // Dispatch event
      this._dispatchEvent('toast:show', { id, type, title, message });

      return id;
    }

    /**
     * Show a success toast
     * @param {string} title - Toast title
     * @param {string} [message] - Toast message
     * @param {Object} [options] - Additional options
     * @returns {number} Toast ID
     */
    success(title, message = '', options = {}) {
      return this.show({ ...options, type: 'success', title, message });
    }

    /**
     * Show an error toast
     * @param {string} title - Toast title
     * @param {string} [message] - Toast message with suggested actions
     * @param {Object} [options] - Additional options
     * @returns {number} Toast ID
     */
    error(title, message = '', options = {}) {
      // Error toasts stay longer by default
      const duration = options.duration || this.config.dismissTimeout * 2;
      return this.show({ ...options, type: 'error', title, message, duration });
    }

    /**
     * Show a warning toast
     * @param {string} title - Toast title
     * @param {string} [message] - Toast message
     * @param {Object} [options] - Additional options
     * @returns {number} Toast ID
     */
    warning(title, message = '', options = {}) {
      return this.show({ ...options, type: 'warning', title, message });
    }

    /**
     * Show an info toast
     * @param {string} title - Toast title
     * @param {string} [message] - Toast message
     * @param {Object} [options] - Additional options
     * @returns {number} Toast ID
     */
    info(title, message = '', options = {}) {
      return this.show({ ...options, type: 'info', title, message });
    }

    /**
     * Dismiss a toast by ID
     * @param {number} id - Toast ID
     */
    dismiss(id) {
      const index = this.toasts.findIndex(t => t.id === id);
      if (index === -1) return;

      const toastData = this.toasts[index];
      
      // Clear timeout if exists
      if (toastData.timeoutId) {
        clearTimeout(toastData.timeoutId);
      }

      // Animate out
      toastData.element.classList.remove('toast-visible');
      toastData.element.classList.add('toast-hiding');

      // Remove after animation
      const animDuration = this.reducedMotion ? 0 : this.config.animationDuration;
      setTimeout(() => {
        if (toastData.element.parentNode) {
          toastData.element.parentNode.removeChild(toastData.element);
        }
        this.toasts.splice(index, 1);
        this._dispatchEvent('toast:dismiss', { id });
      }, animDuration);
    }

    /**
     * Dismiss all toasts
     */
    dismissAll() {
      [...this.toasts].forEach(toast => this.dismiss(toast.id));
    }

    /**
     * Get all active toasts
     * @returns {Array} Array of toast data
     */
    getActiveToasts() {
      return this.toasts.map(t => ({
        id: t.id,
        type: t.type,
        title: t.title,
        message: t.message,
        timestamp: t.timestamp
      }));
    }

    /**
     * Show a loading spinner for an action
     * @param {string} actionId - Unique identifier for the action
     * @param {string} [message] - Loading message
     * @returns {Function} Function to hide the spinner
     */
    showSpinner(actionId, message = '載入中...') {
      const startTime = Date.now();
      let spinnerShown = false;
      let spinnerElement = null;

      // Create spinner element
      const createSpinner = () => {
        spinnerElement = document.createElement('div');
        spinnerElement.className = 'loading-spinner-wrapper';
        spinnerElement.setAttribute('data-action-id', actionId);
        spinnerElement.innerHTML = `
          <div class="loading-spinner">
            <div class="spinner-circle"></div>
          </div>
          <div class="spinner-message">${this._escapeHtml(message)}</div>
        `;
        return spinnerElement;
      };

      // Show spinner after threshold
      const timeoutId = setTimeout(() => {
        if (!spinnerShown) {
          spinnerShown = true;
          spinnerElement = createSpinner();
          if (this.spinnerContainer) {
            this.spinnerContainer.appendChild(spinnerElement);
            this.spinnerContainer.style.display = 'flex';
          }
          this._dispatchEvent('spinner:show', { actionId, message });
        }
      }, this.config.spinnerThreshold);

      // Track spinner
      this.activeSpinners.set(actionId, {
        timeoutId,
        startTime,
        spinnerShown: () => spinnerShown,
        element: () => spinnerElement
      });

      // Return hide function
      return () => this.hideSpinner(actionId);
    }

    /**
     * Hide a loading spinner
     * @param {string} actionId - Action identifier
     */
    hideSpinner(actionId) {
      const spinnerData = this.activeSpinners.get(actionId);
      if (!spinnerData) return;

      // Clear timeout if spinner hasn't shown yet
      clearTimeout(spinnerData.timeoutId);

      // Remove spinner element if it was shown
      const element = spinnerData.element();
      if (element && element.parentNode) {
        element.parentNode.removeChild(element);
      }

      // Hide container if no more spinners
      this.activeSpinners.delete(actionId);
      if (this.activeSpinners.size === 0 && this.spinnerContainer) {
        this.spinnerContainer.style.display = 'none';
      }

      this._dispatchEvent('spinner:hide', { actionId });
    }

    /**
     * Check if a spinner is currently shown for an action
     * @param {string} actionId - Action identifier
     * @returns {boolean}
     */
    isSpinnerShown(actionId) {
      const spinnerData = this.activeSpinners.get(actionId);
      return spinnerData ? spinnerData.spinnerShown() : false;
    }

    /**
     * Show clipboard copy confirmation
     * @param {HTMLElement} targetElement - Element to show tooltip near
     * @param {string} [message] - Confirmation message
     */
    showClipboardConfirmation(targetElement, message = '已複製!') {
      if (!targetElement) return;

      // Create tooltip element
      const tooltip = document.createElement('div');
      tooltip.className = 'clipboard-tooltip';
      tooltip.textContent = message;
      tooltip.setAttribute('role', 'status');
      tooltip.setAttribute('aria-live', 'polite');

      // Position tooltip
      const rect = targetElement.getBoundingClientRect();
      tooltip.style.position = 'fixed';
      tooltip.style.top = `${rect.top - 8}px`;
      tooltip.style.left = `${rect.left + rect.width / 2}px`;
      tooltip.style.transform = 'translate(-50%, -100%)';

      document.body.appendChild(tooltip);

      // Animate in
      if (typeof requestAnimationFrame !== 'undefined') {
        requestAnimationFrame(() => {
          tooltip.classList.add('clipboard-tooltip-visible');
        });
      } else {
        setTimeout(() => {
          tooltip.classList.add('clipboard-tooltip-visible');
        }, 0);
      }

      // Auto-hide after duration
      setTimeout(() => {
        tooltip.classList.remove('clipboard-tooltip-visible');
        tooltip.classList.add('clipboard-tooltip-hiding');
        
        setTimeout(() => {
          if (tooltip.parentNode) {
            tooltip.parentNode.removeChild(tooltip);
          }
        }, this.reducedMotion ? 0 : 200);
      }, this.config.clipboardConfirmDuration);

      this._dispatchEvent('clipboard:confirm', { message });
    }

    /**
     * Copy text to clipboard and show confirmation
     * @param {string} text - Text to copy
     * @param {HTMLElement} [targetElement] - Element to show tooltip near
     * @returns {Promise<boolean>} Whether copy was successful
     */
    async copyToClipboard(text, targetElement = null) {
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(text);
        } else {
          // Fallback for older browsers
          const textarea = document.createElement('textarea');
          textarea.value = text;
          textarea.style.position = 'fixed';
          textarea.style.opacity = '0';
          document.body.appendChild(textarea);
          textarea.select();
          document.execCommand('copy');
          document.body.removeChild(textarea);
        }

        if (targetElement) {
          this.showClipboardConfirmation(targetElement);
        }

        return true;
      } catch (error) {
        console.error('Failed to copy to clipboard:', error);
        this.error('複製失敗', '無法複製到剪貼板');
        return false;
      }
    }

    // ========================================================================
    // PRIVATE METHODS
    // ========================================================================

    /**
     * Create a toast DOM element
     * @private
     */
    _createToastElement({ id, type, typeConfig, title, message, dismissible, actions }) {
      const toast = document.createElement('div');
      toast.className = `toast ${typeConfig.className}`;
      toast.setAttribute('data-toast-id', String(id));
      toast.setAttribute('role', 'alert');

      // Icon
      const iconDiv = document.createElement('div');
      iconDiv.className = 'toast-icon';
      iconDiv.innerHTML = `<i class="fas ${typeConfig.icon}"></i>`;
      toast.appendChild(iconDiv);

      // Content
      const contentDiv = document.createElement('div');
      contentDiv.className = 'toast-content';

      const titleDiv = document.createElement('div');
      titleDiv.className = 'toast-title';
      titleDiv.textContent = title;
      contentDiv.appendChild(titleDiv);

      if (message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'toast-message';
        messageDiv.textContent = message;
        contentDiv.appendChild(messageDiv);
      }

      // Actions
      if (actions && actions.length > 0) {
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'toast-actions';
        
        actions.forEach(action => {
          const btn = document.createElement('button');
          btn.className = 'toast-action-btn';
          btn.textContent = action.label;
          btn.addEventListener('click', () => {
            if (action.onClick) action.onClick();
            if (action.dismissOnClick !== false) this.dismiss(id);
          });
          actionsDiv.appendChild(btn);
        });
        
        contentDiv.appendChild(actionsDiv);
      }

      toast.appendChild(contentDiv);

      // Close button
      if (dismissible) {
        const closeBtn = document.createElement('button');
        closeBtn.className = 'toast-close';
        closeBtn.setAttribute('aria-label', '關閉通知');
        closeBtn.innerHTML = '<i class="fas fa-times"></i>';
        closeBtn.addEventListener('click', () => this.dismiss(id));
        toast.appendChild(closeBtn);
      }

      return toast;
    }

    /**
     * Enforce maximum number of toasts
     * @private
     */
    _enforceMaxToasts() {
      while (this.toasts.length > this.config.maxToasts) {
        const oldest = this.toasts[0];
        this.dismiss(oldest.id);
      }
    }

    /**
     * Escape HTML to prevent XSS
     * @private
     */
    _escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    /**
     * Dispatch a custom event
     * @private
     */
    _dispatchEvent(eventName, detail) {
      if (typeof document !== 'undefined') {
        const event = new CustomEvent(eventName, { detail });
        document.dispatchEvent(event);
      }
    }

    /**
     * Set the toast container (for testing)
     * @param {HTMLElement} container - Container element
     */
    setContainer(container) {
      this.container = container;
    }

    /**
     * Set the spinner container (for testing)
     * @param {HTMLElement} container - Container element
     */
    setSpinnerContainer(container) {
      this.spinnerContainer = container;
    }

    /**
     * Update configuration
     * @param {Object} options - New configuration options
     */
    configure(options) {
      this.config = { ...this.config, ...options };
    }
  }

  // Create global instance
  let notificationManager;
  if (typeof document !== 'undefined') {
    notificationManager = new NotificationManager();
  }

  // Export for different module systems
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = NotificationManager;
  } else if (typeof global !== 'undefined') {
    global.NotificationManager = NotificationManager;
    global.notificationManager = notificationManager;
  }

})(typeof window !== 'undefined' ? window : global);
