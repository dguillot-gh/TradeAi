import robin_stocks.robinhood as r
import logging

logger = logging.getLogger(__name__)

def login_to_robinhood(username: str, password: str, mfa_code: str = None):
    try:
        kwargs = {"expiresIn": 86400}
        if mfa_code:
            kwargs["mfa_code"] = mfa_code
            
        # login might still try to prompt standard input if mfa_code is not passed and MFA is required.
        # For an API, this isn't ideal, but robin_stocks is limited here.
        res = r.login(username, password, **kwargs)
        
        return {"success": True, "message": "Logged in successfully", "requires_mfa": False}
    except Exception as e:
        logger.error(f"Robinhood login error: {e}")
        # If EOFError happens, it means it tried to prompt for MFA via stdin because we didn't provide one.
        # So it requires MFA. If we DID provide one and it failed, the code was probably wrong.
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
