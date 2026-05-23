from fastapi import FastAPI
import os
import logging
from dotenv import load_dotenv
from routers import auth, portfolio, ai, analytics
from services.database import init_db

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Stock Trading API")

app.include_router(auth.router)
app.include_router(portfolio.router)
app.include_router(ai.router)
app.include_router(analytics.router)

@app.on_event("startup")
def startup_event():
    logger.info("Initializing database...")
    init_db()
    logger.info("Database ready.")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "API is running"}
