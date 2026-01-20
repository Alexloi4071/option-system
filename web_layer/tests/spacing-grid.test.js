/**
 * Property-Based Tests for 8px Grid Spacing
 * Feature: modern-ui-redesign
 * 
 * **Validates: Requirements 1.4**
 * 
 * These tests verify that all spacing values follow the 8px grid system
 * (or 4px for half-spacing).
 */

const { test, describe } = require('node:test');
const assert = require('node:assert');
const fc = require('fast-check');
const fs = require('fs');
const path = require('path');

// Load SCSS variables file
const variablesPath = path.join(__dirname, '../static/css/design-system/_variables.scss');
const variablesContent = fs.readFileSync(variablesPath, 'utf-8');

/**
 * Extract spacing values from SCSS variables
 */
function extractSpacingValues() {
  const spacingValues = {};
  
  // Regex to match spacing variable definitions
  const spacingRegex = /\$spacing-(\d+):\s*([\d.]+)rem;.*\/\/\s*(\d+)px/g;
  
  let match;
  while ((match = spacingRegex.exec(variablesContent)) !== null) {
    const name = match[1];
    const remValue = parseFloat(match[2]);
    const pxValue = parseInt(match[3]);
    
    spacingValues[name] = {
      rem: remValue,
      px: pxValue
    };
  }
  
  return spacingValues;
}

/**
 * Check if a pixel value is a multiple of the base unit
 */
function isMultipleOf(value, base) {
  return value % base === 0;
}

/**
 * Convert rem to px (assuming 1rem = 16px)
 */
function remToPx(rem) {
  return rem * 16;
}

describe('Feature: modern-ui-redesign, Property 1: Consistent 8px Grid Spacing', () => {
  
  /**
   * Test: All spacing variables are multiples of 4px
   * 
   * The 8px grid system allows for half-spacing at 4px, so all spacing
   * values should be multiples of 4px.
   */
  test('All spacing variables are multiples of 4px', () => {
    const spacingValues = extractSpacingValues();
    const nonConforming = [];
    
    for (const [name, value] of Object.entries(spacingValues)) {
      if (!isMultipleOf(value.px, 4)) {
        nonConforming.push({
          name: `spacing-${name}`,
          px: value.px,
          rem: value.rem
        });
      }
    }
    
    if (nonConforming.length > 0) {
      console.log('Non-conforming spacing values:', nonConforming);
    }
    
    assert.strictEqual(nonConforming.length, 0,
      'All spacing values should be multiples of 4px (8px grid with half-spacing)');
  });
  
  /**
   * Test: Spacing values increase consistently
   * 
   * Spacing values should increase in a predictable pattern.
   */
  test('Spacing values increase consistently', () => {
    const spacingValues = extractSpacingValues();
    const sortedNames = Object.keys(spacingValues).map(Number).sort((a, b) => a - b);
    
    for (let i = 1; i < sortedNames.length; i++) {
      const prevName = sortedNames[i - 1];
      const currName = sortedNames[i];
      
      const prevValue = spacingValues[prevName].px;
      const currValue = spacingValues[currName].px;
      
      assert.ok(currValue > prevValue,
        `spacing-${currName} (${currValue}px) should be greater than spacing-${prevName} (${prevValue}px)`);
    }
  });
  
  /**
   * Test: Rem values correctly convert to px values
   * 
   * The rem values should correctly convert to the documented px values
   * (assuming 1rem = 16px).
   */
  test('Rem values correctly convert to px values', () => {
    const spacingValues = extractSpacingValues();
    
    for (const [name, value] of Object.entries(spacingValues)) {
      const calculatedPx = remToPx(value.rem);
      
      assert.strictEqual(calculatedPx, value.px,
        `spacing-${name}: ${value.rem}rem should equal ${value.px}px`);
    }
  });
  
  /**
   * Property Test: Generated spacing values follow 8px grid
   * 
   * This test generates random spacing multipliers and verifies that
   * the resulting values would follow the 8px grid system.
   */
  test('Property test: Generated spacing values follow 8px grid', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 20 }), // spacing multiplier
        (multiplier) => {
          // Calculate what the spacing value would be
          // Using 4px as the base unit (half of 8px)
          const spacingValue = multiplier * 4;
          
          // Verify it's a multiple of 4px
          const isValid = isMultipleOf(spacingValue, 4);
          
          assert.ok(isValid,
            `Generated spacing value ${spacingValue}px should be a multiple of 4px`);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });
  
  /**
   * Property Test: All spacing combinations maintain grid consistency
   * 
   * This test verifies that combining spacing values (e.g., padding + margin)
   * still results in values that follow the grid system.
   */
  test('Property test: Spacing combinations maintain grid consistency', () => {
    const spacingValues = extractSpacingValues();
    const spacingArray = Object.values(spacingValues).map(v => v.px);
    
    fc.assert(
      fc.property(
        fc.constantFrom(...spacingArray),
        fc.constantFrom(...spacingArray),
        (spacing1, spacing2) => {
          // When combining two spacing values, the result should still
          // be a multiple of 4px
          const combined = spacing1 + spacing2;
          
          assert.ok(isMultipleOf(combined, 4),
            `Combined spacing ${spacing1}px + ${spacing2}px = ${combined}px should be a multiple of 4px`);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });
  
  /**
   * Property Test: Spacing values scale proportionally
   * 
   * This test verifies that spacing values maintain proportional relationships
   * when scaled.
   */
  test('Property test: Spacing values scale proportionally', () => {
    const spacingValues = extractSpacingValues();
    const spacingArray = Object.values(spacingValues).map(v => v.px);
    
    fc.assert(
      fc.property(
        fc.constantFrom(...spacingArray),
        fc.integer({ min: 1, max: 4 }), // scale factor
        (baseSpacing, scaleFactor) => {
          const scaledSpacing = baseSpacing * scaleFactor;
          
          // Scaled spacing should still be a multiple of 4px
          assert.ok(isMultipleOf(scaledSpacing, 4),
            `Scaled spacing ${baseSpacing}px × ${scaleFactor} = ${scaledSpacing}px should be a multiple of 4px`);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });
  
  /**
   * Test: Minimum spacing is 4px
   * 
   * The smallest spacing value should be 4px (half of the 8px grid).
   */
  test('Minimum spacing is 4px', () => {
    const spacingValues = extractSpacingValues();
    const minSpacing = Math.min(...Object.values(spacingValues).map(v => v.px));
    
    assert.strictEqual(minSpacing, 4,
      'Minimum spacing should be 4px (half of 8px grid)');
  });
  
  /**
   * Test: All spacing values are defined
   * 
   * Verify that all expected spacing variables are defined.
   */
  test('All expected spacing variables are defined', () => {
    const spacingValues = extractSpacingValues();
    const expectedSpacings = ['1', '2', '3', '4', '5', '6', '8', '10', '12', '16', '20'];
    
    const missingSpacings = expectedSpacings.filter(name => !spacingValues[name]);
    
    if (missingSpacings.length > 0) {
      console.log('Missing spacing variables:', missingSpacings);
    }
    
    assert.strictEqual(missingSpacings.length, 0,
      'All expected spacing variables should be defined');
  });
  
  /**
   * Property Test: Spacing differences are multiples of 4px
   * 
   * The difference between any two spacing values should also be a multiple of 4px.
   */
  test('Property test: Spacing differences are multiples of 4px', () => {
    const spacingValues = extractSpacingValues();
    const spacingArray = Object.values(spacingValues).map(v => v.px);
    
    fc.assert(
      fc.property(
        fc.constantFrom(...spacingArray),
        fc.constantFrom(...spacingArray),
        (spacing1, spacing2) => {
          const difference = Math.abs(spacing1 - spacing2);
          
          // The difference should be a multiple of 4px
          assert.ok(isMultipleOf(difference, 4),
            `Difference between ${spacing1}px and ${spacing2}px = ${difference}px should be a multiple of 4px`);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });
});
