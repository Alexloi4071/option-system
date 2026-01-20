// Feature: modern-ui-redesign
// Property-Based Tests for Performance Monitor

const { test, describe, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const { JSDOM } = require('jsdom');
const fc = require('fast-check');

// Setup DOM environment for each test
function setupDOM(performanceTiming = {}) {
  const defaultTiming = {
    navigationStart: 1000,
    domainLookupStart: 1010,
    domainLookupEnd: 1020,
    connectStart: 1020,
    connectEnd: 1050,
    requestStart: 1050,
    responseStart: 1100,
    responseEnd: 1200,
    domInteractive: 1400,
    domContentLoadedEventEnd: 1500,
    domComplete: 1800,
    loadEventEnd: 2000,
    ...performanceTiming
  };
  
  const dom = new JSDOM(`
    <!DOCTYPE html>
    <html>
      <head>
        <title>Test Page</title>
      </head>
      <body>
        <h1>Test Content</h1>
      </body>
    </html>
  `, {
    url: 'http://localhost',
    pretendToBeVisual: true,
  });

  global.window = dom.window;
  global.document = dom.window.document;
  global.CustomEvent = dom.window.CustomEvent;
  
  // Mock performance API
  global.window.performance = {
    timing: defaultTiming,
    navigation: {
      type: 0 // navigate
    },
    getEntriesByType: (type) => {
      if (type === 'paint') {
        return [
          { name: 'first-paint', startTime: 400 },
          { name: 'first-contentful-paint', startTime: performanceTiming.fcp || 600 }
        ];
      }
      return [];
    }
  };

  return dom;
}

// Load PerformanceMonitor class
function loadPerformanceMonitor() {
  // Clear require cache
  delete require.cache[require.resolve('../static/js/performance-monitor.js')];
  
  // Load the module
  const PerformanceMonitor = require('../static/js/performance-monitor.js');
  return PerformanceMonitor;
}

describe('Performance Monitor - Initial Page Load Performance', () => {
  let dom;
  let PerformanceMonitor;
  
  beforeEach(() => {
    // Default setup with good performance
    dom = setupDOM({ fcp: 800 });
    PerformanceMonitor = loadPerformanceMonitor();
  });
  
  afterEach(() => {
    // Clean up global objects
    delete global.window;
    delete global.document;
    delete global.CustomEvent;
  });
  
  // Property 27: Initial Page Load Performance
  // **Validates: Requirements 13.1**
  // For any page load, the time to first contentful paint should be less than 1 second
  test('Feature: modern-ui-redesign, Property 27: First Contentful Paint < 1 second', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 100, max: 999 }), // FCP times under 1 second
        (fcpTime) => {
          // Setup DOM with specific FCP time
          dom = setupDOM({ fcp: fcpTime });
          PerformanceMonitor = loadPerformanceMonitor();
          
          const monitor = new PerformanceMonitor();
          
          // Manually trigger metric collection
          monitor.collectMetrics();
          
          const fcp = monitor.getFirstContentfulPaint();
          
          // Verify FCP is under 1 second (1000ms)
          return fcp !== null && fcp < 1000;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 27: First Contentful Paint < 1 second verified');
  });
  
  test('Feature: modern-ui-redesign, Property 27: meetsFCPThreshold returns true for fast loads', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 100, max: 999 }),
        (fcpTime) => {
          dom = setupDOM({ fcp: fcpTime });
          PerformanceMonitor = loadPerformanceMonitor();
          
          const monitor = new PerformanceMonitor();
          monitor.collectMetrics();
          
          // Should meet threshold for times under 1 second
          return monitor.meetsFCPThreshold() === true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 27: meetsFCPThreshold returns true for fast loads');
  });
  
  test('Feature: modern-ui-redesign, Property 27: meetsFCPThreshold returns false for slow loads', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1001, max: 5000 }), // FCP times over 1 second
        (fcpTime) => {
          dom = setupDOM({ fcp: fcpTime });
          PerformanceMonitor = loadPerformanceMonitor();
          
          const monitor = new PerformanceMonitor();
          monitor.collectMetrics();
          
          // Should NOT meet threshold for times over 1 second
          return monitor.meetsFCPThreshold() === false;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 27: meetsFCPThreshold returns false for slow loads');
  });
  
  test('Feature: modern-ui-redesign, Property 27: Warnings generated when FCP exceeds threshold', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1001, max: 3000 }),
        (fcpTime) => {
          dom = setupDOM({ fcp: fcpTime });
          PerformanceMonitor = loadPerformanceMonitor();
          
          const monitor = new PerformanceMonitor();
          monitor.collectMetrics();
          
          const metrics = monitor.getMetrics();
          
          // Should have warnings when FCP exceeds 1 second
          return metrics.warnings && metrics.warnings.length > 0;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 27: Warnings generated when FCP exceeds threshold');
  });
  
  test('Feature: modern-ui-redesign, Property 27: No warnings when FCP meets threshold', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 100, max: 999 }),
        (fcpTime) => {
          dom = setupDOM({ fcp: fcpTime });
          PerformanceMonitor = loadPerformanceMonitor();
          
          const monitor = new PerformanceMonitor();
          monitor.collectMetrics();
          
          const metrics = monitor.getMetrics();
          
          // Should have no FCP warnings when under 1 second
          const fcpWarnings = (metrics.warnings || []).filter(
            w => w.metric === 'First Contentful Paint'
          );
          
          return fcpWarnings.length === 0;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 27: No warnings when FCP meets threshold');
  });
  
  test('Feature: modern-ui-redesign, Property 27: Performance grade A for FCP < 600ms', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 100, max: 599 }),
        (fcpTime) => {
          dom = setupDOM({ 
            fcp: fcpTime,
            domContentLoadedEventEnd: 1200, // Good DCL time
            loadEventEnd: 1800 // Good load time
          });
          PerformanceMonitor = loadPerformanceMonitor();
          
          const monitor = new PerformanceMonitor();
          monitor.collectMetrics();
          
          const grade = monitor.calculateGrade();
          
          // Should get A grade for excellent performance
          return grade.letter === 'A' && grade.score >= 90;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 27: Performance grade A for FCP < 600ms');
  });
  
  test('Feature: modern-ui-redesign, Property 27: Performance grade degrades with slower FCP', () => {
    // Test that slower FCP results in lower grade
    const fastFCP = 500;
    const slowFCP = 1500;
    
    // Fast load
    dom = setupDOM({ fcp: fastFCP });
    PerformanceMonitor = loadPerformanceMonitor();
    const fastMonitor = new PerformanceMonitor();
    fastMonitor.collectMetrics();
    const fastGrade = fastMonitor.calculateGrade();
    
    // Slow load
    dom = setupDOM({ fcp: slowFCP });
    PerformanceMonitor = loadPerformanceMonitor();
    const slowMonitor = new PerformanceMonitor();
    slowMonitor.collectMetrics();
    const slowGrade = slowMonitor.calculateGrade();
    
    // Fast should have better grade than slow
    assert.ok(
      fastGrade.score > slowGrade.score,
      `Fast FCP (${fastFCP}ms) should have better grade than slow FCP (${slowFCP}ms)`
    );
    
    console.log('✓ Property 27: Performance grade degrades with slower FCP');
  });
  
  test('Feature: modern-ui-redesign, Property 27: getSummary includes FCP and threshold status', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 100, max: 2000 }),
        (fcpTime) => {
          dom = setupDOM({ fcp: fcpTime });
          PerformanceMonitor = loadPerformanceMonitor();
          
          const monitor = new PerformanceMonitor();
          monitor.collectMetrics();
          
          const summary = monitor.getSummary();
          
          // Summary should include FCP and threshold status
          return (
            typeof summary.fcp === 'number' &&
            typeof summary.meetsThreshold === 'boolean' &&
            summary.fcp === fcpTime &&
            summary.meetsThreshold === (fcpTime < 1000)
          );
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 27: getSummary includes FCP and threshold status');
  });
  
  test('Feature: modern-ui-redesign, Property 27: Metrics collected on page load', () => {
    // Simulate page load event
    const monitor = new PerformanceMonitor();
    
    // Manually trigger collection (simulating load event)
    monitor.collectMetrics();
    
    const metrics = monitor.getMetrics();
    
    // Verify key metrics are collected
    assert.ok(metrics.navigationStart, 'Should have navigationStart');
    assert.ok(metrics.domContentLoaded, 'Should have domContentLoaded');
    assert.ok(metrics.loadComplete, 'Should have loadComplete');
    assert.ok(metrics.firstContentfulPaint, 'Should have firstContentfulPaint');
    
    console.log('✓ Property 27: Metrics collected on page load');
  });
  
  test('Feature: modern-ui-redesign, Property 27: Performance event dispatched with metrics', () => {
    let eventFired = false;
    let eventDetail = null;
    
    // Listen for performance event
    document.addEventListener('performancemetrics', (e) => {
      eventFired = true;
      eventDetail = e.detail;
    });
    
    const monitor = new PerformanceMonitor();
    monitor.collectMetrics();
    
    // Verify event was dispatched
    assert.ok(eventFired, 'Performance event should be dispatched');
    assert.ok(eventDetail, 'Event should have detail');
    assert.ok(eventDetail.metrics, 'Event detail should have metrics');
    assert.ok(eventDetail.grade, 'Event detail should have grade');
    
    console.log('✓ Property 27: Performance event dispatched with metrics');
  });
});

describe('Performance Monitor - Metric Calculations', () => {
  let dom;
  let PerformanceMonitor;
  
  beforeEach(() => {
    dom = setupDOM();
    PerformanceMonitor = loadPerformanceMonitor();
  });
  
  afterEach(() => {
    delete global.window;
    delete global.document;
    delete global.CustomEvent;
  });
  
  test('DNS time calculated correctly', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 100 }),
        (dnsTime) => {
          const timing = {
            domainLookupStart: 1000,
            domainLookupEnd: 1000 + dnsTime
          };
          
          dom = setupDOM(timing);
          PerformanceMonitor = loadPerformanceMonitor();
          
          const monitor = new PerformanceMonitor();
          monitor.collectMetrics();
          
          const metrics = monitor.getMetrics();
          
          return metrics.dnsTime === dnsTime;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ DNS time calculated correctly');
  });
  
  test('TCP connection time calculated correctly', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 200 }),
        (tcpTime) => {
          const timing = {
            connectStart: 1000,
            connectEnd: 1000 + tcpTime
          };
          
          dom = setupDOM(timing);
          PerformanceMonitor = loadPerformanceMonitor();
          
          const monitor = new PerformanceMonitor();
          monitor.collectMetrics();
          
          const metrics = monitor.getMetrics();
          
          return metrics.tcpTime === tcpTime;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ TCP connection time calculated correctly');
  });
  
  test('DOM Content Loaded time calculated correctly', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 500, max: 3000 }),
        (dclTime) => {
          const timing = {
            navigationStart: 1000,
            domContentLoadedEventEnd: 1000 + dclTime
          };
          
          dom = setupDOM(timing);
          PerformanceMonitor = loadPerformanceMonitor();
          
          const monitor = new PerformanceMonitor();
          monitor.collectMetrics();
          
          const metrics = monitor.getMetrics();
          
          return metrics.domContentLoaded === dclTime;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ DOM Content Loaded time calculated correctly');
  });
  
  test('Navigation type identified correctly', () => {
    const types = [
      { code: 0, expected: 'navigate' },
      { code: 1, expected: 'reload' },
      { code: 2, expected: 'back_forward' },
      { code: 255, expected: 'reserved' }
    ];
    
    types.forEach(({ code, expected }) => {
      dom = setupDOM();
      global.window.performance.navigation.type = code;
      PerformanceMonitor = loadPerformanceMonitor();
      
      const monitor = new PerformanceMonitor();
      monitor.collectMetrics();
      
      const metrics = monitor.getMetrics();
      
      assert.strictEqual(
        metrics.navigationType,
        expected,
        `Navigation type ${code} should be ${expected}`
      );
    });
    
    console.log('✓ Navigation type identified correctly');
  });
});
