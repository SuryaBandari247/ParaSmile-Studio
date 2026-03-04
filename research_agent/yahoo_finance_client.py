"""
Yahoo Finance client for the Research Agent.

Fetches market data, stock movers, and sector performance from Yahoo Finance
using the yfinance library. No API key required. Provides story trigger
detection for stocks with significant daily moves (>5%).
"""

from typing import Any, Dict, List

import yfinance as yf

from research_agent.logger import get_logger, log_error_with_context

logger = get_logger("yahoo_finance_client")


class YahooFinanceClient:
    """
    Fetches market data from Yahoo Finance using yfinance.
    No API key required.
    """

    MAJOR_INDICES: List[str] = [
        "^GSPC",   # S&P 500
        "^DJI",    # Dow Jones Industrial Average
        "^IXIC",   # Nasdaq Composite
        "^RUT",    # Russell 2000
        "^FTSE",   # FTSE 100
        "^N225",   # Nikkei 225
    ]

    SECTORS: Dict[str, str] = {
        "XLK": "Technology",
        "XLF": "Financials",
        "XLV": "Healthcare",
        "XLE": "Energy",
        "XLI": "Industrials",
        "XLY": "Consumer Discretionary",
        "XLP": "Consumer Staples",
        "XLU": "Utilities",
        "XLB": "Materials",
        "XLRE": "Real Estate",
    }

    _STORY_TRIGGER_THRESHOLD: float = 5.0

    def __init__(self) -> None:
        """Initialize Yahoo Finance client."""
        logger.info("YahooFinanceClient initialized")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_market_movers(self) -> Dict[str, Any]:
        """
        Fetch top gainers, losers, and most active stocks.

        Returns:
            Dict with keys:
            - gainers: List[Dict] — top gaining stocks
            - losers: List[Dict] — top losing stocks
            - most_active: List[Dict] — most actively traded
            - story_triggers: List[Dict] — stocks moving >5%

            Each stock dict has keys: symbol, name, price,
            change_percent, volume, sector.

        Note:
            Logs warning and returns empty dict if Yahoo Finance is unreachable.
        """
        try:
            gainers = self._fetch_screener("day_gainers")
            losers = self._fetch_screener("day_losers")
            most_active = self._fetch_screener("most_actives")

            # Combine all stocks and flag story triggers
            all_stocks = gainers + losers + most_active
            story_triggers = [
                s for s in all_stocks
                if abs(s["change_percent"]) > self._STORY_TRIGGER_THRESHOLD
            ]

            result = {
                "gainers": gainers,
                "losers": losers,
                "most_active": most_active,
                "story_triggers": story_triggers,
            }

            logger.info(
                "Fetched market movers: %d gainers, %d losers, %d most active, %d story triggers",
                len(gainers),
                len(losers),
                len(most_active),
                len(story_triggers),
            )
            return result

        except Exception as exc:
            logger.warning("Yahoo Finance unreachable: %s", exc)
            log_error_with_context(
                logger, exc, "fetch_market_movers", {}
            )
            return {}

    def fetch_sector_performance(self) -> List[Dict[str, Any]]:
        """
        Fetch sector ETF performance data.

        Returns:
            List of dicts with keys: sector, symbol, change_percent, volume.

        Note:
            Logs warning and returns empty list if Yahoo Finance is unreachable.
        """
        try:
            symbols = list(self.SECTORS.keys())
            tickers = yf.Tickers(" ".join(symbols))
            results: List[Dict[str, Any]] = []

            for symbol, sector_name in self.SECTORS.items():
                try:
                    ticker = tickers.tickers.get(symbol)
                    if ticker is None:
                        continue
                    info = ticker.fast_info
                    change_pct = self._calc_change_percent(info)
                    results.append({
                        "sector": sector_name,
                        "symbol": symbol,
                        "change_percent": round(change_pct, 2),
                        "volume": int(getattr(info, "last_volume", 0) or 0),
                    })
                except Exception as exc:
                    logger.warning(
                        "Failed to fetch sector ETF %s (%s): %s",
                        symbol, sector_name, exc,
                    )

            logger.info("Fetched performance for %d sectors", len(results))
            return results

        except Exception as exc:
            logger.warning("Yahoo Finance unreachable for sector data: %s", exc)
            log_error_with_context(
                logger, exc, "fetch_sector_performance", {}
            )
            return []

    def enrich_finance_context(
        self, tickers: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetch real-time price data for detected ticker symbols.

        Args:
            tickers: Stock ticker symbols detected from other sources.

        Returns:
            Dict mapping ticker to price data, e.g.:
            {"NVDA": {"price": 130.5, "change_percent": 3.2, "volume": 50000000}}

        Note:
            Logs warning and returns empty dict if Yahoo Finance is unreachable.
        """
        if not tickers:
            return {}

        try:
            result: Dict[str, Dict[str, Any]] = {}
            batch = yf.Tickers(" ".join(tickers))

            for symbol in tickers:
                try:
                    ticker = batch.tickers.get(symbol)
                    if ticker is None:
                        continue
                    info = ticker.fast_info
                    price = float(getattr(info, "last_price", 0) or 0)
                    change_pct = self._calc_change_percent(info)
                    volume = int(getattr(info, "last_volume", 0) or 0)

                    result[symbol] = {
                        "price": round(price, 2),
                        "change_percent": round(change_pct, 2),
                        "volume": volume,
                    }
                except Exception as exc:
                    logger.warning("Failed to enrich ticker %s: %s", symbol, exc)

            logger.info("Enriched %d/%d tickers", len(result), len(tickers))
            return result

        except Exception as exc:
            logger.warning("Yahoo Finance unreachable for ticker enrichment: %s", exc)
            log_error_with_context(
                logger, exc, "enrich_finance_context", {"tickers": tickers}
            )
            return {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_screener(self, screener_key: str) -> List[Dict[str, Any]]:
        """
        Fetch stocks from a yfinance predefined screener.

        Args:
            screener_key: One of 'day_gainers', 'day_losers', 'most_actives'.

        Returns:
            List of stock dicts with standard keys.
        """
        response = yf.screen(screener_key)
        quotes = response.get("quotes", [])
        stocks: List[Dict[str, Any]] = []

        for quote in quotes:
            symbol = quote.get("symbol", "")
            stocks.append({
                "symbol": symbol,
                "name": quote.get("shortName", quote.get("longName", symbol)),
                "price": round(float(quote.get("regularMarketPrice", 0) or 0), 2),
                "change_percent": round(
                    float(quote.get("regularMarketChangePercent", 0) or 0), 2
                ),
                "volume": int(quote.get("regularMarketVolume", 0) or 0),
                "sector": quote.get("sector", "Unknown"),
            })

        return stocks

    @staticmethod
    def _calc_change_percent(fast_info: Any) -> float:
        """
        Calculate daily change percent from yfinance fast_info.

        Args:
            fast_info: yfinance Ticker.fast_info object.

        Returns:
            Change percentage as float.
        """
        prev_close = float(getattr(fast_info, "previous_close", 0) or 0)
        last_price = float(getattr(fast_info, "last_price", 0) or 0)
        if prev_close == 0:
            return 0.0
        return ((last_price - prev_close) / prev_close) * 100.0
