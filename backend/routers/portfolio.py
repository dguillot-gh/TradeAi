from fastapi import APIRouter, HTTPException
from services.robinhood import get_portfolio_holdings, get_account_buying_power, get_portfolio_summary

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])

@router.get("/holdings")
def get_holdings():
    return get_portfolio_holdings()

@router.get("/buying_power")
def get_buying_power():
    bp = get_account_buying_power()
    if bp is None:
        raise HTTPException(status_code=401, detail="Not authenticated with Robinhood")
    return {"buying_power": bp}

@router.get("/summary")
def get_summary():
    summary = get_portfolio_summary()
    if summary is None:
        raise HTTPException(status_code=401, detail="Not authenticated with Robinhood")
    return summary
