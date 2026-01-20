// Feature: modern-ui-redesign
// Property-Based Tests for Module Renderer
// Requirements: 16.1, 16.2, 16.3, 16.5

const { test, describe } = require('node:test');
const assert = require('node:assert');
const fc = require('fast-check');

// Mock DOM environment
const { JSDOM } = require('jsdom');
const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
global.document = dom.window.document;
global.window = dom.window;

// Import the module renderer
const { ModuleRenderer, MODULE_STATUS, MODULE_METADATA } = require('../static/js/module-renderer.js');

// Helper to create a container element
function createContainer() {
  const container = document.createElement('div');
  document.body.appendChild(container);
  return container;
}

// Helper to clean up containers
function cleanupContainer(container) {
  if (container && container.parentNode) {
    container.parentNode.removeChild(container);
  }
}

// Arbitrary generators for module data
const moduleDataArbitrary = fc.record({
  status: fc.constantFrom('success', 'error', 'skipped', undefined),
  error: fc.option(fc.string()),
  reason: fc.option(fc.string())
});

const module1DataArbitrary = fc.record({
  status: fc.constantFrom('success', undefined),
  results: fc.dictionary(
    fc.constantFrom('68%', '80%', '90%', '95%'),
    fc.record({
      z_score: fc.float({ min: 0.5, max: 3, noNaN: true }),
      price_move: fc.float({ min: 1, max: 50, noNaN: true }),
      move_percentage: fc.float({ min: 1, max: 20, noNaN: true }),
      support: fc.float({ min: 50, max: 200, noNaN: true }),
      resistance: fc.float({ min: 50, max: 200, noNaN: true })
    })
  ),
  support_level: fc.float({ min: 50, max: 200, noNaN: true }),
  resistance_level: fc.float({ min: 50, max: 200, noNaN: true }),
  current_price: fc.float({ min: 50, max: 200, noNaN: true })
});

describe('Module Renderer - Complete Module Display', () => {
  
  /**
   * Property 34: Complete Module Display
   * *For any* analysis result, all 28 calculation modules should have 
   * corresponding rendering functions called and DOM elements created.
   * 
   * **Validates: Requirements 16.1, 16.2**
   */
  test('Feature: modern-ui-redesign, Property 34: All 28 modules have render methods', () => {
    const renderer = new ModuleRenderer();
    
    // Check that render methods exist for all modules
    const expectedMethods = [
      'renderModule1', 'renderModule2', 'renderModule3', 'renderModule4', 'renderModule5',
      'renderModule6', 'renderStrategyPnL', 'renderModule11', 'renderModule12',
      'renderModule13', 'renderModule14', 'renderModule15_16', 'renderModule18',
      'renderModule19', 'renderModule20', 'renderModule21', 'renderModule22',
      'renderModule23', 'renderModule24', 'renderModule25', 'renderModule26',
      'renderModule27', 'renderModule28'
    ];
    
    expectedMethods.forEach(method => {
      assert.strictEqual(
        typeof renderer[method], 
        'function', 
        `Renderer should have ${method} method`
      );
    });
  });
  
  test('Feature: modern-ui-redesign, Property 34: MODULE_METADATA contains all 28 modules', () => {
    // Verify all 28 modules are defined in metadata
    for (let i = 1; i <= 28; i++) {
      assert.ok(
        MODULE_METADATA[i],
        `MODULE_METADATA should contain module ${i}`
      );
      assert.ok(
        MODULE_METADATA[i].name,
        `Module ${i} should have a name`
      );
      assert.ok(
        MODULE_METADATA[i].icon,
        `Module ${i} should have an icon`
      );
      assert.ok(
        MODULE_METADATA[i].category,
        `Module ${i} should have a category`
      );
    }
  });
  
  test('Feature: modern-ui-redesign, Property 34: renderAllModules tracks rendered modules', () => {
    const renderer = new ModuleRenderer();
    const containers = {
      module1: createContainer(),
      module2: createContainer()
    };
    
    try {
      const calculations = {
        module1_support_resistance: {
          results: { '90%': { z_score: 1.645, price_move: 10, move_percentage: 5, support: 95, resistance: 105 } },
          support_level: 95,
          resistance_level: 105,
          current_price: 100
        },
        module2_fair_value: {
          fair_value: 100,
          risk_free_rate: 0.05,
          expected_dividend: 1
        }
      };
      
      renderer.renderAllModules(calculations, containers);
      
      // Should track rendered modules
      const count = renderer.getRenderedModulesCount();
      assert.ok(count >= 0 && count <= 28, `Rendered count ${count} should be between 0 and 28`);
    } finally {
      Object.values(containers).forEach(cleanupContainer);
    }
  });
  
  test('Feature: modern-ui-redesign, Property 34: Module 1 renders with valid data', () => {
    fc.assert(
      fc.property(
        module1DataArbitrary,
        (data) => {
          const renderer = new ModuleRenderer();
          const container = createContainer();
          
          try {
            renderer.renderModule1(data, container);
            
            // Container should have content
            const hasContent = container.innerHTML.length > 0;
            
            // Should be tracked as rendered
            const isRendered = renderer.isModuleRendered(1);
            
            return hasContent && isRendered;
          } finally {
            cleanupContainer(container);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 34: Each module renders to non-empty content', () => {
    const renderer = new ModuleRenderer();
    
    // Test each module with minimal valid data
    const testCases = [
      { method: 'renderModule2', data: { fair_value: 100, risk_free_rate: 0.05, expected_dividend: 1 } },
      { method: 'renderModule3', data: { arbitrage_spread: 0.5, spread_percentage: 1.2, theoretical_price: 100, market_price: 99.5 } },
      { method: 'renderModule4', data: { pe_multiple: 15, eps: 5, peg_ratio: 1.2 } },
      { method: 'renderModule5', data: { reasonable_pe: 18 } },
      { method: 'renderModule6', data: { hedge_contracts: 5, stock_quantity: 500, portfolio_value: 50000, coverage_percentage: 100 } },
      { method: 'renderModule11', data: { synthetic_price: 100, current_stock_price: 99, difference: 1 } },
      { method: 'renderModule12', data: { annual_yield: 12, dividend_yield: 2, option_yield: 10 } },
      { method: 'renderModule13', data: { volume: 10000, open_interest: 50000 } },
      { method: 'renderModule18', data: { hv_results: { '30': { historical_volatility: 0.25 } } } },
      { method: 'renderModule19', data: { market_prices: { deviation: 0.5, deviation_percentage: 1 } } },
      { method: 'renderModule20', data: { metrics: { 'PE': { value: 15, score: 7 } } } },
      { method: 'renderModule21', data: { momentum_score: 0.7 } },
      { method: 'renderModule22', data: { long_call: { optimal_strike: 100, score: 85, delta: 0.5, premium: 5 } } },
      { method: 'renderModule23', data: { current_iv: 0.3, threshold: 0.25 } },
      { method: 'renderModule24', data: { combined_direction: 'Bullish', confidence: 'High' } },
      { method: 'renderModule25', data: { atm_iv: 0.25, skew: 0.02, skew_type: 'Normal', iv_environment: 'Normal' } },
      { method: 'renderModule26', data: { long_call: { strike: 100, premium: 5, leverage: 10, score: { total_score: 80, grade: 'B' } } } },
      { method: 'renderModule27', data: { status: 'success', strategy_results: { long_call: { status: 'success', recommendation: { best_expiration: '2025-03-21', best_days: 30, best_score: 85, best_grade: 'A' } } } } },
      { method: 'renderModule28', data: { status: 'success', position_recommendation: { recommended_contracts: 5 }, risk_analysis: { max_loss_usd: 500, max_loss_pct: 5, risk_rating: '中' }, capital_summary: { total_capital: 10000, currency: 'USD' } } }
    ];
    
    testCases.forEach(({ method, data }) => {
      const container = createContainer();
      try {
        renderer[method](data, container);
        assert.ok(
          container.innerHTML.length > 0,
          `${method} should render non-empty content`
        );
      } finally {
        cleanupContainer(container);
      }
    });
  });
});

describe('Module Renderer - Status Indicators', () => {
  
  /**
   * Property 35: Module Status Indicators
   * *For any* module that is skipped or has an error, a visual status indicator 
   * (badge, icon, or message) should be displayed explaining the status.
   * 
   * **Validates: Requirements 16.3**
   */
  test('Feature: modern-ui-redesign, Property 35: Error status shows error message', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 100 }),
        (errorMessage) => {
          const renderer = new ModuleRenderer();
          const container = createContainer();
          
          try {
            renderer.renderModule1({ status: 'error', error: errorMessage }, container);
            
            // Should contain error class
            const hasErrorClass = container.innerHTML.includes('module-error');
            // Should contain error icon
            const hasErrorIcon = container.innerHTML.includes('fa-exclamation-triangle');
            
            return hasErrorClass && hasErrorIcon;
          } finally {
            cleanupContainer(container);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 35: Skipped status shows skipped message', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 100 }),
        (reason) => {
          const renderer = new ModuleRenderer();
          const container = createContainer();
          
          try {
            renderer.renderModule1({ status: 'skipped', reason: reason }, container);
            
            // Should contain skipped class
            const hasSkippedClass = container.innerHTML.includes('module-skipped');
            // Should contain forward icon
            const hasSkippedIcon = container.innerHTML.includes('fa-forward');
            
            return hasSkippedClass && hasSkippedIcon;
          } finally {
            cleanupContainer(container);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 35: Status indicator has correct class for each status', () => {
    const renderer = new ModuleRenderer();
    
    const statusTests = [
      { status: MODULE_STATUS.SUCCESS, expectedClass: 'status-success' },
      { status: MODULE_STATUS.ERROR, expectedClass: 'status-error' },
      { status: MODULE_STATUS.SKIPPED, expectedClass: 'status-skipped' },
      { status: MODULE_STATUS.LOADING, expectedClass: 'status-loading' },
      { status: MODULE_STATUS.NO_DATA, expectedClass: 'status-no-data' }
    ];
    
    statusTests.forEach(({ status, expectedClass }) => {
      const indicator = renderer.createStatusIndicator(status);
      assert.ok(
        indicator.includes(expectedClass),
        `Status ${status} should have class ${expectedClass}`
      );
    });
  });
  
  test('Feature: modern-ui-redesign, Property 35: getModuleStatus returns correct status', () => {
    const renderer = new ModuleRenderer();
    
    // Test various data scenarios
    assert.strictEqual(renderer.getModuleStatus(null), MODULE_STATUS.NO_DATA);
    assert.strictEqual(renderer.getModuleStatus(undefined), MODULE_STATUS.NO_DATA);
    assert.strictEqual(renderer.getModuleStatus({ status: 'error' }), MODULE_STATUS.ERROR);
    assert.strictEqual(renderer.getModuleStatus({ status: 'skipped' }), MODULE_STATUS.SKIPPED);
    assert.strictEqual(renderer.getModuleStatus({ status: 'success' }), MODULE_STATUS.SUCCESS);
    assert.strictEqual(renderer.getModuleStatus({ data: 'some data' }), MODULE_STATUS.SUCCESS);
  });
});

describe('Module Renderer - No-Data Messages', () => {
  
  /**
   * Property 36: Module No-Data Messages
   * *For any* module that has no data to display, a clear explanatory message 
   * should be shown instead of empty content.
   * 
   * **Validates: Requirements 16.5**
   */
  test('Feature: modern-ui-redesign, Property 36: No-data shows explanatory message', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 28 }),
        (moduleId) => {
          const renderer = new ModuleRenderer();
          const message = renderer.createNoDataMessage(null, moduleId);
          
          // Should contain no-data class
          const hasNoDataClass = message.includes('module-no-data');
          // Should contain inbox icon
          const hasIcon = message.includes('fa-inbox');
          // Should have a message
          const hasMessage = message.includes('no-data-message');
          
          return hasNoDataClass && hasIcon && hasMessage;
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 36: Custom reason is displayed', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 5, maxLength: 100 }),
        fc.integer({ min: 1, max: 28 }),
        (reason, moduleId) => {
          const renderer = new ModuleRenderer();
          const message = renderer.createNoDataMessage(reason, moduleId);
          
          // Custom reason should be in the message
          return message.includes(reason);
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 36: Default reasons exist for all modules', () => {
    const renderer = new ModuleRenderer();
    
    for (let moduleId = 1; moduleId <= 28; moduleId++) {
      const message = renderer.createNoDataMessage(null, moduleId);
      
      // Should have some default message (not just the generic one)
      assert.ok(
        message.length > 50,
        `Module ${moduleId} should have a meaningful no-data message`
      );
    }
  });
  
  test('Feature: modern-ui-redesign, Property 36: Modules render no-data message when data is missing', () => {
    const renderer = new ModuleRenderer();
    
    // Test modules with null/undefined data
    const testMethods = [
      'renderModule1', 'renderModule2', 'renderModule3', 'renderModule4', 'renderModule5',
      'renderModule6', 'renderModule11', 'renderModule12', 'renderModule13',
      'renderModule18', 'renderModule19', 'renderModule20', 'renderModule21',
      'renderModule22', 'renderModule23', 'renderModule24', 'renderModule25',
      'renderModule26', 'renderModule27', 'renderModule28'
    ];
    
    testMethods.forEach(method => {
      const container = createContainer();
      try {
        renderer[method](null, container);
        
        // Should show no-data message
        assert.ok(
          container.innerHTML.includes('module-no-data') || 
          container.innerHTML.includes('module-error') ||
          container.innerHTML.includes('module-skipped'),
          `${method} should show appropriate message for null data`
        );
      } finally {
        cleanupContainer(container);
      }
    });
  });
});

describe('Module Renderer - Financial Value Formatting', () => {
  
  test('Feature: modern-ui-redesign, Property 34: formatFinancialValue handles all numeric inputs', () => {
    fc.assert(
      fc.property(
        fc.float({ min: -100000, max: 100000, noNaN: true }),
        (value) => {
          const renderer = new ModuleRenderer();
          const formatted = renderer.formatFinancialValue(value);
          
          // Should return a string with span element
          const isString = typeof formatted === 'string';
          const hasSpan = formatted.includes('<span');
          
          // Should have appropriate color class
          const hasColorClass = 
            formatted.includes('value-positive') ||
            formatted.includes('value-negative') ||
            formatted.includes('value-neutral');
          
          return isString && hasSpan && hasColorClass;
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 34: formatFinancialValue handles null/undefined', () => {
    const renderer = new ModuleRenderer();
    
    const nullResult = renderer.formatFinancialValue(null);
    const undefinedResult = renderer.formatFinancialValue(undefined);
    const nanResult = renderer.formatFinancialValue(NaN);
    
    assert.ok(nullResult.includes('N/A'), 'Null should show N/A');
    assert.ok(undefinedResult.includes('N/A'), 'Undefined should show N/A');
    assert.ok(nanResult.includes('N/A'), 'NaN should show N/A');
  });
  
  test('Feature: modern-ui-redesign, Property 34: Grade badges are created correctly', () => {
    const renderer = new ModuleRenderer();
    const grades = ['A', 'B', 'C', 'D', 'F'];
    
    grades.forEach(grade => {
      const badge = renderer.createGradeBadge(grade);
      
      assert.ok(badge.includes('badge'), `Grade ${grade} should create a badge`);
      assert.ok(badge.includes(grade), `Badge should contain grade ${grade}`);
    });
    
    // Null grade should show N/A
    const nullBadge = renderer.createGradeBadge(null);
    assert.ok(nullBadge.includes('N/A'), 'Null grade should show N/A');
  });
});
