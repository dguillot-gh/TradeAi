from fastapi import APIRouter, HTTPException
import yfinance as yf
from services.database import get_connection, mark_suggestion_actioned
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/market-pulse")
def get_market_pulse():
    indices = {
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "Dow Jones": "^DJI"
    }
    
    results = []
    try:
        tickers = yf.Tickers(" ".join(indices.values()))
        for name, symbol in indices.items():
            try:
                info = tickers.tickers[symbol].fast_info
                last_price = info.last_price
                prev_close = info.previous_close
                pct_change = ((last_price - prev_close) / prev_close) * 100
                
                results.append({
                    "name": name,
                    "price": round(last_price, 2),
                    "percent_change": round(pct_change, 2),
                    "is_up": pct_change >= 0
                })
            except Exception:
                pass
        return results
    except Exception as e:
        logger.error(f"Failed to fetch market pulse: {e}")
        return []

@router.get("/deepdive/{symbol}")
def get_deepdive_data(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        
        # 1-month historical data (daily)
        hist = ticker.history(period="1mo")
        history_data = []
        if not hist.empty:
            for index, row in hist.iterrows():
                history_data.append({
                    "date": index.strftime("%Y-%m-%d"),
                    "close": float(row["Close"])
                })

        # Fundamentals
        info = ticker.info
        fundamentals = {
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "recommendation": info.get("recommendationKey", "none").replace("_", " ").title()
        }

        # News (limit to 3)
        news_items = []
        try:
            raw_news = ticker.news
            if raw_news:
                for n in raw_news[:3]:
                    news_items.append({
                        "title": n.get("title", ""),
                        "publisher": n.get("publisher", ""),
                        "link": n.get("link", "")
                    })
        except Exception as e:
            logger.error(f"Failed to fetch news for {symbol}: {e}")

        return {
            "symbol": symbol,
            "current_price": ticker.fast_info.last_price if hasattr(ticker.fast_info, 'last_price') else None,
            "history": history_data,
            "fundamentals": fundamentals,
            "news": news_items
        }

    except Exception as e:
        logger.error(f"Deep dive error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch deep dive data")

@router.post("/suggestions/{suggestion_id}/action")
def action_suggestion(suggestion_id: int):
    success = mark_suggestion_actioned(suggestion_id)
    if not success:
        raise HTTPException(status_code=404, detail="Suggestion not found or could not be updated")
    return {"status": "success", "message": "Trade marked as executed"}

@router.get("/performance")
def get_performance():
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, symbol, action, price_at_suggestion, is_actioned, generated_at
            FROM suggestions
            WHERE price_at_suggestion IS NOT NULL
            ORDER BY generated_at DESC
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            return {"theoretical": {"win_rate": 0, "average_return": 0}, "actual": {"win_rate": 0, "average_return": 0}, "ledger": []}

        ledger = []
        
        # Batch fetch current prices to save time
        symbols = list(set([r["symbol"] for r in rows]))
        current_prices = {}
        if symbols:
            tickers = yf.Tickers(" ".join(symbols))
            for sym in symbols:
                try:
                    current_prices[sym] = tickers.tickers[sym].fast_info.last_price
                except Exception:
                    current_prices[sym] = None

        theoretical_wins = 0
        theoretical_total = 0
        theoretical_returns = 0.0

        actual_wins = 0
        actual_total = 0
        actual_returns = 0.0

        for r in rows:
            sym = r["symbol"]
            start_price = float(r["price_at_suggestion"])
            curr_price = current_prices.get(sym)
            
            if not curr_price:
                continue

            curr_price = float(curr_price)
            
            # Calculate return %
            # If AI said Buy, we want price to go UP. If Sell, we want price to go DOWN.
            if r["action"].lower() == "buy":
                ret_pct = ((curr_price - start_price) / start_price) * 100
            else: # Sell
                ret_pct = ((start_price - curr_price) / start_price) * 100

            is_win = ret_pct > 0

            ledger.append({
                "id": r["id"],
                "symbol": sym,
                "action": r["action"],
                "suggested_price": start_price,
                "current_price": curr_price,
                "return_percent": round(ret_pct, 2),
                "is_actioned": r["is_actioned"],
                "generated_at": r["generated_at"].isoformat()
            })

            # Theoretical stats
            theoretical_total += 1
            if is_win: theoretical_wins += 1
            theoretical_returns += ret_pct

            # Actual stats
            if r["is_actioned"]:
                actual_total += 1
                if is_win: actual_wins += 1
                actual_returns += ret_pct

        return {
            "theoretical": {
                "win_rate": round((theoretical_wins / theoretical_total * 100), 2) if theoretical_total > 0 else 0,
                "average_return": round((theoretical_returns / theoretical_total), 2) if theoretical_total > 0 else 0,
                "total_trades": theoretical_total
            },
            "actual": {
                "win_rate": round((actual_wins / actual_total * 100), 2) if actual_total > 0 else 0,
                "average_return": round((actual_returns / actual_total), 2) if actual_total > 0 else 0,
                "total_trades": actual_total
            },
            "ledger": ledger
        }

    except Exception as e:
        logger.error(f"Performance error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch performance data")
