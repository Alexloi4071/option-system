/**
 * Accessibility Manager Integration Tests
 * Verifies that the AccessibilityManager initializes automatically in a browser-like environment.
 */

const { test, describe } = require('node:test');
const assert = require('node:assert');
const { JSDOM } = require('jsdom');
const fs = require('fs');
const path = require('path');

// Load script content
const scriptPath = path.join(__dirname, '../static/js/accessibility-manager.js');
const scriptContent = fs.readFileSync(scriptPath, 'utf-8');

describe('Integration: AccessibilityManager Initialization', () => {

    test('It should automatically initialize and attach to window when loaded in browser', () => {
        // Setup JSDOM environment
        const dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <head></head>
        <body>
          <div id="root"></div>
        </body>
      </html>
    `, {
            runScripts: "dangerously", // Allow script execution
            resources: "usable",
            url: "http://localhost"
        });

        const { window } = dom;

        // The script expects CommonJS module.exports checks or similar, which might fail in pure JSDOM script injection
        // if 'module' is not defined. We need to normalize the environment.
        // However, the fix in accessibility-manager.js likely has "if (typeof window !== 'undefined')" checks.

        // We'll define a minimal module/require mock if the script requires it, 
        // but the key is checking the SIDE EFFECT of the script execution.

        // Using window.eval to execute the script content in the window context
        // We intentionally don't mock 'module' or 'require' to see if it handles browser env correctly.
        // BUT if the file has `module.exports = ...`, it might throw if `module` is not defined.
        // Let's check if we need to mock module.exports for the script to run without erroring out.

        window.module = { exports: {} };

        // Execute the script
        window.eval(scriptContent);

        // Helper to trigger DOMContentLoaded
        const triggerDOMContentLoaded = () => {
            const event = new window.Event('DOMContentLoaded', {
                bubbles: true,
                cancelable: false
            });
            window.document.dispatchEvent(event);
        };

        // If the script listens for DOMContentLoaded, we need to fire it.
        // But JSDOM might already be in 'loading' or 'complete' state.
        // The previous fix code was:
        // if (document.readyState === 'loading') { document.addEventListener... } else { init... }

        // Check initial state
        // console.log('ReadyState:', window.document.readyState);

        // If readyState is 'complete' (default in JSDOM usually), it should have initialized immediately.
        // If it requires an event, we trigger it.

        if (!window.accessibilityManager) {
            triggerDOMContentLoaded();
        }

        // Assert
        assert.ok(window.accessibilityManager, 'accessibilityManager should be attached to window');
        assert.strictEqual(typeof window.accessibilityManager.init, 'function', 'Should have init method or similar prototype');

        // Verify it is actually an instance of the class
        assert.strictEqual(window.accessibilityManager.constructor.name, 'AccessibilityManager');
    });

});
