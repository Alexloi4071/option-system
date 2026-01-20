/**
 * Icon System Controller
 * Standardizes icon usage across the application using Font Awesome 6.0+
 * Requirements: 12.1, 12.3, 12.4, 12.5
 */

// ============================================================================
// ICON LIBRARY CONFIGURATION
// ============================================================================

/**
 * The single icon library used throughout the application
 * All icons must use this library prefix
 */
const ICON_LIBRARY = 'fa';
const ICON_LIBRARY_PREFIX = 'fas'; // Font Awesome Solid (default)
const ICON_LIBRARY_REGULAR = 'far'; // Font Awesome Regular
const ICON_LIBRARY_BRANDS = 'fab'; // Font Awesome Brands

/**
 * Valid icon library prefixes
 */
const VALID_ICON_PREFIXES = [
  'fa',      // Generic Font Awesome
  'fas',     // Font Awesome Solid
  'far',     // Font Awesome Regular
  'fab',     // Font Awesome Brands
  'fal',     // Font Awesome Light (Pro)
  'fad',     // Font Awesome Duotone (Pro)
  'fat'      // Font Awesome Thin (Pro)
];

// ============================================================================
// STATUS ICON MAPPING
// ============================================================================

/**
 * Status icon mapping for consistent status indicators
 * Maps status types to their corresponding Font Awesome icons
 */
const STATUS_ICONS = {
  success: 'fa-check-circle',
  warning: 'fa-exclamation-triangle',
  error: 'fa-times-circle',
  info: 'fa-info-circle',
  loading: 'fa-spinner',
  pending: 'fa-clock',
  complete: 'fa-check',
  incomplete: 'fa-circle',
  active: 'fa-circle',
  inactive: 'fa-circle-notch',
  connected: 'fa-plug',
  disconnected: 'fa-plug-circle-xmark',
  online: 'fa-wifi',
  offline: 'fa-wifi-slash'
};

/**
 * Get the icon class for a status type
 * @param {string} status - The status type
 * @returns {string} The Font Awesome icon class
 */
function getStatusIcon(status) {
  const normalizedStatus = String(status).toLowerCase().trim();
  return STATUS_ICONS[normalizedStatus] || STATUS_ICONS.info;
}

// ============================================================================
// DIRECTIONAL ICON MAPPING
// ============================================================================

/**
 * Directional icon mapping for price changes and trends
 * Maps direction types to their corresponding Font Awesome icons
 */
const DIRECTIONAL_ICONS = {
  up: 'fa-arrow-up',
  down: 'fa-arrow-down',
  flat: 'fa-minus',
  increase: 'fa-arrow-up',
  decrease: 'fa-arrow-down',
  unchanged: 'fa-minus',
  positive: 'fa-arrow-up',
  negative: 'fa-arrow-down',
  neutral: 'fa-minus',
  bullish: 'fa-arrow-trend-up',
  bearish: 'fa-arrow-trend-down',
  sideways: 'fa-arrows-left-right'
};

/**
 * Get the directional icon for a price change
 * @param {number|string} value - The numeric value or direction string
 * @returns {string} The Font Awesome icon class
 */
function getDirectionalIcon(value) {
  // Handle string directions
  if (typeof value === 'string') {
    const normalizedDirection = value.toLowerCase().trim();
    return DIRECTIONAL_ICONS[normalizedDirection] || DIRECTIONAL_ICONS.flat;
  }
  
  // Handle numeric values
  if (typeof value === 'number' && !isNaN(value)) {
    if (value > 0) {
      return DIRECTIONAL_ICONS.up;
    } else if (value < 0) {
      return DIRECTIONAL_ICONS.down;
    }
  }
  
  return DIRECTIONAL_ICONS.flat;
}

// ============================================================================
// MODULE ICON MAPPING
// ============================================================================

/**
 * Module icon mapping for analysis modules
 */
const MODULE_ICONS = {
  'support-resistance': 'fa-chart-line',
  'fair-value': 'fa-balance-scale',
  'arbitrage': 'fa-exchange-alt',
  'pe-valuation': 'fa-calculator',
  'rate-pe': 'fa-percentage',
  'hedge': 'fa-shield-alt',
  'long-call': 'fa-arrow-up',
  'long-put': 'fa-arrow-down',
  'short-call': 'fa-arrow-down',
  'short-put': 'fa-arrow-up',
  'synthetic': 'fa-sync-alt',
  'yield': 'fa-coins',
  'position': 'fa-layer-group',
  'monitoring': 'fa-eye',
  'black-scholes': 'fa-square-root-alt',
  'greeks': 'fa-chart-area',
  'iv': 'fa-wave-square',
  'hv': 'fa-history',
  'parity': 'fa-equals',
  'health': 'fa-heartbeat',
  'momentum': 'fa-tachometer-alt',
  'optimal-strike': 'fa-bullseye',
  'iv-threshold': 'fa-sliders-h',
  'technical': 'fa-compass',
  'volatility-smile': 'fa-smile',
  'long-option': 'fa-chart-bar',
  'multi-expiry': 'fa-calendar-alt',
  'position-calculator': 'fa-calculator'
};

/**
 * Get the icon for a module
 * @param {string} moduleKey - The module key
 * @returns {string} The Font Awesome icon class
 */
function getModuleIcon(moduleKey) {
  const normalizedKey = String(moduleKey).toLowerCase().trim();
  return MODULE_ICONS[normalizedKey] || 'fa-cube';
}

// ============================================================================
// ACTION ICON MAPPING
// ============================================================================

/**
 * Action icon mapping for buttons and interactive elements
 */
const ACTION_ICONS = {
  analyze: 'fa-play',
  refresh: 'fa-sync-alt',
  settings: 'fa-cog',
  search: 'fa-search',
  filter: 'fa-filter',
  sort: 'fa-sort',
  expand: 'fa-expand',
  collapse: 'fa-compress',
  close: 'fa-times',
  save: 'fa-save',
  export: 'fa-download',
  import: 'fa-upload',
  copy: 'fa-copy',
  edit: 'fa-edit',
  delete: 'fa-trash',
  add: 'fa-plus',
  remove: 'fa-minus',
  help: 'fa-question-circle',
  theme: 'fa-moon',
  'theme-light': 'fa-sun',
  'theme-dark': 'fa-moon'
};

/**
 * Get the icon for an action
 * @param {string} action - The action type
 * @returns {string} The Font Awesome icon class
 */
function getActionIcon(action) {
  const normalizedAction = String(action).toLowerCase().trim();
  return ACTION_ICONS[normalizedAction] || 'fa-circle';
}

// ============================================================================
// ICON SIZE CONFIGURATION
// ============================================================================

/**
 * Standard icon sizes for consistent sizing
 */
const ICON_SIZES = {
  xs: '0.75rem',   // 12px
  sm: '0.875rem',  // 14px
  base: '1rem',    // 16px
  lg: '1.125rem',  // 18px
  xl: '1.25rem',   // 20px
  '2xl': '1.5rem', // 24px
  '3xl': '2rem',   // 32px
  '4xl': '2.5rem'  // 40px
};

/**
 * Get the CSS size value for an icon size
 * @param {string} size - The size key
 * @returns {string} The CSS size value
 */
function getIconSize(size) {
  return ICON_SIZES[size] || ICON_SIZES.base;
}

// ============================================================================
// ICON VALIDATION
// ============================================================================

/**
 * Check if an icon class uses the standard Font Awesome library
 * @param {string} iconClass - The icon class string
 * @returns {boolean} True if the icon uses Font Awesome
 */
function isValidIconLibrary(iconClass) {
  if (!iconClass || typeof iconClass !== 'string') {
    return false;
  }
  
  const classes = iconClass.trim().split(/\s+/);
  
  // Check if any class starts with a valid Font Awesome prefix
  return classes.some(cls => {
    return VALID_ICON_PREFIXES.some(prefix => 
      cls === prefix || cls.startsWith(`${prefix}-`)
    );
  });
}

/**
 * Check if an icon class is from a mixed/invalid library
 * @param {string} iconClass - The icon class string
 * @returns {boolean} True if the icon is from a non-Font Awesome library
 */
function isMixedLibraryIcon(iconClass) {
  if (!iconClass || typeof iconClass !== 'string') {
    return false;
  }
  
  const classes = iconClass.trim().split(/\s+/);
  
  // Check for common non-Font Awesome icon libraries
  const invalidPrefixes = [
    'material-icons',
    'mdi',
    'bi',           // Bootstrap Icons
    'icon-',
    'glyphicon',
    'ion-',         // Ionicons
    'feather-',     // Feather Icons
    'heroicon'      // Heroicons
  ];
  
  return classes.some(cls => 
    invalidPrefixes.some(prefix => 
      cls.startsWith(prefix) || cls === prefix
    )
  );
}

// ============================================================================
// ICON ELEMENT CREATION
// ============================================================================

/**
 * Create an icon element with standardized classes
 * @param {string} iconName - The icon name (without prefix, e.g., 'check-circle')
 * @param {Object} [options] - Icon options
 * @param {string} [options.prefix] - Icon prefix (default: 'fas')
 * @param {string} [options.size] - Icon size key
 * @param {string} [options.color] - Icon color class
 * @param {boolean} [options.spin] - Whether to add spin animation
 * @param {boolean} [options.pulse] - Whether to add pulse animation
 * @param {string} [options.ariaLabel] - Accessibility label
 * @returns {HTMLElement} The icon element
 */
function createIcon(iconName, options = {}) {
  const {
    prefix = ICON_LIBRARY_PREFIX,
    size,
    color,
    spin = false,
    pulse = false,
    ariaLabel
  } = options;
  
  const icon = document.createElement('i');
  
  // Add base classes
  icon.className = prefix;
  
  // Add icon name (ensure it has fa- prefix)
  const normalizedName = iconName.startsWith('fa-') ? iconName : `fa-${iconName}`;
  icon.classList.add(normalizedName);
  
  // Add size class if specified
  if (size && ICON_SIZES[size]) {
    icon.style.fontSize = ICON_SIZES[size];
  }
  
  // Add color class if specified
  if (color) {
    icon.classList.add(`icon-${color}`);
  }
  
  // Add animation classes
  if (spin) {
    icon.classList.add('fa-spin');
  }
  if (pulse) {
    icon.classList.add('fa-pulse');
  }
  
  // Add accessibility attributes
  if (ariaLabel) {
    icon.setAttribute('aria-label', ariaLabel);
    icon.setAttribute('role', 'img');
  } else {
    icon.setAttribute('aria-hidden', 'true');
  }
  
  return icon;
}

/**
 * Create a status icon element
 * @param {string} status - The status type
 * @param {Object} [options] - Additional icon options
 * @returns {HTMLElement} The status icon element
 */
function createStatusIcon(status, options = {}) {
  const iconName = getStatusIcon(status);
  const colorMap = {
    success: 'success',
    warning: 'warning',
    error: 'danger',
    info: 'info',
    loading: 'primary',
    pending: 'secondary'
  };
  
  return createIcon(iconName, {
    ...options,
    color: options.color || colorMap[status] || 'secondary',
    spin: status === 'loading' ? true : options.spin
  });
}

/**
 * Create a directional icon element for price changes
 * @param {number|string} value - The numeric value or direction string
 * @param {Object} [options] - Additional icon options
 * @returns {HTMLElement} The directional icon element
 */
function createDirectionalIcon(value, options = {}) {
  const iconName = getDirectionalIcon(value);
  
  // Determine color based on value
  let color = 'neutral';
  if (typeof value === 'number' && !isNaN(value)) {
    if (value > 0) color = 'success';
    else if (value < 0) color = 'danger';
  } else if (typeof value === 'string') {
    const positiveDirections = ['up', 'increase', 'positive', 'bullish'];
    const negativeDirections = ['down', 'decrease', 'negative', 'bearish'];
    const normalizedValue = value.toLowerCase().trim();
    
    if (positiveDirections.includes(normalizedValue)) color = 'success';
    else if (negativeDirections.includes(normalizedValue)) color = 'danger';
  }
  
  return createIcon(iconName, {
    ...options,
    color: options.color || color
  });
}

// ============================================================================
// ICON AUDIT UTILITIES
// ============================================================================

/**
 * Audit all icons in a container for library consistency
 * @param {HTMLElement} container - The container to audit
 * @returns {Object} Audit results with valid and invalid icons
 */
function auditIcons(container) {
  const allIcons = container.querySelectorAll('i, span.icon, [class*="icon"]');
  const results = {
    total: 0,
    valid: [],
    invalid: [],
    mixed: []
  };
  
  allIcons.forEach(icon => {
    const className = icon.className;
    results.total++;
    
    if (isValidIconLibrary(className)) {
      results.valid.push({ element: icon, className });
    } else if (isMixedLibraryIcon(className)) {
      results.mixed.push({ element: icon, className });
    } else {
      // Check if it might be an icon element without proper classes
      if (icon.tagName === 'I' || icon.classList.contains('icon')) {
        results.invalid.push({ element: icon, className });
      }
    }
  });
  
  return results;
}

/**
 * Replace invalid icons with Font Awesome equivalents
 * @param {HTMLElement} container - The container to process
 * @param {Object} [mappings] - Custom icon mappings
 */
function standardizeIcons(container, mappings = {}) {
  const audit = auditIcons(container);
  
  // Process mixed library icons
  audit.mixed.forEach(({ element, className }) => {
    // Try to find a mapping for the icon
    const iconName = extractIconName(className);
    const faEquivalent = mappings[iconName] || findFontAwesomeEquivalent(iconName);
    
    if (faEquivalent) {
      element.className = `${ICON_LIBRARY_PREFIX} ${faEquivalent}`;
    }
  });
}

/**
 * Extract the icon name from a class string
 * @param {string} className - The class string
 * @returns {string|null} The extracted icon name
 */
function extractIconName(className) {
  if (!className) return null;
  
  const classes = className.split(/\s+/);
  for (const cls of classes) {
    // Skip prefix classes
    if (VALID_ICON_PREFIXES.includes(cls)) continue;
    
    // Extract icon name from various formats
    const match = cls.match(/(?:fa-|icon-|mdi-|bi-)?(.+)/);
    if (match) {
      return match[1];
    }
  }
  
  return null;
}

/**
 * Find Font Awesome equivalent for common icon names
 * @param {string} iconName - The icon name to find
 * @returns {string|null} The Font Awesome equivalent
 */
function findFontAwesomeEquivalent(iconName) {
  const equivalents = {
    'check': 'fa-check',
    'close': 'fa-times',
    'x': 'fa-times',
    'menu': 'fa-bars',
    'hamburger': 'fa-bars',
    'search': 'fa-search',
    'home': 'fa-home',
    'user': 'fa-user',
    'settings': 'fa-cog',
    'gear': 'fa-cog',
    'arrow-left': 'fa-arrow-left',
    'arrow-right': 'fa-arrow-right',
    'chevron-left': 'fa-chevron-left',
    'chevron-right': 'fa-chevron-right',
    'chevron-up': 'fa-chevron-up',
    'chevron-down': 'fa-chevron-down',
    'plus': 'fa-plus',
    'minus': 'fa-minus',
    'edit': 'fa-edit',
    'pencil': 'fa-pencil',
    'trash': 'fa-trash',
    'delete': 'fa-trash',
    'save': 'fa-save',
    'download': 'fa-download',
    'upload': 'fa-upload',
    'refresh': 'fa-sync-alt',
    'reload': 'fa-sync-alt',
    'spinner': 'fa-spinner',
    'loading': 'fa-spinner'
  };
  
  return equivalents[iconName] || null;
}

// ============================================================================
// EXPORTS
// ============================================================================

// Export for Node.js/CommonJS
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    // Constants
    ICON_LIBRARY,
    ICON_LIBRARY_PREFIX,
    VALID_ICON_PREFIXES,
    STATUS_ICONS,
    DIRECTIONAL_ICONS,
    MODULE_ICONS,
    ACTION_ICONS,
    ICON_SIZES,
    
    // Status icons
    getStatusIcon,
    createStatusIcon,
    
    // Directional icons
    getDirectionalIcon,
    createDirectionalIcon,
    
    // Module icons
    getModuleIcon,
    
    // Action icons
    getActionIcon,
    
    // Icon sizing
    getIconSize,
    
    // Validation
    isValidIconLibrary,
    isMixedLibraryIcon,
    
    // Element creation
    createIcon,
    
    // Audit utilities
    auditIcons,
    standardizeIcons,
    extractIconName,
    findFontAwesomeEquivalent
  };
}

// Export for browser
if (typeof window !== 'undefined') {
  window.IconSystem = {
    // Constants
    ICON_LIBRARY,
    ICON_LIBRARY_PREFIX,
    VALID_ICON_PREFIXES,
    STATUS_ICONS,
    DIRECTIONAL_ICONS,
    MODULE_ICONS,
    ACTION_ICONS,
    ICON_SIZES,
    
    // Status icons
    getStatusIcon,
    createStatusIcon,
    
    // Directional icons
    getDirectionalIcon,
    createDirectionalIcon,
    
    // Module icons
    getModuleIcon,
    
    // Action icons
    getActionIcon,
    
    // Icon sizing
    getIconSize,
    
    // Validation
    isValidIconLibrary,
    isMixedLibraryIcon,
    
    // Element creation
    createIcon,
    
    // Audit utilities
    auditIcons,
    standardizeIcons,
    extractIconName,
    findFontAwesomeEquivalent
  };
}
