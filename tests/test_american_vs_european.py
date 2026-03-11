from calculation_layer.module16_greeks import GreeksCalculator
import time

def run_compare():
    calc = GreeksCalculator()
    
    # 測試1: 深度價內 Put, 無股息 (美式應該 > 歐式)
    S = 80
    K = 100
    T = 0.5
    r = 0.05
    sigma = 0.3
    q = 0.0
    
    print("=== Test 1: Deep ITM Put (S=80, K=100) ===")
    
    start = time.time()
    res_amer = calc.calculate_all_greeks(S, K, r, T, sigma, 'put', q, is_american=True)
    t_amer = time.time() - start
    
    start = time.time()
    res_euro = calc.calculate_all_greeks(S, K, r, T, sigma, 'put', q, is_american=False)
    t_euro = time.time() - start
    
    print(f"American (Vectorized Tree 500 steps) - Time: {t_amer:.4f}s")
    print(f"  Price: {res_amer.to_dict().get('american_price', 'N/A')}")
    print(f"  Delta: {res_amer.delta:.4f}")
    print(f"  Gamma: {res_amer.gamma:.4f}")
    print(f"  Theta: {res_amer.theta:.4f}")
    
    print(f"\nEuropean (Black-Scholes) - Time: {t_euro:.4f}s")
    print(f"  Price: {res_euro.to_dict().get('european_price', 'N/A')}")
    print(f"  Delta: {res_euro.delta:.4f}")
    print(f"  Gamma: {res_euro.gamma:.4f}")
    print(f"  Theta: {res_euro.theta:.4f}")
    
    # 測試2: 高配息 Call (S=100, K=100, Dividend=0.08)
    print("\n=== Test 2: High Dividend ATM Call (S=100, K=100, q=0.08) ===")
    q2 = 0.08
    res_amer2 = calc.calculate_all_greeks(100, 100, r, T, sigma, 'call', q2, is_american=True)
    res_euro2 = calc.calculate_all_greeks(100, 100, r, T, sigma, 'call', q2, is_american=False)
    
    print(f"American Delta: {res_amer2.delta:.4f} | European Delta: {res_euro2.delta:.4f}")
    
    # 測試 3: Discrete Dividends (S=100, K=100, Div=$2 at T=0.25)
    print("\n=== Test 3: Discrete Dividend at T=0.25 (S=100, K=100, Div=$2.0) ===")
    discrete_divs = [(0.25, 2.0)]
    res_amer_div = calc.calculate_all_greeks(100, 100, r, T, sigma, 'call', 0.0, discrete_dividends=discrete_divs, is_american=True)
    res_euro_div = calc.calculate_all_greeks(100, 100, r, T, sigma, 'call', 0.0, discrete_dividends=discrete_divs, is_american=False)
    
    print(f"American (Vectorized Tree 500 steps)")
    print(f"  Price: {res_amer_div.to_dict().get('american_price', 'N/A')}")
    print(f"  Delta: {res_amer_div.delta:.4f}")
    
    print(f"\nEuropean (Black-Scholes)")
    print(f"  Price: {res_euro_div.to_dict().get('european_price', 'N/A')}")
    print(f"  Delta: {res_euro_div.delta:.4f}")

if __name__ == "__main__":
    run_compare()
