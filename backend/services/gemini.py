import os
import json
from google import genai
from google.genai import types
import logging

logger = logging.getLogger(__name__)

# Global token tracker
TOTAL_TOKENS_USED = 0

def analyze_market_query(query: str, portfolio_context: dict = None):
    global TOTAL_TOKENS_USED
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "Error: GEMINI_API_KEY is not set."
            
        client = genai.Client(api_key=api_key)
        
        system_instruction = "You are an AI financial advisor. Provide analysis and stock suggestions based on market trends. Do not execute trades, only suggest."
        
        context = f"User Portfolio Context: {portfolio_context}\n\n" if portfolio_context else ""
        prompt = context + f"User Query: {query}"
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
            ),
        )
        
        if response.usage_metadata:
            TOTAL_TOKENS_USED += getattr(response.usage_metadata, 'total_token_count', 0)
            
        return response.text
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return f"Error connecting to AI advisor: {str(e)}"

def _build_memory_context(previous_suggestions: list = None) -> str:
    """
    Build a memory context string from previous suggestion batches
    so the AI can reference its own history and maintain consistency.
    """
    if not previous_suggestions:
        return ""

    lines = ["## Your Previous Suggestions (for context — maintain consistency):\n"]
    for batch in previous_suggestions:
        generated_at = batch.get("generated_at", "Unknown time")
        lines.append(f"### Batch from {generated_at}:")
        for s in batch.get("suggestions", []):
            price_str = f" at ${s['price_at_suggestion']:.2f}" if s.get("price_at_suggestion") else ""
            actioned_str = " [USER EXECUTED THIS TRADE]" if s.get("is_actioned") else ""
            lines.append(
                f"- {s.get('action', '?')} {s.get('symbol', '?')}{price_str}{actioned_str} "
                f"({s.get('confidence', '?')} confidence) — \"{s.get('reason', '')}\""
            )
        lines.append("")

    lines.append(
        "CRITICAL INSTRUCTION: If a past suggestion is marked with [USER EXECUTED THIS TRADE], the user has already taken your advice. "
        "Do NOT suggest that same exact trade again. You must suggest completely NEW trades to expand their portfolio. "
        "If a past suggestion was not executed, you may reiterate it if it's still a good idea, or provide new ones.\n"
    )
    return "\n".join(lines)


def generate_trade_suggestions(portfolio_context: dict = None, previous_suggestions: list = None):
    global TOTAL_TOKENS_USED
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return []
            
        client = genai.Client(api_key=api_key)

        memory_context = _build_memory_context(previous_suggestions)
        
        system_instruction = f"""You are an AI financial advisor. Based on current market conditions and the user's specific portfolio holdings, provide exactly 2 stock trade suggestions.
        If their portfolio is overly concentrated in one sector, suggest diversifying. If they hold a risky asset, suggest taking profits. 
        
        CRITICAL RULE: If you suggest a "Sell" action, it MUST be for a stock the user currently holds in their portfolio context. Do NOT suggest selling stocks they do not own (no short selling).
        
{memory_context}
        
        Respond ONLY with a valid JSON array of objects with keys: symbol, action, confidence, reason. Example:
        [{{"symbol": "AAPL", "action": "Buy", "confidence": "High", "reason": "Diversifies your portfolio."}}]"""
        
        context = f"User Portfolio Context: {portfolio_context}\n\n" if portfolio_context else ""
        prompt = context + "Generate 2 stock trade suggestions."
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json"
            ),
        )
        
        if response.usage_metadata:
            TOTAL_TOKENS_USED += getattr(response.usage_metadata, 'total_token_count', 0)
            
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Gemini API error generating suggestions: {e}")
        return []
