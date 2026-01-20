/**
 * Performance Monitor
 * Tracks and reports page load performance metrics
 * Requirements: 13.1 - Initial page load < 1 second
 */

class PerformanceMonitor {
  constructor() {
    this.metrics = {};
    this.thresholds = {
      firstContentfulPaint: 1000, // 1 second per Requirement 13.1
      domContentLoaded: 1500,
      loadComplete: 2500
    };
    
    this.init();
  }
  
  /**
   * Initialize performance monitoring
   */
  init() {
    if (typeof window === 'undefined' || !window.performance) {
      console.warn('Performance API not available');
      return;
    }
    
    // Wait for page to load before collecting metrics
    if (document.readyState === 'complete') {
      this.collectMetrics();
    } else {
      window.addEventListener('load', () => {
        // Small delay to ensure all metrics are available
        setTimeout(() => this.collectMetrics(), 100);
      });
    }
  }
  
  /**
   * Collect performance metrics
   */
  collectMetrics() {
    const perfData = window.performance;
    
    if (!perfData || !perfData.timing) {
      console.warn('Performance timing not available');
      return;
    }
    
    const timing = perfData.timing;
    const navigation = perfData.navigation;
    
    // Calculate key metrics
    this.metrics = {
      // Navigation timing
      navigationStart: timing.navigationStart,
      
      // DNS lookup
      dnsTime: timing.domainLookupEnd - timing.domainLookupStart,
      
      // TCP connection
      tcpTime: timing.connectEnd - timing.connectStart,
      
      // Request/Response
      requestTime: timing.responseStart - timing.requestStart,
      responseTime: timing.responseEnd - timing.responseStart,
      
      // DOM processing
      domInteractive: timing.domInteractive - timing.navigationStart,
      domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
      domComplete: timing.domComplete - timing.navigationStart,
      
      // Load complete
      loadComplete: timing.loadEventEnd - timing.navigationStart,
      
      // Navigation type
      navigationType: this.getNavigationType(navigation.type)
    };
    
    // Get paint timing if available
    if (perfData.getEntriesByType) {
      const paintEntries = perfData.getEntriesByType('paint');
      paintEntries.forEach(entry => {
        if (entry.name === 'first-paint') {
          this.metrics.firstPaint = Math.round(entry.startTime);
        } else if (entry.name === 'first-contentful-paint') {
          this.metrics.firstContentfulPaint = Math.round(entry.startTime);
        }
      });
    }
    
    // Check thresholds and log warnings
    this.checkThresholds();
    
    // Dispatch performance event
    this.dispatchPerformanceEvent();
    
    // Log metrics in development
    if (this.isDevelopment()) {
      this.logMetrics();
    }
  }
  
  /**
   * Get navigation type as string
   * @param {number} type
   * @returns {string}
   */
  getNavigationType(type) {
    const types = {
      0: 'navigate',
      1: 'reload',
      2: 'back_forward',
      255: 'reserved'
    };
    return types[type] || 'unknown';
  }
  
  /**
   * Check if metrics meet performance thresholds
   */
  checkThresholds() {
    const warnings = [];
    
    // Check First Contentful Paint (critical for Requirement 13.1)
    if (this.metrics.firstContentfulPaint) {
      if (this.metrics.firstContentfulPaint > this.thresholds.firstContentfulPaint) {
        warnings.push({
          metric: 'First Contentful Paint',
          value: this.metrics.firstContentfulPaint,
          threshold: this.thresholds.firstContentfulPaint,
          severity: 'high'
        });
      }
    }
    
    // Check DOM Content Loaded
    if (this.metrics.domContentLoaded > this.thresholds.domContentLoaded) {
      warnings.push({
        metric: 'DOM Content Loaded',
        value: this.metrics.domContentLoaded,
        threshold: this.thresholds.domContentLoaded,
        severity: 'medium'
      });
    }
    
    // Check Load Complete
    if (this.metrics.loadComplete > this.thresholds.loadComplete) {
      warnings.push({
        metric: 'Load Complete',
        value: this.metrics.loadComplete,
        threshold: this.thresholds.loadComplete,
        severity: 'low'
      });
    }
    
    this.metrics.warnings = warnings;
    
    // Log warnings
    if (warnings.length > 0 && this.isDevelopment()) {
      console.warn('Performance thresholds exceeded:');
      warnings.forEach(w => {
        console.warn(`  ${w.metric}: ${w.value}ms (threshold: ${w.threshold}ms) [${w.severity}]`);
      });
    }
  }
  
  /**
   * Check if running in development mode
   * @returns {boolean}
   */
  isDevelopment() {
    return window.location.hostname === 'localhost' || 
           window.location.hostname === '127.0.0.1';
  }
  
  /**
   * Log performance metrics to console
   */
  logMetrics() {
    console.group('📊 Performance Metrics');
    console.log('First Paint:', this.metrics.firstPaint ? `${this.metrics.firstPaint}ms` : 'N/A');
    console.log('First Contentful Paint:', this.metrics.firstContentfulPaint ? `${this.metrics.firstContentfulPaint}ms` : 'N/A');
    console.log('DOM Interactive:', `${this.metrics.domInteractive}ms`);
    console.log('DOM Content Loaded:', `${this.metrics.domContentLoaded}ms`);
    console.log('Load Complete:', `${this.metrics.loadComplete}ms`);
    console.log('DNS Lookup:', `${this.metrics.dnsTime}ms`);
    console.log('TCP Connection:', `${this.metrics.tcpTime}ms`);
    console.log('Request Time:', `${this.metrics.requestTime}ms`);
    console.log('Response Time:', `${this.metrics.responseTime}ms`);
    console.log('Navigation Type:', this.metrics.navigationType);
    console.groupEnd();
    
    // Performance grade
    const grade = this.calculateGrade();
    console.log(`Performance Grade: ${grade.letter} (${grade.score}/100)`);
  }
  
  /**
   * Calculate performance grade
   * @returns {Object} Grade object with letter and score
   */
  calculateGrade() {
    let score = 100;
    
    // Deduct points for slow metrics
    if (this.metrics.firstContentfulPaint) {
      if (this.metrics.firstContentfulPaint > 1000) score -= 20;
      else if (this.metrics.firstContentfulPaint > 800) score -= 10;
      else if (this.metrics.firstContentfulPaint > 600) score -= 5;
    }
    
    if (this.metrics.domContentLoaded > 1500) score -= 15;
    else if (this.metrics.domContentLoaded > 1200) score -= 8;
    
    if (this.metrics.loadComplete > 2500) score -= 10;
    else if (this.metrics.loadComplete > 2000) score -= 5;
    
    // Determine letter grade
    let letter;
    if (score >= 90) letter = 'A';
    else if (score >= 80) letter = 'B';
    else if (score >= 70) letter = 'C';
    else if (score >= 60) letter = 'D';
    else letter = 'F';
    
    return { score, letter };
  }
  
  /**
   * Dispatch custom performance event
   */
  dispatchPerformanceEvent() {
    if (typeof document !== 'undefined') {
      const event = new CustomEvent('performancemetrics', {
        detail: {
          metrics: this.metrics,
          grade: this.calculateGrade(),
          timestamp: Date.now()
        }
      });
      document.dispatchEvent(event);
    }
  }
  
  /**
   * Get all metrics
   * @returns {Object} Performance metrics
   */
  getMetrics() {
    return { ...this.metrics };
  }
  
  /**
   * Get First Contentful Paint time
   * @returns {number|null} FCP time in milliseconds
   */
  getFirstContentfulPaint() {
    return this.metrics.firstContentfulPaint || null;
  }
  
  /**
   * Check if FCP meets threshold (< 1 second)
   * @returns {boolean}
   */
  meetsFCPThreshold() {
    if (!this.metrics.firstContentfulPaint) return false;
    return this.metrics.firstContentfulPaint < this.thresholds.firstContentfulPaint;
  }
  
  /**
   * Get performance summary for reporting
   * @returns {Object}
   */
  getSummary() {
    return {
      fcp: this.metrics.firstContentfulPaint,
      dcl: this.metrics.domContentLoaded,
      load: this.metrics.loadComplete,
      grade: this.calculateGrade(),
      meetsThreshold: this.meetsFCPThreshold(),
      warnings: this.metrics.warnings || []
    };
  }
}

// Create global instance
const performanceMonitor = new PerformanceMonitor();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = PerformanceMonitor;
}

// Make available globally
if (typeof window !== 'undefined') {
  window.PerformanceMonitor = PerformanceMonitor;
  window.performanceMonitor = performanceMonitor;
}
