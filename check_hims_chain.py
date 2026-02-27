import asyncio
from ib_insync import IB, Stock, Option
import pandas as pd

async def get_hims_chain():
    ib = IB()
    try:
        await ib.connectAsync('127.0.0.1', 4002, clientId=998)
        ib.reqMarketDataType(3)  # Delayed data
        stock = Stock('HIMS', 'SMART', 'USD')
        await ib.qualifyContractsAsync(stock)
        
        chains = await ib.reqSecDefOptParamsAsync(stock.symbol, '', stock.secType, stock.conId)
        chain = next(c for c in chains if c.exchange == 'SMART')
        
        target_exp = '20260227'
        if target_exp not in chain.expirations:
            print(f"Expiration {target_exp} not found. Available: {chain.expirations}")
            return

        strikes = sorted([s for s in chain.strikes])
        # Filter for OTM strikes (Price is ~16.5)
        otm_strikes = [s for s in strikes if 16.0 <= s <= 25.0]
        
        contracts = [Option('HIMS', target_exp, s, 'C', 'SMART') for s in otm_strikes]
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
                'delta': t.modelGreeks.delta if t.modelGreeks else None
            })
            
        df = pd.DataFrame(data)
        print(f"\nHIMS Call Option Chain (Exp: {target_exp}) [Delayed Data]:")
        print(df.to_string(index=False))
        
    finally:
        ib.disconnect()

if __name__ == "__main__":
    asyncio.run(get_hims_chain())
