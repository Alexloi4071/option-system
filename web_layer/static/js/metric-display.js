/**
 * Metric Display Controller
 * Handles rendering of metric cards with color-coded financial values
 * Requirements: 4.1, 4.2, 9.5, 15.2
 */

/**
 * Format a number as currency
 * @param {number} value - The numeric value
 * @param {string} currency - Currency symbol (default: '$')
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {string} Formatted currency string
 */
function formatCurrency(value, currency = '$', decimals = 2) {
  if (typeof value !== 'number' || isNaN(value)) {
    return `${currency}--`;
  }
  
  const absValue = Math.abs(value);
  const formatted = absValue.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
  
  const sign = value < 0 ? '-' : '';
  return `${sign}${currency}${formatted}`;
}

/**
 * Format a number as percentage
 * @param {number} value - The numeric value (e.g., 0.05 for 5%)
 * @param {number} decimals - Number of decimal places (default: 2)
 * @param {boolean} includeSign - Whether to include + for positive values
 * @returns {string} Formatted percentage string
 */
function formatPercentage(value, decimals = 2, includeSign = false) {
  if (typeof value !== 'number' || isNaN(value)) {
    return '--%';
  }
  
  const percentValue = value * 100;
  const sign = includeSign && percentValue > 0 ? '+' : '';
  return `${sign}${percentValue.toFixed(decimals)}%`;
}

/**
 * Determine the color class for a financial value
 * @param {number} value - The numeric value
 * @returns {string} CSS class name ('positive', 'negative', or 'neutral')
 */
function getValueColorClass(value) {
  if (typeof value !== 'number' || isNaN(value)) {
    return 'neutral';
  }
  
  if (value > 0) {
    return 'positive';
  } else if (value < 0) {
    return 'negative';
  }
  return 'neutral';
}

/**
 * Get the appropriate trend icon class
 * @param {number} value - The numeric value
 * @returns {string} Font Awesome icon class
 */
function getTrendIconClass(value) {
  if (typeof value !== 'number' || isNaN(value)) {
    return 'fa-minus';
  }
  
  if (value > 0) {
    return 'fa-arrow-up';
  } else if (value < 0) {
    return 'fa-arrow-down';
  }
  return 'fa-minus';
}

/**
 * Create a metric card element
 * @param {Object} config - Metric card configuration
 * @param {string} config.label - The metric label
 * @param {string|number} config.value - The metric value
 * @param {string} [config.icon] - Font Awesome icon class (e.g., 'fa-dollar-sign')
 * @param {string} [config.iconVariant] - Icon color variant ('success', 'danger', 'warning', 'info')
 * @param {number} [config.change] - Change value for trend indicator
 * @param {string} [config.changeLabel] - Label for change (e.g., 'vs yesterday')
 * @param {string} [config.variant] - Card variant ('compact', 'vertical', 'highlighted')
 * @returns {HTMLElement} The metric card element
 */
function createMetricCard(config) {
  const {
    label,
    value,
    icon,
    iconVariant,
    change,
    changeLabel,
    variant
  } = config;
  
  // Create card container
  const card = document.createElement('div');
  card.className = 'metric-card';
  
  if (variant) {
    card.classList.add(`metric-card--${variant}`);
  }
  
  // Create icon if provided
  if (icon) {
    const iconContainer = document.createElement('div');
    iconContainer.className = 'metric-icon metric-icon--light';
    
    if (iconVariant) {
      iconContainer.classList.add(`metric-icon--${iconVariant}`);
    }
    
    const iconElement = document.createElement('i');
    iconElement.className = `fas ${icon}`;
    iconContainer.appendChild(iconElement);
    card.appendChild(iconContainer);
  }
  
  // Create content container
  const content = document.createElement('div');
  content.className = 'metric-content';
  
  // Create label
  const labelElement = document.createElement('div');
  labelElement.className = 'metric-label';
  labelElement.textContent = label;
  content.appendChild(labelElement);
  
  // Create value
  const valueElement = document.createElement('div');
  valueElement.className = 'metric-value';
  valueElement.textContent = value;
  content.appendChild(valueElement);
  
  // Create change indicator if provided
  if (typeof change === 'number') {
    const changeElement = document.createElement('div');
    changeElement.className = `metric-change ${getValueColorClass(change)}`;
    
    const changeIcon = document.createElement('i');
    changeIcon.className = `fas ${getTrendIconClass(change)}`;
    changeElement.appendChild(changeIcon);
    
    const changeText = document.createTextNode(` ${formatPercentage(change / 100, 2, true)}`);
    changeElement.appendChild(changeText);
    
    if (changeLabel) {
      const changeLabelSpan = document.createElement('span');
      changeLabelSpan.className = 'text-tertiary-color';
      changeLabelSpan.textContent = ` ${changeLabel}`;
      changeElement.appendChild(changeLabelSpan);
    }
    
    content.appendChild(changeElement);
  }
  
  card.appendChild(content);
  
  return card;
}

/**
 * Render a financial value with color coding
 * @param {number} value - The numeric value
 * @param {Object} [options] - Rendering options
 * @param {string} [options.format] - Format type ('currency', 'percentage', 'number')
 * @param {string} [options.currency] - Currency symbol for currency format
 * @param {number} [options.decimals] - Number of decimal places
 * @param {boolean} [options.showSign] - Whether to show + for positive values
 * @param {boolean} [options.showIcon] - Whether to show trend icon
 * @returns {HTMLElement} The formatted value element
 */
function renderFinancialValue(value, options = {}) {
  const {
    format = 'number',
    currency = '$',
    decimals = 2,
    showSign = false,
    showIcon = false
  } = options;
  
  const container = document.createElement('span');
  container.className = `financial-value ${getValueColorClass(value)}`;
  
  // Add trend icon if requested
  if (showIcon && typeof value === 'number' && !isNaN(value) && value !== 0) {
    const icon = document.createElement('i');
    icon.className = `fas ${getTrendIconClass(value)}`;
    icon.style.marginRight = 'var(--spacing-1)'; // 4px
    icon.style.fontSize = '0.75em';
    container.appendChild(icon);
  }
  
  // Format the value
  let formattedValue;
  switch (format) {
    case 'currency':
      formattedValue = formatCurrency(value, currency, decimals);
      break;
    case 'percentage':
      formattedValue = formatPercentage(value, decimals, showSign);
      break;
    default:
      if (typeof value !== 'number' || isNaN(value)) {
        formattedValue = '--';
      } else {
        const sign = showSign && value > 0 ? '+' : '';
        formattedValue = `${sign}${value.toLocaleString('en-US', {
          minimumFractionDigits: decimals,
          maximumFractionDigits: decimals
        })}`;
      }
  }
  
  container.appendChild(document.createTextNode(formattedValue));
  
  return container;
}

/**
 * Apply color coding to all financial values in a container
 * @param {HTMLElement} container - The container element
 * @param {string} [selector] - CSS selector for value elements (default: '[data-financial-value]')
 */
function applyFinancialColorCoding(container, selector = '[data-financial-value]') {
  const elements = container.querySelectorAll(selector);
  
  elements.forEach(element => {
    const value = parseFloat(element.dataset.financialValue || element.textContent);
    
    if (!isNaN(value)) {
      // Remove existing color classes
      element.classList.remove('positive', 'negative', 'neutral');
      
      // Add appropriate color class
      element.classList.add(getValueColorClass(value));
    }
  });
}

/**
 * Create a trend indicator element
 * @param {number} value - The change value
 * @param {string} [label] - Optional label text
 * @returns {HTMLElement} The trend indicator element
 */
function createTrendIndicator(value, label) {
  const container = document.createElement('div');
  container.className = 'trend-indicator';
  
  // Create arrow
  const arrow = document.createElement('span');
  arrow.className = 'trend-arrow';
  
  if (value > 0) {
    arrow.classList.add('trend-up');
  } else if (value < 0) {
    arrow.classList.add('trend-down');
  } else {
    arrow.classList.add('trend-flat');
  }
  
  const arrowIcon = document.createElement('i');
  arrowIcon.className = `fas ${getTrendIconClass(value)}`;
  arrow.appendChild(arrowIcon);
  container.appendChild(arrow);
  
  // Create value text
  const valueText = document.createElement('span');
  valueText.className = `trend-value ${getValueColorClass(value)}`;
  valueText.textContent = label || formatPercentage(Math.abs(value) / 100, 2);
  container.appendChild(valueText);
  
  return container;
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    formatCurrency,
    formatPercentage,
    getValueColorClass,
    getTrendIconClass,
    createMetricCard,
    renderFinancialValue,
    applyFinancialColorCoding,
    createTrendIndicator
  };
}

// Make functions available globally for browser use
if (typeof window !== 'undefined') {
  window.MetricDisplay = {
    formatCurrency,
    formatPercentage,
    getValueColorClass,
    getTrendIconClass,
    createMetricCard,
    renderFinancialValue,
    applyFinancialColorCoding,
    createTrendIndicator
  };
}
