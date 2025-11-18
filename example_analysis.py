#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
簡單的期權分析示例
直接運行此文件即可開始分析
"""

from main import OptionsAnalysisSystem
import json

def main():
    """主函數"""
    print("="*70)
    print("🚀 期權交易系統 - 簡單示例")
    print("="*70)
    
    # 步驟 1: 初始化系統
    print("\n📌 步驟 1: 初始化系統...")
    system = OptionsAnalysisSystem(use_ibkr=False)
    print("✅ 系統初始化完成")
    
    # 步驟 2: 設置分析參數
    print("\n📌 步驟 2: 設置分析參數...")
    
    # 你可以修改這裡的股票代碼
    ticker = 'AAPL'  # 改成你想分析的股票，如 'TSLA', 'MSFT', 'GOOGL'
    
    print(f"  股票代碼: {ticker}")
    print(f"  到期日: 自動選擇最近的到期日")
    
    # 步驟 3: 運行分析
    print(f"\n📌 步驟 3: 開始分析 {ticker}...")
    print("  (這可能需要 30-60 秒，請耐心等待...)")
    
    try:
        results = system.run_complete_analysis(
            ticker=ticker,
            expiration=None  # None 表示自動選擇
        )
        
        print("\n✅ 分析完成！")
        
        # 步驟 4: 顯示關鍵結果
        print("\n" + "="*70)
        print("📊 分析結果摘要")
        print("="*70)
        
        # 顯示股票基本信息
        if 'stock_info' in results:
            stock = results['stock_info']
            print(f"\n💰 股票信息:")
            print(f"  當前股價: ${stock.get('current_price', 'N/A'):.2f}")
            print(f"  市盈率 (PE): {stock.get('pe_ratio', 'N/A'):.2f}")
            print(f"  每股收益 (EPS): ${stock.get('eps', 'N/A'):.2f}")
        
        # 顯示 Black-Scholes 定價
        if 'module15_black_scholes' in results:
            bs = results['module15_black_scholes']
            print(f"\n🎯 Black-Scholes 期權定價:")
            if 'call' in bs:
                print(f"  Call 期權理論價: ${bs['call']['option_price']:.2f}")
            if 'put' in bs:
                print(f"  Put 期權理論價: ${bs['put']['option_price']:.2f}")
        
        # 顯示 Greeks
        if 'module16_greeks' in results:
            greeks = results['module16_greeks']
            print(f"\n📈 Greeks 風險指標:")
            if 'call' in greeks:
                print(f"  Call Delta: {greeks['call']['delta']:.4f} (股價變動敏感度)")
                print(f"  Call Gamma: {greeks['call']['gamma']:.6f} (Delta 變化率)")
                print(f"  Call Theta: {greeks['call']['theta']:.4f} (時間衰減)")
                print(f"  Call Vega: {greeks['call']['vega']:.4f} (波動率敏感度)")
        
        # 顯示隱含波動率
        if 'module17_implied_volatility' in results:
            iv = results['module17_implied_volatility']
            print(f"\n🔍 隱含波動率 (IV):")
            if 'call' in iv:
                print(f"  Call IV: {iv['call']['implied_volatility']:.2%}")
                print(f"  收斂次數: {iv['call']['iterations']} 次")
                print(f"  收斂狀態: {'✅ 成功' if iv['call']['converged'] else '❌ 失敗'}")
        
        # 顯示歷史波動率
        if 'module18_historical_volatility' in results:
            hv = results['module18_historical_volatility']
            print(f"\n📊 歷史波動率 (HV):")
            if 'hv_results' in hv:
                for window, data in hv['hv_results'].items():
                    print(f"  {window}: {data['hv']:.2%}")
            
            if 'iv_hv_ratio' in hv:
                ratio = hv['iv_hv_ratio']
                print(f"\n  IV/HV 比率: {ratio['ratio']:.2f}")
                print(f"  評估: {ratio['assessment']}")
                print(f"  建議: {ratio['recommendation']}")
        
        # 顯示 Put-Call Parity
        if 'module19_put_call_parity' in results:
            parity = results['module19_put_call_parity']
            print(f"\n⚖️ Put-Call Parity 驗證:")
            if 'market_prices' in parity:
                market = parity['market_prices']
                print(f"  市場價格偏離: ${market['deviation']:.2f}")
                print(f"  套利機會: {'✅ 存在' if market['arbitrage_opportunity'] else '❌ 不存在'}")
                if market['arbitrage_opportunity']:
                    print(f"  理論利潤: ${market['theoretical_profit']:.2f}")
                    print(f"  建議策略: {market['strategy_recommendation']}")
        
        # 顯示支撐/阻力位
        if 'module1_support_resistance' in results:
            sr = results['module1_support_resistance']
            print(f"\n📍 支撐/阻力位 (68% 信心度):")
            print(f"  支撐位: ${sr['support_level']:.2f}")
            print(f"  阻力位: ${sr['resistance_level']:.2f}")
            print(f"  波動幅度: ±{sr['volatility_percentage']:.2f}%")
        
        # 步驟 5: 保存結果
        print("\n" + "="*70)
        print("💾 保存結果")
        print("="*70)
        
        output_file = f'analysis_{ticker}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ 完整結果已保存到: {output_file}")
        print(f"   你可以用文本編輯器打開查看詳細數據")
        
        # 顯示 API 狀態
        print("\n" + "="*70)
        print("📡 API 狀態報告")
        print("="*70)
        
        from data_layer.data_fetcher import DataFetcher
        fetcher = DataFetcher(use_ibkr=False)
        api_report = fetcher.get_api_status_report()
        
        print(f"\n可用的數據源:")
        for source, available in api_report['available_sources'].items():
            status = "✅ 可用" if available else "❌ 不可用"
            print(f"  {source}: {status}")
        
        print(f"\n自主計算模塊:")
        for module, available in api_report['self_calculation_available'].items():
            status = "✅ 可用" if available else "❌ 不可用"
            print(f"  {module}: {status}")
        
        print("\n" + "="*70)
        print("🎉 分析完成！")
        print("="*70)
        print(f"\n💡 提示:")
        print(f"  1. 修改此文件第 20 行的 ticker 變量來分析其他股票")
        print(f"  2. 查看 {output_file} 獲取完整的分析數據")
        print(f"  3. 查看 QUICK_START.md 了解更多使用方法")
        
    except Exception as e:
        print(f"\n❌ 分析失敗: {e}")
        print(f"\n💡 可能的原因:")
        print(f"  1. 網絡連接問題")
        print(f"  2. API Keys 未配置或無效")
        print(f"  3. 股票代碼不存在或無期權數據")
        print(f"\n🔧 解決方案:")
        print(f"  1. 檢查網絡連接")
        print(f"  2. 確認 .env 文件中的 API Keys 配置正確")
        print(f"  3. 嘗試其他股票代碼（如 AAPL, MSFT, TSLA）")
        print(f"  4. 運行 test_simple.py 使用模擬數據測試")
        
        import traceback
        print(f"\n詳細錯誤信息:")
        traceback.print_exc()


if __name__ == '__main__':
    main()
