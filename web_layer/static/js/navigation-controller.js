/**
 * Navigation Controller
 * Handles navigation bar scroll effects and mobile menu
 * Requirements: 10.1, 10.2, 10.3, 10.4
 */

class NavigationController {
  constructor() {
    this.navbar = null;
    this.scrollThreshold = 0;
    this.isScrolled = false;
    this.mobileMenuOpen = false;
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.init());
    } else {
      this.init();
    }
  }
  
  /**
   * Initialize navigation controller
   */
  init() {
    this.navbar = document.querySelector('.navbar-modern');
    
    if (!this.navbar) {
      console.warn('NavigationController: No .navbar-modern element found');
      return;
    }
    
    // Set up scroll listener
    this.setupScrollListener();
    
    // Set up mobile menu toggle
    this.setupMobileMenu();
    
    // Set up dropdown menus
    this.setupDropdowns();
    
    // Initial scroll check
    this.checkScroll();
    
    console.log('NavigationController initialized');
  }
  
  /**
   * Set up scroll event listener with throttling
   */
  setupScrollListener() {
    let ticking = false;
    
    window.addEventListener('scroll', () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          this.checkScroll();
          ticking = false;
        });
        ticking = true;
      }
    }, { passive: true });
  }
  
  /**
   * Check scroll position and update navbar state
   */
  checkScroll() {
    const scrollY = window.scrollY || window.pageYOffset;
    const shouldBeScrolled = scrollY > this.scrollThreshold;
    
    if (shouldBeScrolled !== this.isScrolled) {
      this.isScrolled = shouldBeScrolled;
      this.updateNavbarState();
    }
  }
  
  /**
   * Update navbar visual state based on scroll
   */
  updateNavbarState() {
    if (!this.navbar) return;
    
    if (this.isScrolled) {
      this.navbar.classList.add('scrolled');
    } else {
      this.navbar.classList.remove('scrolled');
    }
    
    // Dispatch custom event for other components
    this.dispatchScrollEvent();
  }
  
  /**
   * Dispatch custom scroll state event
   */
  dispatchScrollEvent() {
    const event = new CustomEvent('navbarscroll', {
      detail: {
        isScrolled: this.isScrolled,
        scrollY: window.scrollY || window.pageYOffset,
        timestamp: Date.now()
      }
    });
    document.dispatchEvent(event);
  }
  
  /**
   * Set up mobile menu toggle functionality
   */
  setupMobileMenu() {
    const menuToggle = document.querySelector('.navbar-menu-toggle');
    const mobileMenu = document.querySelector('.navbar-mobile-menu');
    
    if (!menuToggle || !mobileMenu) return;
    
    menuToggle.addEventListener('click', () => {
      this.toggleMobileMenu();
    });
    
    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
      if (this.mobileMenuOpen && 
          !mobileMenu.contains(e.target) && 
          !menuToggle.contains(e.target)) {
        this.closeMobileMenu();
      }
    });
    
    // Close menu on escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.mobileMenuOpen) {
        this.closeMobileMenu();
      }
    });
  }
  
  /**
   * Toggle mobile menu open/closed
   */
  toggleMobileMenu() {
    if (this.mobileMenuOpen) {
      this.closeMobileMenu();
    } else {
      this.openMobileMenu();
    }
  }
  
  /**
   * Open mobile menu
   */
  openMobileMenu() {
    const mobileMenu = document.querySelector('.navbar-mobile-menu');
    const menuToggle = document.querySelector('.navbar-menu-toggle');
    
    if (!mobileMenu) return;
    
    mobileMenu.classList.add('open');
    this.mobileMenuOpen = true;
    
    // Update toggle button icon
    if (menuToggle) {
      const icon = menuToggle.querySelector('i');
      if (icon) {
        icon.className = 'fas fa-times';
      }
      menuToggle.setAttribute('aria-expanded', 'true');
    }
    
    // Prevent body scroll
    document.body.style.overflow = 'hidden';
  }
  
  /**
   * Close mobile menu
   */
  closeMobileMenu() {
    const mobileMenu = document.querySelector('.navbar-mobile-menu');
    const menuToggle = document.querySelector('.navbar-menu-toggle');
    
    if (!mobileMenu) return;
    
    mobileMenu.classList.remove('open');
    this.mobileMenuOpen = false;
    
    // Update toggle button icon
    if (menuToggle) {
      const icon = menuToggle.querySelector('i');
      if (icon) {
        icon.className = 'fas fa-bars';
      }
      menuToggle.setAttribute('aria-expanded', 'false');
    }
    
    // Restore body scroll
    document.body.style.overflow = '';
  }
  
  /**
   * Set up dropdown menu functionality
   */
  setupDropdowns() {
    const dropdowns = document.querySelectorAll('.navbar-dropdown');
    
    dropdowns.forEach(dropdown => {
      const trigger = dropdown.querySelector('.navbar-btn, .dropdown-trigger');
      
      if (!trigger) return;
      
      trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggleDropdown(dropdown);
      });
    });
    
    // Close dropdowns when clicking outside
    document.addEventListener('click', () => {
      this.closeAllDropdowns();
    });
    
    // Close dropdowns on escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.closeAllDropdowns();
      }
    });
  }
  
  /**
   * Toggle a dropdown menu
   * @param {HTMLElement} dropdown - Dropdown element
   */
  toggleDropdown(dropdown) {
    const isOpen = dropdown.classList.contains('open');
    
    // Close all other dropdowns first
    this.closeAllDropdowns();
    
    if (!isOpen) {
      dropdown.classList.add('open');
    }
  }
  
  /**
   * Close all dropdown menus
   */
  closeAllDropdowns() {
    const dropdowns = document.querySelectorAll('.navbar-dropdown.open');
    dropdowns.forEach(dropdown => {
      dropdown.classList.remove('open');
    });
  }
  
  /**
   * Update status indicator
   * @param {string} indicatorId - ID or selector for the status indicator
   * @param {string} status - Status value ('connected', 'disconnected', 'loading', etc.)
   * @param {string} [text] - Optional text to display
   */
  updateStatus(indicatorId, status, text) {
    const indicator = document.querySelector(indicatorId) || 
                      document.getElementById(indicatorId);
    
    if (!indicator) return;
    
    indicator.setAttribute('data-status', status);
    
    if (text) {
      const textElement = indicator.querySelector('span') || indicator;
      if (textElement.tagName !== 'I') {
        textElement.textContent = text;
      }
    }
  }
  
  /**
   * Get current scroll state
   * @returns {boolean} Whether navbar is in scrolled state
   */
  getScrollState() {
    return this.isScrolled;
  }
  
  /**
   * Check if navbar has scrolled class
   * @returns {boolean} Whether navbar has 'scrolled' class
   */
  hasScrolledClass() {
    return this.navbar ? this.navbar.classList.contains('scrolled') : false;
  }
}

// Create global instance only in browser environment
if (typeof window !== 'undefined' && typeof module === 'undefined') {
  const navigationController = new NavigationController();
}

// Export for use in other modules and testing
if (typeof module !== 'undefined' && module.exports) {
  module.exports = NavigationController;
}
