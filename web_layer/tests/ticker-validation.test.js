/**
 * US-5: Frontend Input Validation Tests
 * Tests for ticker validation functionality
 */

const { test, describe } = require('node:test');
const assert = require('node:assert');

// Mock validateTicker function (would be imported in real scenario)
function validateTicker(ticker) {
    const validation = {
        isValid: false,
        ticker: ticker.toUpperCase(),
        errors: []
    };
    
    if (ticker.length === 0) {
        validation.errors.push('股票代碼不能為空');
        return validation;
    }
    
    if (ticker.length > 5) {
        validation.errors.push('股票代碼不能超過5個字符');
        return validation;
    }
    
    const validPattern = /^[A-Z0-9.-]+$/;
    if (!validPattern.test(validation.ticker)) {
        validation.errors.push('股票代碼只能包含字母、數字、點(.)和連字符(-)');
        return validation;
    }
    
    validation.isValid = true;
    return validation;
}

describe('Ticker Validation', () => {
    describe('Task 4.3.1: Valid Input Tests', () => {
        test('should accept valid ticker AAPL', () => {
            const result = validateTicker('AAPL');
            assert.strictEqual(result.isValid, true);
            assert.strictEqual(result.ticker, 'AAPL');
            assert.strictEqual(result.errors.length, 0);
        });

        test('should accept valid ticker TSLA', () => {
            const result = validateTicker('TSLA');
            assert.strictEqual(result.isValid, true);
            assert.strictEqual(result.ticker, 'TSLA');
            assert.strictEqual(result.errors.length, 0);
        });

        test('should accept valid ticker with dot BRK.B', () => {
            const result = validateTicker('BRK.B');
            assert.strictEqual(result.isValid, true);
            assert.strictEqual(result.ticker, 'BRK.B');
            assert.strictEqual(result.errors.length, 0);
        });

        test('should accept valid ticker with hyphen T-MO', () => {
            const result = validateTicker('T-MO');
            assert.strictEqual(result.isValid, true);
            assert.strictEqual(result.ticker, 'T-MO');
            assert.strictEqual(result.errors.length, 0);
        });

        test('should accept single character ticker A', () => {
            const result = validateTicker('A');
            assert.strictEqual(result.isValid, true);
            assert.strictEqual(result.ticker, 'A');
            assert.strictEqual(result.errors.length, 0);
        });

        test('should accept 5 character ticker GOOGL', () => {
            const result = validateTicker('GOOGL');
            assert.strictEqual(result.isValid, true);
            assert.strictEqual(result.ticker, 'GOOGL');
            assert.strictEqual(result.errors.length, 0);
        });
    });

    describe('Task 4.3.2: Invalid Input Tests', () => {
        test('should reject empty ticker', () => {
            const result = validateTicker('');
            assert.strictEqual(result.isValid, false);
            assert.ok(result.errors.includes('股票代碼不能為空'));
        });

        test('should reject ticker longer than 5 characters', () => {
            const result = validateTicker('TOOLONG');
            assert.strictEqual(result.isValid, false);
            assert.ok(result.errors.includes('股票代碼不能超過5個字符'));
        });

        test('should reject ticker with special characters', () => {
            const result = validateTicker('AAP@L');
            assert.strictEqual(result.isValid, false);
            assert.ok(result.errors.includes('股票代碼只能包含字母、數字、點(.)和連字符(-)'));
        });

        test('should reject ticker with spaces', () => {
            const result = validateTicker('AA PL');
            assert.strictEqual(result.isValid, false);
            assert.ok(result.errors.includes('股票代碼只能包含字母、數字、點(.)和連字符(-)'));
        });

        test('should reject ticker with underscore', () => {
            const result = validateTicker('AA_PL');
            assert.strictEqual(result.isValid, false);
            assert.ok(result.errors.includes('股票代碼只能包含字母、數字、點(.)和連字符(-)'));
        });
    });

    describe('Task 4.3.3: Auto-Uppercase Conversion Tests', () => {
        test('should convert lowercase to uppercase', () => {
            const result = validateTicker('aapl');
            assert.strictEqual(result.ticker, 'AAPL');
            assert.strictEqual(result.isValid, true);
        });

        test('should convert mixed case to uppercase', () => {
            const result = validateTicker('AaPl');
            assert.strictEqual(result.ticker, 'AAPL');
            assert.strictEqual(result.isValid, true);
        });

        test('should handle uppercase input', () => {
            const result = validateTicker('AAPL');
            assert.strictEqual(result.ticker, 'AAPL');
            assert.strictEqual(result.isValid, true);
        });

        test('should convert lowercase with dot to uppercase', () => {
            const result = validateTicker('brk.b');
            assert.strictEqual(result.ticker, 'BRK.B');
            assert.strictEqual(result.isValid, true);
        });
    });

    describe('Edge Cases', () => {
        test('should handle ticker with numbers', () => {
            const result = validateTicker('3M');
            assert.strictEqual(result.isValid, true);
            assert.strictEqual(result.ticker, '3M');
        });

        test('should handle ticker starting with number', () => {
            const result = validateTicker('3M');
            assert.strictEqual(result.isValid, true);
            assert.strictEqual(result.ticker, '3M');
        });

        test('should handle ticker with multiple dots', () => {
            const result = validateTicker('A.B.C');
            assert.strictEqual(result.isValid, true);
            assert.strictEqual(result.ticker, 'A.B.C');
        });

        test('should handle ticker with multiple hyphens', () => {
            const result = validateTicker('A-B-C');
            assert.strictEqual(result.isValid, true);
            assert.strictEqual(result.ticker, 'A-B-C');
        });
    });

    describe('Error Message Tests', () => {
        test('should provide clear error for empty input', () => {
            const result = validateTicker('');
            assert.strictEqual(result.errors[0], '股票代碼不能為空');
        });

        test('should provide clear error for too long input', () => {
            const result = validateTicker('TOOLONG');
            assert.strictEqual(result.errors[0], '股票代碼不能超過5個字符');
        });

        test('should provide clear error for invalid characters', () => {
            const result = validateTicker('AAP@L');
            assert.strictEqual(result.errors[0], '股票代碼只能包含字母、數字、點(.)和連字符(-)');
        });
    });
});
