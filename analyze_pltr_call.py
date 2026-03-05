import asyncio
import os
import sys
from datetime import datetime

# Ensure the parent directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.ai_analysis_service import get_ai_service
from data_layer.data_fetcher import DataFetcher
import math

async def main():
    ticker = 'PLTR'
    fetcher = DataFetcher()
    print(f"Fetching recent {ticker} data (Basic)...")
    basic_info = fetcher.get_stock_info(ticker)
    
    current_price = basic_info.get('current_price', 0.0)
    
    print(f"Fetching detailed historical data for volatility and ATR...")
    try:
        hist_data = fetcher.get_historical_data(ticker, period='1y')
        # Simple recent volatility / standard deviation calculation
        recent_closes = hist_data['Close'].tail(20)
        daily_returns = recent_closes.pct_change().dropna()
        daily_vol = daily_returns.std()
        annual_vol = daily_vol * math.sqrt(252)
    except Exception as e:
        print(f"Warning: Could not fetch advanced stat: {e}")
        annual_vol = 0.60 # Default to 60% IV for high growth tech like PLTR
    
    # Calculate DTE to the last trading day of March 2026. 
    # March 31, 2026 is a Tuesday. The last Friday options expiration is March 27, 2026.
    today = datetime.now()
    expiry = datetime(2026, 3, 27)
    dte = (expiry - today).days
    
    if dte <= 0: dte = 1 # Avoid division errors
    
    print(f"Current {ticker} Price: {current_price}")
    print(f"Days to Expiration (DTE): {dte} days (Target Expiry: {expiry.strftime('%Y-%m-%d')})")
    print(f"Estimated Annual Volatility: {annual_vol:.2%}")
    
    # Calculate a simple 1 Standard Deviation expected move up
    # Expected Move = Stock Price * IV * sqrt(DTE / 365)
    expected_move_perc = annual_vol * math.sqrt(dte / 365)
    expected_high = current_price * (1 + expected_move_perc)
    two_sd_high = current_price * (1 + (expected_move_perc * 2))
    
    print(f"1 SD Expected Move (+{expected_move_perc:.2%}): ${expected_high:.2f}")
    
    print("Connecting to Nvidia AI for analysis...")
    ai = get_ai_service()
    
    prompt = f"""
    The user is asking: "Analyze Palantir (Ticker: PLTR) for the options expiration at the end of March ({expiry.strftime('%Y-%m-%d')}). Where could the highest stock price be? I bought a Long Call last Friday expiring at the end of March."
    
    Here is the quantitative data:
    - Target Asset: Palantir Technologies Inc. (PLTR)
    - Current Price: ${current_price:.2f}
    - Days to Expiration (DTE): {dte} days
    - Approximate Annual Volatility: {annual_vol:.2%}
    - Statistical 1 Standard Deviation Expected High: ${expected_high:.2f}
    - Statistical 2 Standard Deviation Extreme High: ${two_sd_high:.2f}
    
    Please provide:
    1. A brief analysis of PLTR's recent technical and fundamental momentum (as a prominent AI software company).
    2. An objective assessment of where the "highest stock price" could potentially land by the end of March, using the statistical expected moves provided (1 SD and 2 SD targets) along with recent market sentiment.
    3. An evaluation of their Long Call trade (since they bought it last Friday, are they currently at an advantage? Remind them about time decay/Theta given {dte} days remaining).
    
    Respond in Traditional Chinese. Be professional, quantitative, and realistic.
    """
    
    print("Generating AI Analysis report via Nvidia NIM...")
    try:
        response = await ai._call_nvidia_api_async(prompt)
        
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', ticker, f'{ticker}_EndOfMarch_Long_Call_Analysis.txt')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"=== {ticker} Long Call Analysis (Nvidia AI) ===\n\n")
            f.write(response)
        print(f"\n\nAnalysis saved to {output_path}")
        
    except Exception as e:
        print(f"Error calling Nvidia AI: {e}")

if __name__ == "__main__":
    asyncio.run(main())
