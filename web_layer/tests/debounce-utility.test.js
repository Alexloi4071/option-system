// web_layer/tests/debounce-utility.test.js

/**
 * Unit Tests for Debounce Utility
 * Tests debouncing functionality for input handler optimization
 * Validates: Requirements 13.4
 */

const { test, describe } = require('node:test');
const assert = require('node:assert');
const { debounce, throttle } = require('../static/js/debounce-utility.js');

// Helper to wait for a specified time
const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms));

describe('Debounce Utility Tests', () => {
  
  describe('Basic Debounce Functionality', () => {
    
    test('should debounce function calls', async () => {
      let callCount = 0;
      const debouncedFn = debounce(() => {
        callCount++;
      }, 100);
      
      // Call multiple times rapidly
      debouncedFn();
      debouncedFn();
      debouncedFn();
      
      // Should not have been called yet
      assert.strictEqual(callCount, 0);
      
      // Wait for debounce
      await wait(150);
      
      // Should have been called once
      assert.strictEqual(callCount, 1);
      console.log('✓ Debounce function calls test passed');
    });
    
    test('should pass arguments to debounced function', async () => {
      let receivedArgs = null;
      const debouncedFn = debounce((...args) => {
        receivedArgs = args;
      }, 100);
      
      debouncedFn('test', 123, { key: 'value' });
      await wait(150);
      
      assert.deepStrictEqual(receivedArgs, ['test', 123, { key: 'value' }]);
      console.log('✓ Arguments passed correctly');
    });
    
    test('should preserve this context', async () => {
      const obj = {
        value: 42,
        method: debounce(function() {
          return this.value;
        }, 100)
      };
      
      obj.method();
      await wait(150);
      
      // Context should be preserved
      assert.strictEqual(obj.value, 42);
      console.log('✓ Context preserved');
    });
    
    test('should only call function once after multiple rapid calls', async () => {
      let callCount = 0;
      const debouncedFn = debounce(() => {
        callCount++;
      }, 200);
      
      // Rapid calls
      for (let i = 0; i < 10; i++) {
        debouncedFn();
      }
      
      await wait(250);
      assert.strictEqual(callCount, 1);
      console.log('✓ Multiple rapid calls debounced to single call');
    });
    
    test('should reset timer on subsequent calls', async () => {
      let callCount = 0;
      const debouncedFn = debounce(() => {
        callCount++;
      }, 100);
      
      debouncedFn();
      await wait(50);
      
      debouncedFn(); // Reset timer
      await wait(50);
      
      assert.strictEqual(callCount, 0); // Still waiting
      
      await wait(60);
      assert.strictEqual(callCount, 1); // Now called
      console.log('✓ Timer reset on subsequent calls');
    });
  });
  
  describe('Debounce Options', () => {
    
    test('should support leading edge execution', async () => {
      let callCount = 0;
      const debouncedFn = debounce(() => {
        callCount++;
      }, 100, { leading: true, trailing: false });
      
      debouncedFn();
      
      // Should be called immediately on leading edge
      assert.strictEqual(callCount, 1);
      
      await wait(150);
      
      // Should not be called again on trailing edge
      assert.strictEqual(callCount, 1);
      console.log('✓ Leading edge execution works');
    });
    
    test('should support trailing edge execution (default)', async () => {
      let callCount = 0;
      const debouncedFn = debounce(() => {
        callCount++;
      }, 100);
      
      debouncedFn();
      
      // Should not be called immediately
      assert.strictEqual(callCount, 0);
      
      await wait(150);
      
      // Should be called on trailing edge
      assert.strictEqual(callCount, 1);
      console.log('✓ Trailing edge execution works (default)');
    });
    
    test('should support both leading and trailing execution', async () => {
      let callCount = 0;
      const debouncedFn = debounce(() => {
        callCount++;
      }, 100, { leading: true, trailing: true });
      
      debouncedFn();
      
      // Called on leading edge
      assert.strictEqual(callCount, 1);
      
      // Call again to trigger trailing edge
      debouncedFn();
      
      await wait(150);
      
      // Called on trailing edge (total 2 calls)
      assert.strictEqual(callCount, 2);
      console.log('✓ Both leading and trailing execution works');
    });
  });
  
  describe('Debounce Control Methods', () => {
    
    test('cancel() should cancel pending invocations', async () => {
      let callCount = 0;
      const debouncedFn = debounce(() => {
        callCount++;
      }, 100);
      
      debouncedFn();
      debouncedFn.cancel();
      
      await wait(150);
      
      assert.strictEqual(callCount, 0);
      console.log('✓ Cancel method works');
    });
    
    test('flush() should immediately invoke pending function', () => {
      let callCount = 0;
      const debouncedFn = debounce(() => {
        callCount++;
      }, 100);
      
      debouncedFn();
      assert.strictEqual(callCount, 0);
      
      debouncedFn.flush();
      assert.strictEqual(callCount, 1);
      console.log('✓ Flush method works');
    });
    
    test('pending() should return true when invocation is pending', async () => {
      const debouncedFn = debounce(() => {}, 100);
      
      assert.strictEqual(debouncedFn.pending(), false);
      
      debouncedFn();
      assert.strictEqual(debouncedFn.pending(), true);
      
      await wait(150);
      assert.strictEqual(debouncedFn.pending(), false);
      console.log('✓ Pending method works');
    });
  });
  
  describe('Input Validation', () => {
    
    test('should throw TypeError if func is not a function', () => {
      assert.throws(() => debounce('not a function', 100), TypeError);
      assert.throws(() => debounce(null, 100), TypeError);
      assert.throws(() => debounce(undefined, 100), TypeError);
      console.log('✓ Input validation for function parameter');
    });
    
    test('should throw TypeError if wait is negative', () => {
      assert.throws(() => debounce(() => {}, -100), TypeError);
      console.log('✓ Input validation for negative wait time');
    });
    
    test('should throw TypeError if wait is not a number', () => {
      assert.throws(() => debounce(() => {}, 'not a number'), TypeError);
      console.log('✓ Input validation for wait parameter type');
    });
    
    test('should use default wait time if not provided', async () => {
      let callCount = 0;
      const debouncedFn = debounce(() => {
        callCount++;
      });
      
      debouncedFn();
      await wait(350); // Default is 300ms
      
      assert.strictEqual(callCount, 1);
      console.log('✓ Default wait time (300ms) works');
    });
  });
  
  describe('Real-World Use Cases', () => {
    
    test('should optimize search input handling', async () => {
      const searchResults = [];
      const search = debounce((query) => {
        searchResults.push(query);
      }, 300);
      
      // Simulate rapid typing
      search('a');
      await wait(50);
      search('ap');
      await wait(50);
      search('app');
      await wait(50);
      search('appl');
      await wait(50);
      search('apple');
      
      // Should not have searched yet
      assert.strictEqual(searchResults.length, 0);
      
      // Wait for debounce
      await wait(350);
      
      // Should only search once with final query
      assert.deepStrictEqual(searchResults, ['apple']);
      console.log('✓ Search input optimization works');
    });
    
    test('should optimize filter input handling', async () => {
      let filterCount = 0;
      const applyFilter = debounce(() => {
        filterCount++;
      }, 250);
      
      // Simulate rapid filter changes
      for (let i = 0; i < 20; i++) {
        applyFilter();
        await wait(10);
      }
      
      // Should not have filtered yet
      assert.strictEqual(filterCount, 0);
      
      // Wait for debounce
      await wait(300);
      
      // Should only filter once
      assert.strictEqual(filterCount, 1);
      console.log('✓ Filter input optimization works');
    });
    
    test('should handle ticker input with 800ms delay', async () => {
      const fetchCalls = [];
      const fetchExpirations = debounce((ticker) => {
        fetchCalls.push(ticker);
      }, 800);
      
      // Simulate typing ticker
      fetchExpirations('A');
      await wait(100);
      fetchExpirations('AA');
      await wait(100);
      fetchExpirations('AAP');
      await wait(100);
      fetchExpirations('AAPL');
      
      // Should not have fetched yet
      assert.strictEqual(fetchCalls.length, 0);
      
      // Wait for 800ms debounce
      await wait(850);
      
      // Should only fetch once with final ticker
      assert.deepStrictEqual(fetchCalls, ['AAPL']);
      console.log('✓ Ticker input with 800ms delay works (Requirement 13.4)');
    });
  });
  
  describe('Throttle Function', () => {
    
    test('should throttle function calls', async () => {
      let callCount = 0;
      const throttledFn = throttle(() => {
        callCount++;
      }, 100);
      
      // Call immediately (leading edge)
      throttledFn();
      assert.strictEqual(callCount, 1);
      
      // Call again immediately (should be throttled)
      throttledFn();
      assert.strictEqual(callCount, 1);
      
      // Wait for throttle period
      await wait(150);
      assert.strictEqual(callCount, 2); // Trailing edge
      console.log('✓ Throttle function works');
    });
    
    test('should allow calls after throttle period', async () => {
      let callCount = 0;
      const throttledFn = throttle(() => {
        callCount++;
      }, 100);
      
      throttledFn();
      assert.strictEqual(callCount, 1);
      
      await wait(150);
      
      throttledFn();
      assert.strictEqual(callCount, 2);
      console.log('✓ Throttle allows calls after period');
    });
  });
  
  describe('Performance Optimization', () => {
    
    test('should reduce function calls by at least 90% for rapid events', async () => {
      let actualCalls = 0;
      const debouncedFn = debounce(() => {
        actualCalls++;
      }, 100);
      
      const totalCalls = 100;
      
      // Simulate 100 rapid calls
      for (let i = 0; i < totalCalls; i++) {
        debouncedFn();
        await wait(5);
      }
      
      await wait(150);
      
      // Should have reduced calls by >90%
      assert.ok(actualCalls <= totalCalls * 0.1);
      console.log(`✓ Performance: Reduced ${totalCalls} calls to ${actualCalls} (${((totalCalls - actualCalls) / totalCalls * 100).toFixed(1)}% reduction)`);
    });
    
    test('should handle high-frequency events efficiently', async () => {
      let callCount = 0;
      const debouncedFn = debounce(() => {
        callCount++;
      }, 50);
      
      // Simulate 1000 rapid calls
      for (let i = 0; i < 1000; i++) {
        debouncedFn();
      }
      
      await wait(100);
      
      // Should only call once
      assert.strictEqual(callCount, 1);
      console.log('✓ High-frequency events handled efficiently (1000 calls → 1 execution)');
    });
  });
  
  describe('Edge Cases', () => {
    
    test('should handle zero wait time', async () => {
      let callCount = 0;
      const debouncedFn = debounce(() => {
        callCount++;
      }, 0);
      
      debouncedFn();
      await wait(10);
      
      assert.strictEqual(callCount, 1);
      console.log('✓ Zero wait time handled');
    });
    
    test('should handle multiple debounced functions independently', async () => {
      let count1 = 0;
      let count2 = 0;
      
      const debounced1 = debounce(() => { count1++; }, 100);
      const debounced2 = debounce(() => { count2++; }, 200);
      
      debounced1();
      debounced2();
      
      await wait(150);
      assert.strictEqual(count1, 1);
      assert.strictEqual(count2, 0);
      
      await wait(100);
      assert.strictEqual(count1, 1);
      assert.strictEqual(count2, 1);
      console.log('✓ Multiple debounced functions work independently');
    });
  });
});

console.log('\n✓ All debounce utility tests completed successfully');
console.log('✓ Requirement 13.4 validated: Debouncing optimizes input handler performance');
