from fastapi import APIRouter
from models.schemas import ChatRequest, ChatResponse
import services.gemini as gemini_service
from services.gemini import analyze_market_query, generate_trade_suggestions
from services.robinhood import get_portfolio_holdings
from services.database import (
    get_latest_suggestions,
    get_suggestions_history,
    save_suggestions,
    suggestions_are_stale,
)
import logging
import yfinance as yf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Advisor"])

@router.get("/quota")
def get_ai_quota():
    return {
        "total_tokens_used": gemini_service.TOTAL_TOKENS_USED,
        "estimated_limit": 1000000
    }

def _generate_and_save_suggestions() -> dict:
    """
    Generate fresh suggestions from Gemini with memory context, 
    save them to the database, and return the result.
    """
    # Get portfolio context
    portfolio = get_portfolio_holdings()
    simplified_portfolio = (
        {symbol: data.get("quantity") for symbol, data in portfolio.items()}
        if portfolio
        else {}
    )

    # Get previous suggestions for AI memory
    previous_batches = get_suggestions_history(limit=3)

    # Generate new suggestions with memory context
    suggestions = generate_trade_suggestions(
        portfolio_context=simplified_portfolio,
        previous_suggestions=previous_batches,
    )

    if not suggestions:
        return {
            "suggestions": [],
            "generated_at": None,
            "is_fresh": True,
        }

    # Fetch real-time prices for the suggestions so we can grade them later
    for s in suggestions:
        try:
            symbol = s.get("symbol")
            if symbol:
                ticker = yf.Ticker(symbol)
                # Fast way to get current price
                info = ticker.fast_info
                s["price_at_suggestion"] = info.last_price
        except Exception as e:
            logger.error(f"Failed to fetch price for {s.get('symbol')}: {e}")
            s["price_at_suggestion"] = None

    # Save to database
    saved = save_suggestions(suggestions, portfolio_context=simplified_portfolio)

    return {
        "suggestions": saved["suggestions"],
        "generated_at": saved["generated_at"],
        "is_fresh": True,
    }


@router.get("/suggestions")
def get_ai_suggestions():
    """
    Returns cached suggestions unless they are stale (past a market open/close window).
    If stale or no cache exists, regenerates and saves new suggestions.
    """
    # Check if we need to refresh
    if suggestions_are_stale():
        logger.info("Suggestions are stale — regenerating...")
        return _generate_and_save_suggestions()

    # Return cached suggestions
    cached = get_latest_suggestions()
    if cached:
        return {
            "suggestions": cached["suggestions"],
            "generated_at": cached["generated_at"],
            "is_fresh": False,
        }

    # No cache at all — generate fresh
    logger.info("No cached suggestions found — generating first batch...")
    return _generate_and_save_suggestions()


@router.post("/suggestions/refresh")
def refresh_ai_suggestions():
    """
    Force regenerate suggestions regardless of staleness.
    Called when the user taps the manual 'Refresh Suggestions' button.
    """
    logger.info("Manual suggestion refresh triggered by user.")
    return _generate_and_save_suggestions()


@router.post("/chat", response_model=ChatResponse)
def chat_with_advisor(request: ChatRequest):
    # Fetch current portfolio context to pass to the AI
    portfolio = get_portfolio_holdings()
    
    # We only pass keys/symbols to save tokens, or we can pass the whole thing
    simplified_portfolio = {symbol: data.get("quantity") for symbol, data in portfolio.items()} if portfolio else {}
    
    reply = analyze_market_query(request.message, portfolio_context=simplified_portfolio)
    
    return ChatResponse(reply=reply)
