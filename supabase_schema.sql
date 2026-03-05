-- Supabase Database Schema for Options Trading System
-- Please run this script in the Supabase SQL Editor.

-- 1. iv_surface_history: 儲存各行使價與到期日的 IV，用以建立 IV Rank
CREATE TABLE IF NOT EXISTS iv_surface_history (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    record_date DATE NOT NULL,
    expiration_date DATE NOT NULL,
    strike_price NUMERIC(10, 2) NOT NULL,
    option_type VARCHAR(10) NOT NULL,
    implied_volatility NUMERIC(10, 6),
    delta NUMERIC(10, 6),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_iv_history_ticker_date ON iv_surface_history(ticker, record_date);

-- 2. module_run_log: 記錄各維度的評分結果
CREATE TABLE IF NOT EXISTS module_run_log (
    id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(50) NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    analysis_date DATE NOT NULL,
    module_name VARCHAR(100) NOT NULL,
    score NUMERIC(5, 2),
    signal VARCHAR(20),
    raw_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_module_log_ticker ON module_run_log(ticker, analysis_date);
CREATE INDEX IF NOT EXISTS idx_module_log_run_id ON module_run_log(run_id);

-- 3. ibkr_scanner_alerts: 掃描器的異動觸發記錄
CREATE TABLE IF NOT EXISTS ibkr_scanner_alerts (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    alert_time TIMESTAMP WITH TIME ZONE NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    message TEXT,
    data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_scanner_alerts_ticker ON ibkr_scanner_alerts(ticker, alert_time);

-- 4. trade_decisions: 記錄交易前與交易後的 PNL 狀態
CREATE TABLE IF NOT EXISTS trade_decisions (
    id BIGSERIAL PRIMARY KEY,
    decision_id VARCHAR(50) UNIQUE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    decision_time TIMESTAMP WITH TIME ZONE NOT NULL,
    strategy_name VARCHAR(100),
    action VARCHAR(20) NOT NULL,
    underlying_price NUMERIC(10, 2),
    option_details JSONB,
    ai_confidence_score NUMERIC(5, 2),
    ai_reasoning TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    realized_pnl NUMERIC(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trade_decisions_ticker ON trade_decisions(ticker);

-- Disable Row Level Security (RLS) to allow easy REST API access 
-- (If you want to secure it later, you can enable RLS and create policies)
ALTER TABLE iv_surface_history DISABLE ROW LEVEL SECURITY;
ALTER TABLE module_run_log DISABLE ROW LEVEL SECURITY;
ALTER TABLE ibkr_scanner_alerts DISABLE ROW LEVEL SECURITY;
ALTER TABLE trade_decisions DISABLE ROW LEVEL SECURITY;
