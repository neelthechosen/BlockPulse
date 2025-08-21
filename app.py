from flask import Flask, render_template, request, jsonify
import requests
import json
from datetime import datetime, timedelta

app = Flask(__name__)

# CoinGecko API configuration
API_KEY = "CG-oUpG62o22KvJGpmC99XE5tRz"
BASE_URL = "https://api.coingecko.com/api/v3"
HEADERS = {
    "Accepts": "application/json",
    "X-CG-Pro-API-Key": API_KEY
}

def make_api_request(endpoint, params=None):
    """Helper function to make API requests to CoinGecko"""
    try:
        url = f"{BASE_URL}{endpoint}"
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API request error: {e}")
        return None

@app.route('/')
def index():
    """Render the main dashboard page"""
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search_coin():
    """Search for a cryptocurrency"""
    query = request.form.get('query', '').strip().lower()
    
    if not query:
        return jsonify({"error": "Please enter a coin name or symbol"})
    
    # Get all coins list to search through
    coins_list = make_api_request("/coins/list")
    if not coins_list:
        return jsonify({"error": "Could not fetch coins list"})
    
    # Filter coins by name or symbol
    matched_coins = [
        coin for coin in coins_list 
        if query in coin['name'].lower() or query in coin['symbol'].lower()
    ][:10]  # Limit to 10 results
    
    return jsonify({"results": matched_coins})

@app.route('/coin/<coin_id>')
def get_coin_data(coin_id):
    """Get detailed data for a specific coin"""
    params = {
        "localization": "false",
        "tickers": "false",
        "market_data": "true",
        "community_data": "false",
        "developer_data": "false",
        "sparkline": "false"
    }
    
    coin_data = make_api_request(f"/coins/{coin_id}", params)
    if not coin_data:
        return jsonify({"error": "Could not fetch coin data"})
    
    # Extract relevant information
    result = {
        "name": coin_data.get("name", "N/A"),
        "symbol": coin_data.get("symbol", "N/A").upper(),
        "price": coin_data.get("market_data", {}).get("current_price", {}).get("usd", "N/A"),
        "market_cap": coin_data.get("market_data", {}).get("market_cap", {}).get("usd", "N/A"),
        "volume_24h": coin_data.get("market_data", {}).get("total_volume", {}).get("usd", "N/A"),
        "circulating_supply": coin_data.get("market_data", {}).get("circulating_supply", "N/A"),
        "max_supply": coin_data.get("market_data", {}).get("max_supply", "N/A"),
        "price_change_24h": coin_data.get("market_data", {}).get("price_change_percentage_24h", "N/A")
    }
    
    return jsonify(result)

@app.route('/historical/<coin_id>')
def get_historical_data(coin_id):
    """Get historical price and volume data for charts"""
    # Get price data for 30 days
    price_params = {
        "vs_currency": "usd",
        "days": "30",
        "interval": "daily"
    }
    
    price_data = make_api_request(f"/coins/{coin_id}/market_chart", price_params)
    if not price_data:
        return jsonify({"error": "Could not fetch historical data"})
    
    # Get volume data for 7 days
    volume_params = {
        "vs_currency": "usd",
        "days": "7"
    }
    
    volume_data = make_api_request(f"/coins/{coin_id}/market_chart", volume_params)
    
    # Process price data
    prices = []
    price_dates = []
    
    if 'prices' in price_data:
        for point in price_data['prices']:
            timestamp, price = point
            price_dates.append(datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d'))
            prices.append(price)
    
    # Process volume data
    volumes = []
    volume_dates = []
    
    if 'total_volumes' in volume_data:
        for point in volume_data['total_volumes'][-7:]:  # Last 7 days
            timestamp, volume = point
            volume_dates.append(datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d'))
            volumes.append(volume)
    
    return jsonify({
        "price_dates": price_dates,
        "prices": prices,
        "volume_dates": volume_dates,
        "volumes": volumes
    })

@app.route('/global')
def get_global_data():
    """Get global cryptocurrency market data"""
    global_data = make_api_request("/global")
    if not global_data:
        return jsonify({"error": "Could not fetch global data"})
    
    data = global_data.get("data", {})
    return jsonify({
        "total_market_cap": data.get("total_market_cap", {}).get("usd", "N/A"),
        "btc_dominance": data.get("market_cap_percentage", {}).get("btc", "N/A"),
        "active_cryptocurrencies": data.get("active_cryptocurrencies", "N/A"),
        "markets": data.get("markets", "N/A")
    })

@app.route('/trending')
def get_trending():
    """Get trending coins"""
    trending_data = make_api_request("/search/trending")
    if not trending_data:
        return jsonify({"error": "Could not fetch trending data"})
    
    trending_coins = []
    for coin in trending_data.get("coins", [])[:10]:  # Top 10 trending
        coin_data = coin.get("item", {})
        trending_coins.append({
            "name": coin_data.get("name", "N/A"),
            "symbol": coin_data.get("symbol", "N/A"),
            "market_cap_rank": coin_data.get("market_cap_rank", "N/A"),
            "score": coin_data.get("score", "N/A")
        })
    
    return jsonify({"trending": trending_coins})

@app.route('/top_movers')
def get_top_movers():
    """Get top gainers and losers"""
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h"
    }
    
    coins_data = make_api_request("/coins/markets", params)
    if not coins_data:
        return jsonify({"error": "Could not fetch top movers data"})
    
    # Sort by 24h change to get gainers and losers
    sorted_coins = sorted(coins_data, key=lambda x: x.get("price_change_percentage_24h", 0), reverse=True)
    
    top_gainers = sorted_coins[:10]  # Top 10 gainers
    top_losers = sorted_coins[-10:]  # Top 10 losers
    top_losers.reverse()  # Show worst first
    
    return jsonify({
        "gainers": top_gainers,
        "losers": top_losers
    })

if __name__ == '__main__':
    app.run(debug=True)
