/**
 * Animation Controller
 * Handles animation utilities, staggered animations, and reduced motion support
 * Requirements: 5.1, 5.2, 5.4, 11.1, 13.5
 */

class AnimationController {
  constructor() {
    this.STAGGER_DELAY = 50; // ms between each card animation
    this.HOVER_TRANSITION_DURATION = 100; // ms - must complete within 100ms per Requirement 5.2
    this.BUTTON_FEEDBACK_DELAY = 50; // ms - must trigger within 50ms per Requirement 11.1
    this.reducedMotion = false;
    
    this.init();
  }
  
  /**
   * Initialize animation controller
   */
  init() {
    this.detectReducedMotion();
    this.watchReducedMotionPreference();
    this.applyReducedMotionStyles();
  }
  
  /**
   * Detect if user prefers reduced motion
   * @returns {boolean}
   */
  detectReducedMotion() {
    if (typeof window !== 'undefined' && window.matchMedia) {
      this.reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }
    return this.reducedMotion;
  }
  
  /**
   * Watch for changes in reduced motion preference
   */
  watchReducedMotionPreference() {
    if (typeof window !== 'undefined' && window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
      
      const handleChange = (e) => {
        this.reducedMotion = e.matches;
        this.dispatchMotionPreferenceChange(e.matches);
        this.applyReducedMotionStyles();
        
        // Update CSS variable
        if (typeof document !== 'undefined') {
          document.documentElement.style.setProperty(
            '--motion-enabled', 
            e.matches ? '0' : '1'
          );
        }
        
        // Log change
        console.log('[Animation Controller] Motion preference changed:', e.matches ? 'reduced' : 'normal');
      };
      
      if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener('change', handleChange);
      } else if (mediaQuery.addListener) {
        mediaQuery.addListener(handleChange);
      }
    }
  }
  
  /**
   * Apply reduced motion styles to document
   */
  applyReducedMotionStyles() {
    if (typeof document === 'undefined') return;
    
    if (this.reducedMotion) {
      document.documentElement.classList.add('reduce-motion');
      document.documentElement.style.setProperty('--motion-enabled', '0');
      console.log('[Animation Controller] Reduced motion enabled');
    } else {
      document.documentElement.classList.remove('reduce-motion');
      document.documentElement.style.setProperty('--motion-enabled', '1');
      console.log('[Animation Controller] Normal motion enabled');
    }
  }
  
  /**
   * Check if animations are enabled
   * @returns {boolean}
   */
  isAnimationEnabled() {
    return !this.reducedMotion;
  }
  
  /**
   * Apply staggered entrance animation to a list of cards
   * Each subsequent card has an incrementally larger animation-delay
   * @param {NodeList|Array} cards - List of card elements
   * @param {Object} options - Animation options
   * @returns {Array} Array of animation delays applied
   */
  applyStaggeredAnimation(cards, options = {}) {
    const {
      baseDelay = 0,
      staggerDelay = this.STAGGER_DELAY,
      animationClass = 'animate-card-entrance'
    } = options;
    
    const cardArray = Array.from(cards);
    const delays = [];
    
    if (this.reducedMotion) {
      // Skip animation, just show cards immediately
      cardArray.forEach(card => {
        card.style.opacity = '1';
        card.style.transform = 'none';
      });
      return delays;
    }
    
    cardArray.forEach((card, index) => {
      const delay = baseDelay + (index * staggerDelay);
      delays.push(delay);
      
      // Set animation delay using CSS custom property
      card.style.setProperty('--stagger-index', index.toString());
      card.style.animationDelay = `${delay}ms`;
      
      // Add animation class
      card.classList.add(animationClass);
    });
    
    return delays;
  }
  
  /**
   * Validate that staggered delays are incrementally larger
   * @param {Array} delays - Array of delay values
   * @returns {boolean} True if delays are properly staggered
   */
  validateStaggeredDelays(delays) {
    if (delays.length < 2) return true;
    
    for (let i = 1; i < delays.length; i++) {
      if (delays[i] <= delays[i - 1]) {
        return false;
      }
    }
    return true;
  }
  
  /**
   * Apply hover transition to an element
   * Ensures transition completes within 100ms per Requirement 5.2
   * @param {HTMLElement} element - Element to apply hover transition
   * @param {string} property - CSS property to transition
   */
  applyHoverTransition(element, property = 'all') {
    if (this.reducedMotion) return;
    
    const transitionValue = `${property} ${this.HOVER_TRANSITION_DURATION}ms cubic-bezier(0.4, 0, 0.2, 1)`;
    element.style.transition = transitionValue;
  }
  
  /**
   * Get hover transition duration
   * @returns {number} Duration in milliseconds
   */
  getHoverTransitionDuration() {
    return this.HOVER_TRANSITION_DURATION;
  }
  
  /**
   * Apply button click feedback animation
   * Must trigger within 50ms per Requirement 11.1
   * @param {HTMLElement} button - Button element
   * @param {string} feedbackType - Type of feedback ('scale', 'ripple', 'press')
   */
  applyButtonFeedback(button, feedbackType = 'scale') {
    if (this.reducedMotion) return;
    
    const startTime = performance.now();
    
    switch (feedbackType) {
      case 'scale':
        this.applyScaleFeedback(button);
        break;
      case 'ripple':
        this.applyRippleFeedback(button);
        break;
      case 'press':
        this.applyPressFeedback(button);
        break;
      default:
        this.applyScaleFeedback(button);
    }
    
    const endTime = performance.now();
    const triggerTime = endTime - startTime;
    
    // Log warning if feedback took too long
    if (triggerTime > this.BUTTON_FEEDBACK_DELAY) {
      console.warn(`Button feedback took ${triggerTime}ms, exceeds ${this.BUTTON_FEEDBACK_DELAY}ms target`);
    }
    
    return triggerTime;
  }
  
  /**
   * Apply scale feedback to button
   * @param {HTMLElement} button
   */
  applyScaleFeedback(button) {
    button.classList.add('btn-click-scale');
    button.style.transform = 'scale(0.95)';
    
    // Reset after animation
    setTimeout(() => {
      button.style.transform = '';
    }, 150);
  }
  
  /**
   * Apply ripple feedback to button
   * @param {HTMLElement} button
   * @param {MouseEvent} event - Optional click event for ripple position
   */
  applyRippleFeedback(button, event = null) {
    // Ensure button has ripple container class
    if (!button.classList.contains('ripple-container')) {
      button.classList.add('ripple-container');
    }
    
    // Create ripple element
    const ripple = document.createElement('span');
    ripple.classList.add('ripple-effect');
    
    // Calculate ripple position
    const rect = button.getBoundingClientRect();
    let x, y;
    
    if (event) {
      x = event.clientX - rect.left;
      y = event.clientY - rect.top;
    } else {
      x = rect.width / 2;
      y = rect.height / 2;
    }
    
    // Set ripple size based on button dimensions
    const size = Math.max(rect.width, rect.height);
    ripple.style.width = ripple.style.height = `${size}px`;
    ripple.style.left = `${x}px`;
    ripple.style.top = `${y}px`;
    
    // Add ripple to button
    button.appendChild(ripple);
    
    // Remove ripple after animation
    setTimeout(() => {
      ripple.remove();
    }, 600);
  }
  
  /**
   * Apply press animation feedback to button
   * @param {HTMLElement} button
   */
  applyPressFeedback(button) {
    button.classList.add('btn-press-animation');
    
    // Remove class after animation completes
    setTimeout(() => {
      button.classList.remove('btn-press-animation');
    }, 150);
  }
  
  /**
   * Dispatch motion preference change event
   * @param {boolean} reducedMotion
   */
  dispatchMotionPreferenceChange(reducedMotion) {
    if (typeof document !== 'undefined') {
      const event = new CustomEvent('motionpreferencechange', {
        detail: { reducedMotion, timestamp: Date.now() }
      });
      document.dispatchEvent(event);
    }
  }
  
  /**
   * Animate element entrance
   * @param {HTMLElement} element
   * @param {string} animationType - Type of entrance animation
   * @param {number} delay - Animation delay in ms
   */
  animateEntrance(element, animationType = 'fade-in', delay = 0) {
    if (this.reducedMotion) {
      element.style.opacity = '1';
      return;
    }
    
    const animationClass = `animate-${animationType}`;
    
    if (delay > 0) {
      element.style.animationDelay = `${delay}ms`;
    }
    
    element.classList.add(animationClass);
  }
  
  /**
   * Remove animation classes from element
   * @param {HTMLElement} element
   */
  clearAnimations(element) {
    const animationClasses = [
      'animate-fade-in',
      'animate-fade-out',
      'animate-slide-in-up',
      'animate-slide-in-down',
      'animate-slide-in-left',
      'animate-slide-in-right',
      'animate-scale-in',
      'animate-scale-out',
      'animate-card-entrance',
      'btn-press-animation'
    ];
    
    animationClasses.forEach(cls => {
      element.classList.remove(cls);
    });
    
    element.style.animationDelay = '';
    element.style.removeProperty('--stagger-index');
  }
  
  /**
   * Get stagger delay value
   * @returns {number} Stagger delay in milliseconds
   */
  getStaggerDelay() {
    return this.STAGGER_DELAY;
  }
  
  /**
   * Get button feedback delay threshold
   * @returns {number} Delay threshold in milliseconds
   */
  getButtonFeedbackDelay() {
    return this.BUTTON_FEEDBACK_DELAY;
  }
  
  /**
   * Get animated properties from an element
   * Extracts properties being animated from animation or transition
   * @param {HTMLElement} element
   * @returns {Array<string>} Array of property names being animated
   */
  getAnimatedProperties(element) {
    const properties = [];
    
    // Check animation properties
    const animation = element.style.animation || 
                     window.getComputedStyle(element).animation;
    
    // Check transition properties
    const transition = element.style.transition || 
                      window.getComputedStyle(element).transition;
    
    // For our animations, we use transform and opacity
    // Check if element has animation classes
    if (element.classList.contains('animate-card-entrance') ||
        element.classList.contains('animate-fade-in') ||
        element.classList.contains('animate-slide-in-up') ||
        element.classList.contains('animate-scale-in')) {
      properties.push('transform', 'opacity');
    }
    
    // Parse transition string for properties
    if (transition && transition !== 'none' && transition !== '') {
      const transitionParts = transition.split(',');
      transitionParts.forEach(part => {
        const propMatch = part.trim().match(/^([a-z-]+)/);
        if (propMatch) {
          const prop = propMatch[1];
          if (!properties.includes(prop)) {
            properties.push(prop);
          }
        }
      });
    }
    
    return properties;
  }
  
  /**
   * Validate that only GPU-accelerated properties are being animated
   * GPU-accelerated properties: transform, opacity
   * Non-GPU properties: width, height, top, left, margin, padding, etc.
   * @param {Array<string>} properties - Array of CSS property names
   * @returns {boolean} True if all properties are GPU-accelerated
   */
  validateGPUAcceleration(properties) {
    const gpuProperties = ['transform', 'opacity'];
    const nonGPUProperties = [
      'width', 'height', 'top', 'left', 'right', 'bottom',
      'margin', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
      'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
      'border-width', 'font-size', 'line-height'
    ];
    
    // Empty array is valid (no animations)
    if (properties.length === 0) {
      return true;
    }
    
    // Check each property
    for (const prop of properties) {
      // If it's a non-GPU property, fail validation
      if (nonGPUProperties.includes(prop)) {
        return false;
      }
      
      // If it's not a GPU property and not 'all', fail validation
      if (!gpuProperties.includes(prop) && prop !== 'all') {
        // Allow some exceptions like box-shadow, filter, background-color
        const allowedExceptions = ['box-shadow', 'filter', 'background-color', 'color', 'border-color'];
        if (!allowedExceptions.includes(prop)) {
          return false;
        }
      }
    }
    
    return true;
  }
  
  /**
   * Apply hover effect to an element
   * @param {HTMLElement} element
   * @param {string} effectType - Type of hover effect
   */
  applyHoverEffect(element, effectType = 'lift') {
    if (this.reducedMotion) return;
    
    switch (effectType) {
      case 'lift':
        element.classList.add('hover-lift');
        element.style.transition = 'transform 100ms cubic-bezier(0.4, 0, 0.2, 1), box-shadow 100ms cubic-bezier(0.4, 0, 0.2, 1)';
        break;
      case 'scale':
        element.classList.add('hover-scale');
        element.style.transition = 'transform 100ms cubic-bezier(0.4, 0, 0.2, 1)';
        break;
      case 'brightness':
        element.classList.add('hover-brightness');
        element.style.transition = 'filter 100ms cubic-bezier(0.4, 0, 0.2, 1)';
        break;
      case 'opacity':
        element.classList.add('hover-opacity');
        element.style.transition = 'opacity 100ms cubic-bezier(0.4, 0, 0.2, 1)';
        break;
      default:
        element.classList.add('hover-lift');
        element.style.transition = 'transform 100ms cubic-bezier(0.4, 0, 0.2, 1)';
    }
  }
}

// Create global instance
const animationController = new AnimationController();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = AnimationController;
}

// Auto-initialize button click handlers when DOM is ready
if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    // Add click feedback to all buttons with data-feedback attribute
    document.querySelectorAll('[data-click-feedback]').forEach(button => {
      const feedbackType = button.getAttribute('data-click-feedback') || 'scale';
      
      button.addEventListener('click', (e) => {
        animationController.applyButtonFeedback(button, feedbackType);
      });
    });
    
    // Apply staggered animation to card grids
    document.querySelectorAll('.stagger-children').forEach(container => {
      const cards = container.children;
      animationController.applyStaggeredAnimation(cards);
    });
    
    console.log('Animation Controller initialized. Reduced motion:', animationController.reducedMotion);
  });
}
