import ccxt
import asyncio

async def test_context_data():
    exchange = ccxt.binanceusdm() # Use Futures for Funding Rate
    try:
        print("🔍 Checking BTC/USDT Ticker (24h Change)...")
        ticker = await exchange.fetch_ticker('BTC/USDT')
        print(f"   Price: {ticker['last']}")
        print(f"   24h Change: {ticker['percentage']:.2f}%")
        
        print("\n🔍 Checking Funding Rate...")
        funding = await exchange.fetch_funding_rate('BTC/USDT')
        print(f"   Funding Rate: {funding['fundingRate']:.6f} ({funding['fundingRate']*100:.4f}%)")
        print(f"   Next Funding Time: {funding['fundingTimestamp']}")
        
        print("\n✅ Data Check Passed.")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_context_data())
