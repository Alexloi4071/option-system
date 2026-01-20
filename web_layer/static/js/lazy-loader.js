// web_layer/static/js/lazy-loader.js
// Lazy Loading Manager for Images and Non-Critical Content
// Implements Requirement 13.3: Lazy-load images and non-critical content

/**
 * LazyLoader class handles lazy loading of images and non-critical content
 * using Intersection Observer API for optimal performance
 */
class LazyLoader {
    constructor(options = {}) {
        this.options = {
            // Intersection Observer options
            rootMargin: options.rootMargin || '50px',
            threshold: options.threshold || 0.01,
            
            // Selectors for lazy loading
            imageSelector: options.imageSelector || 'img[data-src], img[loading="lazy"]',
            contentSelector: options.contentSelector || '[data-lazy-load]',
            
            // Class names
            loadingClass: options.loadingClass || 'lazy-loading',
            loadedClass: options.loadedClass || 'lazy-loaded',
            errorClass: options.errorClass || 'lazy-error',
            
            // Callbacks
            onImageLoad: options.onImageLoad || null,
            onImageError: options.onImageError || null,
            onContentLoad: options.onContentLoad || null
        };
        
        // Check for Intersection Observer support
        this.isSupported = 'IntersectionObserver' in window;
        
        // Initialize observers
        this.imageObserver = null;
        this.contentObserver = null;
        
        // Track loaded elements
        this.loadedImages = new Set();
        this.loadedContent = new Set();
        
        this.init();
    }
    
    /**
     * Initialize the lazy loader
     */
    init() {
        if (!this.isSupported) {
            console.warn('Intersection Observer not supported. Loading all content immediately.');
            this.loadAllImmediately();
            return;
        }
        
        // Create observers
        this.createImageObserver();
        this.createContentObserver();
        
        // Observe existing elements
        this.observeImages();
        this.observeContent();
        
        // Set up mutation observer to handle dynamically added content
        this.setupMutationObserver();
    }
    
    /**
     * Create Intersection Observer for images
     */
    createImageObserver() {
        const options = {
            root: null,
            rootMargin: this.options.rootMargin,
            threshold: this.options.threshold
        };
        
        this.imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.loadImage(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, options);
    }
    
    /**
     * Create Intersection Observer for non-critical content
     */
    createContentObserver() {
        const options = {
            root: null,
            rootMargin: this.options.rootMargin,
            threshold: this.options.threshold
        };
        
        this.contentObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.loadContent(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, options);
    }
    
    /**
     * Observe all images on the page
     */
    observeImages() {
        const images = document.querySelectorAll(this.options.imageSelector);
        images.forEach(img => {
            if (!this.loadedImages.has(img)) {
                this.imageObserver.observe(img);
            }
        });
    }
    
    /**
     * Observe all lazy-loadable content on the page
     */
    observeContent() {
        const elements = document.querySelectorAll(this.options.contentSelector);
        elements.forEach(element => {
            if (!this.loadedContent.has(element)) {
                this.contentObserver.observe(element);
            }
        });
    }
    
    /**
     * Load an image
     * @param {HTMLImageElement} img - The image element to load
     */
    loadImage(img) {
        if (this.loadedImages.has(img)) {
            return;
        }
        
        // Add loading class
        img.classList.add(this.options.loadingClass);
        
        // Get the source URL
        const src = img.dataset.src || img.src;
        const srcset = img.dataset.srcset;
        
        // Create a new image to preload
        const tempImg = new Image();
        
        tempImg.onload = () => {
            // Set the actual source
            img.src = src;
            if (srcset) {
                img.srcset = srcset;
            }
            
            // Update classes
            img.classList.remove(this.options.loadingClass);
            img.classList.add(this.options.loadedClass);
            
            // Remove data attributes
            delete img.dataset.src;
            delete img.dataset.srcset;
            
            // Mark as loaded
            this.loadedImages.add(img);
            
            // Callback
            if (this.options.onImageLoad) {
                this.options.onImageLoad(img);
            }
        };
        
        tempImg.onerror = () => {
            img.classList.remove(this.options.loadingClass);
            img.classList.add(this.options.errorClass);
            
            // Callback
            if (this.options.onImageError) {
                this.options.onImageError(img);
            }
            
            console.error('Failed to load image:', src);
        };
        
        // Start loading
        tempImg.src = src;
    }
    
    /**
     * Load non-critical content
     * @param {HTMLElement} element - The element to load
     */
    loadContent(element) {
        if (this.loadedContent.has(element)) {
            return;
        }
        
        // Add loading class
        element.classList.add(this.options.loadingClass);
        
        // Check if element has a data-lazy-src attribute (for iframe, etc.)
        const lazySrc = element.dataset.lazySrc;
        if (lazySrc) {
            if (element.tagName === 'IFRAME') {
                element.src = lazySrc;
            }
            delete element.dataset.lazySrc;
        }
        
        // Check if element has data-lazy-content attribute
        const lazyContent = element.dataset.lazyContent;
        if (lazyContent) {
            try {
                // Parse and insert content
                const content = JSON.parse(lazyContent);
                if (typeof content === 'string') {
                    element.innerHTML = content;
                }
            } catch (e) {
                console.error('Failed to parse lazy content:', e);
            }
            delete element.dataset.lazyContent;
        }
        
        // Update classes
        element.classList.remove(this.options.loadingClass);
        element.classList.add(this.options.loadedClass);
        
        // Mark as loaded
        this.loadedContent.add(element);
        
        // Callback
        if (this.options.onContentLoad) {
            this.options.onContentLoad(element);
        }
    }
    
    /**
     * Set up mutation observer to handle dynamically added content
     */
    setupMutationObserver() {
        const mutationObserver = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === 1) { // Element node
                            // Check if the node itself is an image
                            if (node.matches && node.matches(this.options.imageSelector)) {
                                this.imageObserver.observe(node);
                            }
                            
                            // Check if the node itself is lazy content
                            if (node.matches && node.matches(this.options.contentSelector)) {
                                this.contentObserver.observe(node);
                            }
                            
                            // Check for images within the node
                            const images = node.querySelectorAll && node.querySelectorAll(this.options.imageSelector);
                            if (images) {
                                images.forEach(img => this.imageObserver.observe(img));
                            }
                            
                            // Check for lazy content within the node
                            const content = node.querySelectorAll && node.querySelectorAll(this.options.contentSelector);
                            if (content) {
                                content.forEach(el => this.contentObserver.observe(el));
                            }
                        }
                    });
                }
            });
        });
        
        // Start observing
        mutationObserver.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
    
    /**
     * Load all content immediately (fallback for unsupported browsers)
     */
    loadAllImmediately() {
        // Load all images
        const images = document.querySelectorAll(this.options.imageSelector);
        images.forEach(img => {
            const src = img.dataset.src || img.src;
            if (src) {
                img.src = src;
            }
            const srcset = img.dataset.srcset;
            if (srcset) {
                img.srcset = srcset;
            }
        });
        
        // Load all content
        const elements = document.querySelectorAll(this.options.contentSelector);
        elements.forEach(element => {
            const lazySrc = element.dataset.lazySrc;
            if (lazySrc && element.tagName === 'IFRAME') {
                element.src = lazySrc;
            }
            
            const lazyContent = element.dataset.lazyContent;
            if (lazyContent) {
                try {
                    const content = JSON.parse(lazyContent);
                    if (typeof content === 'string') {
                        element.innerHTML = content;
                    }
                } catch (e) {
                    console.error('Failed to parse lazy content:', e);
                }
            }
        });
    }
    
    /**
     * Manually trigger loading of a specific element
     * @param {HTMLElement} element - The element to load
     */
    loadElement(element) {
        if (element.tagName === 'IMG') {
            this.loadImage(element);
        } else {
            this.loadContent(element);
        }
    }
    
    /**
     * Refresh observers (useful after dynamic content changes)
     */
    refresh() {
        this.observeImages();
        this.observeContent();
    }
    
    /**
     * Destroy the lazy loader and clean up
     */
    destroy() {
        if (this.imageObserver) {
            this.imageObserver.disconnect();
        }
        if (this.contentObserver) {
            this.contentObserver.disconnect();
        }
        this.loadedImages.clear();
        this.loadedContent.clear();
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LazyLoader;
}

// Auto-initialize on DOM ready
if (typeof window !== 'undefined') {
    window.LazyLoader = LazyLoader;
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.lazyLoader = new LazyLoader();
        });
    } else {
        window.lazyLoader = new LazyLoader();
    }
}
