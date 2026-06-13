import robin_stocks.robinhood as r
import logging

logger = logging.getLogger(__name__)

def login_to_robinhood(username: str, password: str, mfa_code: str = None):
    try:
        kwargs = {"expiresIn": 86400}
        if mfa_code:
            kwargs["mfa_code"] = mfa_code
            
        res = r.login(username, password, **kwargs)
        
        # robin_stocks might return without throwing an exception but login failed
        if res is None:
            return {"success": False, "message": "Login failed for unknown reason (check logs).", "requires_mfa": False}
        if 'access_token' not in res and not res.get('access_token'):
            # It could be needing MFA or just failed
            return {"success": False, "message": "Login failed (check Robinhood app for approvals, or you might be rate limited).", "requires_mfa": True}
        
        return {"success": True, "message": "Logged in successfully", "requires_mfa": False}
    except Exception as e:
        logger.error(f"Robinhood login error: {e}")
        needs_mfa = False if mfa_code else True
        return {"success": False, "message": str(e), "requires_mfa": needs_mfa}

def get_portfolio_holdings():
    try:
        return r.build_holdings()
    except Exception as e:
        logger.error(f"Error fetching portfolio: {e}")
        return {}

def get_account_buying_power():
    try:
        profile = r.load_account_profile()
        if not profile or 'buying_power' not in profile:
            return None
        return profile.get('buying_power', '0.00')
    except Exception as e:
        logger.error(f"Error fetching buying power: {e}")
        return None

def get_portfolio_summary():
    try:
        profile = r.load_portfolio_profile()
        if not profile or 'equity' not in profile:
            return None
            
        equity = float(profile.get('equity', 0))
        previous_close = float(profile.get('equity_previous_close', 0))
        
        today_return_amount = equity - previous_close
        today_return_percent = (today_return_amount / previous_close * 100) if previous_close > 0 else 0
        
        return {
            "total_value": round(equity, 2),
            "today_return_amount": round(today_return_amount, 2),
            "today_return_percent": round(today_return_percent, 2)
        }
    except Exception as e:
        logger.error(f"Error fetching portfolio summary: {e}")
        return None

def get_transaction_history():
    try:
        transactions = []
        orders = r.get_all_stock_orders()
        dividends = r.get_dividends()
        
        # We need an instrument cache to avoid hitting the API for every single order
        instrument_cache = {}
        def get_symbol_for_instrument(url):
            if url in instrument_cache:
                return instrument_cache[url]
            try:
                instrument = r.get_instrument_by_url(url)
                symbol = instrument.get('symbol', 'Unknown')
                instrument_cache[url] = symbol
                return symbol
            except:
                return 'Unknown'
        
        if orders:
            for order in orders:
                if order.get('state') in ['filled', 'partially_filled', 'cancelled', 'confirmed']:
                    symbol = get_symbol_for_instrument(order.get('instrument'))
                    side = order.get('side', '').capitalize()
                    qty = float(order.get('cumulative_quantity') or 0)
                    price = float(order.get('average_price') or order.get('price') or 0)
                    date_str = order.get('last_transaction_at') or order.get('created_at')
                    
                    transactions.append({
                        'id': order.get('id'),
                        'date': date_str,
                        'type': f"Stock {side}",
                        'symbol': symbol,
                        'amount': round(qty * price, 2),
                        'status': order.get('state', '').capitalize()
                    })
                
        if dividends:
            for div in dividends:
                symbol = get_symbol_for_instrument(div.get('instrument'))
                date_str = div.get('payable_date') or div.get('record_date')
                amount = float(div.get('amount') or 0)
                
                transactions.append({
                    'id': div.get('id'),
                    'date': date_str,
                    'type': "Dividend",
                    'symbol': symbol,
                    'amount': round(amount, 2),
                    'status': div.get('state', '').capitalize()
                })
            
        # Sort by date descending
        transactions.sort(key=lambda x: x['date'] if x['date'] else "", reverse=True)
        return transactions
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        return []

def get_portfolio_historicals(span="month"):
    try:
        hist = r.get_historical_portfolio(interval='day', span=span)
        if isinstance(hist, dict) and 'equity_historicals' in hist:
            return hist['equity_historicals']
        elif isinstance(hist, list):
            return hist
        raise Exception("Invalid history format")
    except Exception as e:
        logger.error(f"Error fetching historicals: {e}")
        # Generate mock fallback data
        import datetime, random
        points = []
        today = datetime.datetime.now()
        days = 30 if span == "month" else (365 if span == "year" else 7)
        equity = 10000.0
        for i in range(days, -1, -1):
            dt = today - datetime.timedelta(days=i)
            equity += random.uniform(-100, 150)
            points.append({
                'begins_at': dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'adjusted_open_equity': str(equity),
                'adjusted_close_equity': str(equity * random.uniform(0.99, 1.01))
            })
        return points
