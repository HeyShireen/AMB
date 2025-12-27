#!/usr/bin/env python3
"""Simple test script to verify IBKR connection."""

import asyncio
from ib_insync import IB, util


async def test_connection():
    """Test basic IBKR connection."""
    ib = IB()
    
    # Connection parameters (adjust as needed)
    host = "127.0.0.1"
    port = 4002  # IB Gateway paper trading (7497 for TWS paper)
    client_id = 1
    
    print(f"🔌 Connecting to IBKR at {host}:{port}...")
    
    try:
        await ib.connectAsync(host, port, clientId=client_id, timeout=20)
        print("✅ Connection successful!")
        
        # Get account summary
        print("\n📊 Account Summary:")
        account_values = ib.accountSummary()
        for item in account_values[:10]:  # Show first 10 items
            print(f"  {item.tag}: {item.value} {item.currency}")
        
        # Get positions
        print("\n📈 Current Positions:")
        positions = ib.positions()
        if positions:
            for pos in positions:
                print(f"  {pos.contract.symbol}: {pos.position} @ {pos.avgCost}")
        else:
            print("  No positions")
        
        # Test market data
        print("\n💹 Testing Market Data (AAPL):")
        from ib_insync import Stock
        contract = Stock("AAPL", "SMART", "USD")
        await ib.qualifyContractsAsync(contract)
        ticker = ib.reqMktData(contract)
        await asyncio.sleep(2)  # Wait for data
        
        print(f"  Last price: {ticker.last}")
        print(f"  Bid: {ticker.bid} | Ask: {ticker.ask}")
        print(f"  Volume: {ticker.volume}")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n🔍 Troubleshooting:")
        print("  1. Is TWS/Gateway running?")
        print("  2. Is API access enabled in TWS settings?")
        print("  3. Is the port correct? (7497 for TWS paper)")
        print("  4. Check firewall settings")
        return False
    
    finally:
        ib.disconnect()
        print("\n🔌 Disconnected")
    
    return True


if __name__ == "__main__":
    util.startLoop()
    asyncio.run(test_connection())
