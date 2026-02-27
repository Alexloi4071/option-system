
import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock
import logging
from scanner_service import ScannerService
from config.strategy_profiles import MOMENTUM_PROFILE
from ib_insync import Stock, Option, TickData

# Setup Logging
logging.basicConfig(level=logging.INFO)

class TestTickerData:
    def __init__(self, last, close, volume):
        self.last = last
        self.close = close
        self.volume = volume

class TestOptionData:
    def __init__(self, bid, ask, impliedVolatility, delta, theta):
        self.bid = bid
        self.ask = ask
        self.impliedVolatility = impliedVolatility
        self.modelGreeks = MagicMock()
        self.modelGreeks.delta = delta
        self.modelGreeks.theta = theta

class TestShortStrategy(unittest.IsolatedAsyncioTestCase):
    async def test_short_call_trigger(self):
        print("\n=== Testing Short Call Trigger (Gap Up > 3%) ===")
        service = ScannerService()
        service.running = True
        service.is_connected = True
        
        # 1. Mock IB
        service.ib = MagicMock()
        service.ib.qualifyContracts = MagicMock()
        
        # 2. Mock Market Data (Gap Up)
        # Close = 100, Last = 105 (+5% Gap)
        # This should trigger SHORT_CALL logic in scanner_service
        stock_data = TestTickerData(105.0, 100.0, 1000000)
        service.ib.reqMktData = MagicMock(return_value=stock_data)
        
        # 3. Mock Option Chains
        chain = MagicMock()
        chain.exchange = 'SMART'
        chain.expirations = ['20260220', '20260227']
        chain.strikes = [100, 105, 110, 115, 120]
        service.ib.reqSecDefOptParamsAsync = AsyncMock(return_value=[chain])
        
        # 4. Mock Option Market Data (Short Call Analysis)
        # We want to sell OTM Call (Strike ~110-115)
        # Make it look attractive: High IV, Good Premium
        opt_data = TestOptionData(2.0, 2.2, 0.6, 0.25, -0.05) # Bid, Ask, IV, Delta, Theta
        # Note: Theta for Long is negative. For Short, we receive positive decay, but IB reports negative theta for the option contract itself.
        # My Short Analyzer expects 'theta' input. If I pass IB's negative theta, does it handle it?
        # module28 uses `abs(theta)` to calculate income, so sign doesn't matter much unless we check specific logic.
        
        # IMPORTANT: scanner_service calls reqMktData for the option.
        # We need to make sure subsequent calls return this opt_data
        # First call: analyze_options (Long Call) -> will ignore (delta 0.25)
        # Second call: analyze_short_options (Short Call) -> will accept
        service.ib.reqMktData.side_effect = [stock_data, opt_data, opt_data] 
        
        # 5. Run Scan
        print("Scannng ticker 'TEST' with Momentum Profile...")
        opps = await service.scan_ticker("TEST", MOMENTUM_PROFILE)
        
        print(f"Opportunities Found: {len(opps)}")
        for op in opps:
            print(f"- {op['strategy']} | Score: {op['score']}")
            
        # Assertions
        found_short_call = any(op['strategy'] == 'SHORT_CALL' for op in opps)
        self.assertTrue(found_short_call, "Should find a SHORT_CALL opportunity due to 5% Gap Up")

if __name__ == "__main__":
    unittest.main()
