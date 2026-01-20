// web_layer/static/js/debounce-utility.js

/**
 * Debounce Utility
 * 
 * Provides debouncing functionality to optimize event handler performance
 * by limiting the rate at which a function can fire.
 * 
 * Validates: Requirements 13.4
 */

/**
 * Creates a debounced function that delays invoking func until after wait milliseconds
 * have elapsed since the last time the debounced function was invoked.
 * 
 * @param {Function} func - The function to debounce
 * @param {number} wait - The number of milliseconds to delay (default: 300ms)
 * @param {Object} options - Optional configuration
 * @param {boolean} options.leading - Invoke on the leading edge of the timeout (default: false)
 * @param {boolean} options.trailing - Invoke on the trailing edge of the timeout (default: true)
 * @returns {Function} The debounced function
 * 
 * @example
 * // Basic usage
 * const debouncedSearch = debounce((query) => {
 *   console.log('Searching for:', query);
 * }, 300);
 * 
 * input.addEventListener('input', (e) => debouncedSearch(e.target.value));
 * 
 * @example
 * // With leading edge execution
 * const debouncedClick = debounce(handleClick, 500, { leading: true, trailing: false });
 */
function debounce(func, wait = 300, options = {}) {
  if (typeof func !== 'function') {
    throw new TypeError('Expected a function');
  }
  
  if (typeof wait !== 'number' || wait < 0) {
    throw new TypeError('Expected wait to be a non-negative number');
  }
  
  const { leading = false, trailing = true } = options;
  
  let timeoutId = null;
  let lastCallTime = 0;
  let lastInvokeTime = 0;
  let lastArgs = null;
  let lastThis = null;
  let result = undefined;
  
  /**
   * Invokes the debounced function
   */
  function invokeFunc(time) {
    const args = lastArgs;
    const thisArg = lastThis;
    
    lastArgs = lastThis = null;
    lastInvokeTime = time;
    result = func.apply(thisArg, args);
    return result;
  }
  
  /**
   * Handles leading edge execution
   */
  function leadingEdge(time) {
    lastInvokeTime = time;
    timeoutId = setTimeout(timerExpired, wait);
    return leading ? invokeFunc(time) : result;
  }
  
  /**
   * Handles trailing edge execution
   */
  function trailingEdge(time) {
    timeoutId = null;
    
    if (trailing && lastArgs) {
      return invokeFunc(time);
    }
    lastArgs = lastThis = null;
    return result;
  }
  
  /**
   * Handles timer expiration
   */
  function timerExpired() {
    const time = Date.now();
    if (shouldInvoke(time)) {
      return trailingEdge(time);
    }
    // Restart the timer
    timeoutId = setTimeout(timerExpired, remainingWait(time));
  }
  
  /**
   * Calculates remaining wait time
   */
  function remainingWait(time) {
    const timeSinceLastCall = time - lastCallTime;
    const timeSinceLastInvoke = time - lastInvokeTime;
    const timeWaiting = wait - timeSinceLastCall;
    
    return timeWaiting;
  }
  
  /**
   * Checks if function should be invoked
   */
  function shouldInvoke(time) {
    const timeSinceLastCall = time - lastCallTime;
    const timeSinceLastInvoke = time - lastInvokeTime;
    
    return (
      lastCallTime === 0 ||
      timeSinceLastCall >= wait ||
      timeSinceLastCall < 0 ||
      (leading && timeSinceLastInvoke >= wait)
    );
  }
  
  /**
   * The debounced function
   */
  function debounced(...args) {
    const time = Date.now();
    const isInvoking = shouldInvoke(time);
    
    lastArgs = args;
    lastThis = this;
    lastCallTime = time;
    
    if (isInvoking) {
      if (timeoutId === null) {
        return leadingEdge(lastCallTime);
      }
    }
    
    if (timeoutId === null) {
      timeoutId = setTimeout(timerExpired, wait);
    }
    
    return result;
  }
  
  /**
   * Cancels any pending invocations
   */
  debounced.cancel = function() {
    if (timeoutId !== null) {
      clearTimeout(timeoutId);
    }
    lastInvokeTime = 0;
    lastArgs = lastCallTime = lastThis = timeoutId = null;
  };
  
  /**
   * Immediately invokes the debounced function
   */
  debounced.flush = function() {
    return timeoutId === null ? result : trailingEdge(Date.now());
  };
  
  /**
   * Checks if there are any pending invocations
   */
  debounced.pending = function() {
    return timeoutId !== null;
  };
  
  return debounced;
}

/**
 * Creates a throttled function that only invokes func at most once per every wait milliseconds.
 * Throttling is useful for rate-limiting events that fire frequently (e.g., scroll, resize).
 * 
 * @param {Function} func - The function to throttle
 * @param {number} wait - The number of milliseconds to throttle invocations to
 * @returns {Function} The throttled function
 * 
 * @example
 * const throttledScroll = throttle(() => {
 *   console.log('Scroll event');
 * }, 100);
 * 
 * window.addEventListener('scroll', throttledScroll);
 */
function throttle(func, wait = 300) {
  return debounce(func, wait, { leading: true, trailing: true });
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { debounce, throttle };
}

// Make available globally for browser usage
if (typeof window !== 'undefined') {
  window.debounce = debounce;
  window.throttle = throttle;
}
