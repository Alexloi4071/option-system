import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

class SQLiteManager:
    """
    本機 SQLite 資料庫管理器
    用於記錄每一次掃描出的高分期權機會，方便未來回測與追蹤準確率。
    """
    
    def __init__(self, db_path: str = "scanner_results.db"):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """初始化資料庫與資料表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # 建立掃描結果歷史表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS scan_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        scan_time TIMESTAMP NOT NULL,
                        ticker TEXT NOT NULL,
                        profile TEXT,
                        strategy TEXT NOT NULL,
                        strike REAL,
                        expiry TEXT,
                        stock_price REAL,
                        premium REAL,
                        score REAL,
                        uoa_score REAL,
                        reasoning TEXT,
                        raw_json TEXT
                    )
                ''')
                
                # 建立索引以加速查詢
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_scan_time ON scan_history(scan_time)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_ticker ON scan_history(ticker)')
                
                conn.commit()
                logger.info(f"* SQLite 本地資料庫就緒 ({self.db_path})")
        except Exception as e:
            logger.error(f"x 初始化 SQLite 失敗: {e}")
            
    def insert_opportunity(self, opp: Dict):
        """插入單筆掃描機會"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                scan_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ticker = opp.get('ticker', '')
                profile = opp.get('profile', '')
                strategy = opp.get('strategy', '')
                strike = opp.get('strike', 0.0)
                expiry = opp.get('expiry', '')
                stock_price = opp.get('price', 0.0)
                premium = opp.get('premium', 0.0)
                score = opp.get('score', 0.0)
                uoa_score = opp.get('uoa_score', 0.0)
                reasoning = opp.get('reasoning', '')
                
                # 將完整分析結果轉為 JSON 字串備份
                raw_json = json.dumps(opp, default=str)
                
                cursor.execute('''
                    INSERT INTO scan_history (
                        scan_time, ticker, profile, strategy, strike, expiry, 
                        stock_price, premium, score, uoa_score, reasoning, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    scan_time, ticker, profile, strategy, strike, expiry,
                    stock_price, premium, score, uoa_score, reasoning, raw_json
                ))
                
                conn.commit()
        except Exception as e:
            logger.error(f"x SQLite 寫入失敗 ({opp.get('ticker')}): {e}")

    def bulk_insert(self, opportunities: List[Dict]):
        """批次寫入掃描機會"""
        if not opportunities:
            return
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                scan_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                records = []
                
                for opp in opportunities:
                    ticker = opp.get('ticker', '')
                    profile = opp.get('profile', '')
                    strategy = opp.get('strategy', '')
                    strike = opp.get('strike', 0.0)
                    expiry = opp.get('expiry', '')
                    stock_price = opp.get('price', 0.0)
                    premium = opp.get('premium', 0.0)
                    score = opp.get('score', 0.0)
                    uoa_score = opp.get('uoa_score', 0.0)
                    reasoning = opp.get('reasoning', '')
                    raw_json = json.dumps(opp, default=str)
                    
                    records.append((
                        scan_time, ticker, profile, strategy, strike, expiry,
                        stock_price, premium, score, uoa_score, reasoning, raw_json
                    ))
                    
                cursor.executemany('''
                    INSERT INTO scan_history (
                        scan_time, ticker, profile, strategy, strike, expiry, 
                        stock_price, premium, score, uoa_score, reasoning, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', records)
                
                conn.commit()
                logger.info(f"* 成功將 {len(records)} 筆機會寫入 SQLite 資料庫")
        except Exception as e:
            logger.error(f"x SQLite 批次寫入失敗: {e}")
            
    def query_recent(self, days: int = 7) -> List[Dict]:
        """查詢最近 N 天的記錄 (用於日後回測)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(f'''
                    SELECT * FROM scan_history 
                    WHERE scan_time >= datetime('now', '-{days} days')
                    ORDER BY scan_time DESC
                ''')
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"x SQLite 查詢失敗: {e}")
            return []

if __name__ == "__main__":
    # Test DB insertion
    logging.basicConfig(level=logging.INFO)
    db = SQLiteManager("test_scanner.db")
    db.insert_opportunity({
        "ticker": "TEST",
        "strategy": "LONG_CALL",
        "strike": 150.0,
        "expiry": "20261231",
        "price": 145.0,
        "premium": 5.0,
        "score": 90.0,
        "uoa_score": 85.0,
        "reasoning": "UOA異動 + Bullish趨勢 + 支撐位(150.0)"
    })
    print(db.query_recent())
