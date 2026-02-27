import asyncio
import logging
import nest_asyncio
from scanner_service import ScannerService
from config.strategy_profiles import TITANS_PROFILE
from services.ai_analysis_service import get_ai_service

nest_asyncio.apply()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_integration_test():
    print("=== Starting Full Integration Test ===")
    
    # 1. Initialize Services
    scanner = ScannerService()
    ai_service = get_ai_service()
    
    # 2. Connect to IBKR
    print("--> Connecting to IBKR...")
    if not await scanner.connect():
        print("x IBKR Connection Failed. Aborting.")
        return

    # 3. Test Titans Profile Scanning
    # For testing, we might want to force a specific ticker if market is closed/quiet,
    # but let's try the real flow first.
    print(f"--> Scanning with Profile: {TITANS_PROFILE.name}")
    
    # Get Candidates
    candidates = await scanner.get_candidates_for_profile("titans", TITANS_PROFILE)
    print(f"--> Candidates: {candidates}")
    
    # Limit to first 3 for testing speed
    test_candidates = candidates[:3]
    
    opportunities = []
    for ticker in test_candidates:
        print(f"--> Analyzing {ticker}...")
        opps = await scanner.scan_ticker(ticker, TITANS_PROFILE)
        if opps:
            opportunities.extend(opps)
            print(f"!!! FOUND OPPORTUNITY: {ticker} !!!")
            
    # 4. Test AI Generation
    if opportunities:
        top_pick = opportunities[0]
        print(f"--> Generating AI Report for {top_pick['ticker']}...")
        
        report = ai_service.generate_analysis(top_pick['ticker'], top_pick)
        
        print("\n" + "="*30)
        print("AI ANALYSIS REPORT (繁體中文)")
        print("="*30)
        print(report)
        print("="*30 + "\n")
    else:
        print("--> No opportunities found in this test run (Market might be closed or no proper setups).")
        print("--> Trying to force AI generation with Mock Data for verification...")
        
        mock_opp = {
            'ticker': 'NVDA',
            'strategy': 'LONG_CALL',
            'price': 135.50,
            'gap': 1.2,
            'strike': 140,
            'expiry': '20241115',
            'score': 85,
            'analysis': {
                'iv': 0.45,
                'breakeven': 142.10,
                'leverage': 12.5
            }
        }
        report = ai_service.generate_analysis('NVDA', mock_opp)
        print("\n" + "="*30)
        print("AI ANALYSIS REPORT (MOCK TEST)")
        print("="*30)
        print(report)
        print("="*30 + "\n")

    print("=== Integration Test Complete ===")

if __name__ == "__main__":
    asyncio.run(run_integration_test())
