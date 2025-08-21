from flask import Flask, render_template, request
import requests
import json
from datetime import datetime, timedelta

app = Flask(__name__)

# CoinGecko API configuration
COINGECKO_API_KEY = "CG-oUpG62o22KvJGpmC99XE5tRz"
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

# Alternative.me API for Fear & Greed Index
FEAR_GREED_API_URL = "https://api.alternative.me/fng/"

def get_coin_data(coin_id):
    """Fetch detailed coin data from CoinGecko API"""
    headers = {"X-CGI-API-KEY": COINGECKO_API_KEY}
    url = f"{COINGECKO_BASE_URL}/coins/{coin_id}"
    params = {
        "localization": "false",
        "tickers": "false",
        "market_data": "true",
        "community_data": "false",
        "developer_data": "false",
        "sparkline": "false"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None

def search_coins(query):
    """Search for coins by name or symbol"""
    headers = {"X-CGI-API-KEY": COINGECKO_API_KEY}
    url = f"{COINGECKO_BASE_URL}/search"
    params = {"query": query}
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json().get("coins", [])[:10]  # Return top 10 results
    except requests.exceptions.RequestException:
        return []

def get_coin_history(coin_id, days):
    """Fetch historical market data for a coin"""
    headers = {"X-CGI-API-KEY": COINGECKO_API_KEY}
    url = f"{COINGECKO_BASE_URL}/coins/{coin_id}/market_chart"
    params = {
        "vs_currency": "usd",
        "days": days,
        "interval": "daily" if days != "1" else "hourly"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None

def get_global_data():
    """Fetch global cryptocurrency market data"""
    headers = {"X-CGI-API-KEY": COINGECKO_API_KEY}
    url = f"{COINGECKO_BASE_URL}/global"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("data", {})
    except requests.exceptions.RequestException:
        return {}

def get_trending_coins():
    """Fetch trending coins from CoinGecko"""
    headers = {"X-CGI-API-KEY": COINGECKO_API_KEY}
    url = f"{COINGECKO_BASE_URL}/search/trending"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("coins", [])
    except requests.exceptions.RequestException:
        return []

def get_top_coins(limit=10, order="market_cap_desc"):
    """Fetch top coins by market cap"""
    headers = {"X-CGI-API-KEY": COINGECKO_API_KEY}
    url = f"{COINGECKO_BASE_URL}/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": order,
        "per_page": limit,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return []

def get_fear_greed_index():
    """Fetch Fear & Greed Index data"""
    try:
        response = requests.get(FEAR_GREED_API_URL)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])[0] if data.get("data") else {}
    except requests.exceptions.RequestException:
        return {}

@app.route('/', methods=['GET', 'POST'])
def index():
    # Default data
    coin_data = None
    chart_data = None
    volume_data = None
    labels = None
    comparison_data = []
    timeframe = "7"
    
    # Fetch global data, trending coins, and fear & greed index
    global_data = get_global_data()
    trending_coins = get_trending_coins()
    fear_greed_data = get_fear_greed_index()
    
    # Get top gainers and losers
    top_gainers = get_top_coins(limit=5, order="price_change_percentage_24h_desc")
    top_losers = get_top_coins(limit=5, order="price_change_percentage_24h_asc")
    
    if request.method == 'POST':
        # Handle coin search
        if 'search_query' in request.form:
            query = request.form['search_query']
            if query:
                search_results = search_coins(query)
                if search_results:
                    coin_id = search_results[0]['id']
                    coin_data = get_coin_data(coin_id)
        
        # Handle timeframe selection
        if 'timeframe' in request.form:
            timeframe = request.form['timeframe']
            if coin_data:
                history = get_coin_history(coin_data['id'], timeframe)
                if history and 'prices' in history:
                    prices = history['prices']
                    chart_data = [price[1] for price in prices]
                    volume_data = [volume[1] for volume in history['total_volumes']]
                    
                    # Generate labels based on timeframe
                    if timeframe == "1":
                        labels = [datetime.fromtimestamp(price[0]/1000).strftime('%H:%M') for price in prices]
                    else:
                        labels = [datetime.fromtimestamp(price[0]/1000).strftime('%Y-%m-%d') for price in prices]
        
        # Handle coin comparison
        if 'compare_coins' in request.form:
            coin_ids = request.form.getlist('compare_coin')
            for coin_id in coin_ids[:3]:  # Limit to 3 coins
                if coin_id:
                    data = get_coin_data(coin_id)
                    if data:
                        comparison_data.append(data)
    
    # Render the template with all data
    return render_template(
        'index.html',
        coin_data=coin_data,
        chart_data=chart_data,
        volume_data=volume_data,
        labels=labels,
        comparison_data=comparison_data,
        global_data=global_data,
        trending_coins=trending_coins,
        fear_greed_data=fear_greed_data,
        top_gainers=top_gainers,
        top_losers=top_losers,
        timeframe=timeframe
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
