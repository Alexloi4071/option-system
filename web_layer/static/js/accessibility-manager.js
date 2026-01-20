/**
 * Accessibility Manager
 * Manages keyboard navigation, focus management, and ARIA attributes
 */

class AccessibilityManager {
  constructor() {
    this.focusableSelectors = [
      'a[href]',
      'button:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      '[tabindex]:not([tabindex="-1"])',
      '[role="button"]:not([disabled])',
      '[role="link"]',
      '[role="tab"]',
      '[role="menuitem"]'
    ].join(',');
    
    this.init();
  }

  init() {
    this.ensureFocusableElements();
    this.setupKeyboardShortcuts();
    this.setupFocusTrap();
    this.addSkipToContent();
    this.addKeyboardShortcutHelp();
  }

  /**
   * Ensure all interactive elements are keyboard accessible
   */
  ensureFocusableElements() {
    // Find all interactive elements
    const interactiveElements = document.querySelectorAll(
      'button, a, input, select, textarea, [role="button"], [role="link"]'
    );

    interactiveElements.forEach(element => {
      // Ensure element can receive focus
      if (!element.hasAttribute('tabindex') && element.getAttribute('tabindex') !== '-1') {
        // Element is naturally focusable or should be
        if (element.disabled) {
          element.setAttribute('tabindex', '-1');
        }
      }

      // Add ARIA labels to icon-only buttons
      if (element.tagName === 'BUTTON' && !element.textContent.trim()) {
        if (!element.hasAttribute('aria-label') && !element.hasAttribute('aria-labelledby')) {
          // Try to infer label from icon or context
          const icon = element.querySelector('i, svg');
          if (icon) {
            const iconClass = icon.className;
            const label = this.inferLabelFromIcon(iconClass);
            if (label) {
              element.setAttribute('aria-label', label);
            }
          }
        }
      }
    });
  }

  /**
   * Infer ARIA label from icon class
   */
  inferLabelFromIcon(iconClass) {
    const iconMap = {
      'fa-moon': 'Toggle dark mode',
      'fa-sun': 'Toggle light mode',
      'fa-cog': 'Settings',
      'fa-settings': 'Settings',
      'fa-expand': 'Expand',
      'fa-compress': 'Collapse',
      'fa-times': 'Close',
      'fa-close': 'Close',
      'fa-copy': 'Copy to clipboard',
      'fa-download': 'Download',
      'fa-upload': 'Upload',
      'fa-refresh': 'Refresh',
      'fa-search': 'Search',
      'fa-filter': 'Filter',
      'fa-sort': 'Sort',
      'fa-info': 'Information',
      'fa-question': 'Help',
      'fa-exclamation': 'Warning',
      'fa-check': 'Success',
      'fa-arrow-up': 'Increase',
      'fa-arrow-down': 'Decrease',
      'fa-chevron-up': 'Collapse',
      'fa-chevron-down': 'Expand',
      'fa-chevron-left': 'Previous',
      'fa-chevron-right': 'Next'
    };

    for (const [iconKey, label] of Object.entries(iconMap)) {
      if (iconClass.includes(iconKey)) {
        return label;
      }
    }

    return null;
  }

  /**
   * Setup keyboard shortcuts
   */
  setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      // ? key: Show keyboard shortcuts help
      if (e.key === '?' && !this.isInputFocused()) {
        e.preventDefault();
        this.showKeyboardShortcutHelp();
      }

      // Alt + T: Toggle theme
      if (e.altKey && e.key === 't') {
        e.preventDefault();
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
          themeToggle.click();
          this.announceToScreenReader('Theme toggled');
        }
      }

      // Alt + S: Focus search/ticker input
      if (e.altKey && e.key === 's') {
        e.preventDefault();
        const tickerInput = document.getElementById('ticker');
        if (tickerInput) {
          tickerInput.focus();
          tickerInput.select();
          this.announceToScreenReader('Ticker input focused');
        }
      }

      // Alt + R: Run analysis (submit form)
      if (e.altKey && e.key === 'r') {
        e.preventDefault();
        const analyzeButton = document.getElementById('analyzeButton') || 
                             document.querySelector('button[type="submit"]');
        if (analyzeButton && !analyzeButton.disabled) {
          analyzeButton.click();
          this.announceToScreenReader('Analysis started');
        }
      }

      // Alt + C: Clear form
      if (e.altKey && e.key === 'c') {
        e.preventDefault();
        const clearButton = document.getElementById('clearButton') ||
                           document.querySelector('button[type="reset"]');
        if (clearButton) {
          clearButton.click();
          this.announceToScreenReader('Form cleared');
        }
      }

      // Alt + D: Download results
      if (e.altKey && e.key === 'd') {
        e.preventDefault();
        const downloadButton = document.getElementById('downloadButton') ||
                              document.querySelector('[data-action="download"]');
        if (downloadButton) {
          downloadButton.click();
          this.announceToScreenReader('Download started');
        }
      }

      // Alt + 1-9: Jump to module section
      if (e.altKey && e.key >= '1' && e.key <= '9') {
        e.preventDefault();
        const moduleNumber = parseInt(e.key);
        this.jumpToModule(moduleNumber);
      }

      // Ctrl/Cmd + K: Command palette (future feature)
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        // Placeholder for command palette
        this.announceToScreenReader('Command palette - coming soon');
      }

      // Escape: Close modals/dialogs
      if (e.key === 'Escape') {
        // First check if keyboard help is open
        const helpOverlay = document.getElementById('keyboard-shortcut-help');
        if (helpOverlay && !helpOverlay.classList.contains('d-none')) {
          this.hideKeyboardShortcutHelp();
          return;
        }

        // Then check for modals
        const openModal = document.querySelector('.modal.show, .dialog.show');
        if (openModal) {
          const closeButton = openModal.querySelector('[data-dismiss="modal"], .modal-close');
          if (closeButton) {
            closeButton.click();
          }
        }

        // Close any open dropdowns
        const openDropdown = document.querySelector('.dropdown.show');
        if (openDropdown) {
          openDropdown.classList.remove('show');
        }
      }

      // Arrow keys for table navigation
      if (e.target.tagName === 'TD' || e.target.tagName === 'TR') {
        this.handleTableNavigation(e);
      }

      // Home/End keys for navigation
      if (e.key === 'Home' && !this.isInputFocused()) {
        e.preventDefault();
        window.scrollTo({ top: 0, behavior: 'smooth' });
        this.announceToScreenReader('Scrolled to top');
      }

      if (e.key === 'End' && !this.isInputFocused()) {
        e.preventDefault();
        window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
        this.announceToScreenReader('Scrolled to bottom');
      }
    });
  }

  /**
   * Check if an input element is currently focused
   */
  isInputFocused() {
    const activeElement = document.activeElement;
    return activeElement && (
      activeElement.tagName === 'INPUT' ||
      activeElement.tagName === 'TEXTAREA' ||
      activeElement.tagName === 'SELECT' ||
      activeElement.isContentEditable
    );
  }

  /**
   * Handle keyboard navigation in tables
   */
  handleTableNavigation(e) {
    const cell = e.target.closest('td');
    if (!cell) return;

    const row = cell.parentElement;
    const table = row.closest('table');
    const cells = Array.from(row.cells);
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    
    const cellIndex = cells.indexOf(cell);
    const rowIndex = rows.indexOf(row);

    let targetCell = null;

    switch (e.key) {
      case 'ArrowLeft':
        if (cellIndex > 0) {
          targetCell = cells[cellIndex - 1];
        }
        break;
      case 'ArrowRight':
        if (cellIndex < cells.length - 1) {
          targetCell = cells[cellIndex + 1];
        }
        break;
      case 'ArrowUp':
        if (rowIndex > 0) {
          targetCell = rows[rowIndex - 1].cells[cellIndex];
        }
        break;
      case 'ArrowDown':
        if (rowIndex < rows.length - 1) {
          targetCell = rows[rowIndex + 1].cells[cellIndex];
        }
        break;
    }

    if (targetCell) {
      e.preventDefault();
      targetCell.focus();
      targetCell.setAttribute('tabindex', '0');
    }
  }

  /**
   * Setup focus trap for modals
   */
  setupFocusTrap() {
    // Observe for modal/dialog elements
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === 1 && (node.classList?.contains('modal') || node.classList?.contains('dialog'))) {
            this.trapFocus(node);
          }
        });
      });
    });

    observer.observe(document.body, { childList: true, subtree: true });
  }

  /**
   * Trap focus within a container (for modals/dialogs)
   */
  trapFocus(container) {
    const focusableElements = container.querySelectorAll(this.focusableSelectors);
    if (focusableElements.length === 0) return;

    const firstFocusable = focusableElements[0];
    const lastFocusable = focusableElements[focusableElements.length - 1];

    // Mark for focus trap
    firstFocusable.setAttribute('data-focus-trap-first', '');
    lastFocusable.setAttribute('data-focus-trap-last', '');

    // Focus first element
    firstFocusable.focus();

    // Handle tab key
    container.addEventListener('keydown', (e) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        // Shift + Tab
        if (document.activeElement === firstFocusable) {
          e.preventDefault();
          lastFocusable.focus();
        }
      } else {
        // Tab
        if (document.activeElement === lastFocusable) {
          e.preventDefault();
          firstFocusable.focus();
        }
      }
    });
  }

  /**
   * Add skip to content link
   */
  addSkipToContent() {
    const skipLink = document.createElement('a');
    skipLink.href = '#main-content';
    skipLink.className = 'skip-to-content';
    skipLink.textContent = 'Skip to main content';
    
    skipLink.addEventListener('click', (e) => {
      e.preventDefault();
      const mainContent = document.getElementById('main-content');
      if (mainContent) {
        mainContent.setAttribute('tabindex', '-1');
        mainContent.focus();
      }
    });

    document.body.insertBefore(skipLink, document.body.firstChild);
  }

  /**
   * Get all focusable elements in a container
   */
  getFocusableElements(container = document) {
    return Array.from(container.querySelectorAll(this.focusableSelectors));
  }

  /**
   * Check if element is focusable
   */
  isFocusable(element) {
    return element.matches(this.focusableSelectors);
  }

  /**
   * Add ARIA label to element
   */
  addAriaLabel(element, label) {
    if (!element.hasAttribute('aria-label') && !element.hasAttribute('aria-labelledby')) {
      element.setAttribute('aria-label', label);
    }
  }

  /**
   * Add keyboard shortcut help overlay
   */
  addKeyboardShortcutHelp() {
    // Create help overlay
    const helpOverlay = document.createElement('div');
    helpOverlay.id = 'keyboard-shortcut-help';
    helpOverlay.className = 'keyboard-help-overlay d-none';
    helpOverlay.setAttribute('role', 'dialog');
    helpOverlay.setAttribute('aria-labelledby', 'keyboard-help-title');
    helpOverlay.setAttribute('aria-modal', 'true');
    
    helpOverlay.innerHTML = `
      <div class="keyboard-help-content">
        <div class="keyboard-help-header">
          <h2 id="keyboard-help-title">Keyboard Shortcuts</h2>
          <button class="btn-icon keyboard-help-close" aria-label="Close keyboard shortcuts">
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="keyboard-help-body">
          <div class="keyboard-help-section">
            <h3>Navigation</h3>
            <div class="keyboard-shortcut">
              <kbd>Tab</kbd>
              <span>Move forward through elements</span>
            </div>
            <div class="keyboard-shortcut">
              <kbd>Shift</kbd> + <kbd>Tab</kbd>
              <span>Move backward through elements</span>
            </div>
            <div class="keyboard-shortcut">
              <kbd>Home</kbd>
              <span>Scroll to top of page</span>
            </div>
            <div class="keyboard-shortcut">
              <kbd>End</kbd>
              <span>Scroll to bottom of page</span>
            </div>
            <div class="keyboard-shortcut">
              <kbd>Esc</kbd>
              <span>Close modals and dialogs</span>
            </div>
          </div>
          
          <div class="keyboard-help-section">
            <h3>Actions</h3>
            <div class="keyboard-shortcut">
              <kbd>Alt</kbd> + <kbd>T</kbd>
              <span>Toggle light/dark theme</span>
            </div>
            <div class="keyboard-shortcut">
              <kbd>Alt</kbd> + <kbd>S</kbd>
              <span>Focus ticker input</span>
            </div>
            <div class="keyboard-shortcut">
              <kbd>Alt</kbd> + <kbd>R</kbd>
              <span>Run analysis</span>
            </div>
            <div class="keyboard-shortcut">
              <kbd>Alt</kbd> + <kbd>C</kbd>
              <span>Clear form</span>
            </div>
            <div class="keyboard-shortcut">
              <kbd>Alt</kbd> + <kbd>D</kbd>
              <span>Download results</span>
            </div>
            <div class="keyboard-shortcut">
              <kbd>Alt</kbd> + <kbd>1-9</kbd>
              <span>Jump to module section</span>
            </div>
          </div>
          
          <div class="keyboard-help-section">
            <h3>Table Navigation</h3>
            <div class="keyboard-shortcut">
              <kbd>←</kbd> <kbd>→</kbd> <kbd>↑</kbd> <kbd>↓</kbd>
              <span>Navigate table cells</span>
            </div>
          </div>
          
          <div class="keyboard-help-section">
            <h3>Help</h3>
            <div class="keyboard-shortcut">
              <kbd>?</kbd>
              <span>Show this help dialog</span>
            </div>
          </div>
        </div>
        <div class="keyboard-help-footer">
          <p class="text-muted">Press <kbd>Esc</kbd> to close this dialog</p>
        </div>
      </div>
    `;
    
    document.body.appendChild(helpOverlay);
    
    // Add close button handler
    const closeButton = helpOverlay.querySelector('.keyboard-help-close');
    closeButton.addEventListener('click', () => {
      this.hideKeyboardShortcutHelp();
    });
    
    // Close on overlay click
    helpOverlay.addEventListener('click', (e) => {
      if (e.target === helpOverlay) {
        this.hideKeyboardShortcutHelp();
      }
    });
  }

  /**
   * Show keyboard shortcut help overlay
   */
  showKeyboardShortcutHelp() {
    const helpOverlay = document.getElementById('keyboard-shortcut-help');
    if (helpOverlay) {
      helpOverlay.classList.remove('d-none');
      this.trapFocus(helpOverlay);
      this.announceToScreenReader('Keyboard shortcuts help opened');
    }
  }

  /**
   * Hide keyboard shortcut help overlay
   */
  hideKeyboardShortcutHelp() {
    const helpOverlay = document.getElementById('keyboard-shortcut-help');
    if (helpOverlay) {
      helpOverlay.classList.add('d-none');
      this.announceToScreenReader('Keyboard shortcuts help closed');
    }
  }

  /**
   * Jump to a specific module section
   */
  jumpToModule(moduleNumber) {
    // Try different selectors for module sections
    const selectors = [
      `#module-${moduleNumber}`,
      `[data-module="${moduleNumber}"]`,
      `.module-card[data-module="${moduleNumber}"]`,
      `#module${moduleNumber}`
    ];
    
    let moduleElement = null;
    for (const selector of selectors) {
      moduleElement = document.querySelector(selector);
      if (moduleElement) break;
    }
    
    if (moduleElement) {
      moduleElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
      moduleElement.setAttribute('tabindex', '-1');
      moduleElement.focus();
      this.announceToScreenReader(`Jumped to Module ${moduleNumber}`);
    } else {
      this.announceToScreenReader(`Module ${moduleNumber} not found`);
    }
  }

  /**
   * Update ARIA live region
   */
  announceToScreenReader(message, priority = 'polite') {
    let liveRegion = document.getElementById('aria-live-region');
    
    if (!liveRegion) {
      liveRegion = document.createElement('div');
      liveRegion.id = 'aria-live-region';
      liveRegion.className = 'sr-only';
      liveRegion.setAttribute('aria-live', priority);
      liveRegion.setAttribute('aria-atomic', 'true');
      document.body.appendChild(liveRegion);
    }

    // Clear and set new message
    liveRegion.textContent = '';
    setTimeout(() => {
      liveRegion.textContent = message;
    }, 100);
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = AccessibilityManager;
}
