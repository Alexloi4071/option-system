// Feature: modern-ui-redesign
// Property-Based Tests for Progress Controller

const { test, describe, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const { JSDOM } = require('jsdom');
const fc = require('fast-check');

// Setup DOM environment for each test
function setupDOM() {
  const dom = new JSDOM(`
    <!DOCTYPE html>
    <html>
      <head>
        <style>
          :root {
            --progress-circle-size: 120px;
            --progress-circle-stroke-width: 8px;
            --progress-animation-duration: 300ms;
            --checkmark-animation-duration: 400ms;
            --color-primary: #2563eb;
            --color-success: #047857;
            --spacing-6: 1.5rem;
          }
        </style>
      </head>
      <body>
        <div id="progress-container" class="progress-modern idle">
          <div class="progress-circle">
            <svg viewBox="0 0 100 100">
              <circle class="progress-bg" cx="50" cy="50" r="45"></circle>
              <circle class="progress-bar" cx="50" cy="50" r="45" style="--progress: 0"></circle>
            </svg>
            <div class="progress-text">0%</div>
          </div>
          <div class="progress-details">
            <h5>準備分析...</h5>
            <p class="progress-step"></p>
            <div class="progress-time"></div>
            <div class="progress-modules">
              <div class="modules-title">已完成模塊:</div>
              <div class="modules-list"></div>
            </div>
          </div>
        </div>
      </body>
    </html>
  `, {
    url: 'http://localhost',
    pretendToBeVisual: true,
  });

  global.window = dom.window;
  global.document = dom.window.document;
  global.HTMLElement = dom.window.HTMLElement;
  global.SVGElement = dom.window.SVGElement;
  
  // Mock matchMedia for reduced motion detection
  global.window.matchMedia = (query) => ({
    matches: false,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  });

  return dom;
}

// Load ProgressController class
function loadProgressController() {
  delete require.cache[require.resolve('../static/js/progress-controller.js')];
  const ProgressController = require('../static/js/progress-controller.js');
  return ProgressController;
}

// Module names for testing
const MODULE_NAMES = [
  'Support/Resistance',
  'Fair Value',
  'Arbitrage Spread',
  'PE Valuation',
  'Rate PE Relation',
  'Hedge Quantity',
  'Long Call',
  'Long Put',
  'Short Call',
  'Short Put',
  'Synthetic Stock',
  'Annual Yield',
  'Position Analysis',
  'Monitoring Posts',
  'Black-Scholes',
  'Greeks',
  'Implied Volatility',
  'Historical Volatility',
  'Put-Call Parity',
  'Fundamental Health',
  'Momentum Filter',
  'Optimal Strike',
  'Dynamic IV Threshold',
  'Technical Direction',
  'Volatility Smile',
  'Long Option Analysis',
  'Multi-Expiry Comparison',
  'Position Calculator'
];

describe('Progress Controller - Progress Updates During Analysis', () => {
  let dom;
  let ProgressController;
  
  beforeEach(() => {
    dom = setupDOM();
    ProgressController = loadProgressController();
  });
  
  afterEach(() => {
    delete global.window;
    delete global.document;
    delete global.HTMLElement;
    delete global.SVGElement;
  });
  
  // Property 13: Progress Updates During Analysis
  // For any analysis execution, the progress indicator should update with 
  // current step name and completed modules list as each module completes.
  // Validates: Requirements 8.2
  test('Feature: modern-ui-redesign, Property 13: Progress updates with step name on each module', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 28 }), // Module index
        fc.constantFrom(...MODULE_NAMES), // Module name
        (moduleIndex, moduleName) => {
          const controller = new ProgressController();
          controller.init('#progress-container');
          controller.start();
          
          // Update progress with module info
          controller.updateProgress(moduleIndex, moduleName);
          
          // Verify step name is updated
          const currentStep = controller.getCurrentStep();
          if (currentStep !== moduleName) {
            console.log(`Step name mismatch: expected "${moduleName}", got "${currentStep}"`);
            return false;
          }
          
          // Verify progress percentage is calculated correctly
          const expectedProgress = Math.round((moduleIndex / 28) * 100);
          const actualProgress = controller.getProgress();
          if (actualProgress !== Math.min(expectedProgress, 100)) {
            console.log(`Progress mismatch: expected ${expectedProgress}, got ${actualProgress}`);
            return false;
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 13: Progress updates with step name verified');
  });
  
  test('Feature: modern-ui-redesign, Property 13: Completed modules list grows as modules complete', () => {
    fc.assert(
      fc.property(
        fc.array(fc.integer({ min: 1, max: 28 }), { minLength: 1, maxLength: 28 }),
        (moduleNumbers) => {
          const controller = new ProgressController();
          controller.init('#progress-container');
          controller.start();
          
          // Complete modules in sequence
          const uniqueModules = [...new Set(moduleNumbers)];
          uniqueModules.forEach((moduleNum, index) => {
            controller.completeModule(moduleNum, MODULE_NAMES[moduleNum - 1] || `Module ${moduleNum}`);
          });
          
          // Verify completed modules list
          const completedModules = controller.getCompletedModules();
          
          // Should have same number of unique modules
          if (completedModules.length !== uniqueModules.length) {
            console.log(`Completed modules count mismatch: expected ${uniqueModules.length}, got ${completedModules.length}`);
            return false;
          }
          
          // All completed modules should be in the list
          for (const moduleNum of uniqueModules) {
            if (!completedModules.includes(moduleNum)) {
              console.log(`Module ${moduleNum} not found in completed list`);
              return false;
            }
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 13: Completed modules list grows correctly');
  });
  
  test('Feature: modern-ui-redesign, Property 13: Progress percentage increases with completed modules', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 28 }), // Number of modules to complete
        (modulesToComplete) => {
          const controller = new ProgressController();
          controller.init('#progress-container');
          controller.start();
          
          let previousProgress = 0;
          
          // Complete modules one by one
          for (let i = 1; i <= modulesToComplete; i++) {
            controller.completeModule(i, MODULE_NAMES[i - 1] || `Module ${i}`);
            
            const currentProgress = controller.getProgress();
            
            // Progress should increase or stay same (never decrease)
            if (currentProgress < previousProgress) {
              console.log(`Progress decreased: was ${previousProgress}, now ${currentProgress}`);
              return false;
            }
            
            previousProgress = currentProgress;
          }
          
          // Final progress should match expected
          const expectedProgress = Math.round((modulesToComplete / 28) * 100);
          const actualProgress = controller.getProgress();
          
          if (actualProgress !== Math.min(expectedProgress, 100)) {
            console.log(`Final progress mismatch: expected ${expectedProgress}, got ${actualProgress}`);
            return false;
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 13: Progress percentage increases correctly');
  });
  
  test('Feature: modern-ui-redesign, Property 13: DOM elements are updated on progress change', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 28 }),
        fc.constantFrom(...MODULE_NAMES),
        (moduleIndex, moduleName) => {
          const controller = new ProgressController();
          controller.init('#progress-container');
          controller.start();
          
          // Update progress
          controller.updateProgress(moduleIndex, moduleName);
          
          // Check DOM elements
          const stepElement = document.querySelector('.progress-step');
          const progressText = document.querySelector('.progress-text');
          
          // Step name should be in DOM
          if (stepElement && stepElement.textContent !== moduleName) {
            console.log(`DOM step mismatch: expected "${moduleName}", got "${stepElement.textContent}"`);
            return false;
          }
          
          // Progress text should show percentage
          const expectedProgress = Math.round((moduleIndex / 28) * 100);
          if (progressText && !progressText.textContent.includes(`${Math.min(expectedProgress, 100)}%`)) {
            console.log(`DOM progress text mismatch: expected "${expectedProgress}%", got "${progressText.textContent}"`);
            return false;
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 13: DOM elements updated on progress change');
  });
  
  test('Feature: modern-ui-redesign, Property 13: Time remaining is calculated and displayed', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 27 }), // Not all modules (so there's remaining time)
        (completedCount) => {
          // Use a controller without startTime to use default estimate
          const controller = new ProgressController({ timePerModule: 2 });
          controller.init('#progress-container');
          
          // Don't call start() - this way calculateRemainingTime uses default estimate
          // Just set status manually
          controller.status = 'running';
          
          // Complete some modules (without timing data)
          for (let i = 1; i <= completedCount; i++) {
            if (!controller.completedModules.includes(i)) {
              controller.completedModules.push(i);
            }
          }
          
          // Calculate remaining time using default estimate
          const remainingTime = controller.calculateRemainingTime();
          const remainingModules = 28 - completedCount;
          const expectedTime = remainingModules * 2; // timePerModule = 2
          
          // Remaining time should match expected (using default estimate)
          if (remainingTime !== expectedTime) {
            console.log(`Remaining time mismatch: expected ${expectedTime}, got ${remainingTime}`);
            return false;
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 13: Time remaining calculated and displayed');
  });
  
  test('Feature: modern-ui-redesign, Property 13: Status transitions correctly during analysis', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 28 }),
        (modulesToComplete) => {
          const controller = new ProgressController();
          controller.init('#progress-container');
          
          // Initial status should be idle
          if (controller.getStatus() !== 'idle') {
            console.log(`Initial status should be idle, got ${controller.getStatus()}`);
            return false;
          }
          
          // Start analysis
          controller.start();
          if (controller.getStatus() !== 'running') {
            console.log(`Status after start should be running, got ${controller.getStatus()}`);
            return false;
          }
          
          // Complete modules
          for (let i = 1; i <= modulesToComplete; i++) {
            controller.completeModule(i);
          }
          
          // Status should still be running
          if (controller.getStatus() !== 'running') {
            console.log(`Status during analysis should be running, got ${controller.getStatus()}`);
            return false;
          }
          
          // Complete analysis
          controller.complete();
          if (controller.getStatus() !== 'completed') {
            console.log(`Status after complete should be completed, got ${controller.getStatus()}`);
            return false;
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 13: Status transitions correctly');
  });
  
  test('Feature: modern-ui-redesign, Property 13: Duplicate module completions are ignored', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 28 }),
        fc.integer({ min: 2, max: 5 }), // Number of times to complete same module
        (moduleNumber, repeatCount) => {
          const controller = new ProgressController();
          controller.init('#progress-container');
          controller.start();
          
          // Complete same module multiple times
          for (let i = 0; i < repeatCount; i++) {
            controller.completeModule(moduleNumber);
          }
          
          // Should only have one entry
          const completedModules = controller.getCompletedModules();
          const occurrences = completedModules.filter(m => m === moduleNumber).length;
          
          if (occurrences !== 1) {
            console.log(`Module ${moduleNumber} appears ${occurrences} times, expected 1`);
            return false;
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 13: Duplicate module completions ignored');
  });
});

describe('Progress Controller - Time Formatting', () => {
  let dom;
  let ProgressController;
  
  beforeEach(() => {
    dom = setupDOM();
    ProgressController = loadProgressController();
  });
  
  afterEach(() => {
    delete global.window;
    delete global.document;
    delete global.HTMLElement;
    delete global.SVGElement;
  });
  
  test('Time formatting: seconds only for < 60 seconds', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 59 }),
        (seconds) => {
          const controller = new ProgressController();
          const formatted = controller.formatTime(seconds);
          
          // Should contain "秒" and the number
          return formatted.includes('秒') && formatted.includes(String(seconds));
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Time formatting for seconds verified');
  });
  
  test('Time formatting: minutes and seconds for >= 60 seconds', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 60, max: 3600 }),
        (seconds) => {
          const controller = new ProgressController();
          const formatted = controller.formatTime(seconds);
          
          // Should contain "分" for minutes
          return formatted.includes('分');
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Time formatting for minutes verified');
  });
});

describe('Progress Controller - Reset Functionality', () => {
  let dom;
  let ProgressController;
  
  beforeEach(() => {
    dom = setupDOM();
    ProgressController = loadProgressController();
  });
  
  afterEach(() => {
    delete global.window;
    delete global.document;
    delete global.HTMLElement;
    delete global.SVGElement;
  });
  
  test('Reset clears all state', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 28 }),
        (modulesToComplete) => {
          const controller = new ProgressController();
          controller.init('#progress-container');
          controller.start();
          
          // Complete some modules
          for (let i = 1; i <= modulesToComplete; i++) {
            controller.completeModule(i);
          }
          
          // Reset
          controller.reset();
          
          // Verify all state is cleared
          if (controller.getProgress() !== 0) {
            console.log(`Progress should be 0 after reset, got ${controller.getProgress()}`);
            return false;
          }
          
          if (controller.getCurrentStep() !== '') {
            console.log(`Step should be empty after reset, got "${controller.getCurrentStep()}"`);
            return false;
          }
          
          if (controller.getCompletedModules().length !== 0) {
            console.log(`Completed modules should be empty after reset`);
            return false;
          }
          
          if (controller.getStatus() !== 'idle') {
            console.log(`Status should be idle after reset, got ${controller.getStatus()}`);
            return false;
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Reset clears all state verified');
  });
});


describe('Progress Controller - Module Completion Checkmark', () => {
  let dom;
  let ProgressController;
  
  beforeEach(() => {
    dom = setupDOM();
    ProgressController = loadProgressController();
  });
  
  afterEach(() => {
    delete global.window;
    delete global.document;
    delete global.HTMLElement;
    delete global.SVGElement;
  });
  
  // Property 14: Module Completion Checkmark
  // For any module that completes successfully, a checkmark icon with animation 
  // should be displayed in the completed modules list.
  // Validates: Requirements 8.4
  test('Feature: modern-ui-redesign, Property 14: Completed module displays checkmark icon', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 28 }),
        fc.constantFrom(...MODULE_NAMES),
        (moduleNumber, moduleName) => {
          const controller = new ProgressController();
          controller.init('#progress-container');
          controller.start();
          
          // Complete a module
          controller.completeModule(moduleNumber, moduleName);
          
          // Find the module badge in the DOM
          const modulesList = document.querySelector('.modules-list');
          const badge = modulesList.querySelector(`[data-module="${moduleNumber}"]`);
          
          // Badge should exist
          if (!badge) {
            console.log(`Badge for module ${moduleNumber} not found`);
            return false;
          }
          
          // Badge should have completed class
          if (!badge.classList.contains('completed')) {
            console.log(`Badge for module ${moduleNumber} missing 'completed' class`);
            return false;
          }
          
          // Badge should contain a checkmark SVG
          const checkmark = badge.querySelector('.checkmark-svg, .checkmark-icon');
          if (!checkmark) {
            console.log(`Checkmark not found in badge for module ${moduleNumber}`);
            return false;
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 14: Completed module displays checkmark icon');
  });
  
  test('Feature: modern-ui-redesign, Property 14: Checkmark SVG has correct structure', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 28 }),
        (moduleNumber) => {
          const controller = new ProgressController();
          controller.init('#progress-container');
          controller.start();
          
          // Complete a module
          controller.completeModule(moduleNumber);
          
          // Find the checkmark SVG
          const modulesList = document.querySelector('.modules-list');
          const badge = modulesList.querySelector(`[data-module="${moduleNumber}"]`);
          const checkmarkSvg = badge.querySelector('svg');
          
          // SVG should exist
          if (!checkmarkSvg) {
            console.log(`SVG not found for module ${moduleNumber}`);
            return false;
          }
          
          // SVG should have viewBox attribute
          const viewBox = checkmarkSvg.getAttribute('viewBox');
          if (!viewBox) {
            console.log(`SVG missing viewBox attribute`);
            return false;
          }
          
          // SVG should contain a path element (the checkmark)
          const path = checkmarkSvg.querySelector('path');
          if (!path) {
            console.log(`SVG missing path element`);
            return false;
          }
          
          // Path should have the checkmark-path class
          if (!path.classList.contains('checkmark-path')) {
            console.log(`Path missing checkmark-path class`);
            return false;
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 14: Checkmark SVG has correct structure');
  });
  
  test('Feature: modern-ui-redesign, Property 14: Multiple completed modules each have checkmarks', () => {
    fc.assert(
      fc.property(
        fc.array(fc.integer({ min: 1, max: 28 }), { minLength: 2, maxLength: 10 }),
        (moduleNumbers) => {
          const controller = new ProgressController();
          controller.init('#progress-container');
          controller.start();
          
          // Complete multiple modules
          const uniqueModules = [...new Set(moduleNumbers)];
          uniqueModules.forEach(moduleNum => {
            controller.completeModule(moduleNum);
          });
          
          // Each completed module should have a checkmark
          const modulesList = document.querySelector('.modules-list');
          
          for (const moduleNum of uniqueModules) {
            const badge = modulesList.querySelector(`[data-module="${moduleNum}"]`);
            
            if (!badge) {
              console.log(`Badge for module ${moduleNum} not found`);
              return false;
            }
            
            const checkmark = badge.querySelector('svg');
            if (!checkmark) {
              console.log(`Checkmark not found for module ${moduleNum}`);
              return false;
            }
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 14: Multiple completed modules each have checkmarks');
  });
  
  test('Feature: modern-ui-redesign, Property 14: Checkmark has animation class when motion enabled', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 28 }),
        (moduleNumber) => {
          const controller = new ProgressController();
          // Ensure reduced motion is false
          controller.reducedMotion = false;
          controller.init('#progress-container');
          controller.start();
          
          // Complete a module
          controller.completeModule(moduleNumber);
          
          // Find the checkmark SVG
          const modulesList = document.querySelector('.modules-list');
          const badge = modulesList.querySelector(`[data-module="${moduleNumber}"]`);
          const checkmarkSvg = badge.querySelector('svg');
          
          // SVG should have animation class when motion is enabled
          if (!checkmarkSvg.classList.contains('checkmark-animated')) {
            console.log(`Checkmark missing animation class for module ${moduleNumber}`);
            return false;
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 14: Checkmark has animation class when motion enabled');
  });
  
  test('Feature: modern-ui-redesign, Property 14: Checkmark skips animation when reduced motion', () => {
    // Mock reduced motion preference
    global.window.matchMedia = (query) => ({
      matches: query === '(prefers-reduced-motion: reduce)',
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
    });
    
    // Reload controller with reduced motion
    ProgressController = loadProgressController();
    
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 28 }),
        (moduleNumber) => {
          const controller = new ProgressController();
          controller.init('#progress-container');
          controller.start();
          
          // Complete a module
          controller.completeModule(moduleNumber);
          
          // Find the checkmark SVG
          const modulesList = document.querySelector('.modules-list');
          const badge = modulesList.querySelector(`[data-module="${moduleNumber}"]`);
          const checkmarkSvg = badge.querySelector('svg');
          
          // SVG should NOT have animation class when reduced motion is enabled
          if (checkmarkSvg.classList.contains('checkmark-animated')) {
            console.log(`Checkmark should not have animation class with reduced motion`);
            return false;
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 14: Checkmark skips animation when reduced motion');
  });
  
  test('Feature: modern-ui-redesign, Property 14: createCheckmarkSVG returns valid SVG element', () => {
    fc.assert(
      fc.property(
        fc.boolean(), // animated or not
        (animated) => {
          const controller = new ProgressController();
          controller.reducedMotion = false;
          
          const svg = controller.createCheckmarkSVG(animated);
          
          // Should be an SVG element
          if (svg.tagName.toLowerCase() !== 'svg') {
            console.log(`Expected SVG element, got ${svg.tagName}`);
            return false;
          }
          
          // Should have checkmark-svg class
          if (!svg.classList.contains('checkmark-svg')) {
            console.log(`Missing checkmark-svg class`);
            return false;
          }
          
          // Should have animation class only when animated is true
          const hasAnimationClass = svg.classList.contains('checkmark-animated');
          if (animated && !hasAnimationClass) {
            console.log(`Missing animation class when animated=true`);
            return false;
          }
          
          // Should contain a path element
          const path = svg.querySelector('path');
          if (!path) {
            console.log(`Missing path element`);
            return false;
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 14: createCheckmarkSVG returns valid SVG element');
  });
  
  test('Feature: modern-ui-redesign, Property 14: Badge has correct title attribute', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 28 }),
        fc.constantFrom(...MODULE_NAMES),
        (moduleNumber, moduleName) => {
          // Clear the modules list before each iteration
          const modulesList = document.querySelector('.modules-list');
          modulesList.innerHTML = '';
          
          const controller = new ProgressController();
          controller.init('#progress-container');
          controller.start();
          
          // Complete a module with name
          controller.completeModule(moduleNumber, moduleName);
          
          // Find the badge
          const badge = modulesList.querySelector(`[data-module="${moduleNumber}"]`);
          
          // Badge should have title attribute with module name
          const title = badge.getAttribute('title');
          if (title !== moduleName) {
            console.log(`Badge title mismatch: expected "${moduleName}", got "${title}"`);
            return false;
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 14: Badge has correct title attribute');
  });
});
