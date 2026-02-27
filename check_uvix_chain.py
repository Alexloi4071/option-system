import asyncio
from ib_insync import IB, Stock, Option
import pandas as pd

async def get_uvix_chain():
    ib = IB()
    try:
        await ib.connectAsync('127.0.0.1', 4002, clientId=999)
        ib.reqMarketDataType(3)  # Delayed data
        stock = Stock('UVIX', 'SMART', 'USD')
        await ib.qualifyContractsAsync(stock)
        
        chains = await ib.reqSecDefOptParamsAsync(stock.symbol, '', stock.secType, stock.conId)
        chain = next(c for c in chains if c.exchange == 'SMART')
        
        # Filter for 20260227
        target_exp = '20260227'
        if target_exp not in chain.expirations:
            print(f"Expiration {target_exp} not found. Available: {chain.expirations}")
            return

        # Use explicitly available strikes from the chain
        strikes = sorted([s for s in chain.strikes if s <= 20.0]) # Limit range for speed
        print(f"Checking strikes for {target_exp}: {strikes}")
        
        contracts = [Option('UVIX', target_exp, s, 'C', 'SMART') for s in strikes]
        qualified = await ib.qualifyContractsAsync(*contracts)
        
        tickers = await ib.reqTickersAsync(*qualified)
        
        data = []
        for t in tickers:
            data.append({
                'strike': t.contract.strike,
                'bid': t.bid,
                'ask': t.ask,
                'last': t.last,
                'close': t.close,
                'modelIV': t.modelGreeks.impliedVol if t.modelGreeks else None
            })
            
        df = pd.DataFrame(data)
        print("\nUVIX Call Option Chain (2026-02-27) [Delayed Data]:")
        # Fill NaN with 0 or descriptive text for readability
        print(df.to_string(index=False))
        
    finally:
        ib.disconnect()

if __name__ == "__main__":
    asyncio.run(get_uvix_chain())
