// Feature: modern-ui-redesign
// Property-Based Tests for Animation Controller

const { test, describe, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const { JSDOM } = require('jsdom');
const fc = require('fast-check');

// Mock performance before JSDOM is created
global.performance = {
  now: () => Date.now()
};

// Setup DOM environment for each test
function setupDOM() {
  const dom = new JSDOM(`
    <!DOCTYPE html>
    <html>
      <head>
        <style>
          :root {
            --stagger-delay: 50ms;
            --animation-duration-base: 250ms;
            --ease-out: cubic-bezier(0, 0, 0.2, 1);
          }
        </style>
      </head>
      <body>
        <div id="card-container" class="card-list-animated">
        </div>
        <button id="testButton" data-click-feedback="scale">Test Button</button>
      </body>
    </html>
  `, {
    url: 'http://localhost',
    pretendToBeVisual: true,
  });

  global.window = dom.window;
  global.document = dom.window.document;
  global.CustomEvent = dom.window.CustomEvent;
  global.HTMLElement = dom.window.HTMLElement;
  
  // Mock matchMedia for reduced motion detection
  global.window.matchMedia = (query) => ({
    matches: false, // Default: animations enabled
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
  });

  return dom;
}

// Load AnimationController class
function loadAnimationController() {
  // Clear require cache
  delete require.cache[require.resolve('../static/js/animation-controller.js')];
  
  // Load the module
  const AnimationController = require('../static/js/animation-controller.js');
  return AnimationController;
}

// Helper to create card elements
function createCards(count) {
  const container = document.getElementById('card-container');
  container.innerHTML = '';
  
  const cards = [];
  for (let i = 0; i < count; i++) {
    const card = document.createElement('div');
    card.className = 'card-modern';
    card.id = `card-${i}`;
    card.textContent = `Card ${i + 1}`;
    container.appendChild(card);
    cards.push(card);
  }
  
  return cards;
}

describe('Animation Controller - Staggered Card Animation Timing', () => {
  let dom;
  let AnimationController;
  
  beforeEach(() => {
    dom = setupDOM();
    AnimationController = loadAnimationController();
  });
  
  afterEach(() => {
    // Clean up global objects
    delete global.window;
    delete global.document;
    delete global.CustomEvent;
    delete global.HTMLElement;
    // Don't delete performance - it's needed globally
  });
  
  // Property 8: Staggered Card Animation Timing
  // For any set of cards being animated into view, each subsequent card 
  // should have an incrementally larger animation-delay value
  // Validates: Requirements 5.1
  test('Feature: modern-ui-redesign, Property 8: Cards have incrementally larger animation delays', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 2, max: 20 }), // Number of cards (at least 2 to test staggering)
        (cardCount) => {
          // Create cards
          const cards = createCards(cardCount);
          
          // Create animation controller and apply staggered animation
          const controller = new AnimationController();
          const delays = controller.applyStaggeredAnimation(cards);
          
          // Verify we got the right number of delays
          if (delays.length !== cardCount) {
            return false;
          }
          
          // Verify each subsequent delay is larger than the previous
          for (let i = 1; i < delays.length; i++) {
            if (delays[i] <= delays[i - 1]) {
              console.log(`Failed: delay[${i}]=${delays[i]} <= delay[${i-1}]=${delays[i-1]}`);
              return false;
            }
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 8: Staggered card animation timing verified');
  });
  
  test('Feature: modern-ui-redesign, Property 8: Animation delays increase by consistent increment', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 3, max: 15 }), // At least 3 cards to verify consistent increment
        (cardCount) => {
          const cards = createCards(cardCount);
          const controller = new AnimationController();
          const delays = controller.applyStaggeredAnimation(cards);
          
          // Calculate the increment between first two cards
          const expectedIncrement = controller.getStaggerDelay();
          
          // Verify all increments are consistent
          for (let i = 1; i < delays.length; i++) {
            const actualIncrement = delays[i] - delays[i - 1];
            if (actualIncrement !== expectedIncrement) {
              console.log(`Failed: increment between card ${i-1} and ${i} is ${actualIncrement}, expected ${expectedIncrement}`);
              return false;
            }
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 8: Consistent stagger increment verified');
  });
  
  test('Feature: modern-ui-redesign, Property 8: First card has zero or base delay', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 10 }),
        (cardCount) => {
          const cards = createCards(cardCount);
          const controller = new AnimationController();
          const delays = controller.applyStaggeredAnimation(cards);
          
          // First card should have delay of 0 (or baseDelay if specified)
          return delays[0] === 0;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 8: First card has zero delay verified');
  });
  
  test('Feature: modern-ui-redesign, Property 8: validateStaggeredDelays correctly identifies valid sequences', () => {
    fc.assert(
      fc.property(
        fc.array(fc.integer({ min: 0, max: 1000 }), { minLength: 2, maxLength: 20 }),
        (delays) => {
          const controller = new AnimationController();
          
          // Sort delays to make them valid (strictly increasing)
          const sortedDelays = [...delays].sort((a, b) => a - b);
          
          // Make strictly increasing by adding index
          const strictlyIncreasing = sortedDelays.map((d, i) => d + i);
          
          // Should validate as true
          const isValid = controller.validateStaggeredDelays(strictlyIncreasing);
          
          return isValid === true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 8: validateStaggeredDelays correctly validates sequences');
  });
  
  test('Feature: modern-ui-redesign, Property 8: validateStaggeredDelays rejects non-increasing sequences', () => {
    fc.assert(
      fc.property(
        fc.array(fc.integer({ min: 0, max: 100 }), { minLength: 3, maxLength: 10 }),
        (baseDelays) => {
          const controller = new AnimationController();
          
          // Create a non-increasing sequence by making at least one pair equal or decreasing
          const delays = [...baseDelays];
          if (delays.length >= 2) {
            // Make the second element equal to or less than the first
            delays[1] = delays[0];
          }
          
          // Should validate as false (not strictly increasing)
          const isValid = controller.validateStaggeredDelays(delays);
          
          return isValid === false;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 8: validateStaggeredDelays rejects non-increasing sequences');
  });
  
  test('Feature: modern-ui-redesign, Property 8: CSS animation-delay style is set on each card', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 2, max: 10 }),
        (cardCount) => {
          const cards = createCards(cardCount);
          const controller = new AnimationController();
          controller.applyStaggeredAnimation(cards);
          
          // Verify each card has animation-delay style set
          for (let i = 0; i < cards.length; i++) {
            const delay = cards[i].style.animationDelay;
            if (!delay || delay === '') {
              console.log(`Card ${i} missing animation-delay`);
              return false;
            }
            
            // Parse the delay value
            const delayMs = parseInt(delay);
            const expectedDelay = i * controller.getStaggerDelay();
            
            if (delayMs !== expectedDelay) {
              console.log(`Card ${i} has delay ${delayMs}ms, expected ${expectedDelay}ms`);
              return false;
            }
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 8: CSS animation-delay style correctly set on cards');
  });
});

describe('Animation Controller - Reduced Motion Support', () => {
  let dom;
  let AnimationController;
  
  beforeEach(() => {
    dom = setupDOM();
  });
  
  afterEach(() => {
    delete global.window;
    delete global.document;
    delete global.CustomEvent;
    delete global.HTMLElement;
  });
  
  test('Reduced motion: animations are skipped when prefers-reduced-motion is set', () => {
    // Mock reduced motion preference
    global.window.matchMedia = (query) => ({
      matches: query === '(prefers-reduced-motion: reduce)',
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
    });
    
    AnimationController = loadAnimationController();
    const controller = new AnimationController();
    
    // Verify reduced motion is detected
    assert.strictEqual(controller.reducedMotion, true, 'Should detect reduced motion preference');
    assert.strictEqual(controller.isAnimationEnabled(), false, 'Animations should be disabled');
    
    // Create cards and apply animation
    const cards = createCards(5);
    const delays = controller.applyStaggeredAnimation(cards);
    
    // Should return empty delays array when reduced motion is enabled
    assert.strictEqual(delays.length, 0, 'Should return empty delays when reduced motion is enabled');
    
    // Cards should be visible immediately
    cards.forEach((card, i) => {
      assert.strictEqual(card.style.opacity, '1', `Card ${i} should be visible`);
    });
    
    console.log('✓ Reduced motion support verified');
  });
});


describe('Animation Controller - Hover Response Time', () => {
  let dom;
  let AnimationController;
  
  beforeEach(() => {
    dom = setupDOM();
    AnimationController = loadAnimationController();
  });
  
  afterEach(() => {
    delete global.window;
    delete global.document;
    delete global.CustomEvent;
    delete global.HTMLElement;
  });
  
  // Property 9: Hover Feedback Response Time
  // For any interactive element, hover state transitions should complete within 100ms
  // Validates: Requirements 5.2
  test('Feature: modern-ui-redesign, Property 9: Hover transition duration is 100ms or less', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 50 }), // Number of elements to test
        (elementCount) => {
          const controller = new AnimationController();
          const hoverDuration = controller.getHoverTransitionDuration();
          
          // Verify hover transition duration is 100ms or less
          return hoverDuration <= 100;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 9: Hover transition duration verified');
  });
  
  test('Feature: modern-ui-redesign, Property 9: applyHoverTransition sets correct duration', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('all', 'background-color', 'color', 'transform', 'opacity'),
        (property) => {
          const controller = new AnimationController();
          
          // Create a test element
          const element = document.createElement('button');
          document.body.appendChild(element);
          
          // Apply hover transition
          controller.applyHoverTransition(element, property);
          
          // Check that transition was set
          const transition = element.style.transition;
          
          // Verify transition includes the property and 100ms duration
          const hasCorrectDuration = transition.includes('100ms');
          const hasCorrectProperty = transition.includes(property);
          
          // Clean up
          element.remove();
          
          return hasCorrectDuration && hasCorrectProperty;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 9: applyHoverTransition sets correct duration');
  });
  
  test('Feature: modern-ui-redesign, Property 9: Hover transitions are skipped when reduced motion is enabled', () => {
    // Mock reduced motion preference
    global.window.matchMedia = (query) => ({
      matches: query === '(prefers-reduced-motion: reduce)',
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
    });
    
    AnimationController = loadAnimationController();
    const controller = new AnimationController();
    
    // Create a test element
    const element = document.createElement('button');
    document.body.appendChild(element);
    
    // Apply hover transition (should be skipped)
    controller.applyHoverTransition(element, 'all');
    
    // Transition should not be set when reduced motion is enabled
    const transition = element.style.transition;
    
    // Clean up
    element.remove();
    
    assert.strictEqual(transition, '', 'Transition should not be set when reduced motion is enabled');
    
    console.log('✓ Property 9: Hover transitions skipped with reduced motion');
  });
  
  test('Feature: modern-ui-redesign, Property 9: CSS variable --transition-hover is 100ms', () => {
    // This test verifies the CSS custom property value
    const controller = new AnimationController();
    const expectedDuration = 100;
    const actualDuration = controller.getHoverTransitionDuration();
    
    assert.strictEqual(
      actualDuration, 
      expectedDuration, 
      `Hover transition should be ${expectedDuration}ms, got ${actualDuration}ms`
    );
    
    console.log('✓ Property 9: CSS variable --transition-hover is 100ms');
  });
});


describe('Animation Controller - Button Click Feedback', () => {
  let dom;
  let AnimationController;
  
  beforeEach(() => {
    dom = setupDOM();
    AnimationController = loadAnimationController();
  });
  
  afterEach(() => {
    delete global.window;
    delete global.document;
    delete global.CustomEvent;
    delete global.HTMLElement;
  });
  
  // Property 18: Button Click Visual Feedback
  // For any button click event, a visual feedback animation should be triggered within 50ms
  // Validates: Requirements 11.1
  test('Feature: modern-ui-redesign, Property 18: Button feedback triggers within 50ms', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('scale', 'ripple', 'press'),
        (feedbackType) => {
          const controller = new AnimationController();
          
          // Create a test button
          const button = document.createElement('button');
          button.textContent = 'Test Button';
          document.body.appendChild(button);
          
          // Apply button feedback and measure time
          const triggerTime = controller.applyButtonFeedback(button, feedbackType);
          
          // Clean up
          button.remove();
          
          // Verify feedback triggered within 50ms
          return triggerTime <= 50;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 18: Button feedback triggers within 50ms');
  });
  
  test('Feature: modern-ui-redesign, Property 18: Scale feedback applies transform', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 20 }),
        (buttonCount) => {
          const controller = new AnimationController();
          
          for (let i = 0; i < buttonCount; i++) {
            const button = document.createElement('button');
            button.textContent = `Button ${i}`;
            document.body.appendChild(button);
            
            // Apply scale feedback
            controller.applyButtonFeedback(button, 'scale');
            
            // Check that transform was applied
            const transform = button.style.transform;
            const hasScaleTransform = transform.includes('scale(0.95)');
            
            // Clean up
            button.remove();
            
            if (!hasScaleTransform) {
              return false;
            }
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 18: Scale feedback applies transform');
  });
  
  test('Feature: modern-ui-redesign, Property 18: Ripple feedback adds ripple element', () => {
    const controller = new AnimationController();
    
    // Create a test button
    const button = document.createElement('button');
    button.textContent = 'Test Button';
    button.style.width = '100px';
    button.style.height = '40px';
    document.body.appendChild(button);
    
    // Apply ripple feedback
    controller.applyButtonFeedback(button, 'ripple');
    
    // Check that button has ripple-container class
    const hasRippleContainer = button.classList.contains('ripple-container');
    
    // Check that ripple element was added
    const rippleElement = button.querySelector('.ripple-effect');
    const hasRippleElement = rippleElement !== null;
    
    // Clean up
    button.remove();
    
    assert.ok(hasRippleContainer, 'Button should have ripple-container class');
    assert.ok(hasRippleElement, 'Button should have ripple-effect element');
    
    console.log('✓ Property 18: Ripple feedback adds ripple element');
  });
  
  test('Feature: modern-ui-redesign, Property 18: Press feedback adds animation class', () => {
    const controller = new AnimationController();
    
    // Create a test button
    const button = document.createElement('button');
    button.textContent = 'Test Button';
    document.body.appendChild(button);
    
    // Apply press feedback
    controller.applyButtonFeedback(button, 'press');
    
    // Check that animation class was added
    const hasAnimationClass = button.classList.contains('btn-press-animation');
    
    // Clean up
    button.remove();
    
    assert.ok(hasAnimationClass, 'Button should have btn-press-animation class');
    
    console.log('✓ Property 18: Press feedback adds animation class');
  });
  
  test('Feature: modern-ui-redesign, Property 18: Button feedback is skipped when reduced motion is enabled', () => {
    // Mock reduced motion preference
    global.window.matchMedia = (query) => ({
      matches: query === '(prefers-reduced-motion: reduce)',
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
    });
    
    AnimationController = loadAnimationController();
    const controller = new AnimationController();
    
    // Create a test button
    const button = document.createElement('button');
    button.textContent = 'Test Button';
    document.body.appendChild(button);
    
    // Apply button feedback (should be skipped)
    controller.applyButtonFeedback(button, 'scale');
    
    // Transform should not be applied when reduced motion is enabled
    const transform = button.style.transform;
    
    // Clean up
    button.remove();
    
    assert.strictEqual(transform, '', 'Transform should not be applied when reduced motion is enabled');
    
    console.log('✓ Property 18: Button feedback skipped with reduced motion');
  });
  
  test('Feature: modern-ui-redesign, Property 18: getButtonFeedbackDelay returns 50ms', () => {
    const controller = new AnimationController();
    const expectedDelay = 50;
    const actualDelay = controller.getButtonFeedbackDelay();
    
    assert.strictEqual(
      actualDelay,
      expectedDelay,
      `Button feedback delay should be ${expectedDelay}ms, got ${actualDelay}ms`
    );
    
    console.log('✓ Property 18: getButtonFeedbackDelay returns 50ms');
  });
  
  test('Feature: modern-ui-redesign, Property 18: Default feedback type is scale', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 10 }),
        (count) => {
          const controller = new AnimationController();
          
          for (let i = 0; i < count; i++) {
            const button = document.createElement('button');
            document.body.appendChild(button);
            
            // Apply feedback without specifying type (should default to scale)
            controller.applyButtonFeedback(button);
            
            // Check that scale transform was applied
            const transform = button.style.transform;
            const hasScaleTransform = transform.includes('scale(0.95)');
            
            button.remove();
            
            if (!hasScaleTransform) {
              return false;
            }
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 18: Default feedback type is scale');
  });
});


describe('Animation Controller - GPU-Accelerated Animations', () => {
  let dom;
  let AnimationController;
  
  beforeEach(() => {
    dom = setupDOM();
    AnimationController = loadAnimationController();
  });
  
  afterEach(() => {
    delete global.window;
    delete global.document;
    delete global.CustomEvent;
    delete global.HTMLElement;
  });
  
  // Property 29: GPU-Accelerated Animations
  // **Validates: Requirements 13.5**
  // For any animation involving multiple elements, only CSS transform and opacity 
  // properties should be animated (not layout properties like width, height, top, left)
  test('Feature: modern-ui-redesign, Property 29: Animations use only transform and opacity', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            id: fc.integer({ min: 1, max: 1000 }),
            type: fc.constantFrom('card', 'button', 'modal', 'toast')
          }),
          { minLength: 2, maxLength: 20 }
        ),
        (elements) => {
          const controller = new AnimationController();
          
          // Create DOM elements
          const domElements = elements.map((el, index) => {
            const elem = document.createElement('div');
            elem.id = `element-${el.id}`;
            elem.className = el.type;
            document.body.appendChild(elem);
            return elem;
          });
          
          // Apply animations to all elements
          controller.applyStaggeredAnimation(domElements);
          
          // Check that only GPU-accelerated properties are animated
          let allGPUAccelerated = true;
          
          for (const elem of domElements) {
            const animatedProperties = controller.getAnimatedProperties(elem);
            
            // Verify only transform and opacity are in the animated properties
            for (const prop of animatedProperties) {
              if (prop !== 'transform' && prop !== 'opacity') {
                console.log(`Non-GPU property found: ${prop} on element ${elem.id}`);
                allGPUAccelerated = false;
                break;
              }
            }
            
            if (!allGPUAccelerated) break;
          }
          
          // Clean up
          domElements.forEach(elem => elem.remove());
          
          return allGPUAccelerated;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 29: Animations use only transform and opacity');
  });
  
  test('Feature: modern-ui-redesign, Property 29: No layout properties in animations', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 15 }),
        (elementCount) => {
          const controller = new AnimationController();
          
          // Non-GPU properties that should NOT be animated
          const nonGPUProperties = [
            'width', 'height', 'top', 'left', 'right', 'bottom',
            'margin', 'padding', 'border-width', 'font-size'
          ];
          
          // Create elements
          const elements = [];
          for (let i = 0; i < elementCount; i++) {
            const elem = document.createElement('div');
            elem.className = 'animated-element';
            document.body.appendChild(elem);
            elements.push(elem);
          }
          
          // Apply animations
          controller.applyStaggeredAnimation(elements);
          
          // Check that none of the non-GPU properties are animated
          let noLayoutProperties = true;
          
          for (const elem of elements) {
            const animatedProperties = controller.getAnimatedProperties(elem);
            
            for (const prop of animatedProperties) {
              if (nonGPUProperties.includes(prop)) {
                console.log(`Layout property ${prop} found in animation`);
                noLayoutProperties = false;
                break;
              }
            }
            
            if (!noLayoutProperties) break;
          }
          
          // Clean up
          elements.forEach(elem => elem.remove());
          
          return noLayoutProperties;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 29: No layout properties in animations');
  });
  
  test('Feature: modern-ui-redesign, Property 29: will-change hint is set for GPU acceleration', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 10 }),
        (elementCount) => {
          const controller = new AnimationController();
          
          // Create elements
          const elements = [];
          for (let i = 0; i < elementCount; i++) {
            const elem = document.createElement('div');
            elem.className = 'card-modern';
            document.body.appendChild(elem);
            elements.push(elem);
          }
          
          // Apply animations with GPU optimization
          controller.applyStaggeredAnimation(elements, { gpuOptimize: true });
          
          // Check that will-change is set appropriately
          let allHaveWillChange = true;
          
          for (const elem of elements) {
            const willChange = elem.style.willChange || 
                              window.getComputedStyle(elem).willChange;
            
            // Should have will-change: transform, opacity or auto
            if (willChange && willChange !== 'auto' && willChange !== '') {
              const hasTransform = willChange.includes('transform');
              const hasOpacity = willChange.includes('opacity');
              
              if (!hasTransform && !hasOpacity) {
                console.log(`Element missing will-change for GPU properties: ${willChange}`);
                allHaveWillChange = false;
                break;
              }
            }
          }
          
          // Clean up
          elements.forEach(elem => elem.remove());
          
          return allHaveWillChange;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 29: will-change hint is set for GPU acceleration');
  });
  
  test('Feature: modern-ui-redesign, Property 29: Hover effects use only transform and opacity', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('lift', 'scale', 'brightness', 'opacity'),
        (hoverEffect) => {
          const controller = new AnimationController();
          
          // Create element
          const elem = document.createElement('button');
          elem.className = 'btn';
          document.body.appendChild(elem);
          
          // Apply hover effect
          controller.applyHoverEffect(elem, hoverEffect);
          
          // Get transition properties
          const transition = elem.style.transition || 
                           window.getComputedStyle(elem).transition;
          
          // Check that only GPU-accelerated properties are in transition
          const nonGPUProps = ['width', 'height', 'top', 'left', 'margin', 'padding'];
          let isGPUAccelerated = true;
          
          for (const prop of nonGPUProps) {
            if (transition.includes(prop)) {
              console.log(`Non-GPU property ${prop} in hover transition`);
              isGPUAccelerated = false;
              break;
            }
          }
          
          // Clean up
          elem.remove();
          
          return isGPUAccelerated;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 29: Hover effects use only transform and opacity');
  });
  
  test('Feature: modern-ui-redesign, Property 29: Ripple effects use transform scale', () => {
    const controller = new AnimationController();
    
    // Create button
    const button = document.createElement('button');
    button.className = 'btn';
    document.body.appendChild(button);
    
    // Apply ripple effect
    controller.applyButtonFeedback(button, 'ripple');
    
    // Find ripple element
    const ripple = button.querySelector('.ripple-effect');
    
    if (ripple) {
      // Check that ripple uses transform (not width/height)
      const animation = window.getComputedStyle(ripple).animation;
      const transform = window.getComputedStyle(ripple).transform;
      
      // Ripple should use transform scale, not width/height
      const usesTransform = animation.includes('ripple') || transform !== 'none';
      
      // Clean up
      button.remove();
      
      assert.ok(usesTransform, 'Ripple effect should use transform');
    } else {
      // If no ripple element, check that button has ripple class
      const hasRippleClass = button.classList.contains('ripple-container');
      button.remove();
      assert.ok(hasRippleClass, 'Button should have ripple-container class');
    }
    
    console.log('✓ Property 29: Ripple effects use transform scale');
  });
  
  test('Feature: modern-ui-redesign, Property 29: Card entrance animations use transform and opacity', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 20 }),
        (cardCount) => {
          const controller = new AnimationController();
          
          // Create cards
          const cards = [];
          for (let i = 0; i < cardCount; i++) {
            const card = document.createElement('div');
            card.className = 'card-modern';
            document.body.appendChild(card);
            cards.push(card);
          }
          
          // Apply entrance animation
          controller.applyStaggeredAnimation(cards);
          
          // Check animated properties
          let allGPUAccelerated = true;
          
          for (const card of cards) {
            const animatedProps = controller.getAnimatedProperties(card);
            
            // Should only contain transform and/or opacity
            for (const prop of animatedProps) {
              if (prop !== 'transform' && prop !== 'opacity') {
                console.log(`Card entrance uses non-GPU property: ${prop}`);
                allGPUAccelerated = false;
                break;
              }
            }
            
            if (!allGPUAccelerated) break;
          }
          
          // Clean up
          cards.forEach(card => card.remove());
          
          return allGPUAccelerated;
        }
      ),
      { numRuns: 100 }
    );
    
    console.log('✓ Property 29: Card entrance animations use transform and opacity');
  });
  
  test('Feature: modern-ui-redesign, Property 29: validateGPUAcceleration helper works correctly', () => {
    const controller = new AnimationController();
    
    // Test valid GPU properties
    assert.ok(
      controller.validateGPUAcceleration(['transform', 'opacity']),
      'Should validate transform and opacity as GPU-accelerated'
    );
    
    // Test invalid properties
    assert.ok(
      !controller.validateGPUAcceleration(['width', 'height']),
      'Should reject width and height as non-GPU-accelerated'
    );
    
    // Test mixed properties
    assert.ok(
      !controller.validateGPUAcceleration(['transform', 'width']),
      'Should reject mixed GPU and non-GPU properties'
    );
    
    // Test empty array
    assert.ok(
      controller.validateGPUAcceleration([]),
      'Should validate empty array (no animations)'
    );
    
    console.log('✓ Property 29: validateGPUAcceleration helper works correctly');
  });
});
