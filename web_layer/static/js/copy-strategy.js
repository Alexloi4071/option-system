/**
 * 策略複製功能模塊
 * 
 * 功能：
 * - 為策略推薦卡片添加複製按鈕
 * - 支持一鍵複製策略參數到剪貼板
 * - 提供視覺反饋（成功/失敗提示）
 * - 兼容現代瀏覽器和舊版瀏覽器
 * 
 * 使用方法：
 * 1. 在 HTML 中引入此文件
 * 2. 在策略渲染後調用 attachCopyStrategyListeners()
 * 
 * @author Kiro AI
 * @date 2026-01-21
 */

/**
 * 格式化複製內容
 * 
 * @param {Object} data - 策略數據
 * @param {string} data.strategy - 策略名稱
 * @param {string} data.strike - 行使價
 * @param {string} data.expiry - 到期日
 * @param {string} data.direction - 方向（Bullish/Bearish）
 * @param {string} data.confidence - 信心度（High/Medium/Low）
 * @returns {string} 格式化的文本
 */
function formatCopyText(data) {
    return `策略: ${data.strategy}
方向: ${data.direction}
信心度: ${data.confidence}
建議行使價: $${data.strike}
建議到期日: ${data.expiry}

--- 複製自期權分析系統 ---`;
}

/**
 * 使用 Clipboard API 複製文本（現代瀏覽器）
 * 
 * @param {string} text - 要複製的文本
 * @returns {Promise<boolean>} 複製是否成功
 */
async function copyToClipboardModern(text) {
    try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(text);
            return true;
        }
        return false;
    } catch (err) {
        console.error('Clipboard API 複製失敗:', err);
        return false;
    }
}

/**
 * 使用 execCommand 複製文本（降級方案）
 * 
 * @param {string} text - 要複製的文本
 * @returns {boolean} 複製是否成功
 */
function copyToClipboardLegacy(text) {
    try {
        // 創建臨時 textarea
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        textarea.style.left = '-9999px';
        document.body.appendChild(textarea);
        
        // 選擇並複製
        textarea.select();
        textarea.setSelectionRange(0, textarea.value.length);
        
        const successful = document.execCommand('copy');
        
        // 清理
        document.body.removeChild(textarea);
        
        return successful;
    } catch (err) {
        console.error('execCommand 複製失敗:', err);
        return false;
    }
}

/**
 * 複製文本到剪貼板（自動選擇最佳方法）
 * 
 * @param {string} text - 要複製的文本
 * @returns {Promise<boolean>} 複製是否成功
 */
async function copyToClipboard(text) {
    // 優先使用現代 Clipboard API
    const modernSuccess = await copyToClipboardModern(text);
    if (modernSuccess) {
        return true;
    }
    
    // 降級到 execCommand
    return copyToClipboardLegacy(text);
}

/**
 * 顯示複製成功提示
 * 
 * @param {HTMLElement} button - 複製按鈕元素
 */
function showCopySuccess(button) {
    const successSpan = button.nextElementSibling;
    if (successSpan && successSpan.classList.contains('copy-success')) {
        // 顯示成功提示
        successSpan.style.display = 'inline';
        
        // 2秒後隱藏
        setTimeout(() => {
            successSpan.style.display = 'none';
        }, 2000);
    }
}

/**
 * 顯示複製失敗提示
 * 
 * @param {string} message - 錯誤消息
 */
function showCopyError(message) {
    // 使用 alert 作為降級方案
    alert(message || '複製失敗，請手動複製策略參數');
}

/**
 * 處理複製按鈕點擊事件
 * 
 * @param {Event} event - 點擊事件
 */
async function handleCopyButtonClick(event) {
    const button = event.currentTarget;
    
    // 獲取策略數據
    const data = {
        strategy: button.dataset.strategy,
        strike: button.dataset.strike,
        expiry: button.dataset.expiry,
        direction: button.dataset.direction,
        confidence: button.dataset.confidence
    };
    
    // 格式化複製內容
    const copyText = formatCopyText(data);
    
    // 複製到剪貼板
    const success = await copyToClipboard(copyText);
    
    if (success) {
        // 顯示成功提示
        showCopySuccess(button);
        
        // 記錄到控制台（用於調試）
        console.log('策略已複製:', data);
    } else {
        // 顯示失敗提示
        showCopyError('複製失敗，請手動複製策略參數');
    }
}

/**
 * 為所有複製按鈕添加事件監聽器
 * 
 * 此函數應在策略推薦渲染完成後調用
 */
function attachCopyStrategyListeners() {
    const copyButtons = document.querySelectorAll('.copy-strategy-btn');
    
    copyButtons.forEach(button => {
        // 移除舊的監聽器（如果存在）
        button.removeEventListener('click', handleCopyButtonClick);
        
        // 添加新的監聽器
        button.addEventListener('click', handleCopyButtonClick);
    });
    
    console.log(`已為 ${copyButtons.length} 個策略添加複製功能`);
}

/**
 * 測試複製功能
 * 
 * 用於開發和調試
 */
function testCopyFunction() {
    const testData = {
        strategy: 'Long Call',
        strike: '105.00',
        expiry: '2026-06-19',
        direction: 'Bullish',
        confidence: 'High'
    };
    
    const text = formatCopyText(testData);
    console.log('測試複製內容:');
    console.log(text);
    
    copyToClipboard(text).then(success => {
        console.log('測試結果:', success ? '成功' : '失敗');
    });
}

// 導出函數（如果使用模塊系統）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        formatCopyText,
        copyToClipboard,
        attachCopyStrategyListeners,
        testCopyFunction
    };
}
