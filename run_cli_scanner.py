"""
run_cli_scanner.py - Single Pass Quick Scanner
- 一次完整掃描（策略評分 + UOA 異動偵測）後自動退出
- 使用隨機 Client ID 避免與其他連線衝突
"""
import asyncio
import logging
import sys
import time
import random
import json

import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
settings.IBKR_USE_PAPER = False  # Port 4001 (Live Gateway)

import scanner_service as _svc_module
_svc_module.CLIENT_ID = random.randint(150, 199)  # 隨機 ID 避免衝突

from scanner_service import ScannerService
from config.strategy_profiles import ALL_PROFILES

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("CLI_Scanner")


async def run_single_pass():
    logger.info("=" * 55)
    logger.info("  📡 Single-Pass Scanner (策略 + UOA 異動偵測)")
    logger.info("=" * 55)

    scanner = ScannerService()

    logger.info(f"Connecting to IBKR (ClientId={_svc_module.CLIENT_ID})...")
    connected = await scanner.connect()
    if not connected:
        logger.error("❌ Failed to connect to IBKR. Check TWS/Gateway.")
        return

    all_strategy_names = [p.name for p in ALL_PROFILES.values()]
    logger.info(f"✅ Connected! Strategies: {all_strategy_names}")

    # 執行單次完整的 UOA-First 掃描管道
    scanner.running = True
    await scanner.run_loop(single_pass=True)

    logger.info(f"\n{'=' * 55}")
    logger.info(f"  [OK] 掃描完成！結果已儲存在 JSON 和本機 SQLite 中")
    logger.info(f"{'=' * 55}")

    scanner.running = False
    if scanner.ib.isConnected():
        scanner.ib.disconnect()


if __name__ == "__main__":
    asyncio.run(run_single_pass())
