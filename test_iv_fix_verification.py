"""
Test script to verify IV source fix for UVIX
Task 7.1: Verify the fix results
"""
import sys
import os

# Add the option_trading_system to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import OptionsAnalysisSystem

def main():
    print("=" * 70)
    print("IV Source Fix Verification - UVIX Analysis")
    print("=" * 70)
    
    # Run analysis
    system = OptionsAnalysisSystem(use_ibkr=False)
    result = system.run_complete_analysis('UVIX')
    
    if not result:
        print("ERROR: Analysis failed!")
        return
    
    print("\n" + "=" * 70)
    print("VERIFICATION RESULTS")
    print("=" * 70)
    
    # Module 16 Greeks verification
    print("\n=== Module 16 Greeks ===")
    m16 = result.get('module16_greeks', {})
    print(f"IV Source: {m16.get('iv_source', 'N/A')}")
    print(f"IV Used: {m16.get('iv_used_pct', 'N/A')}%")
    print(f"Market IV: {m16.get('market_iv_pct', 'N/A')}%")
    
    call = m16.get('call', {})
    print(f"Call Delta: {call.get('delta', 'N/A')}")
    print(f"Call Gamma: {call.get('gamma', 'N/A')}")
    
    # Verify Delta is around 0.5 for ATM option
    delta = call.get('delta', 0)
    if 0.3 <= delta <= 0.7:
        print(f"✓ Delta {delta:.4f} is in expected ATM range (0.3-0.7)")
    else:
        print(f"✗ Delta {delta:.4f} is NOT in expected ATM range (0.3-0.7)")
    
    # Module 18 IV/HV verification
    print("\n=== Module 18 IV/HV Ratio ===")
    m18 = result.get('module18_historical_volatility', {})
    ivhv = m18.get('iv_hv_comparison', {})
    print(f"IV/HV Ratio: {ivhv.get('iv_hv_ratio', 'N/A')}")
    print(f"IV Source: {ivhv.get('iv_source', 'N/A')}")
    print(f"IV Used: {ivhv.get('iv_used', 'N/A')}")
    
    # Verify IV/HV ratio is reasonable (should be around 0.8-1.2 for normal conditions)
    ratio = ivhv.get('iv_hv_ratio', 0)
    if ratio > 0.5:
        print(f"✓ IV/HV Ratio {ratio:.2f} is reasonable (> 0.5)")
    else:
        print(f"✗ IV/HV Ratio {ratio:.2f} is too low (expected > 0.5)")
    
    # Module 23 Dynamic IV Threshold verification
    print("\n=== Module 23 Dynamic IV Threshold ===")
    m23 = result.get('module23_dynamic_iv_threshold', {})
    print(f"Current IV: {m23.get('current_iv', 'N/A')}")
    print(f"IV Source: {m23.get('iv_source', 'N/A')}")
    print(f"IV Status: {m23.get('iv_status', 'N/A')}")
    print(f"ATM IV Available: {m23.get('atm_iv_available', 'N/A')}")
    
    # Verify current IV is using ATM IV (should be around 100% for UVIX)
    current_iv = m23.get('current_iv', 0)
    if current_iv > 50:
        print(f"✓ Current IV {current_iv:.2f}% is using ATM IV (> 50%)")
    else:
        print(f"✗ Current IV {current_iv:.2f}% might still be using Market IV")
    
    # Module 17 verification
    print("\n=== Module 17 Implied Volatility ===")
    m17 = result.get('module17_implied_volatility', {})
    call_iv = m17.get('call', {})
    print(f"Call IV: {call_iv.get('implied_volatility', 0) * 100:.2f}%")
    print(f"Converged: {call_iv.get('converged', False)}")
    
    # IV Comparison
    print("\n=== IV Comparison ===")
    iv_comp = result.get('iv_comparison', {})
    print(f"Market IV: {iv_comp.get('market_iv', 'N/A')}%")
    print(f"ATM IV: {iv_comp.get('atm_iv', 'N/A')}%")
    print(f"Difference: {iv_comp.get('difference_pct', 'N/A')}%")
    print(f"Has Warning: {iv_comp.get('has_warning', 'N/A')}")
    
    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()
