/**
 * Module Renderer - Modern UI for all 28 analysis modules
 * Requirements: 16.1, 16.2, 16.3, 16.5
 * 
 * This module provides rendering functions for all 28 calculation modules
 * with modern card styles, enhanced table presentation, and visual indicators.
 */

// Module status constants
const MODULE_STATUS = {
  SUCCESS: 'success',
  ERROR: 'error',
  SKIPPED: 'skipped',
  LOADING: 'loading',
  NO_DATA: 'no_data'
};

// Module metadata for all 28 modules
const MODULE_METADATA = {
  1: { name: '支持位/阻力位', icon: 'fa-chart-line', category: 'core' },
  2: { name: '公允值', icon: 'fa-balance-scale', category: 'core' },
  3: { name: '套戥水位', icon: 'fa-exchange-alt', category: 'core' },
  4: { name: 'PE 估值', icon: 'fa-calculator', category: 'valuation' },
  5: { name: '利率PE關係', icon: 'fa-percentage', category: 'valuation' },
  6: { name: '對沖量', icon: 'fa-shield-alt', category: 'risk' },
  7: { name: 'Long Call', icon: 'fa-arrow-up', category: 'strategy' },
  8: { name: 'Long Put', icon: 'fa-arrow-down', category: 'strategy' },
  9: { name: 'Short Call', icon: 'fa-level-down-alt', category: 'strategy' },
  10: { name: 'Short Put', icon: 'fa-level-up-alt', category: 'strategy' },
  11: { name: '合成正股', icon: 'fa-sync-alt', category: 'advanced' },
  12: { name: '年息收益率', icon: 'fa-coins', category: 'yield' },
  13: { name: '倉位分析', icon: 'fa-chart-pie', category: 'position' },
  14: { name: '監察崗位', icon: 'fa-eye', category: 'monitoring' },
  15: { name: 'Black-Scholes', icon: 'fa-square-root-alt', category: 'pricing' },
  16: { name: 'Greeks', icon: 'fa-greek', category: 'pricing' },
  17: { name: '隱含波動率', icon: 'fa-wave-square', category: 'volatility' },
  18: { name: '歷史波動率', icon: 'fa-history', category: 'volatility' },
  19: { name: 'Put-Call Parity', icon: 'fa-equals', category: 'pricing' },
  20: { name: '基本面健康', icon: 'fa-heartbeat', category: 'fundamental' },
  21: { name: '動量過濾器', icon: 'fa-tachometer-alt', category: 'technical' },
  22: { name: '最佳行使價', icon: 'fa-bullseye', category: 'optimization' },
  23: { name: '動態IV閾值', icon: 'fa-sliders-h', category: 'volatility' },
  24: { name: '技術方向', icon: 'fa-compass', category: 'technical' },
  25: { name: '波動率微笑', icon: 'fa-smile', category: 'volatility' },
  26: { name: 'Long期權分析', icon: 'fa-chart-bar', category: 'analysis' },
  27: { name: '多到期日比較', icon: 'fa-calendar-alt', category: 'comparison' },
  28: { name: '資金倉位計算', icon: 'fa-calculator', category: 'position' }
};

/**
 * ModuleRenderer class - handles rendering of all 28 modules
 */
class ModuleRenderer {
  constructor() {
    this.renderedModules = new Set();
  }

  /**
   * Get module status from data
   * @param {Object} moduleData - Module calculation data
   * @returns {string} Module status
   */
  getModuleStatus(moduleData) {
    if (!moduleData) return MODULE_STATUS.NO_DATA;
    if (moduleData.status === 'error') return MODULE_STATUS.ERROR;
    if (moduleData.status === 'skipped') return MODULE_STATUS.SKIPPED;
    if (moduleData.status === 'success' || moduleData.status === undefined) {
      return MODULE_STATUS.SUCCESS;
    }
    return MODULE_STATUS.NO_DATA;
  }

  /**
   * Create status indicator HTML
   * @param {string} status - Module status
   * @returns {string} HTML for status indicator
   */
  createStatusIndicator(status) {
    const statusConfig = {
      [MODULE_STATUS.SUCCESS]: { icon: 'fa-check-circle', class: 'status-success', label: '成功' },
      [MODULE_STATUS.ERROR]: { icon: 'fa-exclamation-circle', class: 'status-error', label: '錯誤' },
      [MODULE_STATUS.SKIPPED]: { icon: 'fa-minus-circle', class: 'status-skipped', label: '跳過' },
      [MODULE_STATUS.LOADING]: { icon: 'fa-spinner fa-spin', class: 'status-loading', label: '載入中' },
      [MODULE_STATUS.NO_DATA]: { icon: 'fa-question-circle', class: 'status-no-data', label: '無數據' }
    };

    const config = statusConfig[status] || statusConfig[MODULE_STATUS.NO_DATA];
    return `<span class="module-status-indicator ${config.class}" title="${config.label}">
      <i class="fas ${config.icon}"></i>
    </span>`;
  }

  /**
   * Create no-data message HTML
   * @param {string} reason - Reason for no data
   * @param {number} moduleId - Module ID
   * @returns {string} HTML for no-data message
   */
  createNoDataMessage(reason, moduleId) {
    const defaultReasons = {
      1: '需要股票價格和IV數據',
      2: '需要股票價格和利率數據',
      3: '需要期權價格數據',
      4: '需要EPS和PE數據',
      5: '需要利率和PE數據',
      6: '需要持倉數據',
      7: '需要Call期權數據',
      8: '需要Put期權數據',
      9: '需要Call期權數據',
      10: '需要Put期權數據',
      11: '需要Call和Put期權數據',
      12: '需要股息和期權數據',
      13: '需要成交量和持倉數據',
      14: '需要完整市場數據',
      15: '需要期權參數數據',
      16: '需要期權定價數據',
      17: '需要期權價格數據',
      18: '需要歷史價格數據',
      19: '需要Call和Put價格數據',
      20: '需要基本面數據',
      21: '需要技術指標數據',
      22: '需要期權鏈數據',
      23: '需要IV歷史數據',
      24: '需要技術分析數據',
      25: '需要多個行使價IV數據',
      26: '需要期權定價數據',
      27: '需要多個到期日數據',
      28: '需要資金和風險參數'
    };

    const displayReason = reason || defaultReasons[moduleId] || '數據不足，無法計算';
    
    return `<div class="module-no-data">
      <div class="no-data-icon">
        <i class="fas fa-inbox"></i>
      </div>
      <p class="no-data-message">${displayReason}</p>
    </div>`;
  }

  /**
   * Create error message HTML
   * @param {string} errorMessage - Error message
   * @returns {string} HTML for error message
   */
  createErrorMessage(errorMessage) {
    return `<div class="module-error">
      <div class="error-icon">
        <i class="fas fa-exclamation-triangle"></i>
      </div>
      <p class="error-message">${errorMessage || '計算過程中發生錯誤'}</p>
      <p class="error-hint">請檢查輸入參數或稍後重試</p>
    </div>`;
  }

  /**
   * Create skipped message HTML
   * @param {string} reason - Reason for skipping
   * @returns {string} HTML for skipped message
   */
  createSkippedMessage(reason) {
    return `<div class="module-skipped">
      <div class="skipped-icon">
        <i class="fas fa-forward"></i>
      </div>
      <p class="skipped-message">${reason || '此模塊已跳過'}</p>
    </div>`;
  }

  /**
   * Format financial value with color coding
   * @param {number} value - Numeric value
   * @param {Object} options - Formatting options
   * @returns {string} Formatted HTML
   */
  formatFinancialValue(value, options = {}) {
    const { prefix = '', suffix = '', decimals = 2, showSign = false } = options;
    
    if (value === null || value === undefined || isNaN(value)) {
      return '<span class="value-neutral">N/A</span>';
    }

    const formattedValue = Number(value).toFixed(decimals);
    const sign = showSign && value > 0 ? '+' : '';
    
    let colorClass = 'value-neutral';
    if (value > 0) colorClass = 'value-positive';
    else if (value < 0) colorClass = 'value-negative';

    return `<span class="${colorClass}">${prefix}${sign}${formattedValue}${suffix}</span>`;
  }

  /**
   * Create grade badge HTML
   * @param {string} grade - Grade letter (A, B, C, D, F)
   * @returns {string} HTML for grade badge
   */
  createGradeBadge(grade) {
    if (!grade) return '<span class="badge badge-secondary">N/A</span>';
    
    const gradeColors = {
      'A': 'badge-success',
      'B': 'badge-info',
      'C': 'badge-warning',
      'D': 'badge-warning',
      'F': 'badge-danger'
    };

    const colorClass = gradeColors[grade.toUpperCase()] || 'badge-secondary';
    return `<span class="badge ${colorClass}">${grade}</span>`;
  }

  // ============================================================================
  // MODULE 1: Support/Resistance
  // ============================================================================
  renderModule1(data, container) {
    const status = this.getModuleStatus(data);
    const moduleId = 1;
    
    if (status === MODULE_STATUS.ERROR) {
      container.innerHTML = this.createErrorMessage(data?.error);
      return;
    }
    
    if (status === MODULE_STATUS.SKIPPED) {
      container.innerHTML = this.createSkippedMessage(data?.reason);
      return;
    }
    
    if (status === MODULE_STATUS.NO_DATA || !data?.results) {
      container.innerHTML = this.createNoDataMessage(data?.reason, moduleId);
      return;
    }

    let html = `
      <div class="table-container">
        <table class="table-modern table-striped">
          <thead>
            <tr>
              <th>信心度</th>
              <th>Z值</th>
              <th class="text-right">波動幅度</th>
              <th class="text-right">支持位</th>
              <th class="text-right">阻力位</th>
            </tr>
          </thead>
          <tbody>
    `;

    Object.entries(data.results).forEach(([conf, res]) => {
      html += `
        <tr>
          <td><span class="badge badge-primary">${conf}</span></td>
          <td>${res.z_score}</td>
          <td class="text-right">${this.formatFinancialValue(res.price_move)} <span class="text-muted">(±${res.move_percentage}%)</span></td>
          <td class="text-right">${this.formatFinancialValue(res.support, { prefix: '$' })}</td>
          <td class="text-right">${this.formatFinancialValue(res.resistance, { prefix: '$' })}</td>
        </tr>
      `;
    });

    html += `
          </tbody>
        </table>
      </div>
    `;

    // Add visual indicator bar
    if (data.support_level && data.resistance_level && data.current_price) {
      const range = data.resistance_level - data.support_level;
      const position = ((data.current_price - data.support_level) / range) * 100;
      
      html += `
        <div class="sr-visual-indicator mt-4">
          <div class="sr-bar">
            <div class="sr-support" title="支持位: $${data.support_level.toFixed(2)}">
              <span class="sr-label">S</span>
            </div>
            <div class="sr-current" style="left: ${Math.min(100, Math.max(0, position))}%" title="當前價: $${data.current_price.toFixed(2)}">
              <span class="sr-marker"></span>
            </div>
            <div class="sr-resistance" title="阻力位: $${data.resistance_level.toFixed(2)}">
              <span class="sr-label">R</span>
            </div>
          </div>
          <div class="sr-values">
            <span class="value-positive">$${data.support_level.toFixed(2)}</span>
            <span class="value-current">$${data.current_price.toFixed(2)}</span>
            <span class="value-negative">$${data.resistance_level.toFixed(2)}</span>
          </div>
        </div>
      `;
    }

    container.innerHTML = html;
    this.renderedModules.add(moduleId);
  }

  // Track rendered modules
  getRenderedModulesCount() {
    return this.renderedModules.size;
  }

  isModuleRendered(moduleId) {
    return this.renderedModules.has(moduleId);
  }

  resetRenderedModules() {
    this.renderedModules.clear();
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { ModuleRenderer, MODULE_STATUS, MODULE_METADATA };
} else {
  window.ModuleRenderer = ModuleRenderer;
  window.MODULE_STATUS = MODULE_STATUS;
  window.MODULE_METADATA = MODULE_METADATA;
}


// Continue ModuleRenderer class with more module rendering methods
ModuleRenderer.prototype.renderModule2 = function(data, container) {
  const status = this.getModuleStatus(data);
  const moduleId = 2;
  
  if (status === MODULE_STATUS.ERROR) {
    container.innerHTML = this.createErrorMessage(data?.error);
    return;
  }
  
  if (status === MODULE_STATUS.SKIPPED) {
    container.innerHTML = this.createSkippedMessage(data?.reason);
    return;
  }
  
  if (status === MODULE_STATUS.NO_DATA || !data?.fair_value) {
    container.innerHTML = this.createNoDataMessage(data?.reason, moduleId);
    return;
  }

  container.innerHTML = `
    <div class="module-metrics-grid">
      <div class="module-metric">
        <div class="metric-label">公允值</div>
        <div class="metric-value">${this.formatFinancialValue(data.fair_value, { prefix: '$' })}</div>
      </div>
      <div class="module-metric">
        <div class="metric-label">無風險利率</div>
        <div class="metric-value">${this.formatFinancialValue(data.risk_free_rate * 100, { suffix: '%' })}</div>
      </div>
      <div class="module-metric">
        <div class="metric-label">預期股息</div>
        <div class="metric-value">${this.formatFinancialValue(data.expected_dividend, { prefix: '$' })}</div>
      </div>
    </div>
  `;
  this.renderedModules.add(moduleId);
};

// Module 3: Arbitrage Spread
ModuleRenderer.prototype.renderModule3 = function(data, container) {
  const status = this.getModuleStatus(data);
  const moduleId = 3;
  
  if (status === MODULE_STATUS.ERROR) {
    container.innerHTML = this.createErrorMessage(data?.error);
    return;
  }
  
  if (status === MODULE_STATUS.SKIPPED) {
    container.innerHTML = this.createSkippedMessage(data?.reason);
    return;
  }
  
  if (status === MODULE_STATUS.NO_DATA || data?.arbitrage_spread === undefined) {
    container.innerHTML = this.createNoDataMessage(data?.reason, moduleId);
    return;
  }

  const isArb = data.arbitrage_spread > 0;
  const arbClass = isArb ? 'value-positive' : 'value-neutral';
  
  container.innerHTML = `
    <div class="gauge-container">
      <div class="gauge-circle">
        <svg viewBox="0 0 100 100" width="120" height="120">
          <circle class="gauge-bg" cx="50" cy="50" r="45"></circle>
          <circle class="gauge-fill" cx="50" cy="50" r="45" 
                  stroke-dasharray="${Math.min(100, Math.abs(data.spread_percentage || 0)) * 2.83} 283"
                  style="stroke: ${isArb ? 'var(--color-success)' : 'var(--color-text-tertiary)'}"></circle>
        </svg>
        <div class="gauge-value ${arbClass}">${this.formatFinancialValue(data.arbitrage_spread)}</div>
      </div>
      <div class="gauge-label">價差 (${data.spread_percentage?.toFixed(2) || 0}%)</div>
    </div>
    <div class="mt-4">
      <p class="text-sm"><strong>建議:</strong> ${data.recommendation || 'N/A'}</p>
      <p class="text-xs text-muted">理論價: ${this.formatFinancialValue(data.theoretical_price, { prefix: '$' })} vs 市場價: ${this.formatFinancialValue(data.market_price, { prefix: '$' })}</p>
      ${data.note ? `<p class="text-xs text-info mt-2">${data.note}</p>` : ''}
    </div>
  `;
  this.renderedModules.add(moduleId);
};

// Module 4: PE Valuation
ModuleRenderer.prototype.renderModule4 = function(data, container) {
  const status = this.getModuleStatus(data);
  const moduleId = 4;
  
  if (status === MODULE_STATUS.ERROR) {
    container.innerHTML = this.createErrorMessage(data?.error);
    return;
  }
  
  if (status === MODULE_STATUS.SKIPPED) {
    container.innerHTML = this.createSkippedMessage(data?.reason);
    return;
  }
  
  if (status === MODULE_STATUS.NO_DATA || !data?.pe_multiple) {
    container.innerHTML = this.createNoDataMessage(data?.reason, moduleId);
    return;
  }

  container.innerHTML = `
    <div class="module-metrics-grid">
      <div class="module-metric">
        <div class="metric-label">當前 PE</div>
        <div class="metric-value">${data.pe_multiple?.toFixed(2) || 'N/A'}</div>
      </div>
      <div class="module-metric">
        <div class="metric-label">EPS</div>
        <div class="metric-value">${this.formatFinancialValue(data.eps, { prefix: '$' })}</div>
      </div>
      <div class="module-metric">
        <div class="metric-label">PEG</div>
        <div class="metric-value">${data.peg_ratio?.toFixed(2) || 'N/A'}</div>
      </div>
    </div>
    ${data.peg_valuation ? `<p class="text-sm text-muted mt-3">${data.peg_valuation}</p>` : ''}
  `;
  this.renderedModules.add(moduleId);
};

// Module 5: Rate PE Relation
ModuleRenderer.prototype.renderModule5 = function(data, container) {
  const status = this.getModuleStatus(data);
  const moduleId = 5;
  
  if (status === MODULE_STATUS.ERROR) {
    container.innerHTML = this.createErrorMessage(data?.error);
    return;
  }
  
  if (status === MODULE_STATUS.SKIPPED) {
    container.innerHTML = this.createSkippedMessage(data?.reason);
    return;
  }
  
  if (status === MODULE_STATUS.NO_DATA || !data?.reasonable_pe) {
    container.innerHTML = this.createNoDataMessage(data?.reason, moduleId);
    return;
  }

  container.innerHTML = `
    <div class="module-metrics-grid">
      <div class="module-metric">
        <div class="metric-label">利率基準 PE</div>
        <div class="metric-value">${data.reasonable_pe?.toFixed(2) || 'N/A'}</div>
      </div>
      <div class="module-metric">
        <div class="metric-label">行業 PE 範圍</div>
        <div class="metric-value text-sm">${data['行業PE範圍'] || 'N/A'}</div>
      </div>
    </div>
    ${data['行業比較'] ? `<p class="text-sm text-info mt-3">${data['行業比較']}</p>` : ''}
  `;
  this.renderedModules.add(moduleId);
};

// Module 6: Hedge Quantity
ModuleRenderer.prototype.renderModule6 = function(data, container) {
  const status = this.getModuleStatus(data);
  const moduleId = 6;
  
  if (status === MODULE_STATUS.ERROR) {
    container.innerHTML = this.createErrorMessage(data?.error);
    return;
  }
  
  if (status === MODULE_STATUS.SKIPPED) {
    container.innerHTML = this.createSkippedMessage(data?.reason);
    return;
  }
  
  if (status === MODULE_STATUS.NO_DATA || !data?.hedge_contracts) {
    container.innerHTML = this.createNoDataMessage(data?.reason, moduleId);
    return;
  }

  container.innerHTML = `
    <div class="module-metrics-grid">
      <div class="module-metric">
        <div class="metric-label">正股數量</div>
        <div class="metric-value">${data.stock_quantity || 0}</div>
      </div>
      <div class="module-metric">
        <div class="metric-label">持倉市值</div>
        <div class="metric-value">${this.formatFinancialValue(data.portfolio_value, { prefix: '$' })}</div>
      </div>
    </div>
    <div class="alert alert-info mt-4 text-center">
      需 <strong>${data.hedge_contracts}</strong> 張 Put 合約對沖
      <div class="text-sm mt-1">覆蓋率: ${data.coverage_percentage?.toFixed(1) || 0}%</div>
    </div>
  `;
  this.renderedModules.add(moduleId);
};

// Modules 7-10: Strategy P&L
ModuleRenderer.prototype.renderStrategyPnL = function(longCall, longPut, shortCall, shortPut, container) {
  const moduleIds = [7, 8, 9, 10];
  
  if (!longCall?.length && !longPut?.length && !shortCall?.length && !shortPut?.length) {
    container.innerHTML = this.createNoDataMessage('需選擇行使價以計算策略損益', 7);
    return;
  }

  let html = `
    <div class="table-container">
      <table class="table-modern table-striped">
        <thead>
          <tr>
            <th>股價場景</th>
            <th class="text-right">Long Call</th>
            <th class="text-right">Long Put</th>
            <th class="text-right">Short Call</th>
            <th class="text-right">Short Put</th>
          </tr>
        </thead>
        <tbody>
  `;

  const scenarios = Math.max(
    longCall?.length || 0,
    longPut?.length || 0,
    shortCall?.length || 0,
    shortPut?.length || 0
  );

  for (let i = 0; i < scenarios; i++) {
    const price = longCall?.[i]?.stock_price_at_expiry || 
                  longPut?.[i]?.stock_price_at_expiry || 
                  shortCall?.[i]?.stock_price_at_expiry || 
                  shortPut?.[i]?.stock_price_at_expiry || 0;
    
    html += `
      <tr>
        <td>${this.formatFinancialValue(price, { prefix: '$' })}</td>
        <td class="text-right">${this.formatFinancialValue(longCall?.[i]?.profit_loss, { showSign: true })}</td>
        <td class="text-right">${this.formatFinancialValue(longPut?.[i]?.profit_loss, { showSign: true })}</td>
        <td class="text-right">${this.formatFinancialValue(shortCall?.[i]?.profit_loss, { showSign: true })}</td>
        <td class="text-right">${this.formatFinancialValue(shortPut?.[i]?.profit_loss, { showSign: true })}</td>
      </tr>
    `;
  }

  html += `
        </tbody>
      </table>
    </div>
    <p class="text-xs text-muted mt-2">* 基於當前選擇的行使價與期權價格計算</p>
  `;

  container.innerHTML = html;
  moduleIds.forEach(id => this.renderedModules.add(id));
};

// Module 11: Synthetic Stock
ModuleRenderer.prototype.renderModule11 = function(data, container) {
  const status = this.getModuleStatus(data);
  const moduleId = 11;
  
  if (status === MODULE_STATUS.ERROR) {
    container.innerHTML = this.createErrorMessage(data?.error);
    return;
  }
  
  if (status === MODULE_STATUS.SKIPPED) {
    container.innerHTML = this.createSkippedMessage(data?.reason);
    return;
  }
  
  if (status === MODULE_STATUS.NO_DATA || !data?.synthetic_price) {
    container.innerHTML = this.createNoDataMessage(data?.reason, moduleId);
    return;
  }

  const isArb = data.arbitrage_opportunity;
  
  container.innerHTML = `
    <div class="module-metrics-grid">
      <div class="module-metric">
        <div class="metric-label">合成價格</div>
        <div class="metric-value">${this.formatFinancialValue(data.synthetic_price, { prefix: '$' })}</div>
      </div>
      <div class="module-metric">
        <div class="metric-label">實際股價</div>
        <div class="metric-value">${this.formatFinancialValue(data.current_stock_price, { prefix: '$' })}</div>
      </div>
      <div class="module-metric">
        <div class="metric-label">價差</div>
        <div class="metric-value ${isArb ? 'value-positive' : ''}">${this.formatFinancialValue(data.difference, { prefix: '$' })}</div>
      </div>
    </div>
    <div class="text-sm text-muted mt-3 border-t pt-3">
      <strong>策略:</strong> ${data.strategy || 'N/A'}
    </div>
  `;
  this.renderedModules.add(moduleId);
};

// Module 12: Annual Yield
ModuleRenderer.prototype.renderModule12 = function(data, container) {
  const status = this.getModuleStatus(data);
  const moduleId = 12;
  
  if (status === MODULE_STATUS.ERROR) {
    container.innerHTML = this.createErrorMessage(data?.error);
    return;
  }
  
  if (status === MODULE_STATUS.SKIPPED) {
    container.innerHTML = this.createSkippedMessage(data?.reason);
    return;
  }
  
  if (status === MODULE_STATUS.NO_DATA || !data?.annual_yield) {
    container.innerHTML = this.createNoDataMessage(data?.reason, moduleId);
    return;
  }

  container.innerHTML = `
    <div class="gauge-container">
      <div class="gauge-circle">
        <svg viewBox="0 0 100 100" width="120" height="120">
          <circle class="gauge-bg" cx="50" cy="50" r="45"></circle>
          <circle class="gauge-fill" cx="50" cy="50" r="45" 
                  stroke-dasharray="${Math.min(100, data.annual_yield) * 2.83} 283"
                  style="stroke: var(--color-success)"></circle>
        </svg>
        <div class="gauge-value value-positive">${data.annual_yield?.toFixed(2)}%</div>
      </div>
      <div class="gauge-label">總年化收益率</div>
    </div>
    <div class="module-metrics-grid mt-4">
      <div class="module-metric">
        <div class="metric-label">派息收益</div>
        <div class="metric-value">${data.dividend_yield?.toFixed(2) || 0}%</div>
      </div>
      <div class="module-metric">
        <div class="metric-label">期權收益</div>
        <div class="metric-value">${data.option_yield?.toFixed(2) || 0}%</div>
      </div>
    </div>
  `;
  this.renderedModules.add(moduleId);
};


// Module 13: Position Analysis
ModuleRenderer.prototype.renderModule13 = function(data, container) {
  const status = this.getModuleStatus(data);
  const moduleId = 13;
  
  if (status === MODULE_STATUS.ERROR) {
    container.innerHTML = this.createErrorMessage(data?.error);
    return;
  }
  
  if (status === MODULE_STATUS.SKIPPED) {
    container.innerHTML = this.createSkippedMessage(data?.reason);
    return;
  }
  
  if (status === MODULE_STATUS.NO_DATA || (!data?.volume && !data?.open_interest)) {
    container.innerHTML = this.createNoDataMessage(data?.reason, moduleId);
    return;
  }

  const volOiRatio = data.open_interest > 0 ? (data.volume / data.open_interest) * 100 : 0;
  
  container.innerHTML = `
    <div class="mb-4">
      <div class="text-xs text-muted mb-1">成交量/持倉量</div>
      <div class="progress-bar-container">
        <div class="progress-bar-fill" style="width: ${Math.min(100, volOiRatio)}%; background: var(--color-primary)"></div>
      </div>
      <div class="d-flex justify-between text-xs mt-1">
        <span>Vol: ${data.volume?.toLocaleString() || 0}</span>
        <span>OI: ${data.open_interest?.toLocaleString() || 0}</span>
      </div>
    </div>
    <div class="text-sm border-t pt-3">
      <div class="d-flex justify-between mb-2">
        <span>機構持股:</span>
        <span class="fw-bold">${data.institutional_ownership || 0}%</span>
      </div>
      <div class="d-flex justify-between mb-2">
        <span>內部人持股:</span>
        <span class="fw-bold">${data.insider_ownership || 0}%</span>
      </div>
      <div class="d-flex justify-between">
        <span>做空比例:</span>
        <span class="fw-bold">${data.short_float || 0}%</span>
      </div>
    </div>
  `;
  this.renderedModules.add(moduleId);
};

// Module 14: Monitoring Posts
ModuleRenderer.prototype.renderModule14 = function(data, container) {
  const status = this.getModuleStatus(data);
  const moduleId = 14;
  
  if (status === MODULE_STATUS.ERROR) {
    container.innerHTML = this.createErrorMessage(data?.error);
    return;
  }
  
  if (status === MODULE_STATUS.SKIPPED) {
    container.innerHTML = this.createSkippedMessage(data?.reason);
    return;
  }
  
  if (status === MODULE_STATUS.NO_DATA || !data?.post_details) {
    container.innerHTML = this.createNoDataMessage(data?.reason, moduleId);
    return;
  }

  let html = '<div class="monitoring-grid">';
  
  Object.entries(data.post_details).forEach(([key, post]) => {
    const isPass = post.status?.includes('正常');
    const isFail = post.status?.includes('警報');
    const statusClass = isPass ? 'status-pass' : (isFail ? 'status-fail' : 'status-warning');
    const icon = isPass ? 'fa-check-circle' : (isFail ? 'fa-exclamation-triangle' : 'fa-info-circle');
    
    html += `
      <div class="monitoring-item ${statusClass}">
        <div class="monitoring-header">
          <i class="fas ${icon} monitoring-icon"></i>
          <span class="monitoring-name">${post.name}</span>
        </div>
        <div class="monitoring-values">
          <span>當前: ${typeof post.value === 'number' ? post.value.toFixed(2) : (post.value || 'N/A')}</span>
          <span>標準: ${post.threshold || 'N/A'}</span>
        </div>
      </div>
    `;
  });
  
  html += '</div>';
  container.innerHTML = html;
  this.renderedModules.add(moduleId);
};

// Modules 15 & 16: Black-Scholes and Greeks
ModuleRenderer.prototype.renderModule15_16 = function(bsData, greeksData, container) {
  const moduleIds = [15, 16];
  
  if (!bsData && !greeksData) {
    container.innerHTML = this.createNoDataMessage('需要期權定價數據', 15);
    return;
  }

  let html = '<div class="greeks-container">';
  
  // Call Panel
  html += `
    <div class="greeks-panel call-panel">
      <div class="greeks-title text-success">Call Option</div>
      <div class="greeks-price">
        <div class="price-label">理論價</div>
        <div class="price-value">${this.formatFinancialValue(bsData?.call?.option_price, { prefix: '$' })}</div>
      </div>
      <div class="greeks-values">
        <div class="greek-row"><span class="greek-name">Delta</span><span class="greek-value">${greeksData?.call?.delta?.toFixed(4) || 'N/A'}</span></div>
        <div class="greek-row"><span class="greek-name">Gamma</span><span class="greek-value">${greeksData?.call?.gamma?.toFixed(4) || 'N/A'}</span></div>
        <div class="greek-row"><span class="greek-name">Theta</span><span class="greek-value">${greeksData?.call?.theta?.toFixed(4) || 'N/A'}</span></div>
        <div class="greek-row"><span class="greek-name">Vega</span><span class="greek-value">${greeksData?.call?.vega?.toFixed(4) || 'N/A'}</span></div>
        <div class="greek-row"><span class="greek-name">Rho</span><span class="greek-value">${greeksData?.call?.rho?.toFixed(4) || 'N/A'}</span></div>
      </div>
    </div>
  `;
  
  // Put Panel
  html += `
    <div class="greeks-panel put-panel">
      <div class="greeks-title text-danger">Put Option</div>
      <div class="greeks-price">
        <div class="price-label">理論價</div>
        <div class="price-value">${this.formatFinancialValue(bsData?.put?.option_price, { prefix: '$' })}</div>
      </div>
      <div class="greeks-values">
        <div class="greek-row"><span class="greek-name">Delta</span><span class="greek-value">${greeksData?.put?.delta?.toFixed(4) || 'N/A'}</span></div>
        <div class="greek-row"><span class="greek-name">Gamma</span><span class="greek-value">${greeksData?.put?.gamma?.toFixed(4) || 'N/A'}</span></div>
        <div class="greek-row"><span class="greek-name">Theta</span><span class="greek-value">${greeksData?.put?.theta?.toFixed(4) || 'N/A'}</span></div>
        <div class="greek-row"><span class="greek-name">Vega</span><span class="greek-value">${greeksData?.put?.vega?.toFixed(4) || 'N/A'}</span></div>
        <div class="greek-row"><span class="greek-name">Rho</span><span class="greek-value">${greeksData?.put?.rho?.toFixed(4) || 'N/A'}</span></div>
      </div>
    </div>
  `;
  
  html += '</div>';
  container.innerHTML = html;
  moduleIds.forEach(id => this.renderedModules.add(id));
};

// Module 18: Historical Volatility
ModuleRenderer.prototype.renderModule18 = function(data, container) {
  const status = this.getModuleStatus(data);
  const moduleId = 18;
  
  if (status === MODULE_STATUS.ERROR) {
    container.innerHTML = this.createErrorMessage(data?.error);
    return;
  }
  
  if (status === MODULE_STATUS.SKIPPED) {
    container.innerHTML = this.createSkippedMessage(data?.reason);
    return;
  }
  
  if (status === MODULE_STATUS.NO_DATA || !data?.hv_results) {
    container.innerHTML = this.createNoDataMessage(data?.reason, moduleId);
    return;
  }

  let html = `
    <div class="table-container">
      <table class="table-modern">
        <tbody>
  `;
  
  Object.entries(data.hv_results).forEach(([window, res]) => {
    html += `
      <tr>
        <td>${window}日 HV</td>
        <td class="text-right fw-bold">${(res.historical_volatility * 100).toFixed(2)}%</td>
      </tr>
    `;
  });
  
  html += '</tbody></table></div>';
  
  if (data.iv_hv_comparison) {
    const ratio = data.iv_hv_comparison.iv_hv_ratio;
    const colorClass = ratio > 1.2 ? 'value-negative' : (ratio < 0.8 ? 'value-positive' : 'value-neutral');
    html += `
      <div class="text-center mt-4 pt-3 border-t">
        <div class="text-xs text-muted">IV / HV (30日) 比率</div>
        <div class="text-xl fw-bold ${colorClass}">${ratio?.toFixed(2) || 'N/A'}</div>
        <div class="text-xs text-muted">${data.iv_hv_comparison.assessment || ''}</div>
      </div>
    `;
  }
  
  container.innerHTML = html;
  this.renderedModules.add(moduleId);
};

// Module 19: Put-Call Parity
ModuleRenderer.prototype.renderModule19 = function(data, container) {
  const status = this.getModuleStatus(data);
  const moduleId = 19;
  
  if (status === MODULE_STATUS.ERROR) {
    container.innerHTML = this.createErrorMessage(data?.error);
    return;
  }
  
  if (status === MODULE_STATUS.SKIPPED) {
    container.innerHTML = this.createSkippedMessage(data?.reason);
    return;
  }
  
  if (status === MODULE_STATUS.NO_DATA || !data?.market_prices) {
    container.innerHTML = this.createNoDataMessage(data?.reason, moduleId);
    return;
  }

  const mp = data.market_prices;
  const isArb = mp.arbitrage_opportunity;
  const colorClass = isArb ? 'value-negative' : 'value-positive';
  
  container.innerHTML = `
    <div class="d-flex justify-between mb-2">
      <span>偏離度:</span>
      <span class="${colorClass} fw-bold">${mp.deviation?.toFixed(2) || 'N/A'}</span>
    </div>
    <div class="progress-bar-container mb-3">
      <div class="progress-bar-fill" style="width: ${Math.min(100, Math.abs(mp.deviation_percentage || 0))}%; background: ${isArb ? 'var(--color-danger)' : 'var(--color-success)'}"></div>
    </div>
    <div class="text-sm text-muted">${mp.strategy || ''}</div>
  `;
  this.renderedModules.add(moduleId);
};

// Module 20: Fundamental Health
ModuleRenderer.prototype.renderModule20 = function(data, container) {
  const status = this.getModuleStatus(data);
  const moduleId = 20;
  
  if (status === MODULE_STATUS.ERROR) {
    container.innerHTML = this.createErrorMessage(data?.error);
    return;
  }
  
  if (status === MODULE_STATUS.SKIPPED) {
    container.innerHTML = this.createSkippedMessage(data?.reason);
    return;
  }
  
  if (status === MODULE_STATUS.NO_DATA || !data?.metrics) {
    container.innerHTML = this.createNoDataMessage(data?.reason, moduleId);
    return;
  }

  let html = '';
  
  Object.entries(data.metrics).forEach(([key, m]) => {
    const scoreColor = m.score >= 8 ? 'value-positive' : (m.score >= 5 ? 'value-neutral' : 'value-negative');
    html += `
      <div class="d-flex justify-between align-center mb-2 pb-2 border-b">
        <span>${key}</span>
        <div class="text-right">
          <div class="fw-bold">${m.value !== null ? m.value : 'N/A'}</div>
          <small class="${scoreColor}">評分: ${m.score}/10</small>
        </div>
      </div>
    `;
  });
  
  container.innerHTML = html;
  this.renderedModules.add(moduleId);
};

// Module 21: Momentum Filter
ModuleRenderer.prototype.renderModule21 = function(data, container) {
  const status = this.getModuleStatus(data);
  const moduleId = 21;
  
  if (status === MODULE_STATUS.ERROR) {
    container.innerHTML = this.createErrorMessage(data?.error);
    return;
  }
  
  if (status === MODULE_STATUS.SKIPPED) {
    container.innerHTML = this.createSkippedMessage(data?.reason);
    return;
  }
  
  if (status === MODULE_STATUS.NO_DATA || data?.momentum_score === undefined) {
    container.innerHTML = this.createNoDataMessage(data?.reason, moduleId);
    return;
  }

  const score = data.momentum_score || 0.5;
  const scoreColor = score >= 0.7 ? 'value-positive' : (score <= 0.3 ? 'value-negative' : 'value-neutral');
  const direction = score >= 0.7 ? '強勢上漲' : (score <= 0.3 ? '弱勢下跌' : '中性震盪');
  
  container.innerHTML = `
    <div class="gauge-container">
      <div class="gauge-circle">
        <svg viewBox="0 0 100 100" width="120" height="120">
          <circle class="gauge-bg" cx="50" cy="50" r="45"></circle>
          <circle class="gauge-fill" cx="50" cy="50" r="45" 
                  stroke-dasharray="${score * 283} 283"
                  style="stroke: ${score >= 0.7 ? 'var(--color-success)' : (score <= 0.3 ? 'var(--color-danger)' : 'var(--color-warning)')}"></circle>
        </svg>
        <div class="gauge-value ${scoreColor}">${(score * 100).toFixed(0)}%</div>
      </div>
      <div class="gauge-label">動量得分</div>
    </div>
    <div class="d-flex justify-between mt-4">
      <span>趨勢方向:</span>
      <span class="${scoreColor} fw-bold">${direction}</span>
    </div>
    ${data.recommendation ? `<div class="alert alert-${score >= 0.7 ? 'success' : (score <= 0.3 ? 'danger' : 'warning')} mt-3 text-sm">${data.recommendation}</div>` : ''}
  `;
  this.renderedModules.add(moduleId);
};


// Module 22: Optimal Strike
ModuleRenderer.prototype.renderModule22 = function(data, container) {
  const status = this.getModuleStatus(data);
  const moduleId = 22;
  
  if (status === MODULE_STATUS.ERROR) {
    container.innerHTML = this.createErrorMessage(data?.error);
    return;
  }
  
  if (status === MODULE_STATUS.SKIPPED) {
    container.innerHTML = this.createSkippedMessage(data?.reason);
    return;
  }
  
  if (status === MODULE_STATUS.NO_DATA) {
    container.innerHTML = this.createNoDataMessage(data?.reason, moduleId);
    return;
  }

  const strategies = ['long_call', 'long_put', 'short_call', 'short_put'];
  const strategyNames = {'long_call': 'Long Call', 'long_put': 'Long Put', 'short_call': 'Short Call', 'short_put': 'Short Put'};
  const strategyClasses = {'long_call': 'strategy-long-call', 'long_put': 'strategy-long-put', 'short_call': 'strategy-short-call', 'short_put': 'strategy-short-put'};
  
  let html = '<div class="strategy-card-grid">';
  
  strategies.forEach(strategy => {
    const stratData = data[strategy];
    if (stratData && stratData.optimal_strike) {
      html += `
        <div class="strategy-card ${strategyClasses[strategy]}">
          <div class="strategy-header">
            <span class="strategy-name">${strategyNames[strategy]}</span>
            ${this.createGradeBadge(stratData.grade)}
          </div>
          <div class="strategy-value">${this.formatFinancialValue(stratData.optimal_strike, { prefix: '$' })}</div>
          <div class="strategy-details">
            <div class="detail-row"><span>評分:</span><span>${stratData.score?.toFixed(1) || 'N/A'}</span></div>
            <div class="detail-row"><span>Delta:</span><span>${stratData.delta?.toFixed(3) || 'N/A'}</span></div>
            <div class="detail-row"><span>權利金:</span><span>${this.formatFinancialValue(stratData.premium, { prefix: '$' })}</span></div>
          </div>
        </div>
      `;
    }
  });
  
  html += '</div>';
  
  if (data.recommendation) {
    html += `<div class="alert alert-info mt-4"><i class="fas fa-lightbulb me-2"></i>${data.recommendation}</div>`;
  }
  
  container.innerHTML = html;
  this.renderedModules.add(moduleId);
};

// Module 23: Dynamic IV Threshold
ModuleRenderer.prototype.renderModule23 = function(data, container) {
  const status = this.getModuleStatus(data);
  const moduleId = 23;
  
  if (status === MODULE_STATUS.ERROR) {
    container.innerHTML = this.createErrorMessage(data?.error);
    return;
  }
  
  if (status === MODULE_STATUS.SKIPPED) {
    container.innerHTML = this.createSkippedMessage(data?.reason);
    return;
  }
  
  if (status === MODULE_STATUS.NO_DATA || data?.current_iv === undefined) {
    container.innerHTML = this.createNoDataMessage(data?.reason, moduleId);
    return;
  }

  const currentIV = data.current_iv || 0;
  const threshold = data.threshold || 0;
  const isHigh = currentIV > threshold;
  const colorClass = isHigh ? 'value-negative' : 'value-positive';
  
  container.innerHTML = `
    <div class="gauge-container">
      <div class="gauge-circle">
        <svg viewBox="0 0 100 100" width="120" height="120">
          <circle class="gauge-bg" cx="50" cy="50" r="45"></circle>
          <circle class="gauge-fill" cx="50" cy="50" r="45" 
                  stroke-dasharray="${Math.min(100, currentIV * 100) * 2.83} 283"
                  style="stroke: ${isHigh ? 'var(--color-danger)' : 'var(--color-success)'}"></circle>
        </svg>
        <div class="gauge-value ${colorClass}">${(currentIV * 100).toFixed(1)}%</div>
      </div>
      <div class="gauge-label">當前 IV</div>
    </div>
    <div class="module-metrics-grid mt-4">
      <div class="module-metric">
        <div class="metric-label">動態閾值</div>
        <div class="metric-value">${(threshold * 100).toFixed(1)}%</div>
      </div>
      <div class="module-metric">
        <div class="metric-label">IV Rank</div>
        <div class="metric-value">${data.iv_rank ? data.iv_rank.toFixed(1) + '%' : 'N/A'}</div>
      </div>
    </div>
    <div class="alert alert-${isHigh ? 'warning' : 'info'} mt-4 text-sm">
      ${isHigh ? '⚠️ IV 偏高，適合賣方策略' : '✓ IV 正常，可考慮買方策略'}
    </div>
  `;
  this.renderedModules.add(moduleId);
};

// Module 24: Technical Direction
ModuleRenderer.prototype.renderModule24 = function(data, container) {
  const status = this.getModuleStatus(data);
  const moduleId = 24;
  
  if (status === MODULE_STATUS.ERROR) {
    container.innerHTML = this.createErrorMessage(data?.error);
    return;
  }
  
  if (status === MODULE_STATUS.SKIPPED) {
    container.innerHTML = this.createSkippedMessage(data?.reason);
    return;
  }
  
  if (status === MODULE_STATUS.NO_DATA || !data?.combined_direction) {
    container.innerHTML = this.createNoDataMessage(data?.reason, moduleId);
    return;
  }

  const direction = data.combined_direction || 'Neutral';
  const confidence = data.confidence || 'Low';
  const dirColor = direction === 'Bullish' ? 'success' : (direction === 'Bearish' ? 'danger' : 'secondary');
  const confColor = confidence === 'High' ? 'success' : (confidence === 'Medium' ? 'warning' : 'secondary');
  
  let html = `
    <div class="text-center mb-4">
      <span class="badge badge-${dirColor} text-lg px-4 py-2">${direction}</span>
      <div class="mt-2">
        <span class="text-xs text-muted">信心度: </span>
        <span class="badge badge-${confColor}">${confidence}</span>
      </div>
    </div>
  `;
  
  if (data.daily_trend) {
    const dt = data.daily_trend;
    const trendColor = dt.trend === 'Bullish' ? 'value-positive' : (dt.trend === 'Bearish' ? 'value-negative' : 'value-neutral');
    html += `
      <div class="border-t pt-3">
        <h6 class="text-sm fw-bold mb-2">日線趨勢</h6>
        <div class="d-flex justify-between text-sm mb-1">
          <span>趨勢:</span>
          <span class="${trendColor}">${dt.trend}</span>
        </div>
        ${dt.ma_20 ? `<div class="d-flex justify-between text-sm mb-1"><span>MA20:</span><span>${dt.ma_20.toFixed(2)}</span></div>` : ''}
        ${dt.ma_50 ? `<div class="d-flex justify-between text-sm mb-1"><span>MA50:</span><span>${dt.ma_50.toFixed(2)}</span></div>` : ''}
      </div>
    `;
  }
  
  container.innerHTML = html;
  this.renderedModules.add(moduleId);
};

// Module 25: Volatility Smile
ModuleRenderer.prototype.renderModule25 = function(data, container) {
  const status = this.getModuleStatus(data);
  const moduleId = 25;
  
  if (status === MODULE_STATUS.ERROR) {
    container.innerHTML = this.createErrorMessage(data?.error);
    return;
  }
  
  if (status === MODULE_STATUS.SKIPPED) {
    container.innerHTML = this.createSkippedMessage(data?.reason);
    return;
  }
  
  if (status === MODULE_STATUS.NO_DATA || data?.atm_iv === undefined) {
    container.innerHTML = this.createNoDataMessage(data?.reason, moduleId);
    return;
  }

  const atmIV = data.atm_iv || 0;
  const skew = data.skew || 0;
  const skewType = data.skew_type || 'Normal';
  const ivEnv = data.iv_environment || 'Normal';
  
  const skewColor = skew > 0 ? 'value-negative' : 'value-positive';
  const skewTypeColor = skewType === 'Put Skew' ? 'danger' : (skewType === 'Call Skew' ? 'success' : 'secondary');
  const ivEnvColor = ivEnv === 'High' ? 'danger' : (ivEnv === 'Low' ? 'success' : 'warning');
  
  container.innerHTML = `
    <div class="text-center mb-4">
      <div class="text-3xl fw-bold">${(atmIV * 100).toFixed(1)}%</div>
      <div class="text-xs text-muted">ATM IV</div>
    </div>
    <div class="d-flex justify-between mb-2">
      <span>Skew:</span>
      <span class="${skewColor} fw-bold">${(skew * 100).toFixed(2)}%</span>
    </div>
    <div class="d-flex justify-between mb-2">
      <span>Skew 類型:</span>
      <span class="badge badge-${skewTypeColor}">${skewType}</span>
    </div>
    <div class="d-flex justify-between mb-2">
      <span>IV 環境:</span>
      <span class="badge badge-${ivEnvColor}">${ivEnv}</span>
    </div>
    ${data.anomaly_count > 0 ? `<div class="alert alert-warning mt-3 text-sm"><i class="fas fa-exclamation-triangle me-1"></i>發現 ${data.anomaly_count} 個定價異常</div>` : ''}
  `;
  this.renderedModules.add(moduleId);
};

// Module 26: Long Option Analysis
ModuleRenderer.prototype.renderModule26 = function(data, container) {
  const status = this.getModuleStatus(data);
  const moduleId = 26;
  
  if (status === MODULE_STATUS.ERROR) {
    container.innerHTML = this.createErrorMessage(data?.error);
    return;
  }
  
  if (status === MODULE_STATUS.SKIPPED) {
    container.innerHTML = this.createSkippedMessage(data?.reason);
    return;
  }
  
  if (status === MODULE_STATUS.NO_DATA || (!data?.long_call && !data?.long_put)) {
    container.innerHTML = this.createNoDataMessage(data?.reason, moduleId);
    return;
  }

  let html = '<div class="strategy-card-grid">';
  
  if (data.long_call) {
    const lc = data.long_call;
    const score = lc.score || {};
    html += `
      <div class="strategy-card strategy-long-call">
        <div class="strategy-header">
          <span class="strategy-name">Long Call</span>
          ${this.createGradeBadge(score.grade)}
        </div>
        <div class="strategy-value">${score.total_score || 'N/A'}</div>
        <div class="strategy-details">
          <div class="detail-row"><span>行使價:</span><span>${this.formatFinancialValue(lc.strike, { prefix: '$' })}</span></div>
          <div class="detail-row"><span>權利金:</span><span>${this.formatFinancialValue(lc.premium, { prefix: '$' })}</span></div>
          <div class="detail-row"><span>槓桿:</span><span>${lc.leverage?.toFixed(1) || 'N/A'}x</span></div>
        </div>
      </div>
    `;
  }
  
  if (data.long_put) {
    const lp = data.long_put;
    const score = lp.score || {};
    html += `
      <div class="strategy-card strategy-long-put">
        <div class="strategy-header">
          <span class="strategy-name">Long Put</span>
          ${this.createGradeBadge(score.grade)}
        </div>
        <div class="strategy-value">${score.total_score || 'N/A'}</div>
        <div class="strategy-details">
          <div class="detail-row"><span>行使價:</span><span>${this.formatFinancialValue(lp.strike, { prefix: '$' })}</span></div>
          <div class="detail-row"><span>權利金:</span><span>${this.formatFinancialValue(lp.premium, { prefix: '$' })}</span></div>
          <div class="detail-row"><span>槓桿:</span><span>${lp.leverage?.toFixed(1) || 'N/A'}x</span></div>
        </div>
      </div>
    `;
  }
  
  html += '</div>';
  
  if (data.comparison) {
    html += `<div class="alert alert-info mt-4"><i class="fas fa-balance-scale me-2"></i><strong>推薦:</strong> ${data.comparison.better_choice || 'N/A'}</div>`;
  }
  
  container.innerHTML = html;
  this.renderedModules.add(moduleId);
};

// Module 27: Multi-Expiry Comparison
ModuleRenderer.prototype.renderModule27 = function(data, container) {
  const status = this.getModuleStatus(data);
  const moduleId = 27;
  
  if (status === MODULE_STATUS.ERROR) {
    container.innerHTML = this.createErrorMessage(data?.error);
    return;
  }
  
  if (status === MODULE_STATUS.SKIPPED) {
    container.innerHTML = this.createSkippedMessage(data?.reason);
    return;
  }
  
  if (status === MODULE_STATUS.NO_DATA || !data?.strategy_results) {
    container.innerHTML = this.createNoDataMessage(data?.reason, moduleId);
    return;
  }

  const strategyResults = data.strategy_results || {};
  const strategyNames = {'long_call': 'Long Call', 'long_put': 'Long Put', 'short_call': 'Short Call', 'short_put': 'Short Put'};
  const strategyClasses = {'long_call': 'strategy-long-call', 'long_put': 'strategy-long-put', 'short_call': 'strategy-short-call', 'short_put': 'strategy-short-put'};
  
  let html = `
    <div class="mb-3 d-flex justify-between align-center">
      <span class="text-sm text-muted">
        <i class="fas fa-calendar-check me-1"></i>
        分析了 <strong>${data.expirations_analyzed || 0}</strong> 個到期日
      </span>
    </div>
    <div class="strategy-card-grid">
  `;
  
  Object.entries(strategyResults).forEach(([strategy, result]) => {
    if (result && result.status === 'success') {
      const rec = result.recommendation || {};
      html += `
        <div class="strategy-card ${strategyClasses[strategy]}">
          <div class="strategy-header">
            <span class="strategy-name">${strategyNames[strategy]}</span>
            ${this.createGradeBadge(rec.best_grade)}
          </div>
          <div class="strategy-value">${rec.best_expiration || 'N/A'}</div>
          <div class="strategy-details">
            <div class="detail-row"><span>天數:</span><span>${rec.best_days || 0}</span></div>
            <div class="detail-row"><span>評分:</span><span>${rec.best_score || 'N/A'}</span></div>
            <div class="detail-row"><span>權利金:</span><span>${this.formatFinancialValue(rec.best_premium, { prefix: '$' })}</span></div>
          </div>
        </div>
      `;
    }
  });
  
  html += '</div>';
  
  // Comparison table
  const firstStrategy = Object.values(strategyResults).find(r => r && r.status === 'success');
  if (firstStrategy && firstStrategy.comparison_table && firstStrategy.comparison_table.length > 0) {
    html += `
      <div class="table-container mt-4">
        <table class="table-modern table-striped comparison-table">
          <thead>
            <tr>
              <th>到期日</th>
              <th class="text-right">天數</th>
              <th class="text-right">權利金</th>
              <th class="text-right">IV</th>
              <th class="text-right">Theta/日</th>
              <th class="text-right">評分</th>
            </tr>
          </thead>
          <tbody>
    `;
    
    firstStrategy.comparison_table.forEach((row, index) => {
      const isBest = index === 0;
      html += `
        <tr class="${isBest ? 'best-row' : ''}">
          <td><strong>${row.expiration || 'N/A'}</strong></td>
          <td class="text-right">${row.days || 0}</td>
          <td class="text-right">${this.formatFinancialValue(row.premium, { prefix: '$' })}</td>
          <td class="text-right">${row.iv?.toFixed(1) || 'N/A'}%</td>
          <td class="text-right ${row.theta_pct > 3 ? 'value-negative' : ''}">${row.theta_pct?.toFixed(2) || 'N/A'}%</td>
          <td class="text-right">${this.createGradeBadge(row.grade)} ${row.score || 0}</td>
        </tr>
      `;
    });
    
    html += '</tbody></table></div>';
  }
  
  container.innerHTML = html;
  this.renderedModules.add(moduleId);
};

// Module 28: Position Calculator
ModuleRenderer.prototype.renderModule28 = function(data, container) {
  const status = this.getModuleStatus(data);
  const moduleId = 28;
  
  if (status === MODULE_STATUS.ERROR) {
    container.innerHTML = this.createErrorMessage(data?.error);
    return;
  }
  
  if (status === MODULE_STATUS.SKIPPED) {
    container.innerHTML = this.createSkippedMessage(data?.reason);
    return;
  }
  
  if (status === MODULE_STATUS.NO_DATA || !data?.position_recommendation) {
    container.innerHTML = this.createNoDataMessage(data?.reason, moduleId);
    return;
  }

  const posRec = data.position_recommendation || {};
  const riskAna = data.risk_analysis || {};
  const capSum = data.capital_summary || {};
  
  const riskColor = riskAna.risk_rating === '低' ? 'success' : (riskAna.risk_rating === '高' ? 'danger' : 'warning');
  
  container.innerHTML = `
    <div class="gauge-container">
      <div class="gauge-circle">
        <svg viewBox="0 0 100 100" width="120" height="120">
          <circle class="gauge-bg" cx="50" cy="50" r="45"></circle>
        </svg>
        <div class="gauge-value text-primary">${posRec.recommended_contracts || 0}</div>
      </div>
      <div class="gauge-label">建議合約數量</div>
    </div>
    <div class="module-metrics-grid mt-4">
      <div class="module-metric">
        <div class="metric-label">總資金</div>
        <div class="metric-value text-sm">${capSum.currency || 'HKD'} ${(capSum.total_capital || 0).toLocaleString()}</div>
      </div>
      <div class="module-metric">
        <div class="metric-label">投入金額</div>
        <div class="metric-value">${this.formatFinancialValue(posRec.actual_investment_usd, { prefix: '$', decimals: 0 })}</div>
      </div>
    </div>
    <div class="d-flex justify-between mt-4 pt-3 border-t">
      <span>最大虧損:</span>
      <span class="value-negative fw-bold">${this.formatFinancialValue(riskAna.max_loss_usd, { prefix: '$', decimals: 0 })} (${riskAna.max_loss_pct || 0}%)</span>
    </div>
    <div class="d-flex justify-between mt-2">
      <span>風險評級:</span>
      <span class="badge badge-${riskColor}">${riskAna.risk_rating || 'N/A'}</span>
    </div>
  `;
  this.renderedModules.add(moduleId);
};

// Render all modules
ModuleRenderer.prototype.renderAllModules = function(calculations, containers) {
  this.resetRenderedModules();
  
  // Module 1
  if (containers.module1) {
    this.renderModule1(calculations.module1_support_resistance_multi || calculations.module1_support_resistance, containers.module1);
  }
  
  // Module 2
  if (containers.module2) {
    this.renderModule2(calculations.module2_fair_value, containers.module2);
  }
  
  // Module 3
  if (containers.module3) {
    this.renderModule3(calculations.module3_arbitrage_spread, containers.module3);
  }
  
  // Module 4
  if (containers.module4) {
    this.renderModule4(calculations.module4_pe_valuation, containers.module4);
  }
  
  // Module 5
  if (containers.module5) {
    this.renderModule5(calculations.module5_rate_pe_relation, containers.module5);
  }
  
  // Module 6
  if (containers.module6) {
    this.renderModule6(calculations.module6_hedge_quantity, containers.module6);
  }
  
  // Modules 7-10 (Strategy P&L)
  if (containers.strategyPnL) {
    this.renderStrategyPnL(
      calculations.module7_long_call,
      calculations.module8_long_put,
      calculations.module9_short_call,
      calculations.module10_short_put,
      containers.strategyPnL
    );
  }
  
  // Module 11
  if (containers.module11) {
    this.renderModule11(calculations.module11_synthetic_stock, containers.module11);
  }
  
  // Module 12
  if (containers.module12) {
    this.renderModule12(calculations.module12_annual_yield, containers.module12);
  }
  
  // Module 13
  if (containers.module13) {
    this.renderModule13(calculations.module13_position_analysis, containers.module13);
  }
  
  // Module 14
  if (containers.module14) {
    this.renderModule14(calculations.module14_monitoring_posts, containers.module14);
  }
  
  // Modules 15 & 16
  if (containers.module15_16) {
    this.renderModule15_16(calculations.module15_black_scholes, calculations.module16_greeks, containers.module15_16);
  }
  
  // Module 18
  if (containers.module18) {
    this.renderModule18(calculations.module18_historical_volatility, containers.module18);
  }
  
  // Module 19
  if (containers.module19) {
    this.renderModule19(calculations.module19_put_call_parity, containers.module19);
  }
  
  // Module 20
  if (containers.module20) {
    this.renderModule20(calculations.module20_fundamental_health, containers.module20);
  }
  
  // Module 21
  if (containers.module21) {
    this.renderModule21(calculations.module21_momentum_filter, containers.module21);
  }
  
  // Module 22
  if (containers.module22) {
    this.renderModule22(calculations.module22_optimal_strike, containers.module22);
  }
  
  // Module 23
  if (containers.module23) {
    this.renderModule23(calculations.module23_dynamic_iv_threshold, containers.module23);
  }
  
  // Module 24
  if (containers.module24) {
    this.renderModule24(calculations.module24_technical_direction, containers.module24);
  }
  
  // Module 25
  if (containers.module25) {
    this.renderModule25(calculations.module25_volatility_smile, containers.module25);
  }
  
  // Module 26
  if (containers.module26) {
    this.renderModule26(calculations.module26_long_option_analysis, containers.module26);
  }
  
  // Module 27
  if (containers.module27) {
    this.renderModule27(calculations.module27_multi_expiry_comparison, containers.module27);
  }
  
  // Module 28
  if (containers.module28) {
    this.renderModule28(calculations.module28_position_calculator, containers.module28);
  }
  
  return this.getRenderedModulesCount();
};
