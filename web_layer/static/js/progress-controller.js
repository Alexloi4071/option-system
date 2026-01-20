/**
 * Progress Controller
 * Manages circular progress indicator with step tracking and module completion
 * Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
 * 
 * @module ProgressController
 */

(function(global) {
  'use strict';

  // Total number of modules in the analysis system
  const TOTAL_MODULES = 28;
  
  // Default estimated time per module (in seconds)
  const DEFAULT_TIME_PER_MODULE = 2;
  
  // SVG circle properties
  const CIRCLE_RADIUS = 45;
  const CIRCLE_CIRCUMFERENCE = 2 * Math.PI * CIRCLE_RADIUS;

  /**
   * ProgressController class
   * Manages progress indicator state and animations
   */
  class ProgressController {
    /**
     * Create a ProgressController instance
     * @param {Object} options - Configuration options
     * @param {number} [options.totalModules=28] - Total number of modules
     * @param {number} [options.timePerModule=2] - Estimated seconds per module
     */
    constructor(options = {}) {
      this.totalModules = options.totalModules || TOTAL_MODULES;
      this.timePerModule = options.timePerModule || DEFAULT_TIME_PER_MODULE;
      
      // State
      this.currentProgress = 0;
      this.currentStep = '';
      this.currentModuleIndex = 0;
      this.completedModules = [];
      this.startTime = null;
      this.status = 'idle'; // idle, running, completed, error
      
      // DOM elements (set via init or setElements)
      this.elements = {
        container: null,
        progressBar: null,
        progressText: null,
        stepName: null,
        timeRemaining: null,
        modulesList: null
      };
      
      // Detect reduced motion preference
      this.reducedMotion = this._detectReducedMotion();
      
      // Bind methods
      this._updateProgressBar = this._updateProgressBar.bind(this);
      this._animateCheckmark = this._animateCheckmark.bind(this);
    }

    /**
     * Detect if user prefers reduced motion
     * @private
     * @returns {boolean}
     */
    _detectReducedMotion() {
      if (typeof window !== 'undefined' && window.matchMedia) {
        return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      }
      return false;
    }

    /**
     * Initialize the controller with DOM elements
     * @param {string|HTMLElement} container - Container element or selector
     * @returns {ProgressController}
     */
    init(container) {
      if (typeof container === 'string') {
        this.elements.container = document.querySelector(container);
      } else {
        this.elements.container = container;
      }
      
      if (!this.elements.container) {
        console.warn('ProgressController: Container element not found');
        return this;
      }
      
      // Find child elements
      this.elements.progressBar = this.elements.container.querySelector('.progress-bar');
      this.elements.progressText = this.elements.container.querySelector('.progress-text');
      this.elements.stepName = this.elements.container.querySelector('.progress-step');
      this.elements.timeRemaining = this.elements.container.querySelector('.progress-time');
      this.elements.modulesList = this.elements.container.querySelector('.modules-list');
      
      return this;
    }

    /**
     * Set DOM elements directly
     * @param {Object} elements - Object containing DOM element references
     * @returns {ProgressController}
     */
    setElements(elements) {
      this.elements = { ...this.elements, ...elements };
      return this;
    }

    /**
     * Start the progress tracking
     * @returns {ProgressController}
     */
    start() {
      this.startTime = Date.now();
      this.status = 'running';
      this.currentProgress = 0;
      this.currentModuleIndex = 0;
      this.completedModules = [];
      
      this._updateStatus('running');
      this._updateProgressBar(0);
      
      return this;
    }

    /**
     * Update progress with current module information
     * @param {number} moduleIndex - Current module index (1-based)
     * @param {string} moduleName - Name of the current module
     * @returns {ProgressController}
     */
    updateProgress(moduleIndex, moduleName) {
      this.currentModuleIndex = moduleIndex;
      this.currentStep = moduleName;
      
      // Calculate progress percentage
      const progress = Math.round((moduleIndex / this.totalModules) * 100);
      this.currentProgress = Math.min(progress, 100);
      
      // Update UI
      this._updateProgressBar(this.currentProgress);
      this._updateStepName(moduleName);
      this._updateTimeRemaining();
      
      return this;
    }

    /**
     * Mark a module as completed
     * @param {number} moduleNumber - Module number (1-28)
     * @param {string} [moduleName] - Optional module name
     * @returns {ProgressController}
     */
    completeModule(moduleNumber, moduleName) {
      if (!this.completedModules.includes(moduleNumber)) {
        this.completedModules.push(moduleNumber);
        this._addCompletedModuleBadge(moduleNumber, moduleName);
      }
      
      // Update progress
      const progress = Math.round((this.completedModules.length / this.totalModules) * 100);
      this.currentProgress = Math.min(progress, 100);
      this._updateProgressBar(this.currentProgress);
      this._updateTimeRemaining();
      
      return this;
    }

    /**
     * Mark analysis as complete
     * @returns {ProgressController}
     */
    complete() {
      this.status = 'completed';
      this.currentProgress = 100;
      
      this._updateProgressBar(100);
      this._updateStatus('completed');
      this._updateStepName('分析完成');
      
      if (this.elements.timeRemaining) {
        const elapsed = this._getElapsedTime();
        this.elements.timeRemaining.textContent = `完成時間: ${elapsed}`;
      }
      
      return this;
    }

    /**
     * Mark analysis as failed
     * @param {string} [errorMessage] - Error message to display
     * @returns {ProgressController}
     */
    error(errorMessage) {
      this.status = 'error';
      
      this._updateStatus('error');
      this._updateStepName(errorMessage || '分析失敗');
      
      return this;
    }

    /**
     * Reset the progress indicator
     * @returns {ProgressController}
     */
    reset() {
      this.currentProgress = 0;
      this.currentStep = '';
      this.currentModuleIndex = 0;
      this.completedModules = [];
      this.startTime = null;
      this.status = 'idle';
      
      this._updateProgressBar(0);
      this._updateStatus('idle');
      this._updateStepName('');
      
      if (this.elements.timeRemaining) {
        this.elements.timeRemaining.textContent = '';
      }
      
      if (this.elements.modulesList) {
        this.elements.modulesList.innerHTML = '';
      }
      
      return this;
    }

    /**
     * Get current progress percentage
     * @returns {number}
     */
    getProgress() {
      return this.currentProgress;
    }

    /**
     * Get current step name
     * @returns {string}
     */
    getCurrentStep() {
      return this.currentStep;
    }

    /**
     * Get list of completed modules
     * @returns {number[]}
     */
    getCompletedModules() {
      return [...this.completedModules];
    }

    /**
     * Get current status
     * @returns {string}
     */
    getStatus() {
      return this.status;
    }

    /**
     * Calculate estimated remaining time
     * @returns {number} Remaining time in seconds
     */
    calculateRemainingTime() {
      const remainingModules = this.totalModules - this.completedModules.length;
      
      // If we have timing data, use actual average
      if (this.startTime && this.completedModules.length > 0) {
        const elapsed = (Date.now() - this.startTime) / 1000;
        const avgTimePerModule = elapsed / this.completedModules.length;
        return Math.round(remainingModules * avgTimePerModule);
      }
      
      // Otherwise use default estimate
      return remainingModules * this.timePerModule;
    }

    /**
     * Format time in seconds to human-readable string
     * @param {number} seconds - Time in seconds
     * @returns {string}
     */
    formatTime(seconds) {
      if (seconds < 60) {
        return `${seconds} 秒`;
      }
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = seconds % 60;
      if (remainingSeconds === 0) {
        return `${minutes} 分鐘`;
      }
      return `${minutes} 分 ${remainingSeconds} 秒`;
    }

    /**
     * Create a checkmark SVG element
     * @param {boolean} [animated=true] - Whether to animate the checkmark
     * @returns {SVGElement}
     */
    createCheckmarkSVG(animated = true) {
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('class', `checkmark-svg${animated && !this.reducedMotion ? ' checkmark-animated' : ''}`);
      svg.setAttribute('viewBox', '0 0 24 24');
      svg.setAttribute('width', '14');
      svg.setAttribute('height', '14');
      
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('class', 'checkmark-path');
      path.setAttribute('d', 'M5 12l5 5L19 7');
      path.setAttribute('fill', 'none');
      path.setAttribute('stroke', 'currentColor');
      path.setAttribute('stroke-width', '2');
      path.setAttribute('stroke-linecap', 'round');
      path.setAttribute('stroke-linejoin', 'round');
      
      svg.appendChild(path);
      return svg;
    }

    /**
     * Create a circular progress SVG element
     * @param {number} [progress=0] - Initial progress percentage
     * @returns {HTMLElement}
     */
    createProgressCircle(progress = 0) {
      const container = document.createElement('div');
      container.className = 'progress-circle';
      
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('viewBox', '0 0 100 100');
      
      // Background circle
      const bgCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      bgCircle.setAttribute('class', 'progress-bg');
      bgCircle.setAttribute('cx', '50');
      bgCircle.setAttribute('cy', '50');
      bgCircle.setAttribute('r', String(CIRCLE_RADIUS));
      
      // Progress bar circle
      const progressCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      progressCircle.setAttribute('class', 'progress-bar');
      progressCircle.setAttribute('cx', '50');
      progressCircle.setAttribute('cy', '50');
      progressCircle.setAttribute('r', String(CIRCLE_RADIUS));
      progressCircle.style.setProperty('--progress', String(progress));
      
      svg.appendChild(bgCircle);
      svg.appendChild(progressCircle);
      
      // Percentage text
      const text = document.createElement('div');
      text.className = 'progress-text';
      text.textContent = `${progress}%`;
      
      container.appendChild(svg);
      container.appendChild(text);
      
      return container;
    }

    /**
     * Create a complete progress indicator component
     * @param {Object} [options] - Options for the component
     * @returns {HTMLElement}
     */
    createProgressComponent(options = {}) {
      const container = document.createElement('div');
      container.className = `progress-modern ${options.status || 'idle'}`;
      
      // Progress circle
      const circle = this.createProgressCircle(options.progress || 0);
      container.appendChild(circle);
      
      // Details section
      const details = document.createElement('div');
      details.className = 'progress-details';
      
      const title = document.createElement('h5');
      title.textContent = options.title || '準備分析...';
      details.appendChild(title);
      
      const step = document.createElement('p');
      step.className = 'progress-step';
      step.textContent = options.step || '';
      details.appendChild(step);
      
      const time = document.createElement('div');
      time.className = 'progress-time';
      time.textContent = options.time || '';
      details.appendChild(time);
      
      // Completed modules section
      if (options.showModules !== false) {
        const modulesSection = document.createElement('div');
        modulesSection.className = 'progress-modules';
        
        const modulesTitle = document.createElement('div');
        modulesTitle.className = 'modules-title';
        modulesTitle.textContent = '已完成模塊:';
        modulesSection.appendChild(modulesTitle);
        
        const modulesList = document.createElement('div');
        modulesList.className = 'modules-list';
        modulesSection.appendChild(modulesList);
        
        details.appendChild(modulesSection);
      }
      
      container.appendChild(details);
      
      // Initialize with this container
      this.init(container);
      
      return container;
    }

    // ========================================================================
    // PRIVATE METHODS
    // ========================================================================

    /**
     * Update the progress bar SVG
     * @private
     * @param {number} progress - Progress percentage (0-100)
     */
    _updateProgressBar(progress) {
      if (this.elements.progressBar) {
        this.elements.progressBar.style.setProperty('--progress', String(progress));
      }
      
      if (this.elements.progressText) {
        this.elements.progressText.textContent = `${progress}%`;
      }
    }

    /**
     * Update the step name display
     * @private
     * @param {string} stepName - Current step name
     */
    _updateStepName(stepName) {
      if (this.elements.stepName) {
        this.elements.stepName.textContent = stepName;
      }
    }

    /**
     * Update the time remaining display
     * @private
     */
    _updateTimeRemaining() {
      if (this.elements.timeRemaining) {
        const remaining = this.calculateRemainingTime();
        this.elements.timeRemaining.textContent = `預計剩餘: ${this.formatTime(remaining)}`;
      }
    }

    /**
     * Update the status class on the container
     * @private
     * @param {string} status - Status string
     */
    _updateStatus(status) {
      if (this.elements.container) {
        this.elements.container.classList.remove('idle', 'running', 'completed', 'error');
        this.elements.container.classList.add(status);
      }
    }

    /**
     * Add a completed module badge to the list
     * @private
     * @param {number} moduleNumber - Module number
     * @param {string} [moduleName] - Module name
     */
    _addCompletedModuleBadge(moduleNumber, moduleName) {
      if (!this.elements.modulesList) return;
      
      const badge = document.createElement('span');
      badge.className = 'module-badge-progress completed';
      badge.setAttribute('data-module', String(moduleNumber));
      badge.setAttribute('title', moduleName || `Module ${moduleNumber}`);
      
      // Add checkmark
      const checkmark = this.createCheckmarkSVG(!this.reducedMotion);
      checkmark.classList.add('checkmark-icon');
      badge.appendChild(checkmark);
      
      // Add module number (hidden when completed)
      const number = document.createElement('span');
      number.className = 'module-number';
      number.textContent = String(moduleNumber);
      badge.appendChild(number);
      
      this.elements.modulesList.appendChild(badge);
      
      // Trigger animation
      if (!this.reducedMotion) {
        this._animateCheckmark(badge);
      }
    }

    /**
     * Animate a checkmark element
     * @private
     * @param {HTMLElement} element - Element containing the checkmark
     */
    _animateCheckmark(element) {
      // Force reflow to trigger animation
      element.offsetHeight;
      element.classList.add('animate-in');
    }

    /**
     * Get elapsed time as formatted string
     * @private
     * @returns {string}
     */
    _getElapsedTime() {
      if (!this.startTime) return '0 秒';
      const elapsed = Math.round((Date.now() - this.startTime) / 1000);
      return this.formatTime(elapsed);
    }
  }

  // Export for different module systems
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = ProgressController;
  } else if (typeof global !== 'undefined') {
    global.ProgressController = ProgressController;
  }

})(typeof window !== 'undefined' ? window : global);
