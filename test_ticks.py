from ib_insync import IB, Stock, Option, util
import sys
import time

def test_ticks():
    ib = IB()
    try:
        ib.connect('127.0.0.1', 4001, clientId=999)
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)
        
    contract = Stock('MSFT', 'SMART', 'USD')
    try:
        ib.qualifyContracts(contract)
    except Exception as e:
        print(f"Contract err: {e}")
    
    # tick list
    generic_tick_list = "100,101,104,106,165,221,225,232,233,236,258,293,294,295,318,375,411,456,595"
    ticker = ib.reqMktData(contract, generic_tick_list, False, False)
    
    print("Waiting for data...")
    ib.sleep(3)
    
    print("\n--- TICKER ATTRIBUTES ---")
    print(f"markPrice: getattr -> {getattr(ticker, 'markPrice', None)}")
    print(f"dividends: getattr -> {getattr(ticker, 'dividends', None)}")
    print(f"rtHistoricalVolatility: getattr -> {getattr(ticker, 'rtHistoricalVolatility', None)}")
    print(f"historicalVolatility: getattr -> {getattr(ticker, 'historicalVolatility', None)}")
    
    print("\n--- TICKER TICKS (Raw data items) ---")
    for tick in ticker.ticks:
        print(f"TickType: {tick.tickType}, Value: {tick.value}")

    print("\n--- ALL AVAILABLE ATTRIBUTES IN TICKER ---")
    print(dir(ticker))
    
    ib.disconnect()

if __name__ == '__main__':
    test_ticks()
