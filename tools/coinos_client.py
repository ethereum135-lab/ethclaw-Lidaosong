"""CoinOS Python客户端 — 封装AiCoin免费市场数据

使用方式:
    from tools.coinos_client import coinos

    # 获取K线
    klines = coinos.kline("btcusdt:okex", "3600", 5)

    # 获取价格
    prices = coinos.ticker(["btcusdt:binance", "ethusdt:binance"])

    # 搜索币种
    results = coinos.search("meme")

安装要求：Node.js (已安装在系统中)
CoinOS路径: {SELF_DIR}/coinos/
"""

import json
import os
import subprocess
from typing import Any, Optional

SELF_DIR = os.path.dirname(os.path.abspath(__file__))
COINOS_DIR = os.path.join(SELF_DIR, "coinos")
MARKET_SCRIPT = os.path.join(COINOS_DIR, "skills", "aicoin-market", "scripts", "market.mjs")
COIN_SCRIPT = os.path.join(COINOS_DIR, "skills", "aicoin-market", "scripts", "coin.mjs")
NEWS_SCRIPT = os.path.join(COINOS_DIR, "skills", "aicoin-market", "scripts", "news.mjs")


def _run_node(script: str, action: str, params: Optional[dict] = None) -> dict:
    """调用CoinOS Node.js脚本并返回解析后的JSON"""
    cmd = ["node", script, action]
    if params:
        cmd.append(json.dumps(params))

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
        cwd=COINOS_DIR,
    )

    if result.returncode != 0:
        return {"success": False, "error": result.stderr[:500]}

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"success": False, "error": f"JSON解析失败: {result.stdout[:500]}"}


class CoinOSClient:
    """CoinOS 市场数据客户端"""

    # ─── 价格/行情 ────────────────────────────────────────

    def ticker(self, markets: list[str]) -> dict:
        """获取多个交易对实时价格
        
        Args:
            markets: ["btcusdt:binance", "ethusdt:binance"]
        """
        return _run_node(MARKET_SCRIPT, "ticker", {"market_list": ",".join(markets)})

    def coin_ticker(self, coins: list[str]) -> dict:
        """获取多个币种实时价格（按coin_key）
        
        Args:
            coins: ["bitcoin", "ethereum", "solana"]
        """
        return _run_node(COIN_SCRIPT, "coin_ticker", {"coin_list": ",".join(coins)})

    def kline(self, symbol: str, period: str = "3600", size: int = 100) -> dict:
        """获取K线数据
        
        Args:
            symbol: "btcusdt:okex" (格式: 币种:交易所)
            period: "60"(1m), "300"(5m), "900"(15m), "3600"(1h), "14400"(4h), "86400"(1d)
            size: 返回多少根K线
        """
        return _run_node(MARKET_SCRIPT, "kline", {
            "symbol": symbol,
            "period": period,
            "size": str(size),
        })

    def hot_coins(self, market_type: str = "spot") -> dict:
        """热门币种（内置key有限，只支持 'defi' 类）"""
        return _run_node(MARKET_SCRIPT, "hot_coins", {"market_type": market_type})

    # ─── 搜索 ──────────────────────────────────────────

    def search(self, keyword: str, trade_type: str = "spot") -> dict:
        """搜索币种
        
        Args:
            keyword: 关键词 (如 "BTC", "meme", "AI")
            trade_type: "spot"(现货) 或 "swap"(合约)
        """
        return _run_node(COIN_SCRIPT, "search", {
            "search": keyword,
            "trade_type": trade_type,
        })

    # ─── 上币信息 ──────────────────────────────────────

    def exchange_listing(self) -> dict:
        """交易所上币信息（免费）"""
        return _run_node(NEWS_SCRIPT, "exchange_listing")

    def exchange_listing_flash(self) -> dict:
        """上币快讯（免费）"""
        return _run_node(NEWS_SCRIPT, "exchange_listing_flash")

    # ─── 指数/期货 ──────────────────────────────────────

    def futures_interest(self, symbol: str) -> dict:
        """期货持仓量
        
        Args:
            symbol: "btcusdt:binance"
        """
        return _run_node(MARKET_SCRIPT, "futures_interest", {"symbol": symbol})

    def index_price(self, symbol: str) -> dict:
        """指数价格
        
        Args:
            symbol: "btc"
        """
        return _run_node(MARKET_SCRIPT, "index_price", {"symbol": symbol})


# 单例
coinos = CoinOSClient()


# ─── 直接运行测试 ─────────────────────────────────────

if __name__ == "__main__":
    import sys

    def test(name: str, result: dict):
        ok = result.get("success") or result.get("code") == "0"
        status = "✅" if ok else "❌"
        err = result.get("error", result.get("_note", ""))
        print(f"{status} {name}: {err[:80] if err else 'OK'}")

    print("=" * 50)
    print("  CoinOS 客户端测试")
    print("=" * 50)

    # 1. 价格
    r = coinos.coin_ticker(["bitcoin", "ethereum", "solana"])
    test("价格(b/s/e)", r)
    if r.get("success") and "data" in r:
        for d in r["data"][:3]:
            print(f"   {d.get('coin_key'):12} ${d.get('price_usd', '?')}")

    # 2. K线
    r = coinos.kline("btcusdt:okex", "3600", 3)
    test("K线(BTC 1h)", r)
    if r.get("success") and "data" in r:
        kdata = r["data"].get("kline_data", [])
        for k in kdata[:3]:
            print(f"   {k[0]} open={k[1]:.2f} close={k[4]:.2f}")

    # 3. 搜索
    r = coinos.search("AI", "spot")
    test("搜索(AI)", r)
    count = 0
    if r.get("code") == "0" and "data" in r:
        count = r["data"].get("count", 0)
        print(f"   找到 {count} 个结果")

    # 4. 上币信息
    r = coinos.exchange_listing()
    test("上币信息", r)

    # 5. 期货持仓
    r = coinos.futures_interest("btcusdt:binance")
    test("期货持仓(BTC)", r)

    print("=" * 50)
