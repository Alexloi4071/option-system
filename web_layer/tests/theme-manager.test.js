// Feature: modern-ui-redesign
// Property-Based Tests for Theme Manager

const { test, describe, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const { JSDOM } = require('jsdom');

// Mock localStorage for testing
class LocalStorageMock {
  constructor() {
    this.store = {};
  }

  getItem(key) {
    return this.store[key] || null;
  }

  setItem(key, value) {
    this.store[key] = String(value);
  }

  removeItem(key) {
    delete this.store[key];
  }

  clear() {
    this.store = {};
  }
}

// Setup DOM environment for each test
function setupDOM() {
  const dom = new JSDOM(`
    <!DOCTYPE html>
    <html>
      <head></head>
      <body>
        <button id="themeToggle">
          <i class="fas fa-moon"></i>
        </button>
      </body>
    </html>
  `, {
    url: 'http://localhost',
    pretendToBeVisual: true,
  });

  global.window = dom.window;
  global.document = dom.window.document;
  global.localStorage = new LocalStorageMock();
  global.CustomEvent = dom.window.CustomEvent;
  
  // Mock matchMedia
  global.window.matchMedia = (query) => ({
    matches: query === '(prefers-color-scheme: dark)',
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
  });

  return dom;
}

// Load ThemeManager class
function loadThemeManager() {
  // Clear require cache
  delete require.cache[require.resolve('../static/js/theme-manager.js')];
  
  // Load the module
  const ThemeManager = require('../static/js/theme-manager.js');
  return ThemeManager;
}

describe('Theme Manager - Theme Persistence', () => {
  let dom;
  let ThemeManager;
  
  beforeEach(() => {
    dom = setupDOM();
    ThemeManager = loadThemeManager();
  });
  
  afterEach(() => {
    if (global.localStorage) {
      global.localStorage.clear();
    }
    // Clean up global objects
    delete global.window;
    delete global.document;
    delete global.localStorage;
    delete global.CustomEvent;
  });
  
  // Property 3: Theme Persistence Round-Trip
  // Validates: Requirements 2.3, 2.4
  test('Feature: modern-ui-redesign, Property 3: Light theme persists across page reloads', () => {
    // Create first instance and set light theme
    const manager1 = new ThemeManager();
    manager1.setTheme('light', true);
    
    // Verify it was saved
    const saved = global.localStorage.getItem('user-theme-preference');
    assert.strictEqual(saved, 'light', 'Light theme should be saved to localStorage');
    
    // Verify document attribute
    assert.strictEqual(
      global.document.documentElement.getAttribute('data-theme'),
      'light',
      'Document should have light theme attribute'
    );
    
    // Simulate page reload by creating new instance
    const manager2 = new ThemeManager();
    
    // Verify theme was restored
    assert.strictEqual(
      manager2.getCurrentTheme(),
      'light',
      'Light theme should be restored after reload'
    );
    
    assert.strictEqual(
      global.document.documentElement.getAttribute('data-theme'),
      'light',
      'Document should still have light theme attribute after reload'
    );
    
    console.log('✓ Light theme persistence verified');
  });
  
  test('Feature: modern-ui-redesign, Property 3: Dark theme persists across page reloads', () => {
    // Create first instance and set dark theme
    const manager1 = new ThemeManager();
    manager1.setTheme('dark', true);
    
    // Verify it was saved
    const saved = global.localStorage.getItem('user-theme-preference');
    assert.strictEqual(saved, 'dark', 'Dark theme should be saved to localStorage');
    
    // Verify document attribute
    assert.strictEqual(
      global.document.documentElement.getAttribute('data-theme'),
      'dark',
      'Document should have dark theme attribute'
    );
    
    // Simulate page reload by creating new instance
    const manager2 = new ThemeManager();
    
    // Verify theme was restored
    assert.strictEqual(
      manager2.getCurrentTheme(),
      'dark',
      'Dark theme should be restored after reload'
    );
    
    assert.strictEqual(
      global.document.documentElement.getAttribute('data-theme'),
      'dark',
      'Document should still have dark theme attribute after reload'
    );
    
    console.log('✓ Dark theme persistence verified');
  });
  
  test('Feature: modern-ui-redesign, Property 3: Theme toggle persists correctly', () => {
    const manager = new ThemeManager();
    
    // Start with light theme
    manager.setTheme('light', true);
    assert.strictEqual(manager.getCurrentTheme(), 'light');
    
    // Toggle to dark
    manager.toggleTheme();
    assert.strictEqual(manager.getCurrentTheme(), 'dark');
    assert.strictEqual(global.localStorage.getItem('user-theme-preference'), 'dark');
    
    // Simulate reload
    const manager2 = new ThemeManager();
    assert.strictEqual(manager2.getCurrentTheme(), 'dark', 'Dark theme should persist after toggle');
    
    // Toggle back to light
    manager2.toggleTheme();
    assert.strictEqual(manager2.getCurrentTheme(), 'light');
    assert.strictEqual(global.localStorage.getItem('user-theme-preference'), 'light');
    
    // Simulate another reload
    const manager3 = new ThemeManager();
    assert.strictEqual(manager3.getCurrentTheme(), 'light', 'Light theme should persist after second toggle');
    
    console.log('✓ Theme toggle persistence verified');
  });
  
  test('Feature: modern-ui-redesign, Property 3: System preference is used when no saved preference exists', () => {
    // Ensure no saved preference
    global.localStorage.clear();
    
    // Mock system preference for dark mode
    global.window.matchMedia = (query) => ({
      matches: query === '(prefers-color-scheme: dark)',
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
    });
    
    // Create manager - should detect system preference
    const manager = new ThemeManager();
    
    // Should use system preference (dark)
    assert.strictEqual(
      manager.getCurrentTheme(),
      'dark',
      'Should use system preference when no saved preference exists'
    );
    
    console.log('✓ System preference detection verified');
  });
  
  test('Feature: modern-ui-redesign, Property 3: Saved preference overrides system preference', () => {
    // Save light theme preference
    global.localStorage.setItem('user-theme-preference', 'light');
    
    // Mock system preference for dark mode
    global.window.matchMedia = (query) => ({
      matches: query === '(prefers-color-scheme: dark)',
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
    });
    
    // Create manager
    const manager = new ThemeManager();
    
    // Should use saved preference (light) not system preference (dark)
    assert.strictEqual(
      manager.getCurrentTheme(),
      'light',
      'Saved preference should override system preference'
    );
    
    console.log('✓ Saved preference priority verified');
  });
  
  test('Feature: modern-ui-redesign, Property 3: Invalid theme falls back to light', () => {
    const manager = new ThemeManager();
    
    // Try to set invalid theme
    manager.setTheme('invalid-theme', true);
    
    // Should fall back to light
    assert.strictEqual(
      manager.getCurrentTheme(),
      'light',
      'Invalid theme should fall back to light'
    );
    
    assert.strictEqual(
      global.document.documentElement.getAttribute('data-theme'),
      'light',
      'Document should have light theme attribute after invalid theme'
    );
    
    console.log('✓ Invalid theme fallback verified');
  });
  
  test('Feature: modern-ui-redesign, Property 3: Theme change event is dispatched', () => {
    const manager = new ThemeManager();
    let eventFired = false;
    let eventDetail = null;
    
    // Listen for theme change event
    global.document.addEventListener('themechange', (e) => {
      eventFired = true;
      eventDetail = e.detail;
    });
    
    // Change theme
    manager.setTheme('dark', true);
    
    // Verify event was fired
    assert.ok(eventFired, 'Theme change event should be dispatched');
    assert.strictEqual(eventDetail.theme, 'dark', 'Event should contain correct theme');
    assert.ok(eventDetail.timestamp, 'Event should contain timestamp');
    
    console.log('✓ Theme change event verified');
  });
  
  test('Feature: modern-ui-redesign, Property 3: Multiple theme changes persist correctly', () => {
    const manager = new ThemeManager();
    const themes = ['light', 'dark', 'light', 'dark', 'light'];
    
    themes.forEach((theme, index) => {
      manager.setTheme(theme, true);
      
      // Verify immediate state
      assert.strictEqual(manager.getCurrentTheme(), theme, `Theme ${index + 1} should be set`);
      assert.strictEqual(
        global.localStorage.getItem('user-theme-preference'),
        theme,
        `Theme ${index + 1} should be saved`
      );
      
      // Simulate reload
      const newManager = new ThemeManager();
      assert.strictEqual(
        newManager.getCurrentTheme(),
        theme,
        `Theme ${index + 1} should persist after reload`
      );
    });
    
    console.log('✓ Multiple theme changes persistence verified');
  });
});
