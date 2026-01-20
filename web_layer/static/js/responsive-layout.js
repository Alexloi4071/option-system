/**
 * Responsive Layout Controller
 * Handles responsive layout detection, touch target validation, and viewport management
 * Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
 */

class ResponsiveLayoutController {
  constructor() {
    // Breakpoint definitions (must match CSS)
    this.breakpoints = {
      mobile: 0,
      tablet: 768,
      desktop: 1200,
      wide: 1600
    };
    
    // Minimum touch target size (44px per WCAG guidelines)
    this.minTouchTargetSize = 44;
    
    // Current breakpoint
    this.currentBreakpoint = this.getCurrentBreakpoint();
    
    // Bind resize handler
    this.handleResize = this.handleResize.bind(this);
    
    // Initialize if in browser environment
    if (typeof window !== 'undefined') {
      this.init();
    }
  }
  
  /**
   * Initialize the responsive layout controller
   */
  init() {
    // Add resize listener with debounce utility
    // Validates: Requirements 13.4
    const debouncedResize = typeof debounce === 'function' 
      ? debounce(this.handleResize, 100)
      : this.handleResize; // Fallback if debounce not available
    
    window.addEventListener('resize', debouncedResize);
    
    // Set initial breakpoint class on body
    this.updateBodyBreakpointClass();
    
    // Prevent horizontal scrolling
    this.preventHorizontalScroll();
  }
  
  /**
   * Handle window resize events
   */
  handleResize() {
    const newBreakpoint = this.getCurrentBreakpoint();
    
    if (newBreakpoint !== this.currentBreakpoint) {
      const oldBreakpoint = this.currentBreakpoint;
      this.currentBreakpoint = newBreakpoint;
      
      // Update body class
      this.updateBodyBreakpointClass();
      
      // Dispatch custom event for breakpoint change
      if (typeof window !== 'undefined' && typeof CustomEvent !== 'undefined') {
        window.dispatchEvent(new CustomEvent('breakpointChange', {
          detail: {
            from: oldBreakpoint,
            to: newBreakpoint,
            width: this.getViewportWidth()
          }
        }));
      }
    }
  }
  
  /**
   * Get current viewport width
   * @returns {number} Viewport width in pixels
   */
  getViewportWidth() {
    if (typeof window !== 'undefined') {
      return window.innerWidth || document.documentElement.clientWidth;
    }
    return 1200; // Default to desktop
  }
  
  /**
   * Get current breakpoint name based on viewport width
   * @returns {string} Breakpoint name ('mobile', 'tablet', 'desktop', 'wide')
   */
  getCurrentBreakpoint() {
    const width = this.getViewportWidth();
    
    if (width >= this.breakpoints.wide) {
      return 'wide';
    } else if (width >= this.breakpoints.desktop) {
      return 'desktop';
    } else if (width >= this.breakpoints.tablet) {
      return 'tablet';
    }
    return 'mobile';
  }
  
  /**
   * Check if current viewport is mobile
   * @returns {boolean}
   */
  isMobile() {
    return this.getViewportWidth() < this.breakpoints.tablet;
  }
  
  /**
   * Check if current viewport is tablet
   * @returns {boolean}
   */
  isTablet() {
    const width = this.getViewportWidth();
    return width >= this.breakpoints.tablet && width < this.breakpoints.desktop;
  }
  
  /**
   * Check if current viewport is desktop
   * @returns {boolean}
   */
  isDesktop() {
    return this.getViewportWidth() >= this.breakpoints.desktop;
  }
  
  /**
   * Check if current viewport is wide
   * @returns {boolean}
   */
  isWide() {
    return this.getViewportWidth() >= this.breakpoints.wide;
  }
  
  /**
   * Update body element with current breakpoint class
   */
  updateBodyBreakpointClass() {
    if (typeof document !== 'undefined') {
      const body = document.body;
      
      // Remove all breakpoint classes
      body.classList.remove('breakpoint-mobile', 'breakpoint-tablet', 'breakpoint-desktop', 'breakpoint-wide');
      
      // Add current breakpoint class
      body.classList.add(`breakpoint-${this.currentBreakpoint}`);
    }
  }
  
  /**
   * Prevent horizontal scrolling on the page
   */
  preventHorizontalScroll() {
    if (typeof document !== 'undefined') {
      document.documentElement.style.overflowX = 'hidden';
      document.body.style.overflowX = 'hidden';
      document.documentElement.style.maxWidth = '100vw';
      document.body.style.maxWidth = '100vw';
    }
  }
  
  /**
   * Get minimum touch target size
   * @returns {number} Minimum touch target size in pixels
   */
  getMinTouchTargetSize() {
    return this.minTouchTargetSize;
  }
  
  /**
   * Check if an element meets minimum touch target size requirements
   * @param {HTMLElement} element - Element to check
   * @returns {boolean} True if element meets minimum size
   */
  meetsMinTouchTargetSize(element) {
    if (!element) return false;
    
    const rect = element.getBoundingClientRect();
    return rect.width >= this.minTouchTargetSize && rect.height >= this.minTouchTargetSize;
  }
  
  /**
   * Validate all interactive elements meet touch target requirements
   * @param {HTMLElement} container - Container to check (defaults to document.body)
   * @returns {Object} Validation result with passing and failing elements
   */
  validateTouchTargets(container) {
    if (typeof document === 'undefined') {
      return { valid: true, passing: [], failing: [] };
    }
    
    const root = container || document.body;
    const interactiveSelectors = 'button, a, input, select, textarea, [role="button"], [tabindex]:not([tabindex="-1"])';
    const elements = root.querySelectorAll(interactiveSelectors);
    
    const passing = [];
    const failing = [];
    
    elements.forEach(element => {
      const rect = element.getBoundingClientRect();
      const meetsSize = rect.width >= this.minTouchTargetSize && rect.height >= this.minTouchTargetSize;
      
      const result = {
        element,
        width: rect.width,
        height: rect.height,
        meetsMinSize: meetsSize
      };
      
      if (meetsSize) {
        passing.push(result);
      } else {
        failing.push(result);
      }
    });
    
    return {
      valid: failing.length === 0,
      passing,
      failing,
      minSize: this.minTouchTargetSize
    };
  }
  
  /**
   * Apply touch-friendly sizing to interactive elements on mobile
   * @param {HTMLElement} container - Container to process
   */
  applyMobileTouchTargets(container) {
    if (!this.isMobile() || typeof document === 'undefined') return;
    
    const root = container || document.body;
    const interactiveSelectors = 'button, a, input, select, textarea, [role="button"]';
    const elements = root.querySelectorAll(interactiveSelectors);
    
    elements.forEach(element => {
      const rect = element.getBoundingClientRect();
      
      // Only adjust if below minimum size
      if (rect.width < this.minTouchTargetSize || rect.height < this.minTouchTargetSize) {
        element.style.minWidth = `${this.minTouchTargetSize}px`;
        element.style.minHeight = `${this.minTouchTargetSize}px`;
      }
    });
  }
  
  /**
   * Check if page has horizontal overflow
   * @returns {boolean} True if page has horizontal scrolling
   */
  hasHorizontalOverflow() {
    if (typeof document === 'undefined') return false;
    
    return document.documentElement.scrollWidth > document.documentElement.clientWidth;
  }
  
  /**
   * Get elements causing horizontal overflow
   * @returns {Array} Array of elements causing overflow
   */
  getOverflowingElements() {
    if (typeof document === 'undefined') return [];
    
    const viewportWidth = this.getViewportWidth();
    const overflowing = [];
    
    const allElements = document.querySelectorAll('*');
    allElements.forEach(element => {
      const rect = element.getBoundingClientRect();
      if (rect.right > viewportWidth || rect.left < 0) {
        overflowing.push({
          element,
          rect,
          overflowRight: rect.right - viewportWidth,
          overflowLeft: -rect.left
        });
      }
    });
    
    return overflowing;
  }
  
  /**
   * Get breakpoint configuration
   * @returns {Object} Breakpoint configuration
   */
  getBreakpoints() {
    return { ...this.breakpoints };
  }
  
  /**
   * Get layout configuration for current breakpoint
   * @returns {Object} Layout configuration
   */
  getLayoutConfig() {
    const breakpoint = this.getCurrentBreakpoint();
    
    const configs = {
      mobile: {
        columns: 1,
        gap: 16,
        containerPadding: 16,
        cardDirection: 'column'
      },
      tablet: {
        columns: 2,
        gap: 24,
        containerPadding: 24,
        cardDirection: 'row'
      },
      desktop: {
        columns: 3,
        gap: 24,
        containerPadding: 32,
        cardDirection: 'row'
      },
      wide: {
        columns: 4,
        gap: 32,
        containerPadding: 32,
        cardDirection: 'row'
      }
    };
    
    return configs[breakpoint];
  }
  
  /**
   * Apply responsive grid to a container
   * @param {HTMLElement} container - Container element
   * @param {Object} options - Grid options
   */
  applyResponsiveGrid(container, options = {}) {
    if (!container) return;
    
    const config = this.getLayoutConfig();
    const columns = options.columns || config.columns;
    const gap = options.gap || config.gap;
    
    container.style.display = 'grid';
    container.style.gridTemplateColumns = `repeat(${columns}, 1fr)`;
    container.style.gap = `${gap}px`;
  }
  
  /**
   * Stack cards vertically on mobile
   * @param {HTMLElement} container - Container with cards
   */
  stackCardsOnMobile(container) {
    if (!container) return;
    
    if (this.isMobile()) {
      container.style.display = 'flex';
      container.style.flexDirection = 'column';
      container.style.gap = 'var(--spacing-4)'; // 16px
    } else {
      // Reset to grid on larger screens
      this.applyResponsiveGrid(container);
    }
  }
}

// Export for both CommonJS and ES modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ResponsiveLayoutController;
} else if (typeof window !== 'undefined') {
  window.ResponsiveLayoutController = ResponsiveLayoutController;
}
