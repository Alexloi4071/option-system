#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 2 修复验证脚本
验证所有4个问题的修复是否正常工作
"""

import sys
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_module1_multi_confidence():
    """测试Module 1多信心度计算"""
    logger.info("=" * 70)
    logger.info("测试1: Module 1 多信心度计算")
    logger.info("=" * 70)
    
    try:
        from calculation_layer.module1_support_resistance import SupportResistanceCalculator
        
        calc = SupportResistanceCalculator()
        
        # 验证CONFIDENCE_LEVELS存在
        assert hasattr(calc, 'CONFIDENCE_LEVELS'), "缺少CONFIDENCE_LEVELS配置"
        assert '68%' in calc.CONFIDENCE_LEVELS, "缺少68%信心度"
        assert '99%' in calc.CONFIDENCE_LEVELS, "缺少99%信心度"
        logger.info("✓ CONFIDENCE_LEVELS配置存在")
        
        # 测试多信心度计算
        results = calc.calculate_multi_confidence(
            stock_price=180.50,
            implied_volatility=22.0,
            days_to_expiration=37
        )
        
        assert 'results' in results, "缺少results字段"
        assert '68%' in results['results'], "缺少68%结果"
        assert '99%' in results['results'], "缺少99%结果"
        assert len(results['results']) == 5, f"应该有5个信心度，实际{len(results['results'])}"
        
        # 验证计算正确性
        assert results['results']['68%']['price_move'] < results['results']['99%']['price_move'], "68%波动应该小于99%"
        
        logger.info("✓ 多信心度计算功能正常")
        logger.info(f"  计算了{len(results['results'])}个信心度")
        return True
        
    except Exception as e:
        logger.error(f"✗ Module 1测试失败: {e}")
        return False

def test_module3_relative_thresholds():
    """测试Module 3相对阈值"""
    logger.info("=" * 70)
    logger.info("测试2: Module 3 相对阈值")
    logger.info("=" * 70)
    
    try:
        from calculation_layer.module3_arbitrage_spread import ArbitrageSpreadCalculator
        
        calc = ArbitrageSpreadCalculator()
        
        # 验证THRESHOLDS存在
        assert hasattr(calc, 'THRESHOLDS'), "缺少THRESHOLDS配置"
        assert calc.THRESHOLDS['strong_overvalued'] == 5.0, "strong_overvalued应该是5.0%"
        logger.info("✓ THRESHOLDS配置存在")
        
        # 测试低价格期权（$10，spread $0.50 = 5%）
        result1 = calc.calculate(
            market_option_price=10.50,
            fair_value=10.00
        )
        assert result1.spread_percentage == 5.0, f"spread_percentage应该是5.0%，实际{result1.spread_percentage}"
        assert "嚴重高估" in result1.recommendation, "应该判断为严重高估"
        logger.info(f"✓ 低价格期权测试通过: {result1.recommendation}")
        
        # 测试高价格期权（$200，相同spread $0.50 = 0.25%）
        result2 = calc.calculate(
            market_option_price=200.50,
            fair_value=200.00
        )
        assert result2.spread_percentage == 0.25, f"spread_percentage应该是0.25%，实际{result2.spread_percentage}"
        assert "合理" in result2.recommendation or "公平" in result2.recommendation, "应该判断为合理定价"
        logger.info(f"✓ 高价格期权测试通过: {result2.recommendation}")
        
        logger.info("✓ Module 3相对阈值功能正常")
        return True
        
    except Exception as e:
        logger.error(f"✗ Module 3测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_datafetcher_fallback():
    """测试DataFetcher降级策略"""
    logger.info("=" * 70)
    logger.info("测试3: DataFetcher 降级策略")
    logger.info("=" * 70)
    
    try:
        from data_layer.data_fetcher import DataFetcher
        
        # 测试初始化（不使用IBKR）
        fetcher = DataFetcher(use_ibkr=False)
        assert fetcher.use_ibkr == False, "use_ibkr应该是False"
        logger.info("✓ DataFetcher初始化正常")
        
        # 测试get_option_greeks降级（应该返回默认值）
        greeks = fetcher.get_option_greeks('AAPL', 150, '2024-12-20', 'C')
        assert greeks is not None, "应该返回默认值而非None"
        assert 'delta' in greeks, "应该包含delta字段"
        assert 'source' in greeks, "应该包含source字段"
        logger.info(f"✓ get_option_greeks降级正常: source={greeks.get('source')}")
        
        logger.info("✓ DataFetcher降级策略正常")
        return True
        
    except Exception as e:
        logger.error(f"✗ DataFetcher测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_module14_12_posts():
    """测试Module 14 12个岗位"""
    logger.info("=" * 70)
    logger.info("测试4: Module 14 12监察岗位")
    logger.info("=" * 70)
    
    try:
        from calculation_layer.module14_monitoring_posts import MonitoringPostsCalculator
        
        calc = MonitoringPostsCalculator()
        
        # 测试计算
        result = calc.calculate(
            stock_price=180.50,
            option_premium=35.00,
            iv=22.0,
            delta=0.12,
            open_interest=45000,
            volume=12500,
            bid_ask_spread=0.10,
            atr=5.0,
            vix=18.0,
            dividend_date="2024-12-20",
            earnings_date="2024-12-25",
            expiration_date="2024-12-27"
        )
        
        # 验证12个岗位状态字段
        assert hasattr(result, 'post1_stock_price_status'), "缺少post1状态字段"
        assert hasattr(result, 'post12_vix_status'), "缺少post12状态字段"
        logger.info("✓ 12个岗位状态字段存在")
        
        # 验证post_details
        assert result.post_details is not None, "缺少post_details"
        assert 'post1' in result.post_details, "缺少post1详细信息"
        assert 'post12' in result.post_details, "缺少post12详细信息"
        assert len(result.post_details) == 12, f"应该有12个岗位详细信息，实际{len(result.post_details)}"
        logger.info(f"✓ post_details包含{len(result.post_details)}个岗位信息")
        
        # 验证风险等级
        assert result.risk_level in ['低風險', '中風險', '高風險'], f"风险等级无效: {result.risk_level}"
        logger.info(f"✓ 风险等级: {result.risk_level} ({result.total_alerts}个警报)")
        
        logger.info("✓ Module 14 12岗位功能正常")
        return True
        
    except Exception as e:
        logger.error(f"✗ Module 14测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """运行所有测试"""
    logger.info("\n" + "=" * 70)
    logger.info("Phase 2 修复验证测试")
    logger.info("=" * 70 + "\n")
    
    results = []
    
    # 运行所有测试
    results.append(("Module 1 多信心度", test_module1_multi_confidence()))
    results.append(("Module 3 相对阈值", test_module3_relative_thresholds()))
    results.append(("DataFetcher 降级", test_datafetcher_fallback()))
    results.append(("Module 14 12岗位", test_module14_12_posts()))
    
    # 汇总结果
    logger.info("\n" + "=" * 70)
    logger.info("测试结果汇总")
    logger.info("=" * 70)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        logger.info(f"{status}: {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    logger.info("=" * 70)
    logger.info(f"总计: {passed}个通过, {failed}个失败")
    logger.info("=" * 70)
    
    if failed == 0:
        logger.info("\n🎉 所有测试通过！")
        return 0
    else:
        logger.error(f"\n❌ {failed}个测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())

