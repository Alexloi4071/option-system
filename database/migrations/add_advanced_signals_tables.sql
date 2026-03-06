-- Migration: Add Advanced Data Utilization Signal Tables
-- Date: 2026-03-06
-- Description: Add tables for dark pool, large orders, liquidity, and short interest signals

-- Table: dark_pool_signals
CREATE TABLE IF NOT EXISTS dark_pool_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    dark_volume INTEGER NOT NULL,
    total_volume INTEGER NOT NULL,
    dark_pool_pct REAL NOT NULL,
    vwap REAL NOT NULL,
    price REAL NOT NULL,
    buy_sell_pressure TEXT NOT NULL,
    surge_detected INTEGER NOT NULL,
    surge_ratio REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dark_pool_ticker_timestamp 
ON dark_pool_signals(ticker, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_dark_pool_surge 
ON dark_pool_signals(surge_detected, timestamp DESC);

-- Table: large_order_signals
CREATE TABLE IF NOT EXISTS large_order_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    order_size INTEGER NOT NULL,
    order_value REAL NOT NULL,
    price REAL NOT NULL,
    consecutive_count INTEGER NOT NULL,
    institutional_footprint INTEGER NOT NULL,
    vwap_deviation REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_large_order_ticker_timestamp 
ON large_order_signals(ticker, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_large_order_institutional 
ON large_order_signals(institutional_footprint, timestamp DESC);

-- Table: liquidity_signals
CREATE TABLE IF NOT EXISTS liquidity_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    volume_3min INTEGER NOT NULL,
    volume_5min INTEGER NOT NULL,
    volume_10min INTEGER NOT NULL,
    acceleration_ratio REAL NOT NULL,
    breakout_confirmed INTEGER NOT NULL,
    exhaustion_signal INTEGER NOT NULL,
    avg_volume_baseline INTEGER NOT NULL,
    volume_monotonic INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_liquidity_ticker_timestamp 
ON liquidity_signals(ticker, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_liquidity_breakout 
ON liquidity_signals(breakout_confirmed, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_liquidity_exhaustion 
ON liquidity_signals(exhaustion_signal, timestamp DESC);

-- Table: short_interest_signals
CREATE TABLE IF NOT EXISTS short_interest_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    shortable_difficulty TEXT NOT NULL,
    shortable_shares INTEGER NOT NULL,
    difficulty_change TEXT NOT NULL,
    short_squeeze_potential INTEGER NOT NULL,
    squeeze_score REAL NOT NULL,
    price_trend TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_short_interest_ticker_timestamp 
ON short_interest_signals(ticker, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_short_interest_squeeze 
ON short_interest_signals(short_squeeze_potential, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_short_interest_score 
ON short_interest_signals(squeeze_score DESC, timestamp DESC);
