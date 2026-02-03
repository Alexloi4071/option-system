/**
 * Module Renderer - Glassmorphism UI for all 28 analysis modules
 */

const MODULE_STATUS = {
  SUCCESS: 'success',
  ERROR: 'error',
  SKIPPED: 'skipped',
  LOADING: 'loading',
  NO_DATA: 'no_data'
};

class ModuleRenderer {
  constructor() {
    this.renderedModules = new Set();
  }

  getModuleStatus(moduleData) {
    if (!moduleData) return MODULE_STATUS.NO_DATA;
    if (moduleData.status === 'error') return MODULE_STATUS.ERROR;
    if (moduleData.status === 'skipped') return MODULE_STATUS.SKIPPED;
    if (moduleData.status === 'success' || moduleData.status === undefined) {
      return MODULE_STATUS.SUCCESS;
    }
    return MODULE_STATUS.NO_DATA;
  }

  createStatusIndicator(status) {
    // Simplified for new UI - icons only
    const icons = {
      [MODULE_STATUS.SUCCESS]: 'fa-check text-neon-green',
      [MODULE_STATUS.ERROR]: 'fa-exclamation-triangle text-neon-red',
      [MODULE_STATUS.SKIPPED]: 'fa-minus text-muted',
      [MODULE_STATUS.LOADING]: 'fa-spinner fa-spin text-neon-blue',
      [MODULE_STATUS.NO_DATA]: 'fa-question text-muted'
    };
    return `<i class="fas ${icons[status] || icons[MODULE_STATUS.NO_DATA]}"></i>`;
  }

  createNoDataMessage(reason, moduleId) {
    return `
      <div class="text-center py-4 text-muted">
        <i class="fas fa-inbox fa-2x mb-2 opacity-50"></i>
        <p class="small mb-0">${reason || 'No Data Available'}</p>
      </div>`;
  }

  createErrorMessage(errorMessage) {
    return `
      <div class="text-center py-3 text-neon-red">
        <i class="fas fa-exclamation-circle mb-1"></i>
        <p class="small mb-0">${errorMessage || 'Module Error'}</p>
      </div>`;
  }

  createSkippedMessage(reason) {
    return `
      <div class="text-center py-3 text-muted">
        <small class="fst-italic opacity-75">${reason || 'Skipped'}</small>
      </div>`;
  }

  formatFinancialValue(value, options = {}) {
    const { prefix = '', suffix = '', decimals = 2, showSign = false } = options;
    
    if (value === null || value === undefined || isNaN(value)) {
      return '<span class="text-muted">---</span>';
    }

    const formattedValue = Number(value).toFixed(decimals);
    const sign = showSign && value > 0 ? '+' : '';
    
    let colorClass = 'text-white';
    if (value > 0) colorClass = 'text-neon-green';
    else if (value < 0) colorClass = 'text-neon-red';

    return `<span class="${colorClass}">${prefix}${sign}${formattedValue}${suffix}</span>`;
  }

  createGradeBadge(grade) {
    if (!grade) return '<span class="badge bg-secondary text-dark">N/A</span>';
    const numGrade = String(grade).toUpperCase();
    const colors = {
      'A': 'bg-success text-white',
      'B': 'bg-info text-dark',
      'C': 'bg-warning text-dark',
      'D': 'bg-danger text-white',
      'F': 'bg-danger text-white'
    };
    return `<span class="badge ${colors[numGrade] || 'bg-secondary'}">${numGrade}</span>`;
  }

  // --- RENDER FUNCTIONS ---
  // Wrapped in try-catch blocks for robustness

  renderModule1(data, container) {
    try {
      if (!data) throw new Error("No Data");
      
      const tbody = container.querySelector('tbody');
      if (!tbody) {
          // If container is just a div (legacy), create wrapper. 
          // But main.js should pass the right container.
          // Assuming main.js might need update, let's just use innerHTML on container if table doesn't exist
          // Actually, in new index.html, module 1 is explicit.
          // For Module 1, we pass the data object directly.
          if(data.results) {
              let rows = '';
              Object.entries(data.results).forEach(([conf, res]) => {
                  rows += `
                  <tr>
                      <td><span class="badge bg-primary bg-opacity-25 text-primary border border-primary">${conf}</span></td>
                      <td class="text-center text-secondary">${res.z_score}</td>
                      <td class="text-center text-muted">$${Number(res.support).toFixed(2)}</td>
                      <td class="text-center text-muted">$${Number(res.resistance).toFixed(2)}</td>
                  </tr>`;
              });
              // We rely on main.js to select the TABLE BODY if it exists, or we overwrite container
              if (container.tagName === 'TBODY') {
                  container.innerHTML = rows;
              } else {
                  // If passed full container, try to find table inside
                  const tableBody = container.querySelector('tbody');
                  if (tableBody) tableBody.innerHTML = rows;
                  else container.innerHTML = "Error: Table structure missing"; // Debug
              }
          }
      }
    } catch (e) {
      console.error("Render Module 1 Error", e);
      container.innerHTML = this.createErrorMessage(e.message);
    }
  }

  // Generic List Render for Fair Value (Module 2)
  renderModule2(data, container) {
    try {
      const status = this.getModuleStatus(data);
      if (status !== MODULE_STATUS.SUCCESS) {
          container.innerHTML = this.createNoDataMessage('No Data', 2);
          return;
      }

      container.innerHTML = `
        <div class="d-flex justify-content-between mb-2">
            <span class="text-muted">Fair Value</span>
            <span class="fw-bold text-neon-blue">$${Number(data.fair_value).toFixed(2)}</span>
        </div>
        <div class="d-flex justify-content-between mb-2">
            <span class="text-muted">Risk Free Rate</span>
            <span>${(Number(data.risk_free_rate)*100).toFixed(2)}%</span>
        </div>
        <div class="d-flex justify-content-between">
            <span class="text-muted">Exp. Dividend</span>
            <span>$${Number(data.expected_dividend).toFixed(2)}</span>
        </div>
      `;
    } catch (e) {
       container.innerHTML = this.createErrorMessage(e.message);
    }
  }

  // renderModule15_16 (Greeks) - Needs to fill specific divs
  renderModule15_16(bsData, greeksData, container) {
      // Container here is actually passed as 'module15_16' from main.js, 
      // but in my new HTML I have #callGreeks and #putGreeks separately.
      // So main.js needs to handle the split or I handle it here by finding selectors
      
      // Let's assume 'container' is a parent wrapper OR main.js calls this helper
      // Wait, main.js usually calls `renderModule15_16(..., container)`
      
      // I will update this method to expect just the data, and I'll find DOM elements internally 
      // OR I expect 'container' to be an object with {call: el, put: el}.
      // To be safe with existing main.js (which passes a single container usually), 
      // I should restart `main.js` refactoring next.
      
      // For now, let's generate generic HTML if a single container is passed.
      try {
          if (!bsData && !greeksData) throw new Error("No Greeks Data");

          // HELPER for Grid
          const renderGrid = (type) => {
              const g = greeksData?.[type] || {};
              const price = bsData?.[type]?.option_price;
              
              return `
                <div class="mb-3 text-center">
                    <span class="text-muted small">THEORETICAL PRICE</span>
                    <div class="h3 ${type==='call'?'text-neon-green':'text-neon-red'}">$${Number(price||0).toFixed(2)}</div>
                </div>
                <div class="row g-2 text-center small font-mono">
                    <div class="col-4 mb-2"><span class="d-block text-muted" style="font-size:0.7em">DELTA</span>${Number(g.delta||0).toFixed(3)}</div>
                    <div class="col-4 mb-2"><span class="d-block text-muted" style="font-size:0.7em">GAMMA</span>${Number(g.gamma||0).toFixed(3)}</div>
                    <div class="col-4 mb-2"><span class="d-block text-muted" style="font-size:0.7em">THETA</span>${Number(g.theta||0).toFixed(3)}</div>
                    <div class="col-6"><span class="d-block text-muted" style="font-size:0.7em">VEGA</span>${Number(g.vega||0).toFixed(3)}</div>
                    <div class="col-6"><span class="d-block text-muted" style="font-size:0.7em">RHO</span>${Number(g.rho||0).toFixed(3)}</div>
                </div>
              `;
          };

          // If container is a DOM element
          if (container instanceof HTMLElement) {
             // If this container contains our split logic (unlikely if passed from main.js as generic ID)
             // I'll check if it has children with IDs
             const callDiv = document.getElementById('callGreeks');
             const putDiv = document.getElementById('putGreeks');
             
             if (callDiv && putDiv) {
                 callDiv.innerHTML = renderGrid('call');
                 putDiv.innerHTML = renderGrid('put');
             } else {
                 // Fallback if main.js passes a container that blindly overwrites
                 container.innerHTML = `
                    <div class="row">
                        <div class="col-6 border-end border-secondary">${renderGrid('call')}</div>
                        <div class="col-6">${renderGrid('put')}</div>
                    </div>
                 `;
             }
          }
      } catch (e) {
          console.error("Greeks Render Error", e);
      }
  }

  // Strategy PnL (Module 7-10)
  renderStrategyPnL(lc, lp, sc, sp, container) {
      try {
        const scenarios = Math.max(lc?.length||0, lp?.length||0, sc?.length||0, sp?.length||0);
        if (scenarios === 0) {
            if (container.tagName !== 'TBODY') container.innerHTML = this.createNoDataMessage("Select Strike Price");
            return;
        }

        let html = '';
        for (let i=0; i<scenarios; i++) {
            const price = lc?.[i]?.stock_price_at_expiry || lp?.[i]?.stock_price_at_expiry || 0;
            // Helper to fmt
            const fmt = (val) => {
                if(val===undefined) return '-';
                const color = val > 0 ? 'text-neon-green' : (val < 0 ? 'text-neon-red' : 'text-muted');
                return `<span class="${color}">${val>0?'+':''}${Number(val).toFixed(2)}</span>`;
            };

            html += `
                <tr>
                    <td class="text-white">$${Number(price).toFixed(2)}</td>
                    <td>${fmt(lc?.[i]?.profit_loss)}</td>
                    <td>${fmt(lp?.[i]?.profit_loss)}</td>
                    <td>${fmt(sc?.[i]?.profit_loss)}</td>
                    <td>${fmt(sp?.[i]?.profit_loss)}</td>
                </tr>
            `;
        }
        
        const tbody = container.tagName === 'TBODY' ? container : container.querySelector('tbody');
        if (tbody) tbody.innerHTML = html;
        else container.innerHTML = "<table class='table table-dark'><tbody>"+html+"</tbody></table>"; // Fallback

      } catch (e) {
          console.error("PnL Render Error", e);
      }
  }
}

// Export
window.ModuleRenderer = ModuleRenderer;
