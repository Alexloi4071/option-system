// tests/virtual-scrolling.test.js
// Feature: modern-ui-redesign
// Property-Based Tests for Virtual Scrolling
// Property 28: Virtual Scrolling for Large Tables
// Validates: Requirements 13.2

const { test, describe, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const fc = require('fast-check');
const { JSDOM } = require('jsdom');

// Setup DOM environment
function setupDOM() {
  const dom = new JSDOM(`
    <!DOCTYPE html>
    <html>
      <head>
        <style>
          :root {
            --color-surface: #ffffff;
            --color-border-light: #f1f5f9;
            --color-text-tertiary: #94a3b8;
            --color-text-secondary: #64748b;
            --color-primary: #2563eb;
            --radius-full: 9999px;
            --spacing-3: 0.75rem;
            --spacing-4: 1rem;
            --font-size-sm: 0.875rem;
            --color-text-primary: #0f172a;
            --color-border: #e2e8f0;
            --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
            --font-family-mono: 'SF Mono', Monaco, monospace;
            --font-weight-semibold: 600;
            --radius-sm: 0.375rem;
          }
          
          .table-container {
            width: 100%;
            overflow-x: auto;
          }
          
          .table-modern {
            width: 100%;
            border-collapse: collapse;
          }
          
          .virtual-scroll-container {
            position: relative;
            overflow-y: auto;
            max-height: 600px;
          }
        </style>
      </head>
      <body>
        <div id="test-container">
          <table class="table-modern" id="test-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </body>
    </html>
  `, {
    url: 'http://localhost',
    pretendToBeVisual: true,
    resources: 'usable'
  });

  global.window = dom.window;
  global.document = dom.window.document;
  global.HTMLElement = dom.window.HTMLElement;
  global.requestAnimationFrame = (cb) => setTimeout(cb, 0);
  global.cancelAnimationFrame = (id) => clearTimeout(id);

  return dom;
}

// Load VirtualScroller class
function loadVirtualScroller() {
  const fs = require('fs');
  const path = require('path');
  const virtualScrollerPath = path.join(__dirname, '../static/js/virtual-scroller.js');
  const code = fs.readFileSync(virtualScrollerPath, 'utf8');
  
  // Execute in global context
  eval(code);
  
  return global.window.VirtualScroller;
}

// Helper to generate test data
function generateTableData(rowCount) {
  const data = [];
  for (let i = 0; i < rowCount; i++) {
    data.push({
      id: i + 1,
      name: `Row ${i + 1}`,
      value: Math.random() * 1000
    });
  }
  return data;
}

// Helper to create row renderer
function createRowRenderer() {
  return function(rowData, index) {
    const row = document.createElement('tr');
    row.setAttribute('data-index', index);
    
    const idCell = document.createElement('td');
    idCell.textContent = rowData.id;
    row.appendChild(idCell);
    
    const nameCell = document.createElement('td');
    nameCell.textContent = rowData.name;
    row.appendChild(nameCell);
    
    const valueCell = document.createElement('td');
    valueCell.textContent = rowData.value.toFixed(2);
    row.appendChild(valueCell);
    
    return row;
  };
}

describe('Virtual Scrolling - Property 28: Virtual Scrolling for Large Tables', () => {
  let dom;
  let VirtualScroller;
  
  beforeEach(() => {
    dom = setupDOM();
    VirtualScroller = loadVirtualScroller();
  });
  
  afterEach(() => {
    if (dom) {
      dom.window.close();
    }
  });
  
  // Property 28: Virtual Scrolling for Large Tables
  // For any table with more than 100 rows, virtual scrolling should be implemented
  // to maintain performance.
  
  test('Feature: modern-ui-redesign, Property 28: Virtual scrolling is enabled for tables with > 100 rows', () => {
    const table = document.getElementById('test-table');
    const data = generateTableData(150);
    
    const scroller = new VirtualScroller(table, {
      rowHeight: 40,
      bufferSize: 10,
      threshold: 100
    });
    
    scroller.createRow = createRowRenderer();
    const initialized = scroller.initialize(data);
    
    assert.strictEqual(initialized, true, 'Virtual scrolling should be enabled for 150 rows');
    assert.strictEqual(scroller.isEnabled, true, 'Scroller should be enabled');
    assert.strictEqual(scroller.allRows.length, 150, 'All rows should be stored');
    
    // Check that spacers were created
    const spacers = table.querySelectorAll('.virtual-scroll-spacer-top, .virtual-scroll-spacer-bottom');
    assert.strictEqual(spacers.length, 2, 'Should have top and bottom spacers');
    
    console.log('✓ Virtual scrolling enabled for table with 150 rows');
  });
  
  test('Feature: modern-ui-redesign, Property 28: Virtual scrolling is NOT enabled for tables with <= 100 rows', () => {
    const table = document.getElementById('test-table');
    const data = generateTableData(50);
    
    const scroller = new VirtualScroller(table, {
      rowHeight: 40,
      bufferSize: 10,
      threshold: 100
    });
    
    scroller.createRow = createRowRenderer();
    const initialized = scroller.initialize(data);
    
    assert.strictEqual(initialized, false, 'Virtual scrolling should NOT be enabled for 50 rows');
    assert.strictEqual(scroller.isEnabled, false, 'Scroller should not be enabled');
    
    console.log('✓ Virtual scrolling not enabled for table with 50 rows');
  });
  
  test('Feature: modern-ui-redesign, Property 28: Only visible rows are rendered initially', () => {
    const table = document.getElementById('test-table');
    const data = generateTableData(200);
    
    const scroller = new VirtualScroller(table, {
      rowHeight: 40,
      bufferSize: 10,
      threshold: 100
    });
    
    scroller.createRow = createRowRenderer();
    scroller.initialize(data);
    
    // Count rendered rows (excluding spacers)
    const renderedRows = table.querySelectorAll('tbody tr:not(.virtual-scroll-spacer-top):not(.virtual-scroll-spacer-bottom)');
    
    // Should render less than total rows
    assert.ok(renderedRows.length < data.length, 
      `Should render fewer rows than total (rendered: ${renderedRows.length}, total: ${data.length})`);
    
    // Should render at least some rows
    assert.ok(renderedRows.length > 0, 'Should render some rows');
    
    console.log(`✓ Rendered ${renderedRows.length} out of ${data.length} rows initially`);
  });
  
  test('Feature: modern-ui-redesign, Property 28: Spacers maintain correct scroll height', () => {
    const table = document.getElementById('test-table');
    const data = generateTableData(200);
    const rowHeight = 40;
    
    const scroller = new VirtualScroller(table, {
      rowHeight: rowHeight,
      bufferSize: 10,
      threshold: 100
    });
    
    scroller.createRow = createRowRenderer();
    scroller.initialize(data);
    
    const topSpacer = table.querySelector('.virtual-scroll-spacer-top');
    const bottomSpacer = table.querySelector('.virtual-scroll-spacer-bottom');
    
    assert.ok(topSpacer, 'Top spacer should exist');
    assert.ok(bottomSpacer, 'Bottom spacer should exist');
    
    // Calculate expected total height from spacers
    const topHeight = parseInt(topSpacer.style.height) || 0;
    const bottomHeight = parseInt(bottomSpacer.style.height) || 0;
    const renderedRows = table.querySelectorAll('tbody tr:not(.virtual-scroll-spacer-top):not(.virtual-scroll-spacer-bottom)').length;
    
    const totalHeight = topHeight + bottomHeight + (renderedRows * rowHeight);
    const expectedHeight = data.length * rowHeight;
    
    // Allow small margin of error
    assert.ok(Math.abs(totalHeight - expectedHeight) < rowHeight * 2,
      `Total height should approximate expected height (total: ${totalHeight}, expected: ${expectedHeight})`);
    
    console.log(`✓ Spacers maintain scroll height: ${totalHeight}px (expected: ${expectedHeight}px)`);
  });
  
  test('Feature: modern-ui-redesign, Property 28: Container has scrollable overflow', () => {
    const table = document.getElementById('test-table');
    const data = generateTableData(150);
    
    const scroller = new VirtualScroller(table, {
      rowHeight: 40,
      bufferSize: 10,
      threshold: 100
    });
    
    scroller.createRow = createRowRenderer();
    scroller.initialize(data);
    
    assert.ok(scroller.container, 'Container should exist');
    
    const styles = window.getComputedStyle(scroller.container);
    assert.ok(
      styles.overflowY === 'auto' || styles.overflowY === 'scroll',
      'Container should have vertical scroll'
    );
    
    console.log('✓ Container has scrollable overflow');
  });
  
  test('Feature: modern-ui-redesign, Property 28: Property test - virtual scrolling works for various row counts', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 101, max: 500 }), // Row count > threshold
        (rowCount) => {
          const table = document.getElementById('test-table');
          const data = generateTableData(rowCount);
          
          const scroller = new VirtualScroller(table, {
            rowHeight: 40,
            bufferSize: 10,
            threshold: 100
          });
          
          scroller.createRow = createRowRenderer();
          const initialized = scroller.initialize(data);
          
          // Should be enabled
          if (!initialized || !scroller.isEnabled) {
            return false;
          }
          
          // Should have spacers
          const spacers = table.querySelectorAll('.virtual-scroll-spacer-top, .virtual-scroll-spacer-bottom');
          if (spacers.length !== 2) {
            return false;
          }
          
          // Should render fewer rows than total
          const renderedRows = table.querySelectorAll('tbody tr:not(.virtual-scroll-spacer-top):not(.virtual-scroll-spacer-bottom)');
          if (renderedRows.length >= rowCount) {
            return false;
          }
          
          // Clean up
          scroller.destroy();
          
          return true;
        }
      ),
      { numRuns: 50 }
    );
    
    console.log('✓ Virtual scrolling works correctly for 50 different row counts (101-500)');
  });
  
  test('Feature: modern-ui-redesign, Property 28: Property test - tables below threshold do not enable virtual scrolling', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 99 }), // Row count < threshold (not equal)
        (rowCount) => {
          const table = document.getElementById('test-table');
          const data = generateTableData(rowCount);
          
          const scroller = new VirtualScroller(table, {
            rowHeight: 40,
            bufferSize: 10,
            threshold: 100
          });
          
          scroller.createRow = createRowRenderer();
          const initialized = scroller.initialize(data);
          
          // Should NOT be enabled
          return !initialized && !scroller.isEnabled;
        }
      ),
      { numRuns: 50 }
    );
    
    console.log('✓ Virtual scrolling correctly disabled for 50 different row counts (1-99)');
  });
  
  test('Feature: modern-ui-redesign, Property 28: Update method works correctly', () => {
    const table = document.getElementById('test-table');
    const initialData = generateTableData(150);
    
    const scroller = new VirtualScroller(table, {
      rowHeight: 40,
      bufferSize: 10,
      threshold: 100
    });
    
    scroller.createRow = createRowRenderer();
    scroller.initialize(initialData);
    
    // Update with new data
    const newData = generateTableData(200);
    scroller.update(newData);
    
    assert.strictEqual(scroller.allRows.length, 200, 'Should update to new row count');
    assert.strictEqual(scroller.isEnabled, true, 'Should remain enabled');
    
    // Update with small data (below threshold)
    const smallData = generateTableData(50);
    scroller.update(smallData);
    
    assert.strictEqual(scroller.isEnabled, false, 'Should disable when data is below threshold');
    
    console.log('✓ Update method works correctly');
  });
  
  test('Feature: modern-ui-redesign, Property 28: Destroy method cleans up properly', () => {
    const table = document.getElementById('test-table');
    const data = generateTableData(150);
    
    const scroller = new VirtualScroller(table, {
      rowHeight: 40,
      bufferSize: 10,
      threshold: 100
    });
    
    scroller.createRow = createRowRenderer();
    scroller.initialize(data);
    
    // Destroy
    scroller.destroy();
    
    assert.strictEqual(scroller.isEnabled, false, 'Should be disabled after destroy');
    assert.strictEqual(scroller.allRows.length, 0, 'Should clear all rows');
    
    // Spacers should be removed
    const spacers = table.querySelectorAll('.virtual-scroll-spacer-top, .virtual-scroll-spacer-bottom');
    assert.strictEqual(spacers.length, 0, 'Spacers should be removed');
    
    console.log('✓ Destroy method cleans up properly');
  });
  
  test('Feature: modern-ui-redesign, Property 28: getState returns correct information', () => {
    const table = document.getElementById('test-table');
    const data = generateTableData(150);
    
    const scroller = new VirtualScroller(table, {
      rowHeight: 40,
      bufferSize: 10,
      threshold: 100
    });
    
    scroller.createRow = createRowRenderer();
    scroller.initialize(data);
    
    const state = scroller.getState();
    
    assert.strictEqual(state.isEnabled, true, 'State should show enabled');
    assert.strictEqual(state.totalRows, 150, 'State should show correct total rows');
    assert.ok(state.visibleRows > 0, 'State should show visible rows');
    assert.ok(state.visibleStartIndex >= 0, 'State should have valid start index');
    assert.ok(state.visibleEndIndex > state.visibleStartIndex, 'End index should be greater than start');
    
    console.log(`✓ getState returns correct information: ${JSON.stringify(state)}`);
  });
  
  test('Feature: modern-ui-redesign, Property 28: Custom threshold can be configured', () => {
    const table = document.getElementById('test-table');
    const data = generateTableData(75);
    
    // Custom threshold of 50
    const scroller = new VirtualScroller(table, {
      rowHeight: 40,
      bufferSize: 10,
      threshold: 50
    });
    
    scroller.createRow = createRowRenderer();
    const initialized = scroller.initialize(data);
    
    assert.strictEqual(initialized, true, 'Should be enabled with custom threshold of 50');
    assert.strictEqual(scroller.isEnabled, true, 'Scroller should be enabled');
    
    console.log('✓ Custom threshold (50) works correctly for 75 rows');
  });
});
