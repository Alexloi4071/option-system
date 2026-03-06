import asyncio
import os
import sys
from datetime import datetime

# Ensure the parent directory is in the path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.ai_analysis_service import get_ai_service
from data_layer.data_fetcher import DataFetcher

async def main():
    fetcher = DataFetcher()
    basic_info = fetcher.get_stock_info('VZ')
    current_price = basic_info.get('current_price', 50.87)
    
    # Calculate exact DTE
    today = datetime.now()
    expiry = datetime(2026, 6, 18)
    dte = (expiry - today).days
    
    print(f"Current VZ Price: {current_price}")
    print(f"Days to Expiration (DTE): {dte}")
    
    print("Connecting to Nvidia AI for analysis...")
    ai = get_ai_service()
    
    prompt = f"""
    The user is asking two things:
    1. Analyze the recent trend of Verizon Communications (Ticker: VZ). Current price is {current_price}.
    2. Analyze their specific options trade: They bought a VZ Long Put with a strike price of $49.5 expiring on 2026-06-18. 
    
    Please provide:
    - A brief analysis of VZ's current market trend.
    - An evaluation of this 49.5 Long Put's chances of profitability by 2026-06-18. Consider the macroeconomic environment, the time to maturity (DTE is exactly {dte} days), volatility, and the distance to the strike price.
    - Give a clear, objective probability/chance rating of making money.
    
    Respond in Traditional Chinese. Give a realistic and precise assessment since the expiration is only {dte} days away, not a year.
    """
    
    print("Generating AI Analysis report via Nvidia NIM...")
    try:
        response = await ai._call_nvidia_api_async(prompt)
        print("\n=== AI Analysis Result ===")
        print(response)
        
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'VZ', 'VZ_49.5_Long_Put_Analysis_Nvidia.txt')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=== VZ 49.5 Long Put Analysis (Nvidia AI) ===\n\n")
            f.write(response)
        print(f"\n\nAnalysis saved to {output_path}")
        
    except Exception as e:
        print(f"Error calling Nvidia AI: {e}")

if __name__ == "__main__":
    asyncio.run(main())
