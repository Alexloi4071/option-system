// Feature: modern-ui-redesign
// Property-Based Tests for Responsive Layout Controller

const { test, describe, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const { JSDOM } = require('jsdom');
const fc = require('fast-check');

// Setup DOM environment for each test
function setupDOM(viewportWidth = 1200) {
  const dom = new JSDOM(`
    <!DOCTYPE html>
    <html>
      <head>
        <style>
          :root {
            --breakpoint-mobile: 0;
            --breakpoint-tablet: 768px;
            --breakpoint-desktop: 1200px;
            --breakpoint-wide: 1600px;
            --touch-target-min: 44px;
            --spacing-4: 1rem;
            --spacing-6: 1.5rem;
            --spacing-8: 2rem;
          }
          
          /* Simulate mobile styles */
          @media (max-width: 767px) {
            .card-grid {
              display: flex !important;
              flex-direction: column !important;
            }
          }
        </style>
      </head>
      <body class="breakpoint-desktop">
        <div class="container-responsive">
          <div class="card-grid" id="card-container">
          </div>
        </div>
      </body>
    </html>
  `, {
    url: 'http://localhost',
    pretendToBeVisual: true,
  });

  // Mock window.innerWidth
  Object.defineProperty(dom.window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: viewportWidth
  });
  
  Object.defineProperty(dom.window.document.documentElement, 'clientWidth', {
    writable: true,
    configurable: true,
    value: viewportWidth
  });

  global.window = dom.window;
  global.document = dom.window.document;
  global.CustomEvent = dom.window.CustomEvent;
  global.HTMLElement = dom.window.HTMLElement;

  return dom;
}

// Load ResponsiveLayoutController class
function loadResponsiveLayoutController() {
  // Clear require cache
  delete require.cache[require.resolve('../static/js/responsive-layout.js')];
  
  // Load the module
  const ResponsiveLayoutController = require('../static/js/responsive-layout.js');
  return ResponsiveLayoutController;
}

// Helper to create interactive elements
function createInteractiveElements(count, elementType = 'button', size = { width: 44, height: 44 }) {
  const container = document.getElementById('card-container');
  container.innerHTML = '';
  
  const elements = [];
  for (let i = 0; i < count; i++) {
    let element;
    
    switch (elementType) {
      case 'button':
        element = document.createElement('button');
        element.textContent = `Button ${i}`;
        break;
      case 'link':
        element = document.createElement('a');
        element.href = '#';
        element.textContent = `Link ${i}`;
        break;
      case 'input':
        element = document.createElement('input');
        element.type = 'text';
        element.placeholder = `Input ${i}`;
        break;
      case 'select':
        element = document.createElement('select');
        const option = document.createElement('option');
        option.textContent = `Option ${i}`;
        element.appendChild(option);
        break;
      default:
        element = document.createElement('button');
    }
    
    element.id = `element-${i}`;
    element.style.width = `${size.width}px`;
    element.style.height = `${size.height}px`;
    element.style.display = 'inline-block';
    
    // Mock getBoundingClientRect
    element.getBoundingClientRect = () => ({
      width: size.width,
      height: size.height,
      top: 0,
      left: 0,
      right: size.width,
      bottom: size.height
    });
    
    container.appendChild(element);
    elements.push(element);
  }
  
  return elements;
}

describe('Responsive Layout - Touch Target Size', () => {
  let dom;
  let ResponsiveLayoutController;
  
  beforeEach(() => {
    dom = setupDOM(375); // Mobile viewport
    ResponsiveLayoutController = loadResponsiveLayoutController();
  });
  
  afterEach(() => {
    delete global.window;
    delete global.document;
    delete global.CustomEvent;
    delete global.HTMLElement;
  });
  
  // Property 6: Mobile Touch Target Minimum Size
  // For any interactive element on mobile viewports (<768px), 
  // the minimum touch target size should be 44px × 44px
  // Validates: Requirements 3.2, 3.4
  test('Feature: modern-ui-redesign, Property 6: Interactive elements meeting 44px minimum are valid', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 20 }), // Number of elements
        fc.integer({ min: 44, max: 100 }), // Width (at or above minimum)
        fc.integer({ min: 44, max: 100 }), // Height (at or above minimum)
        (count, width, height) => {
          const elements = createInteractiveElements(count, 'button', { width, height });
          const controller = new ResponsiveLayoutController();
          
          // All elements should meet minimum touch target size
          const result = controller.validateTouchTargets();
          
          return result.valid === true && 
                 result.failing.length === 0 && 
                 result.passing.length === count;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 6: Elements at or above 44px minimum are valid');
  });
  
  test('Feature: modern-ui-redesign, Property 6: Elements below 44px minimum are flagged as invalid', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 20 }), // Number of elements
        fc.integer({ min: 10, max: 43 }), // Width (below minimum)
        fc.integer({ min: 10, max: 43 }), // Height (below minimum)
        (count, width, height) => {
          const elements = createInteractiveElements(count, 'button', { width, height });
          const controller = new ResponsiveLayoutController();
          
          // All elements should fail validation
          const result = controller.validateTouchTargets();
          
          return result.valid === false && 
                 result.failing.length === count && 
                 result.passing.length === 0;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 6: Elements below 44px minimum are flagged as invalid');
  });
  
  test('Feature: modern-ui-redesign, Property 6: Mixed size elements are correctly categorized', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 10 }), // Number of valid elements
        fc.integer({ min: 1, max: 10 }), // Number of invalid elements
        (validCount, invalidCount) => {
          const container = document.getElementById('card-container');
          container.innerHTML = '';
          
          const controller = new ResponsiveLayoutController();
          const minSize = controller.getMinTouchTargetSize();
          
          // Create valid elements (44px+)
          for (let i = 0; i < validCount; i++) {
            const btn = document.createElement('button');
            btn.id = `valid-${i}`;
            btn.style.width = '44px';
            btn.style.height = '44px';
            btn.getBoundingClientRect = () => ({ width: 44, height: 44, top: 0, left: 0, right: 44, bottom: 44 });
            container.appendChild(btn);
          }
          
          // Create invalid elements (below 44px)
          for (let i = 0; i < invalidCount; i++) {
            const btn = document.createElement('button');
            btn.id = `invalid-${i}`;
            btn.style.width = '30px';
            btn.style.height = '30px';
            btn.getBoundingClientRect = () => ({ width: 30, height: 30, top: 0, left: 0, right: 30, bottom: 30 });
            container.appendChild(btn);
          }
          
          const result = controller.validateTouchTargets();
          
          return result.passing.length === validCount && 
                 result.failing.length === invalidCount &&
                 result.valid === (invalidCount === 0);
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 6: Mixed size elements are correctly categorized');
  });
  
  test('Feature: modern-ui-redesign, Property 6: getMinTouchTargetSize returns 44', () => {
    const controller = new ResponsiveLayoutController();
    const minSize = controller.getMinTouchTargetSize();
    
    assert.strictEqual(minSize, 44, 'Minimum touch target size should be 44px');
    
    console.log('✓ Property 6: getMinTouchTargetSize returns 44');
  });
  
  test('Feature: modern-ui-redesign, Property 6: meetsMinTouchTargetSize correctly validates elements', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 100 }), // Width
        fc.integer({ min: 1, max: 100 }), // Height
        (width, height) => {
          const container = document.getElementById('card-container');
          container.innerHTML = '';
          
          const btn = document.createElement('button');
          btn.getBoundingClientRect = () => ({ width, height, top: 0, left: 0, right: width, bottom: height });
          container.appendChild(btn);
          
          const controller = new ResponsiveLayoutController();
          const meetsSize = controller.meetsMinTouchTargetSize(btn);
          
          const expectedResult = width >= 44 && height >= 44;
          return meetsSize === expectedResult;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 6: meetsMinTouchTargetSize correctly validates elements');
  });
  
  test('Feature: modern-ui-redesign, Property 6: All interactive element types are validated', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('button', 'link', 'input', 'select'),
        fc.integer({ min: 44, max: 80 }),
        (elementType, size) => {
          const elements = createInteractiveElements(5, elementType, { width: size, height: size });
          const controller = new ResponsiveLayoutController();
          
          const result = controller.validateTouchTargets();
          
          // All elements should pass since they're at or above minimum
          return result.valid === true && result.passing.length === 5;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 6: All interactive element types are validated');
  });
});

describe('Responsive Layout - Breakpoint Detection', () => {
  let ResponsiveLayoutController;
  
  afterEach(() => {
    delete global.window;
    delete global.document;
    delete global.CustomEvent;
    delete global.HTMLElement;
  });
  
  test('Feature: modern-ui-redesign, Property 5: Mobile breakpoint detected for width < 768px', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 320, max: 767 }),
        (width) => {
          setupDOM(width);
          ResponsiveLayoutController = loadResponsiveLayoutController();
          const controller = new ResponsiveLayoutController();
          
          const breakpoint = controller.getCurrentBreakpoint();
          const isMobile = controller.isMobile();
          
          return breakpoint === 'mobile' && isMobile === true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 5: Mobile breakpoint detected for width < 768px');
  });
  
  test('Feature: modern-ui-redesign, Property 5: Tablet breakpoint detected for 768px <= width < 1200px', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 768, max: 1199 }),
        (width) => {
          setupDOM(width);
          ResponsiveLayoutController = loadResponsiveLayoutController();
          const controller = new ResponsiveLayoutController();
          
          const breakpoint = controller.getCurrentBreakpoint();
          const isTablet = controller.isTablet();
          
          return breakpoint === 'tablet' && isTablet === true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 5: Tablet breakpoint detected for 768px <= width < 1200px');
  });
  
  test('Feature: modern-ui-redesign, Property 5: Desktop breakpoint detected for 1200px <= width < 1600px', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1200, max: 1599 }),
        (width) => {
          setupDOM(width);
          ResponsiveLayoutController = loadResponsiveLayoutController();
          const controller = new ResponsiveLayoutController();
          
          const breakpoint = controller.getCurrentBreakpoint();
          const isDesktop = controller.isDesktop();
          
          return breakpoint === 'desktop' && isDesktop === true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 5: Desktop breakpoint detected for 1200px <= width < 1600px');
  });
  
  test('Feature: modern-ui-redesign, Property 5: Wide breakpoint detected for width >= 1600px', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1600, max: 2560 }),
        (width) => {
          setupDOM(width);
          ResponsiveLayoutController = loadResponsiveLayoutController();
          const controller = new ResponsiveLayoutController();
          
          const breakpoint = controller.getCurrentBreakpoint();
          const isWide = controller.isWide();
          
          return breakpoint === 'wide' && isWide === true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 5: Wide breakpoint detected for width >= 1600px');
  });
});

describe('Responsive Layout - Layout Configuration', () => {
  let ResponsiveLayoutController;
  
  afterEach(() => {
    delete global.window;
    delete global.document;
    delete global.CustomEvent;
    delete global.HTMLElement;
  });
  
  test('Feature: modern-ui-redesign, Property 5: Mobile layout has 1 column', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 320, max: 767 }),
        (width) => {
          setupDOM(width);
          ResponsiveLayoutController = loadResponsiveLayoutController();
          const controller = new ResponsiveLayoutController();
          
          const config = controller.getLayoutConfig();
          
          return config.columns === 1 && config.cardDirection === 'column';
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 5: Mobile layout has 1 column');
  });
  
  test('Feature: modern-ui-redesign, Property 5: Tablet layout has 2 columns', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 768, max: 1199 }),
        (width) => {
          setupDOM(width);
          ResponsiveLayoutController = loadResponsiveLayoutController();
          const controller = new ResponsiveLayoutController();
          
          const config = controller.getLayoutConfig();
          
          return config.columns === 2 && config.cardDirection === 'row';
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 5: Tablet layout has 2 columns');
  });
  
  test('Feature: modern-ui-redesign, Property 5: Desktop layout has 3 columns', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1200, max: 1599 }),
        (width) => {
          setupDOM(width);
          ResponsiveLayoutController = loadResponsiveLayoutController();
          const controller = new ResponsiveLayoutController();
          
          const config = controller.getLayoutConfig();
          
          return config.columns === 3 && config.cardDirection === 'row';
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 5: Desktop layout has 3 columns');
  });
  
  test('Feature: modern-ui-redesign, Property 5: Wide layout has 4 columns', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1600, max: 2560 }),
        (width) => {
          setupDOM(width);
          ResponsiveLayoutController = loadResponsiveLayoutController();
          const controller = new ResponsiveLayoutController();
          
          const config = controller.getLayoutConfig();
          
          return config.columns === 4 && config.cardDirection === 'row';
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 5: Wide layout has 4 columns');
  });
});

describe('Responsive Layout - Horizontal Overflow Prevention', () => {
  let ResponsiveLayoutController;
  
  afterEach(() => {
    delete global.window;
    delete global.document;
    delete global.CustomEvent;
    delete global.HTMLElement;
  });
  
  test('Feature: modern-ui-redesign, Property 5: preventHorizontalScroll sets overflow-x hidden', () => {
    setupDOM(1200);
    ResponsiveLayoutController = loadResponsiveLayoutController();
    const controller = new ResponsiveLayoutController();
    
    // preventHorizontalScroll is called in init()
    const htmlOverflow = document.documentElement.style.overflowX;
    const bodyOverflow = document.body.style.overflowX;
    
    assert.strictEqual(htmlOverflow, 'hidden', 'HTML overflow-x should be hidden');
    assert.strictEqual(bodyOverflow, 'hidden', 'Body overflow-x should be hidden');
    
    console.log('✓ Property 5: preventHorizontalScroll sets overflow-x hidden');
  });
  
  test('Feature: modern-ui-redesign, Property 5: hasHorizontalOverflow detects overflow correctly', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 800, max: 1400 }),
        (viewportWidth) => {
          const dom = setupDOM(viewportWidth);
          
          // Mock scrollWidth to be same as clientWidth (no overflow)
          Object.defineProperty(dom.window.document.documentElement, 'scrollWidth', {
            writable: true,
            configurable: true,
            value: viewportWidth
          });
          
          ResponsiveLayoutController = loadResponsiveLayoutController();
          const controller = new ResponsiveLayoutController();
          
          const hasOverflow = controller.hasHorizontalOverflow();
          
          return hasOverflow === false;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 5: hasHorizontalOverflow detects no overflow when scrollWidth equals clientWidth');
  });
});

describe('Responsive Layout - Breakpoint Configuration', () => {
  let ResponsiveLayoutController;
  
  beforeEach(() => {
    setupDOM(1200);
    ResponsiveLayoutController = loadResponsiveLayoutController();
  });
  
  afterEach(() => {
    delete global.window;
    delete global.document;
    delete global.CustomEvent;
    delete global.HTMLElement;
  });
  
  test('Feature: modern-ui-redesign, Property 5: getBreakpoints returns correct values', () => {
    const controller = new ResponsiveLayoutController();
    const breakpoints = controller.getBreakpoints();
    
    assert.strictEqual(breakpoints.mobile, 0, 'Mobile breakpoint should be 0');
    assert.strictEqual(breakpoints.tablet, 768, 'Tablet breakpoint should be 768');
    assert.strictEqual(breakpoints.desktop, 1200, 'Desktop breakpoint should be 1200');
    assert.strictEqual(breakpoints.wide, 1600, 'Wide breakpoint should be 1600');
    
    console.log('✓ Property 5: getBreakpoints returns correct values');
  });
  
  test('Feature: modern-ui-redesign, Property 5: Breakpoints are immutable', () => {
    const controller = new ResponsiveLayoutController();
    const breakpoints = controller.getBreakpoints();
    
    // Try to modify returned breakpoints
    breakpoints.mobile = 999;
    
    // Get breakpoints again
    const breakpoints2 = controller.getBreakpoints();
    
    // Original should be unchanged
    assert.strictEqual(breakpoints2.mobile, 0, 'Breakpoints should be immutable');
    
    console.log('✓ Property 5: Breakpoints are immutable');
  });
});
