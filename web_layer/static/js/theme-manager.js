/**
 * Theme Manager
 * Handles theme switching, persistence, and system preference detection
 * Requirements: 2.2, 2.3, 2.4
 */

class ThemeManager {
  constructor() {
    this.STORAGE_KEY = 'user-theme-preference';
    this.THEME_ATTRIBUTE = 'data-theme';
    this.themes = ['light', 'dark'];
    this.currentTheme = null;
    this.storageAvailable = this.isLocalStorageAvailable();
    this.fallbackStorage = {}; // In-memory fallback when localStorage unavailable
    this.errorCount = 0;
    this.maxErrors = 3;
    
    // Initialize theme on construction
    this.init();
  }
  
  /**
   * Initialize theme manager
   * Loads saved preference or detects system preference
   * Includes comprehensive error handling
   */
  init() {
    try {
      // Check localStorage availability
      if (!this.storageAvailable) {
        console.warn('[Theme Manager] localStorage not available. Using in-memory storage and system preference.');
        this.showStorageWarning();
      }
      
      // Try to load saved preference
      const savedTheme = this.loadTheme();
      
      if (savedTheme && this.themes.includes(savedTheme)) {
        this.setTheme(savedTheme, false); // Don't save again
      } else {
        // Detect system preference as fallback
        const systemTheme = this.getSystemPreference();
        console.log('[Theme Manager] No saved preference found. Using system preference:', systemTheme);
        this.setTheme(systemTheme, true); // Save the detected preference
      }
      
      // Listen for system preference changes
      this.watchSystemPreference();
      
    } catch (error) {
      console.error('[Theme Manager] Initialization error:', error);
      this.handleError(error);
      // Fallback to light theme
      this.setTheme('light', false);
    }
  }
  
  /**
   * Get system color scheme preference
   * @returns {string} 'light' or 'dark'
   */
  getSystemPreference() {
    try {
      if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return 'dark';
      }
      return 'light';
    } catch (error) {
      console.warn('[Theme Manager] Failed to detect system preference:', error);
      return 'light'; // Default fallback
    }
  }
  
  /**
   * Watch for system preference changes
   */
  watchSystemPreference() {
    try {
      if (!window.matchMedia) {
        console.warn('[Theme Manager] matchMedia not supported. System preference watching disabled.');
        return;
      }
      
      const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
      
      const handleChange = (e) => {
        try {
          // Only auto-switch if user hasn't set a preference
          const savedTheme = this.loadTheme();
          if (!savedTheme) {
            const newTheme = e.matches ? 'dark' : 'light';
            console.log('[Theme Manager] System preference changed to:', newTheme);
            this.setTheme(newTheme, false);
          }
        } catch (error) {
          console.warn('[Theme Manager] Error handling system preference change:', error);
        }
      };
      
      // Modern browsers
      if (darkModeQuery.addEventListener) {
        darkModeQuery.addEventListener('change', handleChange);
      }
      // Older browsers
      else if (darkModeQuery.addListener) {
        darkModeQuery.addListener(handleChange);
      }
    } catch (error) {
      console.warn('[Theme Manager] Failed to watch system preference:', error);
    }
  }
  
  /**
   * Set the current theme
   * @param {string} theme - 'light' or 'dark'
   * @param {boolean} persist - Whether to save to localStorage (default: true)
   */
  setTheme(theme, persist = true) {
    try {
      if (!this.themes.includes(theme)) {
        console.warn(`[Theme Manager] Invalid theme: ${theme}. Using 'light' as fallback.`);
        theme = 'light';
      }
      
      // Update document attribute
      document.documentElement.setAttribute(this.THEME_ATTRIBUTE, theme);
      this.currentTheme = theme;
      
      // Persist to localStorage if requested
      if (persist) {
        this.saveTheme(theme);
      }
      
      // Dispatch custom event for other components to listen
      this.dispatchThemeChangeEvent(theme);
      
      // Update theme toggle button icon if it exists
      this.updateThemeToggleIcon(theme);
      
    } catch (error) {
      console.error('[Theme Manager] Error setting theme:', error);
      this.handleError(error);
    }
  }
  
  /**
   * Toggle between light and dark themes
   */
  toggleTheme() {
    const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
    this.setTheme(newTheme, true);
  }
  
  /**
   * Get the current theme
   * @returns {string} Current theme ('light' or 'dark')
   */
  getCurrentTheme() {
    return this.currentTheme;
  }
  
  /**
   * Save theme preference to localStorage
   * @param {string} theme - Theme to save
   */
  saveTheme(theme) {
    try {
      if (this.storageAvailable) {
        localStorage.setItem(this.STORAGE_KEY, theme);
      } else {
        // Use in-memory fallback
        this.fallbackStorage[this.STORAGE_KEY] = theme;
        console.log('[Theme Manager] Saved theme to in-memory storage:', theme);
      }
    } catch (error) {
      console.warn('[Theme Manager] Failed to save theme preference:', error);
      // Try fallback storage
      try {
        this.fallbackStorage[this.STORAGE_KEY] = theme;
      } catch (fallbackError) {
        console.error('[Theme Manager] Fallback storage also failed:', fallbackError);
        this.handleError(error);
      }
    }
  }
  
  /**
   * Load theme preference from localStorage
   * @returns {string|null} Saved theme or null
   */
  loadTheme() {
    try {
      if (this.storageAvailable) {
        return localStorage.getItem(this.STORAGE_KEY);
      } else {
        // Use in-memory fallback
        return this.fallbackStorage[this.STORAGE_KEY] || null;
      }
    } catch (error) {
      console.warn('[Theme Manager] Failed to load theme preference:', error);
      // Try fallback storage
      try {
        return this.fallbackStorage[this.STORAGE_KEY] || null;
      } catch (fallbackError) {
        console.error('[Theme Manager] Fallback storage also failed:', fallbackError);
        return null;
      }
    }
  }
  
  /**
   * Clear saved theme preference
   */
  clearTheme() {
    try {
      localStorage.removeItem(this.STORAGE_KEY);
    } catch (error) {
      console.warn('Failed to clear theme preference:', error);
    }
  }
  
  /**
   * Dispatch custom theme change event
   * @param {string} theme - New theme
   */
  dispatchThemeChangeEvent(theme) {
    const event = new CustomEvent('themechange', {
      detail: { theme, timestamp: Date.now() }
    });
    document.dispatchEvent(event);
  }
  
  /**
   * Update theme toggle button icon
   * @param {string} theme - Current theme
   */
  updateThemeToggleIcon(theme) {
    const toggleBtn = document.getElementById('themeToggle');
    if (!toggleBtn) return;
    
    const icon = toggleBtn.querySelector('i');
    if (!icon) return;
    
    // Update icon based on theme
    if (theme === 'dark') {
      icon.className = 'fas fa-sun'; // Show sun icon in dark mode
    } else {
      icon.className = 'fas fa-moon'; // Show moon icon in light mode
    }
    
    // Update aria-label for accessibility
    toggleBtn.setAttribute('aria-label', `Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`);
  }
  
  /**
   * Check if localStorage is available
   * @returns {boolean} Whether localStorage is available
   */
  isLocalStorageAvailable() {
    try {
      const test = '__localStorage_test__';
      localStorage.setItem(test, test);
      localStorage.removeItem(test);
      return true;
    } catch (error) {
      return false;
    }
  }
  
  /**
   * Handle errors with fallback mechanisms
   * @param {Error} error - Error object
   */
  handleError(error) {
    this.errorCount++;
    
    if (this.errorCount >= this.maxErrors) {
      console.error('[Theme Manager] Maximum errors reached. Disabling theme switching.');
      this.showErrorNotification('主題切換功能暫時不可用。');
      return;
    }
    
    // Try to recover by using system preference
    try {
      const systemTheme = this.getSystemPreference();
      console.log('[Theme Manager] Attempting recovery with system preference:', systemTheme);
      document.documentElement.setAttribute(this.THEME_ATTRIBUTE, systemTheme);
      this.currentTheme = systemTheme;
    } catch (recoveryError) {
      console.error('[Theme Manager] Recovery failed:', recoveryError);
    }
  }
  
  /**
   * Show warning when localStorage is not available
   */
  showStorageWarning() {
    // Only show once per session
    if (sessionStorage.getItem('theme-storage-warning-shown')) {
      return;
    }
    
    try {
      sessionStorage.setItem('theme-storage-warning-shown', 'true');
    } catch (e) {
      // Even sessionStorage might not be available
    }
    
    console.warn('[Theme Manager] Theme preferences will not persist across sessions.');
  }
  
  /**
   * Show error notification to user
   * @param {string} message - Error message
   */
  showErrorNotification(message) {
    // Try to use existing notification system if available
    if (window.NotificationManager && typeof window.NotificationManager.showError === 'function') {
      window.NotificationManager.showError(message);
      return;
    }
    
    // Fallback: simple console error
    console.error('[Theme Manager]', message);
  }
  
  /**
   * Get error status
   * @returns {Object} Error status information
   */
  getErrorStatus() {
    return {
      errorCount: this.errorCount,
      maxErrors: this.maxErrors,
      storageAvailable: this.storageAvailable,
      currentTheme: this.currentTheme
    };
  }
}

// Create global instance
const themeManager = new ThemeManager();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ThemeManager;
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  try {
    // Bind theme toggle button if it exists
    const themeToggleBtn = document.getElementById('themeToggle');
    if (themeToggleBtn) {
      themeToggleBtn.addEventListener('click', () => {
        try {
          themeManager.toggleTheme();
        } catch (error) {
          console.error('[Theme Manager] Error toggling theme:', error);
          themeManager.handleError(error);
        }
      });
    }
    
    // Log current theme for debugging
    console.log('[Theme Manager] Initialized. Current theme:', themeManager.getCurrentTheme());
    console.log('[Theme Manager] Storage available:', themeManager.storageAvailable);
    
  } catch (error) {
    console.error('[Theme Manager] Error during initialization:', error);
  }
});
