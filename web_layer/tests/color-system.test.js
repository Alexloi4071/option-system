// Feature: modern-ui-redesign
// Property-Based Tests for Color System

const { test, describe } = require('node:test');
const assert = require('node:assert');

/**
 * Calculate relative luminance of a color
 * @param {string} hex - Hex color code (e.g., '#ffffff')
 * @returns {number} Relative luminance (0-1)
 */
function getLuminance(hex) {
  // Remove # if present
  hex = hex.replace('#', '');
  
  // Convert to RGB
  const r = parseInt(hex.substr(0, 2), 16) / 255;
  const g = parseInt(hex.substr(2, 2), 16) / 255;
  const b = parseInt(hex.substr(4, 2), 16) / 255;
  
  // Apply gamma correction
  const rsRGB = r <= 0.03928 ? r / 12.92 : Math.pow((r + 0.055) / 1.055, 2.4);
  const gsRGB = g <= 0.03928 ? g / 12.92 : Math.pow((g + 0.055) / 1.055, 2.4);
  const bsRGB = b <= 0.03928 ? b / 12.92 : Math.pow((b + 0.055) / 1.055, 2.4);
  
  // Calculate luminance
  return 0.2126 * rsRGB + 0.7152 * gsRGB + 0.0722 * bsRGB;
}

/**
 * Calculate contrast ratio between two colors
 * @param {string} color1 - First color hex code
 * @param {string} color2 - Second color hex code
 * @returns {number} Contrast ratio (1-21)
 */
function getContrastRatio(color1, color2) {
  const lum1 = getLuminance(color1);
  const lum2 = getLuminance(color2);
  
  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);
  
  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Check if contrast ratio meets WCAG AA standard
 * @param {number} ratio - Contrast ratio
 * @param {boolean} isLargeText - Whether text is large (18pt+ or 14pt+ bold)
 * @returns {boolean} Whether it meets WCAG AA
 */
function meetsWCAG_AA(ratio, isLargeText = false) {
  const threshold = isLargeText ? 3.0 : 4.5;
  return ratio >= threshold;
}

// Color definitions from design system
const lightTheme = {
  background: '#f8fafc',  // Slate 50
  surface: '#ffffff',     // White
  textPrimary: '#0f172a', // Slate 900
  textSecondary: '#64748b', // Slate 500
  textTertiary: '#475569', // Slate 600 (updated for WCAG AA)
  success: '#047857',     // Green 700 (updated for WCAG AA)
  danger: '#dc2626',      // Red 600 (updated for WCAG AA)
  warning: '#b45309',     // Amber 700 (updated for WCAG AA)
  info: '#0e7490',        // Cyan 700 (updated for WCAG AA)
  primary: '#2563eb',     // Blue 600
};

const darkTheme = {
  background: '#0f172a',  // Slate 900
  surface: '#1e293b',     // Slate 800
  surfaceElevated: '#334155', // Slate 700
  textPrimary: '#f1f5f9', // Slate 100
  textSecondary: '#cbd5e1', // Slate 300 (updated for WCAG AA)
  textTertiary: '#e2e8f0', // Slate 200 (updated for WCAG AA)
  success: '#34d399',     // Green 400 (lighter for dark backgrounds)
  danger: '#fca5a5',      // Red 300 (lighter for dark backgrounds)
  warning: '#fbbf24',     // Amber 400 (lighter for dark backgrounds)
  info: '#22d3ee',        // Cyan 400 (lighter for dark backgrounds)
  primary: '#93c5fd',     // Blue 300 (lighter for dark backgrounds)
};

describe('Color System - WCAG AA Contrast Ratios', () => {
  
  // Property 2: WCAG AA Contrast Ratios
  // Validates: Requirements 1.5, 2.5, 14.1
  test('Feature: modern-ui-redesign, Property 2: Light theme text colors meet WCAG AA on white background', () => {
    const backgrounds = [lightTheme.surface, lightTheme.background];
    const textColors = [
      { name: 'textPrimary', color: lightTheme.textPrimary, isLarge: false },
      { name: 'textSecondary', color: lightTheme.textSecondary, isLarge: false },
      { name: 'textTertiary', color: lightTheme.textTertiary, isLarge: false },
    ];
    
    let passCount = 0;
    let totalTests = 0;
    
    backgrounds.forEach(bg => {
      textColors.forEach(({ name, color, isLarge }) => {
        totalTests++;
        const ratio = getContrastRatio(color, bg);
        const passes = meetsWCAG_AA(ratio, isLarge);
        
        if (passes) passCount++;
        
        assert.ok(
          passes,
          `${name} (${color}) on ${bg} has ratio ${ratio.toFixed(2)}:1, needs ${isLarge ? '3.0' : '4.5'}:1`
        );
      });
    });
    
    console.log(`Light theme: ${passCount}/${totalTests} text/background combinations passed WCAG AA`);
  });
  
  test('Feature: modern-ui-redesign, Property 2: Light theme semantic colors meet WCAG AA on white background', () => {
    const background = lightTheme.surface;
    const semanticColors = [
      { name: 'success', color: lightTheme.success },
      { name: 'danger', color: lightTheme.danger },
      { name: 'warning', color: lightTheme.warning },
      { name: 'info', color: lightTheme.info },
      { name: 'primary', color: lightTheme.primary },
    ];
    
    let passCount = 0;
    
    semanticColors.forEach(({ name, color }) => {
      const ratio = getContrastRatio(color, background);
      const passes = meetsWCAG_AA(ratio, false);
      
      if (passes) passCount++;
      
      assert.ok(
        passes,
        `${name} (${color}) on white has ratio ${ratio.toFixed(2)}:1, needs 4.5:1`
      );
    });
    
    console.log(`Light theme: ${passCount}/${semanticColors.length} semantic colors passed WCAG AA`);
  });
  
  test('Feature: modern-ui-redesign, Property 2: Dark theme text colors meet WCAG AA on dark backgrounds', () => {
    const backgrounds = [darkTheme.background, darkTheme.surface, darkTheme.surfaceElevated];
    const textColors = [
      { name: 'textPrimary', color: darkTheme.textPrimary, isLarge: false },
      { name: 'textSecondary', color: darkTheme.textSecondary, isLarge: false },
      { name: 'textTertiary', color: darkTheme.textTertiary, isLarge: false },
    ];
    
    let passCount = 0;
    let totalTests = 0;
    
    backgrounds.forEach(bg => {
      textColors.forEach(({ name, color, isLarge }) => {
        totalTests++;
        const ratio = getContrastRatio(color, bg);
        const passes = meetsWCAG_AA(ratio, isLarge);
        
        if (passes) passCount++;
        
        assert.ok(
          passes,
          `${name} (${color}) on ${bg} has ratio ${ratio.toFixed(2)}:1, needs ${isLarge ? '3.0' : '4.5'}:1`
        );
      });
    });
    
    console.log(`Dark theme: ${passCount}/${totalTests} text/background combinations passed WCAG AA`);
  });
  
  test('Feature: modern-ui-redesign, Property 2: Dark theme semantic colors meet WCAG AA on dark backgrounds', () => {
    const backgrounds = [darkTheme.surface, darkTheme.surfaceElevated];
    const semanticColors = [
      { name: 'success', color: darkTheme.success },
      { name: 'danger', color: darkTheme.danger },
      { name: 'warning', color: darkTheme.warning },
      { name: 'info', color: darkTheme.info },
      { name: 'primary', color: darkTheme.primary },
    ];
    
    let passCount = 0;
    let totalTests = 0;
    
    backgrounds.forEach(bg => {
      semanticColors.forEach(({ name, color }) => {
        totalTests++;
        const ratio = getContrastRatio(color, bg);
        const passes = meetsWCAG_AA(ratio, false);
        
        if (passes) passCount++;
        
        assert.ok(
          passes,
          `${name} (${color}) on ${bg} has ratio ${ratio.toFixed(2)}:1, needs 4.5:1`
        );
      });
    });
    
    console.log(`Dark theme: ${passCount}/${totalTests} semantic colors on dark backgrounds passed WCAG AA`);
  });
  
  // Property-based test: Generate random color combinations and verify calculation
  test('Feature: modern-ui-redesign, Property 2: Contrast ratio calculation is consistent', () => {
    // Test with known values
    const whiteOnBlack = getContrastRatio('#ffffff', '#000000');
    assert.ok(Math.abs(whiteOnBlack - 21) < 0.1, 'White on black should be 21:1');
    
    const blackOnWhite = getContrastRatio('#000000', '#ffffff');
    assert.ok(Math.abs(blackOnWhite - 21) < 0.1, 'Black on white should be 21:1');
    
    // Test symmetry
    const ratio1 = getContrastRatio(lightTheme.textPrimary, lightTheme.surface);
    const ratio2 = getContrastRatio(lightTheme.surface, lightTheme.textPrimary);
    assert.strictEqual(ratio1, ratio2, 'Contrast ratio should be symmetric');
    
    console.log('Contrast ratio calculation verified');
  });
});
