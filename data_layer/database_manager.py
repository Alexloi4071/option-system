# data_layer/database_manager.py
"""
Supabase PostgreSQL Connector
"""

import os
import logging
import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Supabase DB Manager using PostgREST API"""
    
    def __init__(self):
        load_dotenv()
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_KEY")
        
        self.is_configured = bool(self.supabase_url and self.supabase_key)
        
        if self.is_configured:
            # Clean up URL to ensure no trailing slash
            self.supabase_url = self.supabase_url.rstrip('/')
            self.headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            }
            logger.info("✓ Supabase REST API Configuration loaded")
        else:
            logger.warning("! Supabase credentials missing from environment. DatabaseManager disabled.")

    def _insert(self, table: str, data: dict) -> bool:
        """Helper to insert data into a Supabase table via REST"""
        if not self.is_configured:
            return False
            
        endpoint = f"{self.supabase_url}/rest/v1/{table}"
        
        try:
            response = requests.post(
                endpoint, 
                headers=self.headers, 
                json=data,
                timeout=5
            )
            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError as e:
            # Usually implies table doesn't exist or RLS is blocking
            if e.response.status_code == 404:
                logger.error(f"Table '{table}' not found. Please run the Supabase schema setup script.")
            else:
                logger.error(f"Supabase HTTPError ({e.response.status_code}) on {table}: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Failed to insert into {table}: {str(e)}")
            return False

    def insert_iv_history(self, ticker: str, record_date: str, expiration_date: str, 
                          strike_price: float, option_type: str, 
                          implied_volatility: float, delta: float = None) -> bool:
        """Insert IV surface record"""
        data = {
            "ticker": ticker,
            "record_date": record_date,
            "expiration_date": expiration_date,
            "strike_price": strike_price,
            "option_type": option_type,
            "implied_volatility": implied_volatility,
            "delta": delta
        }
        return self._insert("iv_surface_history", data)

    def insert_module_log(self, run_id: str, ticker: str, analysis_date: str, 
                          module_name: str, score: float = None, 
                          signal: str = None, raw_data: dict = None) -> bool:
        """Insert execution results from analysis modules"""
        data = {
            "run_id": run_id,
            "ticker": ticker,
            "analysis_date": analysis_date,
            "module_name": module_name,
            "score": score,
            "signal": signal,
            "raw_data": raw_data or {}
        }
        return self._insert("module_run_log", data)

    def insert_scanner_alert(self, ticker: str, alert_time: str, 
                             alert_type: str, message: str, data: dict = None) -> bool:
        """Insert an alert from the scanner"""
        payload = {
            "ticker": ticker,
            "alert_time": alert_time,
            "alert_type": alert_type,
            "message": message,
            "data": data or {}
        }
        return self._insert("ibkr_scanner_alerts", payload)

    def insert_trade_decision(self, decision_id: str, ticker: str, decision_time: str,
                              action: str, strategy_name: str = None, 
                              underlying_price: float = None, option_details: dict = None,
                              ai_confidence_score: float = None, ai_reasoning: str = None,
                              status: str = 'pending', realized_pnl: float = None) -> bool:
        """Insert a trade decision and its expected EV/PNL parameters"""
        payload = {
            "decision_id": decision_id,
            "ticker": ticker,
            "decision_time": decision_time,
            "strategy_name": strategy_name,
            "action": action,
            "underlying_price": underlying_price,
            "option_details": option_details or {},
            "ai_confidence_score": ai_confidence_score,
            "ai_reasoning": ai_reasoning,
            "status": status,
            "realized_pnl": realized_pnl
        }
        return self._insert("trade_decisions", payload)
