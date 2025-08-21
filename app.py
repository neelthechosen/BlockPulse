# app.py
from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime, timedelta
import json

app = Flask(__name__)

# CoinGecko API configuration
COINGECKO_API_KEY = "CG-oUpG62o22KvJGpmC99XE5tRz"
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
HEADERS = {"X-CG-Pro-API-Key": COINGECKO_API_KEY}

# Fear & Greed Index API
FEAR_GREED_API = "https://api.alternative.me/fng/"

# Custom template filters
@app.template_filter('format_timestamp')
def format_timestamp_filter(timestamp_str):
    """Convert timestamp string to readable date"""
    if not timestamp_str:
        return "N/A"
    try:
        timestamp = int(timestamp_str)
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return timestamp_str

@app.template_filter('format_large_number')
def format_large_number_filter(num):
    """Format large numbers with appropriate suffixes"""
    if not num:
        return "N/A"
    
    if num >= 1e12:
        return f"${num/1e12:.2f}T"
    elif num >= 1e9:
        return f"${num/1e9:.2f}B"
    elif num >= 1e6:
        return f"${num/1e6:.2f}M"
    elif num >= 1e3:
        return f"${num/1e3:.2f}K"
    else:
        return f"${num:.2f}"

def get_global_data():
    """Fetch global cryptocurrency market data"""
    try:
        url = f"{COINGECKO_BASE_URL}/global"
        response = requests.get(url, headers=HEADERS)
        data = response.json().get('data', {})
        return data
    except Exception as e:
        print(f"Error fetching global data: {e}")
        return {}

def get_coin_data(coin_id):
    """Fetch data for a specific cryptocurrency"""
    try:
        url = f"{COINGECKO_BASE_URL}/coins/{coin_id}"
        params = {
            'localization': 'false',
            'tickers': 'false',
            'market_data': 'true',
            'community_data': 'false',
            'developer_data': 'false',
            'sparkline': 'false'
        }
        response = requests.get(url, headers=HEADERS, params=params)
        return response.json()
    except Exception as e:
        print(f"Error fetching coin data: {e}")
        return None

def get_coin_history(coin_id, days):
    """Fetch historical data for a specific cryptocurrency"""
    try:
        url = f"{COINGECKO_BASE_URL}/coins/{coin_id}/market_chart"
        params = {
            'vs_currency': 'usd',
            'days': days,
            'interval': 'daily' if days != '1' else 'hourly'
        }
        response = requests.get(url, headers=HEADERS, params=params)
        return response.json()
    except Exception as e:
        print(f"Error fetching coin history: {e}")
        return None

def search_coins(query):
    """Search for cryptocurrencies by name or symbol"""
    try:
        url = f"{COINGECKO_BASE_URL}/search"
        params = {'query': query}
        response = requests.get(url, headers=HEADERS, params=params)
        return response.json().get('coins', [])[:10]  # Return top 10 results
    except Exception as e:
        print(f"Error searching coins: {e}")
        return []

def get_trending_coins():
    """Fetch trending cryptocurrencies"""
    try:
        url = f"{COINGECKO_BASE_URL}/search/trending"
        response = requests.get(url, headers=HEADERS)
        coins = response.json().get('coins', [])
        return [coin['item'] for coin in coins][:7]  # Return top 7 trending
    except Exception as e:
        print(f"Error fetching trending coins: {e}")
        return []

def get_top_movers():
    """Fetch top gainers and losers"""
    try:
        url = f"{COINGECKO_BASE_URL}/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 50,
            'page': 1,
            'sparkline': 'false',
            'price_change_percentage': '24h'
        }
        response = requests.get(url, headers=HEADERS, params=params)
        coins = response.json()
        
        # Sort by 24h change to get gainers and losers
        sorted_coins = sorted(coins, key=lambda x: x.get('price_change_percentage_24h', 0), reverse=True)
        gainers = sorted_coins[:5]
        losers = sorted_coins[-5:]
        
        return gainers, losers
    except Exception as e:
        print(f"Error fetching top movers: {e}")
        return [], []

def get_fear_greed_index():
    """Fetch Fear & Greed Index data"""
    try:
        response = requests.get(FEAR_GREED_API)
        data = response.json()
        return data.get('data', [{}])[0]
    except Exception as e:
        print(f"Error fetching Fear & Greed Index: {e}")
        return {"value": 50, "value_classification": "Neutral", "timestamp": str(int(datetime.now().timestamp()))}

@app.route('/')
def index():
    # Fetch initial data for the dashboard
    global_data = get_global_data()
    trending_coins = get_trending_coins()
    gainers, losers = get_top_movers()
    fear_greed = get_fear_greed_index()
    
    return render_template('index.html', 
                         global_data=global_data,
                         trending_coins=trending_coins,
                         gainers=gainers,
                         losers=losers,
                         fear_greed=fear_greed)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    results = search_coins(query)
    return jsonify(results)

@app.route('/coin/<coin_id>')
def coin_data(coin_id):
    coin = get_coin_data(coin_id)
    return jsonify(coin)

@app.route('/history/<coin_id>')
def coin_history():
    coin_id = request.args.get('coin_id')
    days = request.args.get('days', '7')
    
    history = get_coin_history(coin_id, days)
    return jsonify(history)

@app.route('/compare', methods=['POST'])
def compare_coins():
    data = request.json
    coin_ids = data.get('coins', [])
    
    comparison_data = []
    for coin_id in coin_ids:
        coin = get_coin_data(coin_id)
        if coin:
            comparison_data.append({
                'id': coin['id'],
                'name': coin['name'],
                'symbol': coin['symbol'],
                'current_price': coin['market_data']['current_price']['usd'],
                'market_cap': coin['market_data']['market_cap']['usd'],
                'price_change_24h': coin['market_data']['price_change_percentage_24h'],
                'circulating_supply': coin['market_data']['circulating_supply'],
                'max_supply': coin['market_data']['max_supply'],
            })
    
    return jsonify(comparison_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
