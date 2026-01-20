// web_layer/static/js/virtual-scroller.js
// Virtual Scrolling Implementation for Large Tables
// Requirements: 13.2
// Property 28: Virtual Scrolling for Large Tables

/**
 * VirtualScroller class implements virtual scrolling for tables with > 100 rows
 * Only renders visible rows plus a buffer, dramatically improving performance
 */
class VirtualScroller {
  /**
   * @param {HTMLTableElement} table - The table element to virtualize
   * @param {Object} options - Configuration options
   * @param {number} options.rowHeight - Height of each row in pixels (default: 40)
   * @param {number} options.bufferSize - Number of extra rows to render above/below viewport (default: 10)
   * @param {number} options.threshold - Minimum rows to trigger virtual scrolling (default: 100)
   */
  constructor(table, options = {}) {
    this.table = table;
    this.tbody = table.querySelector('tbody');
    this.thead = table.querySelector('thead');
    
    if (!this.tbody) {
      console.warn('VirtualScroller: Table must have a tbody element');
      return;
    }
    
    // Configuration
    this.rowHeight = options.rowHeight || 40;
    this.bufferSize = options.bufferSize || 10;
    this.threshold = options.threshold || 100;
    
    // State
    this.allRows = [];
    this.visibleStartIndex = 0;
    this.visibleEndIndex = 0;
    this.scrollTop = 0;
    this.containerHeight = 0;
    this.isEnabled = false;
    
    // Container setup
    this.container = null;
    this.spacerTop = null;
    this.spacerBottom = null;
    
    // Bind methods
    this.handleScroll = this.handleScroll.bind(this);
    this.handleResize = this.handleResize.bind(this);
  }
  
  /**
   * Initialize virtual scrolling for the table
   * @param {Array} rows - Array of row data objects
   */
  initialize(rows) {
    if (!rows || rows.length < this.threshold) {
      // Don't enable virtual scrolling for small tables
      this.isEnabled = false;
      return false;
    }
    
    this.allRows = rows;
    this.isEnabled = true;
    
    // Wrap table in scrollable container if not already wrapped
    this.setupContainer();
    
    // Create spacer elements for virtual scrolling
    this.createSpacers();
    
    // Calculate initial visible range
    this.updateVisibleRange();
    
    // Render initial visible rows
    this.renderVisibleRows();
    
    // Attach event listeners
    this.attachListeners();
    
    return true;
  }
  
  /**
   * Setup scrollable container for the table
   */
  setupContainer() {
    // Check if table is already in a container
    const existingContainer = this.table.closest('.table-container');
    
    if (existingContainer) {
      this.container = existingContainer;
    } else {
      // Create new container
      this.container = document.createElement('div');
      this.container.className = 'table-container virtual-scroll-container';
      this.table.parentNode.insertBefore(this.container, this.table);
      this.container.appendChild(this.table);
    }
    
    // Set container height and enable scrolling
    this.container.style.maxHeight = '600px';
    this.container.style.overflowY = 'auto';
    this.container.style.position = 'relative';
    
    // Make table header sticky
    if (this.thead) {
      this.thead.style.position = 'sticky';
      this.thead.style.top = '0';
      this.thead.style.zIndex = '10';
      this.thead.style.backgroundColor = 'var(--color-surface)';
    }
  }
  
  /**
   * Create spacer elements to maintain scroll height
   */
  createSpacers() {
    // Top spacer
    this.spacerTop = document.createElement('tr');
    this.spacerTop.className = 'virtual-scroll-spacer-top';
    this.spacerTop.style.height = '0px';
    
    // Bottom spacer
    this.spacerBottom = document.createElement('tr');
    this.spacerBottom.className = 'virtual-scroll-spacer-bottom';
    this.spacerBottom.style.height = '0px';
    
    // Insert spacers
    this.tbody.insertBefore(this.spacerTop, this.tbody.firstChild);
    this.tbody.appendChild(this.spacerBottom);
  }
  
  /**
   * Calculate which rows should be visible based on scroll position
   */
  updateVisibleRange() {
    this.scrollTop = this.container.scrollTop;
    this.containerHeight = this.container.clientHeight;
    
    // Calculate visible range with buffer
    const startIndex = Math.max(0, Math.floor(this.scrollTop / this.rowHeight) - this.bufferSize);
    const visibleRowCount = Math.ceil(this.containerHeight / this.rowHeight);
    const endIndex = Math.min(
      this.allRows.length,
      startIndex + visibleRowCount + (this.bufferSize * 2)
    );
    
    this.visibleStartIndex = startIndex;
    this.visibleEndIndex = endIndex;
  }
  
  /**
   * Render only the visible rows
   */
  renderVisibleRows() {
    // Clear existing rows (except spacers)
    const existingRows = Array.from(this.tbody.querySelectorAll('tr:not(.virtual-scroll-spacer-top):not(.virtual-scroll-spacer-bottom)'));
    existingRows.forEach(row => row.remove());
    
    // Update spacer heights
    const topSpacerHeight = this.visibleStartIndex * this.rowHeight;
    const bottomSpacerHeight = (this.allRows.length - this.visibleEndIndex) * this.rowHeight;
    
    this.spacerTop.style.height = `${topSpacerHeight}px`;
    this.spacerBottom.style.height = `${bottomSpacerHeight}px`;
    
    // Render visible rows
    const fragment = document.createDocumentFragment();
    
    for (let i = this.visibleStartIndex; i < this.visibleEndIndex; i++) {
      const rowData = this.allRows[i];
      const row = this.createRow(rowData, i);
      fragment.appendChild(row);
    }
    
    // Insert rows after top spacer
    this.tbody.insertBefore(fragment, this.spacerBottom);
  }
  
  /**
   * Create a table row from data
   * This method should be overridden or provided via options
   * @param {Object} rowData - Data for the row
   * @param {number} index - Row index
   * @returns {HTMLTableRowElement}
   */
  createRow(rowData, index) {
    const row = document.createElement('tr');
    row.setAttribute('data-index', index);
    
    // Default implementation - create cells from object properties
    Object.values(rowData).forEach(value => {
      const cell = document.createElement('td');
      cell.textContent = value;
      row.appendChild(cell);
    });
    
    return row;
  }
  
  /**
   * Handle scroll events
   */
  handleScroll() {
    if (!this.isEnabled) return;
    
    // Use requestAnimationFrame for smooth scrolling
    if (this.scrollTimeout) {
      cancelAnimationFrame(this.scrollTimeout);
    }
    
    this.scrollTimeout = requestAnimationFrame(() => {
      const oldStartIndex = this.visibleStartIndex;
      const oldEndIndex = this.visibleEndIndex;
      
      this.updateVisibleRange();
      
      // Only re-render if visible range changed significantly
      if (
        Math.abs(this.visibleStartIndex - oldStartIndex) > this.bufferSize / 2 ||
        Math.abs(this.visibleEndIndex - oldEndIndex) > this.bufferSize / 2
      ) {
        this.renderVisibleRows();
      }
    });
  }
  
  /**
   * Handle window resize events
   */
  handleResize() {
    if (!this.isEnabled) return;
    
    if (this.resizeTimeout) {
      clearTimeout(this.resizeTimeout);
    }
    
    this.resizeTimeout = setTimeout(() => {
      this.updateVisibleRange();
      this.renderVisibleRows();
    }, 150);
  }
  
  /**
   * Attach event listeners
   */
  attachListeners() {
    if (!this.container) return;
    
    this.container.addEventListener('scroll', this.handleScroll, { passive: true });
    window.addEventListener('resize', this.handleResize);
  }
  
  /**
   * Remove event listeners
   */
  detachListeners() {
    if (!this.container) return;
    
    this.container.removeEventListener('scroll', this.handleScroll);
    window.removeEventListener('resize', this.handleResize);
  }
  
  /**
   * Update the data and re-render
   * @param {Array} rows - New array of row data
   */
  update(rows) {
    this.allRows = rows;
    
    if (rows.length < this.threshold) {
      this.disable();
      return;
    }
    
    if (!this.isEnabled) {
      this.initialize(rows);
    } else {
      this.updateVisibleRange();
      this.renderVisibleRows();
    }
  }
  
  /**
   * Disable virtual scrolling and show all rows
   */
  disable() {
    if (!this.isEnabled) return;
    
    this.isEnabled = false;
    this.detachListeners();
    
    // Remove spacers
    if (this.spacerTop && this.spacerTop.parentNode) {
      this.spacerTop.remove();
    }
    if (this.spacerBottom && this.spacerBottom.parentNode) {
      this.spacerBottom.remove();
    }
    
    // Reset container styles
    if (this.container) {
      this.container.style.maxHeight = '';
    }
  }
  
  /**
   * Destroy the virtual scroller and clean up
   */
  destroy() {
    this.disable();
    this.allRows = [];
    this.container = null;
    this.spacerTop = null;
    this.spacerBottom = null;
  }
  
  /**
   * Get current state information
   * @returns {Object} State information
   */
  getState() {
    return {
      isEnabled: this.isEnabled,
      totalRows: this.allRows.length,
      visibleRows: this.visibleEndIndex - this.visibleStartIndex,
      visibleStartIndex: this.visibleStartIndex,
      visibleEndIndex: this.visibleEndIndex,
      scrollTop: this.scrollTop,
      containerHeight: this.containerHeight
    };
  }
}

/**
 * Helper function to create a virtual scroller for a table
 * @param {string|HTMLTableElement} tableSelector - Table selector or element
 * @param {Array} rows - Array of row data
 * @param {Function} rowRenderer - Function to render a row from data
 * @param {Object} options - Virtual scroller options
 * @returns {VirtualScroller|null}
 */
function createVirtualScroller(tableSelector, rows, rowRenderer, options = {}) {
  const table = typeof tableSelector === 'string' 
    ? document.querySelector(tableSelector)
    : tableSelector;
  
  if (!table) {
    console.warn('VirtualScroller: Table not found');
    return null;
  }
  
  const scroller = new VirtualScroller(table, options);
  
  // Override createRow method with custom renderer
  if (rowRenderer && typeof rowRenderer === 'function') {
    scroller.createRow = rowRenderer;
  }
  
  // Initialize with data
  const initialized = scroller.initialize(rows);
  
  if (!initialized) {
    console.log(`VirtualScroller: Table has ${rows.length} rows (threshold: ${scroller.threshold}), virtual scrolling not enabled`);
  } else {
    console.log(`VirtualScroller: Enabled for table with ${rows.length} rows`);
  }
  
  return scroller;
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { VirtualScroller, createVirtualScroller };
}

// Make available globally
window.VirtualScroller = VirtualScroller;
window.createVirtualScroller = createVirtualScroller;
