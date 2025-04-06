import asyncio
from trader import ChainTrader


async def test_buy_token():
    trader = ChainTrader()
    await trader.initialize_chains()

    # 测试参数
    chain = "sol"  # 可以根据需要修改链名称
    token_address = "6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN"  # 替换为实际的代币地址
    amount_usd = 1  # 可以根据需要修改交易金额 USDT

    tx_hash = await trader.buy_token(chain, token_address, amount_usd)
    if tx_hash:
        print(f"交易成功，交易哈希: {tx_hash}")
        explorer_url = trader.get_tx_explorer_url(chain, tx_hash)
        if explorer_url:
            print(f"交易浏览器链接: {explorer_url}")
    else:
        print("交易失败")

if __name__ == "__main__":
    asyncio.run(test_buy_token())
