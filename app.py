# app.py
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import httpx
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Crypto Analysis Service", version="1.0.0")

# Mount static files (for frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Keys
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")
SOLSCAN_API_TOKEN = os.getenv("SOLSCAN_API_TOKEN")

# Headers for APIs
COINGECKO_HEADERS = {"x-cg-pro-api-key": COINGECKO_API_KEY} if COINGECKO_API_KEY else {}
SOLSCAN_HEADERS = {"Authorization": f"Bearer {SOLSCAN_API_TOKEN}"} if SOLSCAN_API_TOKEN else {}

# Base URLs
COINGECKO_BASE_URL = "https://pro-api.coingecko.com/api/v3"
SOLSCAN_BASE_URL = "https://public-api.solscan.io"

# Health check endpoint
@app.get("/")
async def root():
    return {"status": "healthy", "message": "Crypto Analysis Service is running"}

# Search coins endpoint
@app.get("/api/search")
async def search_coins(q: str):
    if not q:
        return {"suggestions": []}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{COINGECKO_BASE_URL}/search",
                params={"query": q},
                headers=COINGECKO_HEADERS,
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            
            # Return top 10 coins
            coins = data.get("coins", [])[:10]
            return {"suggestions": coins}
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data from CoinGecko: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="CoinGecko API error")

# Price data endpoint
@app.get("/api/price/{coin_id}")
async def get_price_data(coin_id: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{COINGECKO_BASE_URL}/simple/price",
                params={"ids": coin_id, "vs_currencies": "usd", "include_market_cap": "true", "include_24hr_change": "true"},
                headers=COINGECKO_HEADERS,
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            
            if coin_id not in data:
                raise HTTPException(status_code=404, detail="Coin not found")
            
            coin_data = data[coin_id]
            return {
                "price": coin_data.get("usd"),
                "market_cap": coin_data.get("usd_market_cap"),
                "change_24h": coin_data.get("usd_24h_change")
            }
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error fetching price data: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="CoinGecko API error")

# Chart data endpoint
@app.get("/api/chart/{coin_id}")
async def get_chart_data(coin_id: str, days: int = 1):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{COINGECKO_BASE_URL}/coins/{coin_id}/market_chart",
                params={"vs_currency": "usd", "days": days, "interval": "hourly"},
                headers=COINGECKO_HEADERS,
                timeout=15.0
            )
            response.raise_for_status()
            data = response.json()
            
            # Format the data for Chart.js
            prices = data.get("prices", [])
            formatted_data = [
                {"time": datetime.fromtimestamp(price[0] / 1000).strftime("%Y-%m-%d %H:%M"), "price": price[1]}
                for price in prices
            ]
            
            return {"prices": formatted_data}
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error fetching chart data: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="CoinGecko API error")

# Solana token data endpoint
@app.get("/api/solana/{mint}")
async def get_solana_token_data(mint: str):
    try:
        async with httpx.AsyncClient() as client:
            # Get token metadata
            token_response = await client.get(
                f"{SOLSCAN_BASE_URL}/token/meta",
                params={"tokenAddress": mint},
                headers=SOLSCAN_HEADERS,
                timeout=10.0
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            
            # Get token holders
            holders_response = await client.get(
                f"{SOLSCAN_BASE_URL}/token/holders",
                params={"tokenAddress": mint, "limit": 10, "offset": 0},
                headers=SOLSCAN_HEADERS,
                timeout=10.0
            )
            holders_data = holders_response.json() if holders_response.status_code == 200 else {}
            
            # Get recent transactions
            transfers_response = await client.get(
                f"{SOLSCAN_BASE_URL}/token/transfers",
                params={"tokenAddress": mint, "limit": 5},
                headers=SOLSCAN_HEADERS,
                timeout=10.0
            )
            transfers_data = transfers_response.json() if transfers_response.status_code == 200 else {}
            
            return {
                "metadata": token_data,
                "top_holders": holders_data.get("data", [])[:5],
                "recent_transfers": transfers_data.get("data", [])[:5]
            }
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error fetching Solana data: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Solscan API error")

# Serve frontend
@app.get("/frontend")
async def serve_frontend():
    return FileResponse("static/index.html")

# For Render deployment
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
