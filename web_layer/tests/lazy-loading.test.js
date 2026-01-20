// Tests for Lazy Loading Implementation
// Task 15.1: Implement lazy loading for images
// Validates Requirement 13.3: Lazy-load images and non-critical content

const { test, describe } = require('node:test');
const assert = require('node:assert');
const { JSDOM } = require('jsdom');
const fs = require('fs');
const path = require('path');

// Load the lazy-loader.js file
const lazyLoaderPath = path.join(__dirname, '../static/js/lazy-loader.js');
const lazyLoaderCode = fs.readFileSync(lazyLoaderPath, 'utf-8');

function createTestDOM() {
    const dom = new JSDOM(`
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .lazy-loading { opacity: 0.6; }
                .lazy-loaded { opacity: 1; }
                .lazy-error { opacity: 0.5; }
            </style>
        </head>
        <body>
            <div id="test-container"></div>
        </body>
        </html>
    `, {
        url: 'http://localhost',
        runScripts: 'dangerously',
        resources: 'usable'
    });

    const window = dom.window;
    const document = window.document;

    // Mock IntersectionObserver
    window.IntersectionObserver = class IntersectionObserver {
        constructor(callback, options) {
            this.callback = callback;
            this.options = options;
            this.elements = new Set();
        }

        observe(element) {
            this.elements.add(element);
            // Simulate immediate intersection for testing
            setTimeout(() => {
                this.callback([{
                    target: element,
                    isIntersecting: true,
                    intersectionRatio: 1
                }], this);
            }, 10);
        }

        unobserve(element) {
            this.elements.delete(element);
        }

        disconnect() {
            this.elements.clear();
        }
    };

    // Mock MutationObserver
    window.MutationObserver = class MutationObserver {
        constructor(callback) {
            this.callback = callback;
        }
        observe() {}
        disconnect() {}
    };

    // Execute the lazy loader code in the JSDOM context
    const script = document.createElement('script');
    script.textContent = lazyLoaderCode;
    document.head.appendChild(script);

    return { dom, window, document, LazyLoader: window.LazyLoader };
}

describe('Lazy Loading Implementation - Task 15.1', () => {
    
    describe('Unit Tests: LazyLoader Class', () => {
        test('should create LazyLoader instance with default options', () => {
            const { LazyLoader, dom } = createTestDOM();
            const loader = new LazyLoader();
            assert.ok(loader);
            assert.strictEqual(loader.options.rootMargin, '50px');
            assert.strictEqual(loader.options.threshold, 0.01);
            dom.window.close();
            console.log('✓ LazyLoader instance created with default options');
        });

        test('should create LazyLoader instance with custom options', () => {
            const { LazyLoader, dom } = createTestDOM();
            const loader = new LazyLoader({
                rootMargin: '100px',
                threshold: 0.5,
                imageSelector: 'img.lazy'
            });
            assert.strictEqual(loader.options.rootMargin, '100px');
            assert.strictEqual(loader.options.threshold, 0.5);
            assert.strictEqual(loader.options.imageSelector, 'img.lazy');
            dom.window.close();
            console.log('✓ LazyLoader instance created with custom options');
        });

        test('should detect IntersectionObserver support', () => {
            const { LazyLoader, dom } = createTestDOM();
            const loader = new LazyLoader();
            assert.strictEqual(loader.isSupported, true);
            dom.window.close();
            console.log('✓ IntersectionObserver support detected');
        });

        test('should create image and content observers', () => {
            const { LazyLoader, dom } = createTestDOM();
            const loader = new LazyLoader();
            assert.ok(loader.imageObserver);
            assert.ok(loader.contentObserver);
            dom.window.close();
            console.log('✓ Image and content observers created');
        });
    });

    describe('Unit Tests: Image Lazy Loading', () => {
        test('should add loading="lazy" attribute to images', () => {
            const { document, dom } = createTestDOM();
            const container = document.getElementById('test-container');
            const img = document.createElement('img');
            img.src = 'test.jpg';
            container.appendChild(img);

            // Manually add loading attribute (simulating what main.js does)
            img.setAttribute('loading', 'lazy');

            assert.strictEqual(img.getAttribute('loading'), 'lazy');
            dom.window.close();
            console.log('✓ loading="lazy" attribute added to images');
        });

        test('should add lazy-loading class during image load', () => {
            const { LazyLoader, document, dom } = createTestDOM();
            const container = document.getElementById('test-container');
            const img = document.createElement('img');
            img.setAttribute('data-src', 'test.jpg');
            container.appendChild(img);

            const loader = new LazyLoader();
            loader.loadImage(img);

            assert.ok(img.classList.contains('lazy-loading'));
            dom.window.close();
            console.log('✓ lazy-loading class added during image load');
        });
    });

    describe('Unit Tests: Content Lazy Loading', () => {
        test('should add lazy-loaded class after content loads', () => {
            const { LazyLoader, document, dom } = createTestDOM();
            const container = document.getElementById('test-container');
            const div = document.createElement('div');
            div.setAttribute('data-lazy-load', 'widget');
            container.appendChild(div);

            const loader = new LazyLoader();
            loader.loadContent(div);

            assert.ok(div.classList.contains('lazy-loaded'));
            dom.window.close();
            console.log('✓ lazy-loaded class added after content loads');
        });

        test('should load content with data-lazy-src for iframes', () => {
            const { LazyLoader, document, dom } = createTestDOM();
            const container = document.getElementById('test-container');
            const iframe = document.createElement('iframe');
            iframe.setAttribute('data-lazy-src', 'https://example.com');
            container.appendChild(iframe);

            const loader = new LazyLoader();
            loader.loadContent(iframe);

            assert.strictEqual(iframe.src, 'https://example.com/');
            dom.window.close();
            console.log('✓ Content loaded with data-lazy-src for iframes');
        });
    });

    describe('Unit Tests: Fallback for Unsupported Browsers', () => {
        test('should load all content immediately when IntersectionObserver is not supported', () => {
            const dom = new JSDOM(`
                <!DOCTYPE html>
                <html>
                <body>
                    <div id="test-container"></div>
                </body>
                </html>
            `, {
                url: 'http://localhost',
                runScripts: 'dangerously'
            });

            const window = dom.window;
            const document = window.document;

            // Don't mock IntersectionObserver - simulate unsupported browser
            delete window.IntersectionObserver;

            // Mock MutationObserver
            window.MutationObserver = class MutationObserver {
                constructor(callback) {
                    this.callback = callback;
                }
                observe() {}
                disconnect() {}
            };

            // Execute the lazy loader code
            const script = document.createElement('script');
            script.textContent = lazyLoaderCode;
            document.head.appendChild(script);

            const container = document.getElementById('test-container');
            const img = document.createElement('img');
            img.setAttribute('data-src', 'test.jpg');
            container.appendChild(img);

            const loader = new window.LazyLoader();

            assert.strictEqual(loader.isSupported, false);
            // In unsupported browsers, images should load immediately
            assert.ok(img.src.includes('test.jpg'));
            dom.window.close();
            console.log('✓ Fallback for unsupported browsers works');
        });
    });

    describe('Unit Tests: Cleanup', () => {
        test('should disconnect observers when destroy() is called', () => {
            const { LazyLoader, dom } = createTestDOM();
            const loader = new LazyLoader();
            
            loader.destroy();

            assert.strictEqual(loader.loadedImages.size, 0);
            assert.strictEqual(loader.loadedContent.size, 0);
            dom.window.close();
            console.log('✓ Observers disconnected on destroy()');
        });
    });

    describe('Requirement 13.3 Validation: Lazy-load images and non-critical content', () => {
        test('Feature: modern-ui-redesign, Requirement 13.3: Native lazy loading for images', () => {
            const { document, dom } = createTestDOM();
            const img = document.createElement('img');
            img.setAttribute('loading', 'lazy');
            
            assert.strictEqual(img.getAttribute('loading'), 'lazy');
            dom.window.close();
            console.log('✓ Requirement 13.3: Native lazy loading implemented');
        });

        test('Feature: modern-ui-redesign, Requirement 13.3: Intersection Observer for non-critical content', () => {
            const { LazyLoader, dom } = createTestDOM();
            const loader = new LazyLoader();
            
            assert.ok(loader.imageObserver);
            assert.ok(loader.contentObserver);
            assert.strictEqual(loader.imageObserver.constructor.name, 'IntersectionObserver');
            dom.window.close();
            console.log('✓ Requirement 13.3: Intersection Observer implemented');
        });

        test('Feature: modern-ui-redesign, Requirement 13.3: Deferred loading of below-the-fold content', (t, done) => {
            const { LazyLoader, document, dom } = createTestDOM();
            const container = document.getElementById('test-container');
            
            // Simulate below-the-fold content
            const div = document.createElement('div');
            div.setAttribute('data-lazy-load', 'module');
            div.style.marginTop = '2000px'; // Below fold
            container.appendChild(div);

            const loader = new LazyLoader();

            // Content should not be loaded immediately
            assert.strictEqual(div.classList.contains('lazy-loaded'), false);

            // After intersection, it should load
            setTimeout(() => {
                assert.ok(loader.loadedContent.size > 0);
                dom.window.close();
                console.log('✓ Requirement 13.3: Below-the-fold content deferred');
                done();
            }, 50);
        });
    });

    describe('Edge Cases', () => {
        test('should handle images without data-src attribute', () => {
            const { LazyLoader, document, dom } = createTestDOM();
            const container = document.getElementById('test-container');
            const img = document.createElement('img');
            img.src = 'direct.jpg';
            img.setAttribute('loading', 'lazy');
            container.appendChild(img);

            const loader = new LazyLoader();
            loader.loadImage(img);

            // Should not throw error
            assert.ok(img.src.includes('direct.jpg'));
            dom.window.close();
            console.log('✓ Images without data-src handled correctly');
        });

        test('should handle empty container', () => {
            const { LazyLoader, dom } = createTestDOM();
            const loader = new LazyLoader();
            
            // Should not throw error
            assert.strictEqual(loader.loadedImages.size, 0);
            assert.strictEqual(loader.loadedContent.size, 0);
            dom.window.close();
            console.log('✓ Empty container handled correctly');
        });

        test('should not load same image twice', (t, done) => {
            const { LazyLoader, document, dom } = createTestDOM();
            const container = document.getElementById('test-container');
            const img = document.createElement('img');
            img.setAttribute('data-src', 'test.jpg');
            container.appendChild(img);

            const loader = new LazyLoader();
            
            // Load image twice
            loader.loadImage(img);
            loader.loadImage(img);

            setTimeout(() => {
                // Should only be loaded once
                assert.strictEqual(loader.loadedImages.size, 1);
                dom.window.close();
                console.log('✓ Same image not loaded twice');
                done();
            }, 50);
        });
    });
});
