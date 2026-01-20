// Feature: modern-ui-redesign
// Property-Based Tests for Metric Display and Color Coding

const { test, describe } = require('node:test');
const assert = require('node:assert');
const fc = require('fast-check');

// Import the metric display module
const {
  formatCurrency,
  formatPercentage,
  getValueColorClass,
  getTrendIconClass,
  renderFinancialValue
} = require('../static/js/metric-display.js');

// Mock DOM environment for renderFinancialValue
const { JSDOM } = require('jsdom');
const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
global.document = dom.window.document;

describe('Metric Display - Color Coding Properties', () => {
  
  /**
   * Property 7: Consistent Color Coding for Financial Values
   * *For any* numeric financial value displayed in the UI, positive values 
   * should use green color classes and negative values should use red color 
   * classes consistently.
   * 
   * **Validates: Requirements 4.2, 9.5, 15.2**
   */
  test('Feature: modern-ui-redesign, Property 7: Positive values return "positive" color class', () => {
    fc.assert(
      fc.property(
        fc.float({ min: Math.fround(0.0001), max: Math.fround(100000), noNaN: true }),
        (value) => {
          const colorClass = getValueColorClass(value);
          return colorClass === 'positive';
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 7: Negative values return "negative" color class', () => {
    fc.assert(
      fc.property(
        fc.float({ min: Math.fround(-100000), max: Math.fround(-0.0001), noNaN: true }),
        (value) => {
          const colorClass = getValueColorClass(value);
          return colorClass === 'negative';
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 7: Zero values return "neutral" color class', () => {
    const colorClass = getValueColorClass(0);
    assert.strictEqual(colorClass, 'neutral', 'Zero should be neutral');
  });
  
  test('Feature: modern-ui-redesign, Property 7: NaN values return "neutral" color class', () => {
    const colorClass = getValueColorClass(NaN);
    assert.strictEqual(colorClass, 'neutral', 'NaN should be neutral');
  });
  
  test('Feature: modern-ui-redesign, Property 7: Non-numeric values return "neutral" color class', () => {
    fc.assert(
      fc.property(
        fc.oneof(
          fc.string(),
          fc.constant(null),
          fc.constant(undefined),
          fc.object()
        ),
        (value) => {
          const colorClass = getValueColorClass(value);
          return colorClass === 'neutral';
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 7: Rendered financial values have correct color class', () => {
    fc.assert(
      fc.property(
        fc.float({ min: Math.fround(-100000), max: Math.fround(100000), noNaN: true }),
        (value) => {
          const element = renderFinancialValue(value);
          const expectedClass = getValueColorClass(value);
          
          return element.classList.contains(expectedClass);
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 7: Color class is mutually exclusive', () => {
    fc.assert(
      fc.property(
        fc.float({ min: Math.fround(-100000), max: Math.fround(100000), noNaN: true }),
        (value) => {
          const colorClass = getValueColorClass(value);
          const validClasses = ['positive', 'negative', 'neutral'];
          
          // Should return exactly one valid class
          return validClasses.includes(colorClass);
        }
      ),
      { numRuns: 100 }
    );
  });
});

describe('Metric Display - Trend Icon Properties', () => {
  
  test('Feature: modern-ui-redesign, Property 7: Positive values get up arrow icon', () => {
    fc.assert(
      fc.property(
        fc.float({ min: Math.fround(0.0001), max: Math.fround(100000), noNaN: true }),
        (value) => {
          const iconClass = getTrendIconClass(value);
          return iconClass === 'fa-arrow-up';
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 7: Negative values get down arrow icon', () => {
    fc.assert(
      fc.property(
        fc.float({ min: Math.fround(-100000), max: Math.fround(-0.0001), noNaN: true }),
        (value) => {
          const iconClass = getTrendIconClass(value);
          return iconClass === 'fa-arrow-down';
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 7: Zero values get minus icon', () => {
    const iconClass = getTrendIconClass(0);
    assert.strictEqual(iconClass, 'fa-minus', 'Zero should get minus icon');
  });
});

describe('Metric Display - Formatting Properties', () => {
  
  test('Feature: modern-ui-redesign, Property 7: Currency formatting preserves sign', () => {
    fc.assert(
      fc.property(
        fc.float({ min: Math.fround(-100000), max: Math.fround(100000), noNaN: true }),
        (value) => {
          const formatted = formatCurrency(value);
          
          if (value < 0) {
            return formatted.startsWith('-$');
          } else {
            return formatted.startsWith('$') && !formatted.startsWith('-');
          }
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 7: Percentage formatting is consistent', () => {
    fc.assert(
      fc.property(
        fc.float({ min: Math.fround(-10), max: Math.fround(10), noNaN: true }),
        (value) => {
          const formatted = formatPercentage(value);
          
          // Should end with %
          return formatted.endsWith('%');
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 7: Percentage with sign shows + for positive', () => {
    fc.assert(
      fc.property(
        fc.float({ min: Math.fround(0.0001), max: Math.fround(10), noNaN: true }),
        (value) => {
          const formatted = formatPercentage(value, 2, true);
          
          return formatted.startsWith('+');
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 7: Invalid values format gracefully', () => {
    const currencyResult = formatCurrency(NaN);
    assert.strictEqual(currencyResult, '$--', 'NaN currency should show $--');
    
    const percentResult = formatPercentage(NaN);
    assert.strictEqual(percentResult, '--%', 'NaN percentage should show --%');
  });
});

describe('Metric Display - Consistency Properties', () => {
  
  test('Feature: modern-ui-redesign, Property 7: Color coding is deterministic', () => {
    fc.assert(
      fc.property(
        fc.float({ min: Math.fround(-100000), max: Math.fround(100000), noNaN: true }),
        (value) => {
          // Call multiple times with same value
          const result1 = getValueColorClass(value);
          const result2 = getValueColorClass(value);
          const result3 = getValueColorClass(value);
          
          return result1 === result2 && result2 === result3;
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 7: Color and icon are consistent', () => {
    fc.assert(
      fc.property(
        fc.float({ min: Math.fround(-100000), max: Math.fround(100000), noNaN: true }),
        (value) => {
          const colorClass = getValueColorClass(value);
          const iconClass = getTrendIconClass(value);
          
          // Positive values should have positive color and up arrow
          if (value > 0) {
            return colorClass === 'positive' && iconClass === 'fa-arrow-up';
          }
          // Negative values should have negative color and down arrow
          else if (value < 0) {
            return colorClass === 'negative' && iconClass === 'fa-arrow-down';
          }
          // Zero should have neutral color and minus icon
          else {
            return colorClass === 'neutral' && iconClass === 'fa-minus';
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
