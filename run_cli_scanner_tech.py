"""
run_cli_scanner_tech.py - Technical-First Quick Scanner
- 盤前/無期權成交量環境下專用
- 一次完整掃描（只看技術面指標、均線、籌碼分佈）後自動退出
- 使用隨機 Client ID 避免與其他連線衝突
"""
import asyncio
import logging
import sys
import time
import random

import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
settings.IBKR_USE_PAPER = False  # Port 4001 (Live Gateway)

import scanner_service as _svc_module
_svc_module.CLIENT_ID = random.randint(200, 250)  # 隨機 ID 避免衝突

from scanner_service import ScannerService
from config.strategy_profiles import ALL_PROFILES

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("CLI_Scanner_Tech")

async def run_single_pass_tech():
    logger.info("=" * 60)
    logger.info("  📊 Single-Pass Technical Scanner (純技術面與籌碼掃描)")
    logger.info("  適用於盤前、盤後，無須期權即時成交量！")
    logger.info("=" * 60)

    scanner = ScannerService()

    logger.info(f"Connecting to IBKR (ClientId={_svc_module.CLIENT_ID})...")
    connected = await scanner.connect()
    if not connected:
        logger.error("❌ Failed to connect to IBKR. Check TWS/Gateway.")
        return

    all_strategy_names = [p.name for p in ALL_PROFILES.values()]
    logger.info(f"✅ Connected! Strategies check: {all_strategy_names}")

    # 執行單次完整的 Technical-First 掃描管道
    scanner.running = True
    await scanner.run_loop_technical(single_pass=True)

    logger.info(f"\n{'=' * 55}")
    logger.info(f"  [OK] 純技術面掃描完成！結果已儲存在 JSON 和本機 SQLite 中")
    logger.info(f"{'=' * 55}")

    scanner.running = False
    if scanner.ib.isConnected():
        scanner.ib.disconnect()

if __name__ == "__main__":
    asyncio.run(run_single_pass_tech())
