import asyncio
import asyncpg
import uuid

async def main():
    url = "postgresql://postgres.khveaqnldwxbidfesklj:UBky3yIDzjUmqwWF@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"
    conn = await asyncpg.connect(url)
    
    print("Portfolios:")
    portfolios = await conn.fetch("SELECT id, name FROM portfolios")
    for p in portfolios:
        print(f"ID: {p['id']}, Name: {p['name']}")
        holdings = await conn.fetch("SELECT symbol, quantity, average_buy_price FROM holdings WHERE portfolio_id = $1", p["id"])
        for h in holdings:
            print(f"  Holding: {h['symbol']}, Qty: {h['quantity']}, Price: {h['average_buy_price']}")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
