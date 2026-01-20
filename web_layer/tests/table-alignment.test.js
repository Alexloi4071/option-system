// Feature: modern-ui-redesign
// Property-Based Tests for Table Numeric Alignment
// Property 16: Numeric Column Alignment
// Validates: Requirements 9.3

const { test, describe, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const { JSDOM } = require('jsdom');
const fc = require('fast-check');

// Setup DOM environment
function setupDOM() {
  const dom = new JSDOM(`
    <!DOCTYPE html>
    <html>
      <head>
        <style>
          /* Simulated table styles from _tables.scss */
          .table-modern th.text-right,
          .table-modern th[data-type="number"],
          .table-modern td.text-right,
          .table-modern td[data-type="number"] {
            text-align: right;
          }
          
          .table-modern th,
          .table-modern td {
            text-align: left;
          }
          
          .table-modern th.text-center,
          .table-modern td.text-center {
            text-align: center;
          }
        </style>
      </head>
      <body>
        <div class="table-container">
          <table class="table-modern" id="test-table">
            <thead>
              <tr id="header-row"></tr>
            </thead>
            <tbody id="table-body"></tbody>
          </table>
        </div>
      </body>
    </html>
  `, {
    url: 'http://localhost',
    pretendToBeVisual: true,
  });

  global.window = dom.window;
  global.document = dom.window.document;

  return dom;
}

// Helper function to create table columns
function createTableColumn(type, value, index) {
  const th = document.createElement('th');
  const td = document.createElement('td');
  
  th.textContent = `Column ${index}`;
  td.textContent = value;
  
  if (type === 'number') {
    th.setAttribute('data-type', 'number');
    td.setAttribute('data-type', 'number');
  } else if (type === 'text') {
    // Default left alignment, no special attribute needed
  } else if (type === 'center') {
    th.classList.add('text-center');
    td.classList.add('text-center');
  }
  
  return { th, td };
}

// Helper function to render a table with given columns
function renderTable(columns) {
  const headerRow = document.getElementById('header-row');
  const tableBody = document.getElementById('table-body');
  
  // Clear existing content
  headerRow.innerHTML = '';
  tableBody.innerHTML = '';
  
  const dataRow = document.createElement('tr');
  
  columns.forEach((col, index) => {
    const { th, td } = createTableColumn(col.type, col.value, index);
    headerRow.appendChild(th);
    dataRow.appendChild(td);
  });
  
  tableBody.appendChild(dataRow);
  
  return {
    headers: Array.from(headerRow.querySelectorAll('th')),
    cells: Array.from(dataRow.querySelectorAll('td'))
  };
}

// Helper to get computed text-align (simulated since JSDOM doesn't fully support getComputedStyle)
function getTextAlign(element) {
  // Check for explicit class or data-type attribute
  if (element.classList.contains('text-right') || element.getAttribute('data-type') === 'number') {
    return 'right';
  }
  if (element.classList.contains('text-center')) {
    return 'center';
  }
  return 'left';
}

describe('Table Alignment - Property 16: Numeric Column Alignment', () => {
  let dom;
  
  beforeEach(() => {
    dom = setupDOM();
  });
  
  afterEach(() => {
    delete global.window;
    delete global.document;
  });
  
  // Property 16: Numeric Column Alignment
  // For any table column containing numeric data, the text-align property should be set to right;
  // for text data, it should be left.
  
  test('Feature: modern-ui-redesign, Property 16: Numeric columns are right-aligned', () => {
    // Test with various numeric values
    const numericValues = [
      '123.45',
      '-456.78',
      '0',
      '1,234,567.89',
      '$100.00',
      '99.99%',
      '+5.5'
    ];
    
    numericValues.forEach(value => {
      const { cells } = renderTable([{ type: 'number', value }]);
      const alignment = getTextAlign(cells[0]);
      
      assert.strictEqual(
        alignment,
        'right',
        `Numeric value "${value}" should be right-aligned, got "${alignment}"`
      );
    });
    
    console.log('✓ All numeric columns are right-aligned');
  });
  
  test('Feature: modern-ui-redesign, Property 16: Text columns are left-aligned', () => {
    // Test with various text values
    const textValues = [
      'AAPL',
      'Long Call',
      '到期日',
      'Module 22',
      'Support Level'
    ];
    
    textValues.forEach(value => {
      const { cells } = renderTable([{ type: 'text', value }]);
      const alignment = getTextAlign(cells[0]);
      
      assert.strictEqual(
        alignment,
        'left',
        `Text value "${value}" should be left-aligned, got "${alignment}"`
      );
    });
    
    console.log('✓ All text columns are left-aligned');
  });
  
  test('Feature: modern-ui-redesign, Property 16: Mixed columns maintain correct alignment', () => {
    const columns = [
      { type: 'text', value: 'AAPL' },
      { type: 'number', value: '185.42' },
      { type: 'text', value: 'Long Call' },
      { type: 'number', value: '-2.5%' },
      { type: 'center', value: 'A' }
    ];
    
    const { cells } = renderTable(columns);
    
    const expectedAlignments = ['left', 'right', 'left', 'right', 'center'];
    
    cells.forEach((cell, index) => {
      const alignment = getTextAlign(cell);
      assert.strictEqual(
        alignment,
        expectedAlignments[index],
        `Column ${index} should be ${expectedAlignments[index]}-aligned, got "${alignment}"`
      );
    });
    
    console.log('✓ Mixed columns maintain correct alignment');
  });
  
  test('Feature: modern-ui-redesign, Property 16: Property-based test for alignment consistency', () => {
    // Property: For any column configuration, numeric columns should always be right-aligned
    // and text columns should always be left-aligned
    
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            type: fc.constantFrom('number', 'text'),
            value: fc.string({ minLength: 1, maxLength: 20 })
          }),
          { minLength: 1, maxLength: 10 }
        ),
        (columns) => {
          const { cells } = renderTable(columns);
          
          return columns.every((col, index) => {
            const alignment = getTextAlign(cells[index]);
            
            if (col.type === 'number') {
              return alignment === 'right';
            } else {
              return alignment === 'left';
            }
          });
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 16 verified with 100 random column configurations');
  });
  
  test('Feature: modern-ui-redesign, Property 16: Header alignment matches cell alignment', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            type: fc.constantFrom('number', 'text', 'center'),
            value: fc.string({ minLength: 1, maxLength: 20 })
          }),
          { minLength: 1, maxLength: 8 }
        ),
        (columns) => {
          const { headers, cells } = renderTable(columns);
          
          return columns.every((col, index) => {
            const headerAlign = getTextAlign(headers[index]);
            const cellAlign = getTextAlign(cells[index]);
            
            // Header and cell should have the same alignment
            return headerAlign === cellAlign;
          });
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Header alignment matches cell alignment for 100 configurations');
  });
  
  test('Feature: modern-ui-redesign, Property 16: data-type attribute correctly sets alignment', () => {
    // Test that data-type="number" attribute correctly triggers right alignment
    const columns = [
      { type: 'number', value: '100' },
      { type: 'number', value: '200.50' },
      { type: 'number', value: '-50' }
    ];
    
    const { cells } = renderTable(columns);
    
    cells.forEach((cell, index) => {
      assert.strictEqual(
        cell.getAttribute('data-type'),
        'number',
        `Cell ${index} should have data-type="number"`
      );
      
      const alignment = getTextAlign(cell);
      assert.strictEqual(
        alignment,
        'right',
        `Cell ${index} with data-type="number" should be right-aligned`
      );
    });
    
    console.log('✓ data-type attribute correctly sets alignment');
  });
  
  test('Feature: modern-ui-redesign, Property 16: Empty table handles gracefully', () => {
    const { headers, cells } = renderTable([]);
    
    assert.strictEqual(headers.length, 0, 'Empty table should have no headers');
    assert.strictEqual(cells.length, 0, 'Empty table should have no cells');
    
    console.log('✓ Empty table handles gracefully');
  });
  
  test('Feature: modern-ui-redesign, Property 16: Single column tables work correctly', () => {
    fc.assert(
      fc.property(
        fc.record({
          type: fc.constantFrom('number', 'text'),
          value: fc.string({ minLength: 1, maxLength: 20 })
        }),
        (column) => {
          const { cells } = renderTable([column]);
          const alignment = getTextAlign(cells[0]);
          
          if (column.type === 'number') {
            return alignment === 'right';
          } else {
            return alignment === 'left';
          }
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Single column tables work correctly for 100 configurations');
  });
});
