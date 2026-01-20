// Feature: modern-ui-redesign
// Property-Based Tests for Icon System

const { test, describe } = require('node:test');
const assert = require('node:assert');
const fc = require('fast-check');

// Import the icon system module
const {
  ICON_LIBRARY,
  ICON_LIBRARY_PREFIX,
  VALID_ICON_PREFIXES,
  STATUS_ICONS,
  DIRECTIONAL_ICONS,
  ICON_SIZES,
  getStatusIcon,
  getDirectionalIcon,
  getModuleIcon,
  getActionIcon,
  getIconSize,
  isValidIconLibrary,
  isMixedLibraryIcon,
  createIcon,
  extractIconName,
  findFontAwesomeEquivalent
} = require('../static/js/icon-system.js');

// Mock DOM environment
const { JSDOM } = require('jsdom');
const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
global.document = dom.window.document;

describe('Icon System - Library Consistency Properties', () => {
  
  /**
   * Property 23: Consistent Icon Library Usage
   * *For any* icon used in the UI, it should use classes from a single icon 
   * library (Font Awesome), not mixed libraries.
   * 
   * **Validates: Requirements 12.1**
   */
  test('Feature: modern-ui-redesign, Property 23: All status icons use Font Awesome prefix', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...Object.keys(STATUS_ICONS)),
        (status) => {
          const iconClass = getStatusIcon(status);
          // All status icons should start with 'fa-'
          return iconClass.startsWith('fa-');
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 23: All directional icons use Font Awesome prefix', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...Object.keys(DIRECTIONAL_ICONS)),
        (direction) => {
          const iconClass = getDirectionalIcon(direction);
          // All directional icons should start with 'fa-'
          return iconClass.startsWith('fa-');
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 23: Created icons use valid Font Awesome classes', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('check', 'times', 'arrow-up', 'arrow-down', 'spinner', 'cog'),
        (iconName) => {
          const icon = createIcon(iconName);
          const className = icon.className;
          
          // Should contain the default prefix
          return className.includes(ICON_LIBRARY_PREFIX) && 
                 className.includes(`fa-${iconName}`);
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 23: Valid icon library detection works correctly', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(
          'fas fa-check',
          'far fa-circle',
          'fab fa-github',
          'fas fa-arrow-up',
          'far fa-star'
        ),
        (iconClass) => {
          return isValidIconLibrary(iconClass) === true;
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 23: Mixed library icons are detected', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(
          'material-icons',
          'mdi mdi-check',
          'bi bi-check',
          'glyphicon glyphicon-ok',
          'ion-checkmark'
        ),
        (iconClass) => {
          return isMixedLibraryIcon(iconClass) === true;
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 23: Icon library constant is Font Awesome', () => {
    assert.strictEqual(ICON_LIBRARY, 'fa', 'Icon library should be Font Awesome');
    assert.strictEqual(ICON_LIBRARY_PREFIX, 'fas', 'Default prefix should be fas (solid)');
  });
  
  test('Feature: modern-ui-redesign, Property 23: All valid prefixes are Font Awesome variants', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...VALID_ICON_PREFIXES),
        (prefix) => {
          // All valid prefixes should start with 'fa'
          return prefix.startsWith('fa');
        }
      ),
      { numRuns: 100 }
    );
  });
});

describe('Icon System - Status Icon Properties', () => {
  
  /**
   * Property 24: Status Icon Mapping
   * *For any* status indicator (success, warning, error), the appropriate 
   * icon class should be used.
   * 
   * **Validates: Requirements 12.3**
   */
  test('Feature: modern-ui-redesign, Property 24: Success status returns check-circle icon', () => {
    const icon = getStatusIcon('success');
    assert.strictEqual(icon, 'fa-check-circle', 'Success should use check-circle');
  });
  
  test('Feature: modern-ui-redesign, Property 24: Warning status returns exclamation-triangle icon', () => {
    const icon = getStatusIcon('warning');
    assert.strictEqual(icon, 'fa-exclamation-triangle', 'Warning should use exclamation-triangle');
  });
  
  test('Feature: modern-ui-redesign, Property 24: Error status returns times-circle icon', () => {
    const icon = getStatusIcon('error');
    assert.strictEqual(icon, 'fa-times-circle', 'Error should use times-circle');
  });
  
  test('Feature: modern-ui-redesign, Property 24: Info status returns info-circle icon', () => {
    const icon = getStatusIcon('info');
    assert.strictEqual(icon, 'fa-info-circle', 'Info should use info-circle');
  });
  
  test('Feature: modern-ui-redesign, Property 24: Loading status returns spinner icon', () => {
    const icon = getStatusIcon('loading');
    assert.strictEqual(icon, 'fa-spinner', 'Loading should use spinner');
  });
  
  test('Feature: modern-ui-redesign, Property 24: Unknown status defaults to info icon', () => {
    fc.assert(
      fc.property(
        fc.string().filter(s => !Object.keys(STATUS_ICONS).includes(s.toLowerCase().trim())),
        (unknownStatus) => {
          const icon = getStatusIcon(unknownStatus);
          return icon === STATUS_ICONS.info;
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 24: Status icon lookup is case-insensitive', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('SUCCESS', 'Success', 'success', 'WARNING', 'Warning', 'warning'),
        (status) => {
          const icon = getStatusIcon(status);
          const normalizedStatus = status.toLowerCase().trim();
          return icon === STATUS_ICONS[normalizedStatus];
        }
      ),
      { numRuns: 100 }
    );
  });
});

describe('Icon System - Directional Icon Properties', () => {
  
  /**
   * Property 25: Directional Icons for Price Changes
   * *For any* price change display, an upward arrow icon should be used for 
   * positive changes and a downward arrow for negative changes.
   * 
   * **Validates: Requirements 12.4**
   */
  test('Feature: modern-ui-redesign, Property 25: Positive numbers return up arrow', () => {
    fc.assert(
      fc.property(
        fc.float({ min: Math.fround(0.0001), max: Math.fround(100000), noNaN: true }),
        (value) => {
          const icon = getDirectionalIcon(value);
          return icon === 'fa-arrow-up';
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 25: Negative numbers return down arrow', () => {
    fc.assert(
      fc.property(
        fc.float({ min: Math.fround(-100000), max: Math.fround(-0.0001), noNaN: true }),
        (value) => {
          const icon = getDirectionalIcon(value);
          return icon === 'fa-arrow-down';
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 25: Zero returns flat/minus icon', () => {
    const icon = getDirectionalIcon(0);
    assert.strictEqual(icon, 'fa-minus', 'Zero should return minus icon');
  });
  
  test('Feature: modern-ui-redesign, Property 25: NaN returns flat/minus icon', () => {
    const icon = getDirectionalIcon(NaN);
    assert.strictEqual(icon, 'fa-minus', 'NaN should return minus icon');
  });
  
  test('Feature: modern-ui-redesign, Property 25: String "up" returns up arrow', () => {
    const icon = getDirectionalIcon('up');
    assert.strictEqual(icon, 'fa-arrow-up', '"up" should return up arrow');
  });
  
  test('Feature: modern-ui-redesign, Property 25: String "down" returns down arrow', () => {
    const icon = getDirectionalIcon('down');
    assert.strictEqual(icon, 'fa-arrow-down', '"down" should return down arrow');
  });
  
  test('Feature: modern-ui-redesign, Property 25: Bullish returns trend-up icon', () => {
    const icon = getDirectionalIcon('bullish');
    assert.strictEqual(icon, 'fa-arrow-trend-up', '"bullish" should return trend-up');
  });
  
  test('Feature: modern-ui-redesign, Property 25: Bearish returns trend-down icon', () => {
    const icon = getDirectionalIcon('bearish');
    assert.strictEqual(icon, 'fa-arrow-trend-down', '"bearish" should return trend-down');
  });
  
  test('Feature: modern-ui-redesign, Property 25: Direction lookup is case-insensitive', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('UP', 'Up', 'up', 'DOWN', 'Down', 'down'),
        (direction) => {
          const icon = getDirectionalIcon(direction);
          const normalizedDirection = direction.toLowerCase().trim();
          return icon === DIRECTIONAL_ICONS[normalizedDirection];
        }
      ),
      { numRuns: 100 }
    );
  });
});

describe('Icon System - Icon Sizing Properties', () => {
  
  /**
   * Property 26: Consistent Icon Sizing
   * *For any* icon displayed alongside text, the icon size and vertical-align 
   * properties should be consistent across the UI.
   * 
   * **Validates: Requirements 12.5**
   */
  test('Feature: modern-ui-redesign, Property 26: All size keys return valid CSS values', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...Object.keys(ICON_SIZES)),
        (sizeKey) => {
          const size = getIconSize(sizeKey);
          // Should be a valid CSS rem value
          return size.endsWith('rem');
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 26: Icon sizes follow consistent scale', () => {
    const sizes = Object.values(ICON_SIZES).map(s => parseFloat(s));
    
    // Sizes should be in ascending order
    for (let i = 1; i < sizes.length; i++) {
      assert.ok(sizes[i] >= sizes[i-1], 'Icon sizes should be in ascending order');
    }
  });
  
  test('Feature: modern-ui-redesign, Property 26: Unknown size returns base size', () => {
    // Test with specific unknown size names that are definitely not in ICON_SIZES
    const unknownSizes = ['huge', 'tiny', 'massive', 'micro', 'giant'];
    unknownSizes.forEach(unknownSize => {
      const size = getIconSize(unknownSize);
      assert.strictEqual(size, ICON_SIZES.base, `Unknown size '${unknownSize}' should return base size`);
    });
  });
  
  test('Feature: modern-ui-redesign, Property 26: Created icons have consistent structure', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('check', 'times', 'arrow-up'),
        fc.constantFrom('xs', 'sm', 'base', 'lg', 'xl'),
        (iconName, size) => {
          const icon = createIcon(iconName, { size });
          
          // Icon should be an <i> element
          if (icon.tagName !== 'I') return false;
          
          // Icon should have the size applied
          if (size && ICON_SIZES[size]) {
            return icon.style.fontSize === ICON_SIZES[size];
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 26: Icons have aria-hidden by default', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('check', 'times', 'arrow-up', 'spinner'),
        (iconName) => {
          const icon = createIcon(iconName);
          return icon.getAttribute('aria-hidden') === 'true';
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 26: Icons with ariaLabel have role="img"', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('check', 'times', 'arrow-up'),
        fc.string({ minLength: 1, maxLength: 50 }),
        (iconName, label) => {
          const icon = createIcon(iconName, { ariaLabel: label });
          return icon.getAttribute('role') === 'img' && 
                 icon.getAttribute('aria-label') === label;
        }
      ),
      { numRuns: 100 }
    );
  });
});

describe('Icon System - Utility Function Properties', () => {
  
  test('Feature: modern-ui-redesign, Property 23: extractIconName handles various formats', () => {
    const testCases = [
      { input: 'fa-check', expected: 'check' },
      { input: 'fas fa-check', expected: 'check' },
      { input: 'icon-check', expected: 'check' },
      { input: 'mdi-check', expected: 'check' }
    ];
    
    testCases.forEach(({ input, expected }) => {
      const result = extractIconName(input);
      assert.strictEqual(result, expected, `extractIconName('${input}') should return '${expected}'`);
    });
  });
  
  test('Feature: modern-ui-redesign, Property 23: findFontAwesomeEquivalent maps common icons', () => {
    const mappings = [
      { input: 'check', expected: 'fa-check' },
      { input: 'close', expected: 'fa-times' },
      { input: 'x', expected: 'fa-times' },
      { input: 'menu', expected: 'fa-bars' },
      { input: 'search', expected: 'fa-search' }
    ];
    
    mappings.forEach(({ input, expected }) => {
      const result = findFontAwesomeEquivalent(input);
      assert.strictEqual(result, expected, `findFontAwesomeEquivalent('${input}') should return '${expected}'`);
    });
  });
  
  test('Feature: modern-ui-redesign, Property 23: Unknown icons return null from findFontAwesomeEquivalent', () => {
    // Test with specific unknown icon names that are definitely not in the mapping
    const unknownIcons = ['xyz123abc', 'randomicon999', 'notanicon456'];
    unknownIcons.forEach(unknownIcon => {
      const result = findFontAwesomeEquivalent(unknownIcon);
      assert.strictEqual(result, null, `Unknown icon '${unknownIcon}' should return null`);
    });
  });
});

describe('Icon System - Module and Action Icon Properties', () => {
  
  test('Feature: modern-ui-redesign, Property 23: Module icons all use Font Awesome', () => {
    const moduleKeys = [
      'support-resistance', 'fair-value', 'arbitrage', 'pe-valuation',
      'greeks', 'iv', 'hv', 'health', 'momentum', 'optimal-strike'
    ];
    
    fc.assert(
      fc.property(
        fc.constantFrom(...moduleKeys),
        (moduleKey) => {
          const icon = getModuleIcon(moduleKey);
          return icon.startsWith('fa-');
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 23: Action icons all use Font Awesome', () => {
    const actionKeys = [
      'analyze', 'refresh', 'settings', 'search', 'filter',
      'save', 'export', 'copy', 'edit', 'delete', 'add'
    ];
    
    fc.assert(
      fc.property(
        fc.constantFrom(...actionKeys),
        (actionKey) => {
          const icon = getActionIcon(actionKey);
          return icon.startsWith('fa-');
        }
      ),
      { numRuns: 100 }
    );
  });
  
  test('Feature: modern-ui-redesign, Property 23: Unknown module returns default cube icon', () => {
    // Test with specific unknown module names
    const unknownModules = ['xyz123module', 'randommod999', 'notamodule456'];
    unknownModules.forEach(unknownModule => {
      const icon = getModuleIcon(unknownModule);
      assert.strictEqual(icon, 'fa-cube', `Unknown module '${unknownModule}' should return fa-cube`);
    });
  });
  
  test('Feature: modern-ui-redesign, Property 23: Unknown action returns default circle icon', () => {
    // Test with specific unknown action names
    const unknownActions = ['xyz123action', 'randomact999', 'notanaction456'];
    unknownActions.forEach(unknownAction => {
      const icon = getActionIcon(unknownAction);
      assert.strictEqual(icon, 'fa-circle', `Unknown action '${unknownAction}' should return fa-circle`);
    });
  });
});
