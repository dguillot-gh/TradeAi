import os
import uuid
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import pytz

logger = logging.getLogger(__name__)

ET = pytz.timezone("US/Eastern")

# Market schedule constants (Eastern Time)
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16
MARKET_CLOSE_MINUTE = 0

_connection_pool = None


def get_connection():
    """Get a database connection using the DATABASE_URL env var."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)


def init_db():
    """Create the suggestions table if it doesn't exist."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS suggestions (
                id SERIAL PRIMARY KEY,
                batch_id UUID NOT NULL,
                symbol VARCHAR(10) NOT NULL,
                action VARCHAR(20) NOT NULL,
                confidence VARCHAR(20) NOT NULL,
                reason TEXT NOT NULL,
                price_at_suggestion DECIMAL(12, 4),
                generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                portfolio_context JSONB,
                is_actioned BOOLEAN NOT NULL DEFAULT FALSE
            );
        """)
        
        # Safe migration if table exists but column doesn't
        cur.execute("""
            ALTER TABLE suggestions ADD COLUMN IF NOT EXISTS is_actioned BOOLEAN NOT NULL DEFAULT FALSE;
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_suggestions_generated_at
            ON suggestions(generated_at DESC);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_suggestions_batch_id
            ON suggestions(batch_id);
        """)
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Database initialized successfully — suggestions table ready.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def save_suggestions(suggestions: list, portfolio_context: dict = None) -> dict:
    """
    Save a batch of AI suggestions to the database.
    Returns the saved batch with metadata.
    """
    batch_id = str(uuid.uuid4())
    now = datetime.now(pytz.utc)

    try:
        conn = get_connection()
        cur = conn.cursor()

        saved_suggestions = []
        for s in suggestions:
            cur.execute(
                """
                INSERT INTO suggestions (batch_id, symbol, action, confidence, reason, price_at_suggestion, generated_at, portfolio_context)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    batch_id,
                    s.get("symbol", ""),
                    s.get("action", ""),
                    s.get("confidence", ""),
                    s.get("reason", ""),
                    s.get("price_at_suggestion"),
                    now,
                    psycopg2.extras.Json(portfolio_context) if portfolio_context else None,
                ),
            )
            inserted_id = cur.fetchone()["id"]
            
            # Add the ID back into the dictionary so the frontend gets it
            saved_s = dict(s)
            saved_s["id"] = inserted_id
            saved_s["is_actioned"] = False
            saved_suggestions.append(saved_s)

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"Saved {len(suggestions)} suggestions with batch_id={batch_id}")
        return {
            "batch_id": batch_id,
            "generated_at": now.isoformat(),
            "suggestions": saved_suggestions,
        }
    except Exception as e:
        logger.error(f"Failed to save suggestions: {e}")
        raise


def get_latest_suggestions() -> dict | None:
    """
    Fetch the most recent batch of suggestions.
    Returns None if no suggestions exist.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Get the most recent batch_id
        cur.execute(
            """
            SELECT batch_id, generated_at
            FROM suggestions
            ORDER BY generated_at DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return None

        batch_id = row["batch_id"]
        generated_at = row["generated_at"]

        # Get all suggestions in that batch
        cur.execute(
            """
            SELECT id, symbol, action, confidence, reason, price_at_suggestion, is_actioned
            FROM suggestions
            WHERE batch_id = %s
            ORDER BY id
            """,
            (str(batch_id),),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        suggestions = []
        for r in rows:
            suggestions.append({
                "id": r["id"],
                "symbol": r["symbol"],
                "action": r["action"],
                "confidence": r["confidence"],
                "reason": r["reason"],
                "price_at_suggestion": float(r["price_at_suggestion"]) if r["price_at_suggestion"] else None,
                "is_actioned": r["is_actioned"],
            })

        return {
            "batch_id": str(batch_id),
            "generated_at": generated_at.isoformat(),
            "suggestions": suggestions,
        }
    except Exception as e:
        logger.error(f"Failed to fetch latest suggestions: {e}")
        return None


def get_suggestions_history(limit: int = 3) -> list:
    """
    Fetch the most recent N batches of suggestions for AI memory context.
    Returns a list of batches, each with metadata and suggestions.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Get distinct recent batch_ids
        cur.execute(
            """
            SELECT DISTINCT batch_id, MIN(generated_at) as generated_at
            FROM suggestions
            GROUP BY batch_id
            ORDER BY generated_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        batches = cur.fetchall()

        if not batches:
            cur.close()
            conn.close()
            return []

        result = []
        for batch in batches:
            cur.execute(
                """
                SELECT id, symbol, action, confidence, reason, price_at_suggestion, is_actioned
                FROM suggestions
                WHERE batch_id = %s
                ORDER BY id
                """,
                (str(batch["batch_id"]),),
            )
            rows = cur.fetchall()
            result.append({
                "batch_id": str(batch["batch_id"]),
                "generated_at": batch["generated_at"].isoformat(),
                "suggestions": [
                    {
                        "id": r["id"],
                        "symbol": r["symbol"],
                        "action": r["action"],
                        "confidence": r["confidence"],
                        "reason": r["reason"],
                        "price_at_suggestion": float(r["price_at_suggestion"]) if r["price_at_suggestion"] else None,
                        "is_actioned": r["is_actioned"],
                    }
                    for r in rows
                ],
            })

        cur.close()
        conn.close()
        return result
    except Exception as e:
        logger.error(f"Failed to fetch suggestion history: {e}")
        return []


def get_latest_batch_time() -> datetime | None:
    """Return the timestamp of the most recent suggestion batch, or None."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT MAX(generated_at) as latest FROM suggestions")
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row and row["latest"]:
            return row["latest"]
        return None
    except Exception as e:
        logger.error(f"Failed to fetch latest batch time: {e}")
        return None


def is_trading_day(dt: datetime) -> bool:
    """Check if a given datetime falls on a weekday (Mon-Fri). Does not account for holidays."""
    return dt.weekday() < 5


def suggestions_are_stale() -> bool:
    """
    Determine if current suggestions need to be refreshed based on market schedule.

    Refresh windows (Eastern Time):
    - After 9:30 AM ET if last batch was before 9:30 AM ET today
    - After 4:00 PM ET if last batch was before 4:00 PM ET today
    """
    last_generated = get_latest_batch_time()
    if last_generated is None:
        return True  # No suggestions at all — definitely stale

    now_et = datetime.now(ET)

    if not is_trading_day(now_et):
        return False  # Weekend — don't auto-refresh

    last_generated_et = last_generated.astimezone(ET)

    # Today's market open and close in ET
    today_open = now_et.replace(
        hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0
    )
    today_close = now_et.replace(
        hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0
    )

    # If we're past market open and last generation was before today's open
    if now_et >= today_open and last_generated_et < today_open:
        logger.info("Suggestions are stale — market open refresh needed.")
        return True

    # If we're past market close and last generation was before today's close
    if now_et >= today_close and last_generated_et < today_close:
        logger.info("Suggestions are stale — market close refresh needed.")
        return True

    return False

def mark_suggestion_actioned(suggestion_id: int) -> bool:
    """
    Mark a specific suggestion as executed by the user.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            UPDATE suggestions
            SET is_actioned = TRUE
            WHERE id = %s
            RETURNING id
            """,
            (suggestion_id,)
        )
        row = cur.fetchone()
        
        conn.commit()
        cur.close()
        conn.close()
        
        return row is not None
    except Exception as e:
        logger.error(f"Failed to mark suggestion as actioned: {e}")
        return False
