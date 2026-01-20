// Feature: modern-ui-redesign
// Property-Based Tests for Navigation Controller

const { test, describe, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const { JSDOM } = require('jsdom');
const fc = require('fast-check');

// Setup DOM environment for each test
function setupDOM(scrollY = 0) {
  const dom = new JSDOM(`
    <!DOCTYPE html>
    <html>
      <head></head>
      <body class="has-navbar">
        <nav class="navbar-modern">
          <div class="navbar-container">
            <div class="navbar-brand">
              <i class="fas fa-chart-line"></i>
              <span>期權制勝</span>
            </div>
            <div class="navbar-status">
              <span class="status-indicator" data-status="connected" id="ibkr-status">
                <i class="fas fa-circle"></i> IBKR
              </span>
            </div>
            <div class="navbar-actions">
              <button class="navbar-btn navbar-menu-toggle" aria-label="Toggle menu">
                <i class="fas fa-bars"></i>
              </button>
              <button class="navbar-btn" id="themeToggle" aria-label="Toggle theme">
                <i class="fas fa-moon"></i>
              </button>
            </div>
          </div>
        </nav>
        <div class="navbar-mobile-menu">
          <div class="mobile-status"></div>
        </div>
        <main>
          <div style="height: 3000px;">Content</div>
        </main>
      </body>
    </html>
  `, {
    url: 'http://localhost',
    pretendToBeVisual: true,
  });

  global.window = dom.window;
  global.document = dom.window.document;
  global.CustomEvent = dom.window.CustomEvent;
  
  // Mock scrollY
  Object.defineProperty(global.window, 'scrollY', {
    value: scrollY,
    writable: true,
    configurable: true
  });
  
  Object.defineProperty(global.window, 'pageYOffset', {
    value: scrollY,
    writable: true,
    configurable: true
  });
  
  // Mock requestAnimationFrame
  global.window.requestAnimationFrame = (callback) => {
    return setTimeout(callback, 0);
  };

  return dom;
}

// Load NavigationController class
function loadNavigationController() {
  // Clear require cache
  delete require.cache[require.resolve('../static/js/navigation-controller.js')];
  
  // Load the module
  const NavigationController = require('../static/js/navigation-controller.js');
  return NavigationController;
}

describe('Navigation Controller - Scroll Shadow', () => {
  let dom;
  let NavigationController;
  
  beforeEach(() => {
    dom = setupDOM(0);
    NavigationController = loadNavigationController();
  });
  
  afterEach(() => {
    // Clean up global objects
    delete global.window;
    delete global.document;
    delete global.CustomEvent;
  });
  
  // Property 17: Navigation Shadow on Scroll
  // Validates: Requirements 10.2
  // For any scroll event where scrollY > 0, the navigation bar should have a shadow class applied;
  // when scrollY === 0, the shadow should be removed.
  
  test('Feature: modern-ui-redesign, Property 17: Navigation has no shadow when scrollY is 0', () => {
    // Ensure scrollY is 0
    global.window.scrollY = 0;
    global.window.pageYOffset = 0;
    
    const controller = new NavigationController();
    controller.checkScroll();
    
    const navbar = global.document.querySelector('.navbar-modern');
    assert.ok(navbar, 'Navbar element should exist');
    assert.strictEqual(
      navbar.classList.contains('scrolled'),
      false,
      'Navbar should NOT have scrolled class when scrollY is 0'
    );
    
    console.log('✓ No shadow at scrollY = 0');
  });
  
  test('Feature: modern-ui-redesign, Property 17: Navigation has shadow when scrollY > 0', () => {
    // Set scrollY to a positive value
    global.window.scrollY = 100;
    global.window.pageYOffset = 100;
    
    const controller = new NavigationController();
    controller.checkScroll();
    
    const navbar = global.document.querySelector('.navbar-modern');
    assert.ok(navbar, 'Navbar element should exist');
    assert.strictEqual(
      navbar.classList.contains('scrolled'),
      true,
      'Navbar should have scrolled class when scrollY > 0'
    );
    
    console.log('✓ Shadow present at scrollY = 100');
  });
  
  test('Feature: modern-ui-redesign, Property 17: Property-based test for scroll shadow behavior', () => {
    // Property: For any scrollY, navbar should have 'scrolled' class iff scrollY > 0
    // We test this by using a single DOM instance and manually updating scroll position
    
    const controller = new NavigationController();
    const navbar = global.document.querySelector('.navbar-modern');
    assert.ok(navbar, 'Navbar element should exist');
    
    // Generate 100 random scroll values plus edge cases
    const scrollValues = [0, 1, 100, 500, 1000, 5000, 10000];
    for (let i = 0; i < 93; i++) {
      scrollValues.push(Math.floor(Math.random() * 10000));
    }
    
    let passCount = 0;
    
    scrollValues.forEach((scrollY) => {
      // Update scroll position
      global.window.scrollY = scrollY;
      global.window.pageYOffset = scrollY;
      
      // Reset controller state to the OPPOSITE of expected to force re-evaluation
      // If scrollY > 0, we expect scrolled=true, so set isScrolled=false to trigger update
      // If scrollY === 0, we expect scrolled=false, so set isScrolled=true to trigger update
      const expectedScrolled = scrollY > 0;
      controller.isScrolled = !expectedScrolled;
      controller.checkScroll();
      
      const hasScrolledClass = navbar.classList.contains('scrolled');
      
      // Property: scrollY > 0 implies scrolled class, scrollY === 0 implies no scrolled class
      const passed = hasScrolledClass === expectedScrolled;
      
      if (passed) passCount++;
      
      assert.ok(
        passed,
        `scrollY=${scrollY}: expected scrolled=${expectedScrolled}, got scrolled=${hasScrolledClass}`
      );
    });
    
    console.log(`✓ Property 17 verified with ${passCount}/${scrollValues.length} scroll positions`);
  });
  
  test('Feature: modern-ui-redesign, Property 17: Shadow toggles correctly when scrolling up and down', () => {
    const controller = new NavigationController();
    
    // Start at 0 - no shadow
    global.window.scrollY = 0;
    global.window.pageYOffset = 0;
    controller.checkScroll();
    
    let navbar = global.document.querySelector('.navbar-modern');
    assert.strictEqual(navbar.classList.contains('scrolled'), false, 'No shadow at start');
    
    // Scroll down - should add shadow
    global.window.scrollY = 50;
    global.window.pageYOffset = 50;
    controller.checkScroll();
    
    assert.strictEqual(navbar.classList.contains('scrolled'), true, 'Shadow after scroll down');
    
    // Scroll back to top - should remove shadow
    global.window.scrollY = 0;
    global.window.pageYOffset = 0;
    controller.checkScroll();
    
    assert.strictEqual(navbar.classList.contains('scrolled'), false, 'No shadow after scroll to top');
    
    console.log('✓ Shadow toggles correctly');
  });
  
  test('Feature: modern-ui-redesign, Property 17: Scroll event is dispatched with correct state', () => {
    const controller = new NavigationController();
    let eventFired = false;
    let eventDetail = null;
    
    global.document.addEventListener('navbarscroll', (e) => {
      eventFired = true;
      eventDetail = e.detail;
    });
    
    // Trigger scroll
    global.window.scrollY = 100;
    global.window.pageYOffset = 100;
    controller.checkScroll();
    
    assert.ok(eventFired, 'Scroll event should be dispatched');
    assert.strictEqual(eventDetail.isScrolled, true, 'Event should indicate scrolled state');
    assert.ok(eventDetail.timestamp, 'Event should have timestamp');
    
    console.log('✓ Scroll event dispatched correctly');
  });
  
  test('Feature: modern-ui-redesign, Property 17: getScrollState returns correct value', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 5000 }),
        (scrollY) => {
          // Reset DOM
          dom = setupDOM(scrollY);
          NavigationController = loadNavigationController();
          
          const controller = new NavigationController();
          controller.checkScroll();
          
          const expectedState = scrollY > 0;
          return controller.getScrollState() === expectedState;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ getScrollState returns correct value for 100 random positions');
  });
  
  test('Feature: modern-ui-redesign, Property 17: hasScrolledClass matches actual DOM state', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 5000 }),
        (scrollY) => {
          // Reset DOM
          dom = setupDOM(scrollY);
          NavigationController = loadNavigationController();
          
          const controller = new NavigationController();
          controller.checkScroll();
          
          const navbar = global.document.querySelector('.navbar-modern');
          const actualHasClass = navbar.classList.contains('scrolled');
          
          return controller.hasScrolledClass() === actualHasClass;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ hasScrolledClass matches DOM state for 100 random positions');
  });
});

describe('Navigation Controller - Status Indicators', () => {
  let dom;
  let NavigationController;
  
  beforeEach(() => {
    dom = setupDOM(0);
    NavigationController = loadNavigationController();
  });
  
  afterEach(() => {
    delete global.window;
    delete global.document;
    delete global.CustomEvent;
  });
  
  test('Status indicator updates correctly', () => {
    const controller = new NavigationController();
    
    // Update status
    controller.updateStatus('#ibkr-status', 'disconnected', 'IBKR Offline');
    
    const indicator = global.document.querySelector('#ibkr-status');
    assert.strictEqual(
      indicator.getAttribute('data-status'),
      'disconnected',
      'Status attribute should be updated'
    );
    
    console.log('✓ Status indicator updates correctly');
  });
  
  test('Status indicator handles various status values', () => {
    const controller = new NavigationController();
    const statuses = ['connected', 'disconnected', 'loading', 'warning', 'error', 'active'];
    
    statuses.forEach(status => {
      controller.updateStatus('#ibkr-status', status);
      
      const indicator = global.document.querySelector('#ibkr-status');
      assert.strictEqual(
        indicator.getAttribute('data-status'),
        status,
        `Status should be ${status}`
      );
    });
    
    console.log('✓ All status values handled correctly');
  });
});
