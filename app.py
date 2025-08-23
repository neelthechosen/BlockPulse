from flask import Flask, render_template, jsonify, request
import requests
import json
from datetime import datetime, timedelta

app = Flask(__name__)

COINGECKO_API_KEY = "CG-oUpG62o22KvJGpmC99XE5tRz"
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
FEAR_GREED_URL = "https://api.alternative.me/fng/"

def coingecko_request(endpoint, params=None):
    """Helper function to make requests to CoinGecko API"""
    headers = {"X-CG-Pro-API-Key": COINGECKO_API_KEY}
    url = f"{COINGECKO_BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making request to {url}: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

# API Routes for frontend
@app.route('/api/search')
def search_coin():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    # Search for coins
    search_data = coingecko_request("search", {"query": query})
    if not search_data or 'coins' not in search_data:
        return jsonify([])
    
    # Get details for top 5 search results
    coins_data = []
    for coin in search_data['coins'][:5]:
        coin_id = coin['id']
        coin_data = coingecko_request(f"coins/{coin_id}", {
            "localization": "false",
            "tickers": "false",
            "community_data": "false",
            "developer_data": "false"
        })
        if coin_data:
            coins_data.append(coin_data)
    
    return jsonify(coins_data)

@app.route('/api/coin/<coin_id>')
def get_coin_data(coin_id):
    coin_data = coingecko_request(f"coins/{coin_id}", {
        "localization": "false",
        "tickers": "false",
        "community_data": "false",
        "developer_data": "false"
    })
    return jsonify(coin_data) if coin_data else jsonify({})

@app.route('/api/coin/<coin_id>/market_chart')
def get_coin_chart(coin_id):
    days = request.args.get('days', '7')
    chart_data = coingecko_request(f"coins/{coin_id}/market_chart", {
        "vs_currency": "usd",
        "days": days
    })
    return jsonify(chart_data) if chart_data else jsonify({})

@app.route('/api/top_coins')
def get_top_coins():
    coins_data = coingecko_request("coins/markets", {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": "20",
        "page": "1",
        "sparkline": "false"
    })
    return jsonify(coins_data) if coins_data else jsonify([])

@app.route('/api/trending')
def get_trending_coins():
    trending_data = coingecko_request("search/trending")
    if not trending_data or 'coins' not in trending_data:
        return jsonify([])
    
    trending_coins = []
    for coin in trending_data['coins'][:10]:
        coin_data = coin['item']
        trending_coins.append({
            'id': coin_data['id'],
            'name': coin_data['name'],
            'symbol': coin_data['symbol'],
            'thumb': coin_data['thumb'],
            'market_cap_rank': coin_data['market_cap_rank']
        })
    
    return jsonify(trending_coins)

@app.route('/api/gainers_losers')
def get_gainers_losers():
    coins_data = coingecko_request("coins/markets", {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": "100",
        "page": "1",
        "sparkline": "false",
        "price_change_percentage": "24h"
    })
    
    if not coins_data:
        return jsonify({'gainers': [], 'losers': []})
    
    # Sort by 24h change percentage
    sorted_coins = sorted(coins_data, key=lambda x: x['price_change_percentage_24h'], reverse=True)
    
    gainers = sorted_coins[:10]
    losers = sorted_coins[-10:]
    losers.reverse()  # Show worst performers first
    
    return jsonify({
        'gainers': gainers,
        'losers': losers
    })

@app.route('/api/fear_greed')
def get_fear_greed():
    try:
        response = requests.get(FEAR_GREED_URL)
        response.raise_for_status()
        data = response.json()
        return jsonify(data)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Fear & Greed Index: {e}")
        return jsonify({})

@app.route('/api/global')
def get_global_data():
    global_data = coingecko_request("global")
    return jsonify(global_data) if global_data else jsonify({})

@app.route('/api/categories')
def get_categories():
    categories_data = coingecko_request("coins/categories")
    if categories_data:
        # Sort by market cap descending and take top 10
        sorted_categories = sorted(categories_data, key=lambda x: x['market_cap'], reverse=True)[:10]
        return jsonify(sorted_categories)
    return jsonify([])

@app.route('/api/exchanges')
def get_exchanges():
    exchanges_data = coingecko_request("exchanges", {
        "per_page": "10",
        "page": "1"
    })
    return jsonify(exchanges_data) if exchanges_data else jsonify([])

@app.route('/api/recent')
def get_recent_coins():
    coins_data = coingecko_request("coins/markets", {
        "vs_currency": "usd",
        "order": "id_asc",
        "per_page": "5",
        "page": "1",
        "sparkline": "false"
    })
    return jsonify(coins_data) if coins_data else jsonify([])

@app.route('/api/stablecoins')
def get_stablecoins():
    coins_data = coingecko_request("coins/markets", {
        "vs_currency": "usd",
        "category": "stablecoins",
        "order": "market_cap_desc",
        "per_page": "10",
        "page": "1",
        "sparkline": "false"
    })
    return jsonify(coins_data) if coins_data else jsonify([])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
