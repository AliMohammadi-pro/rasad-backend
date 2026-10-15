import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    User,
    EmailVerification,
    PasswordReset,
    Asset,
    MarketPrice,
    MarketCandle,
    Watchlist,
    Wallet,
    WalletBalance,
    Transaction,
    Deposit,
    PortfolioSnapshot,
    Alert,
    Withdrawal,
    PushToken,
    Feedback
)

from app.routers import auth
from app.routers.economic_calendar import router as economic_calendar_router
from app.routers import alerts
from app.routers import portfolio
from app.routers import user
from app.routers import economic
from app.routers import trading
from app.routers import watchlist
from app.routers import market
from app.routers import prices
from app.routers import feedback

from app.services.market_updater import update_market_prices
from app.services.portfolio_snapshot_updater import (
    start_portfolio_snapshot_updater
)


# ============================================================
# FastAPI
# ============================================================

app = FastAPI(
    title="Crypto Market API",
    description="Backend API for Crypto Market Simulator",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://localhost",
    "http://localhost",
    "capacitor://localhost",
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Routers
# ============================================================

app.include_router(trading.router)
app.include_router(alerts.router)
app.include_router(economic.router)
app.include_router(portfolio.router)
app.include_router(economic_calendar_router)
app.include_router(auth.router)
app.include_router(watchlist.router)
app.include_router(user.router)
app.include_router(market.router)
app.include_router(prices.router)
app.include_router(feedback.router)


# ============================================================
# Startup
# ============================================================
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(
        update_market_prices(),
        name="market-updater"
    )
    start_portfolio_snapshot_updater()
# ============================================================
# Root
# ============================================================

@app.get("/")
def root():
    return {
        "message": "Crypto Market API is running",
        "status": "ok"
    }


# ============================================================
# Health
# ============================================================

@app.get("/api/health")
def health():
    return {
        "status": "healthy"
    }


# ============================================================
# Database status
# ============================================================

@app.get("/api/database")
def database_status():
    return {
        "status": "connected",
        "database": "crypto_market"
    }