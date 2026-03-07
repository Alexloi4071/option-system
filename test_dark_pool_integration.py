#!/usr/bin/env python3
"""
Dark Pool 功能整合測試腳本

測試 Layer 1-3 的完整流程：
- Layer 1: IBKRClient.get_dark_pool_ticks()
- Layer 2: DataFetcher.get_dark_pool_data()
- Layer 3: DarkPoolAnalyzer.analyze()

使用方式:
    python test_dark_pool_integration.py AAPL
    python test_dark_pool_integration.py TSLA --duration 30 --method both
"""

import sys
import argparse
from data_layer.ibkr_client import IBKRClient
from data_layer.data_fetcher import DataFetcher
from data_layer.dark_pool_analyzer import DarkPoolAnalyzer
import logging

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_layer1(ticker: str, duration: int = 30, method: str = 'both'):
    """測試 Layer 1: IBKRClient.get_dark_pool_ticks()"""
    logger.info("=" * 80)
    logger.info("測試 Layer 1: IBKRClient.get_dark_pool_ticks()")
    logger.info("=" * 80)
    
    try:
        client = IBKRClient(mode='paper')
        if not client.connect():
            logger.error("無法連接到 IBKR Gateway")
            return None
        
        result = client.get_dark_pool_ticks(
            ticker=ticker,
            duration_seconds=duration,
            method=method
        )
        
        client.disconnect()
        
        if result:
            logger.info(f"\n✓ Layer 1 測試成功")
            logger.info(f"  Ticker: {result['ticker']}")
            logger.info(f"  方法 A (差值法): DP ratio = {result['dp_ratio_diff']:.2f}%")
            logger.info(f"  方法 B (交易所過濾): DP ratio = {result['dp_ratio_exchange']:.2f}%")
            if result.get('methods_agree') is not None:
                logger.info(f"  兩方法一致: {result['methods_agree']}")
                logger.info(f"  Consensus DP ratio: {result['dp_ratio_consensus']:.2f}%")
            logger.info(f"  VWAP: ${result['vwap']}" if result['vwap'] else "  VWAP: N/A")
            logger.info(f"  大單數量: {result['dp_block_count']}")
            logger.info(f"  警告: {result['warnings']}" if result['warnings'] else "  無警告")
        else:
            logger.error("✗ Layer 1 測試失敗: 返回 None")
        
        return result
        
    except Exception as e:
        logger.error(f"✗ Layer 1 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_layer2(ticker: str, duration: int = 30):
    """測試 Layer 2: DataFetcher.get_dark_pool_data()"""
    logger.info("\n" + "=" * 80)
    logger.info("測試 Layer 2: DataFetcher.get_dark_pool_data()")
    logger.info("=" * 80)
    
    try:
        fetcher = DataFetcher(use_ibkr=True)
        
        snapshot = fetcher.get_dark_pool_data(
            ticker=ticker,
            duration_seconds=duration,
            method='both'
        )
        
        if snapshot:
            logger.info(f"\n✓ Layer 2 測試成功")
            logger.info(f"  Ticker: {snapshot['ticker']}")
            logger.info(f"  最佳 DP ratio: {snapshot['dp_ratio']:.2f}%")
            logger.info(f"  最佳 DP volume: {snapshot['dp_volume']:,}")
            logger.info(f"  數據質量: {snapshot['data_quality']}")
            logger.info(f"  大單數量: {snapshot['block_count']}")
            logger.info(f"  大單總量: {snapshot['block_volume']:,}")
            logger.info(f"  VWAP: ${snapshot['vwap']:.4f}" if snapshot['vwap'] else "  VWAP: N/A")
        else:
            logger.error("✗ Layer 2 測試失敗: 返回 None")
        
        return snapshot
        
    except Exception as e:
        logger.error(f"✗ Layer 2 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_layer3(snapshot: dict, current_price: float = None):
    """測試 Layer 3: DarkPoolAnalyzer.analyze()"""
    logger.info("\n" + "=" * 80)
    logger.info("測試 Layer 3: DarkPoolAnalyzer.analyze()")
    logger.info("=" * 80)
    
    if not snapshot:
        logger.error("✗ Layer 3 測試跳過: 沒有 snapshot 數據")
        return None
    
    try:
        analyzer = DarkPoolAnalyzer()
        
        signal = analyzer.analyze(snapshot, current_price=current_price)
        
        logger.info(f"\n✓ Layer 3 測試成功")
        logger.info(f"  Ticker: {signal.ticker}")
        logger.info(f"  訊號類型: {signal.signal_type}")
        logger.info(f"  信心度: {signal.confidence:.2f}")
        logger.info(f"  DP ratio: {signal.dp_ratio:.2f}%")
        logger.info(f"  DP volume: {signal.dp_volume:,}")
        logger.info(f"  大單數量: {signal.block_count}")
        logger.info(f"  大單總量: {signal.block_volume:,}")
        if signal.vwap and signal.vwap_deviation is not None:
            logger.info(f"  VWAP: ${signal.vwap:.4f}")
            logger.info(f"  VWAP 偏差: {signal.vwap_deviation*100:.2f}%")
        logger.info(f"  數據質量: {signal.data_quality}")
        logger.info(f"  兩方法一致: {signal.methods_agree}")
        if signal.warnings:
            logger.info(f"  警告: {signal.warnings}")
        
        return signal
        
    except Exception as e:
        logger.error(f"✗ Layer 3 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_integration(ticker: str, duration: int = 30):
    """測試完整整合流程"""
    logger.info("\n" + "=" * 80)
    logger.info(f"Dark Pool 完整整合測試: {ticker}")
    logger.info("=" * 80)
    
    # 先獲取當前股價（用於 Layer 3 VWAP 偏差計算）
    current_price = None
    try:
        fetcher = DataFetcher(use_ibkr=True)
        stock_info = fetcher.get_stock_info(ticker)
        if stock_info:
            current_price = stock_info.get('current_price')
            logger.info(f"\n當前股價: ${current_price:.2f}")
    except Exception as e:
        logger.warning(f"無法獲取當前股價: {e}")
    
    # Layer 1 測試
    layer1_result = test_layer1(ticker, duration, method='both')
    
    # Layer 2 測試
    layer2_result = test_layer2(ticker, duration)
    
    # Layer 3 測試
    layer3_result = test_layer3(layer2_result, current_price)
    
    # 總結
    logger.info("\n" + "=" * 80)
    logger.info("測試總結")
    logger.info("=" * 80)
    logger.info(f"Layer 1 (IBKRClient): {'✓ 通過' if layer1_result else '✗ 失敗'}")
    logger.info(f"Layer 2 (DataFetcher): {'✓ 通過' if layer2_result else '✗ 失敗'}")
    logger.info(f"Layer 3 (DarkPoolAnalyzer): {'✓ 通過' if layer3_result else '✗ 失敗'}")
    
    if layer1_result and layer2_result and layer3_result:
        logger.info("\n🎉 所有測試通過！Dark Pool 功能正常運作")
        return True
    else:
        logger.error("\n❌ 部分測試失敗，請檢查錯誤訊息")
        return False


def main():
    parser = argparse.ArgumentParser(description='Dark Pool 功能整合測試')
    parser.add_argument('ticker', help='股票代碼 (例如: AAPL, TSLA)')
    parser.add_argument('--duration', type=int, default=30, help='採樣時長（秒），預設 30')
    parser.add_argument('--method', choices=['diff', 'exchange', 'both'], default='both',
                        help='測試方法: diff (差值法), exchange (交易所過濾), both (雙重驗證)')
    parser.add_argument('--layer', choices=['1', '2', '3', 'all'], default='all',
                        help='測試層級: 1 (IBKRClient), 2 (DataFetcher), 3 (Analyzer), all (完整流程)')
    
    args = parser.parse_args()
    
    ticker = args.ticker.upper()
    
    if args.layer == 'all':
        success = test_integration(ticker, args.duration)
        sys.exit(0 if success else 1)
    elif args.layer == '1':
        result = test_layer1(ticker, args.duration, args.method)
        sys.exit(0 if result else 1)
    elif args.layer == '2':
        result = test_layer2(ticker, args.duration)
        sys.exit(0 if result else 1)
    elif args.layer == '3':
        # Layer 3 需要先獲取 snapshot
        snapshot = test_layer2(ticker, args.duration)
        if snapshot:
            result = test_layer3(snapshot)
            sys.exit(0 if result else 1)
        else:
            logger.error("無法獲取 snapshot，Layer 3 測試失敗")
            sys.exit(1)


if __name__ == '__main__':
    main()
