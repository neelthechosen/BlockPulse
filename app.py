# app.py
from flask import Flask, render_template, request, jsonify
import requests
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# CoinGecko API configuration
API_KEY = "CG-oUpG62o22KvJGpmC99XE5tRz"
BASE_URL = "https://api.coingecko.com/api/v3"

def make_api_request(endpoint, params=None):
    """Helper function to make API requests with the API key"""
    headers = {
        "accept": "application/json",
        "x-cg-demo-api-key": API_KEY
    }
    url = f"{BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Request Error: {e}")
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    # Get global market data
    global_data = make_api_request("global")
    
    # Get trending coins
    trending_data = make_api_request("search/trending")
    trending_coins = []
    if trending_data and 'coins' in trending_data:
        trending_coins = [coin['item'] for coin in trending_data['coins'][:10]]
    
    # Get top gainers and losers
    markets_data = make_api_request("coins/markets", {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 100,
        'page': 1,
        'sparkline': 'false',
        'price_change_percentage': '24h'
    })
    
    top_gainers = []
    top_losers = []
    
    if markets_data:
        sorted_by_gain = sorted(markets_data, key=lambda x: x.get('price_change_percentage_24h', 0), reverse=True)
        top_gainers = sorted_by_gain[:10]
        
        sorted_by_loss = sorted(markets_data, key=lambda x: x.get('price_change_percentage_24h', 0))
        top_losers = sorted_by_loss[:10]
    
    # Handle coin search
    search_query = request.form.get('search', '').strip().lower() if request.method == 'POST' else ''
    coin_data = None
    historical_data = None
    volume_data = None
    
    if search_query:
        # First, try to find the coin ID
        coins_list = make_api_request("coins/list")
        coin_id = None
        
        if coins_list:
            for coin in coins_list:
                if search_query in [coin['name'].lower(), coin['symbol'].lower(), coin['id'].lower()]:
                    coin_id = coin['id']
                    break
        
        if coin_id:
            # Get coin data
            coin_data = make_api_request(f"coins/{coin_id}", {
                'localization': 'false',
                'tickers': 'false',
                'market_data': 'true',
                'community_data': 'false',
                'developer_data': 'false',
                'sparkline': 'false'
            })
            
            # Get historical data for charts
            end_date = datetime.now()
            start_date_30d = end_date - timedelta(days=30)
            start_date_7d = end_date - timedelta(days=7)
            
            historical_data = make_api_request(f"coins/{coin_id}/market_chart/range", {
                'vs_currency': 'usd',
                'from': int(start_date_30d.timestamp()),
                'to': int(end_date.timestamp())
            })
            
            # For volume chart (last 7 days)
            volume_data = make_api_request(f"coins/{coin_id}/market_chart/range", {
                'vs_currency': 'usd',
                'from': int(start_date_7d.timestamp()),
                'to': int(end_date.timestamp())
            })
    
    # Handle portfolio simulation
    portfolio_value = 0
    portfolio_data = []
    
    if request.method == 'POST' and 'portfolio_coins' in request.form:
        portfolio_coins = request.form.getlist('portfolio_coins')
        portfolio_amounts = request.form.getlist('portfolio_amounts')
        
        for i, coin_id in enumerate(portfolio_coins):
            if coin_id and i < len(portfolio_amounts) and portfolio_amounts[i]:
                try:
                    amount = float(portfolio_amounts[i])
                    coin_price_data = make_api_request(f"coins/{coin_id}", {
                        'localization': 'false',
                        'tickers': 'false',
                        'market_data': 'true',
                        'community_data': 'false',
                        'developer_data': 'false',
                        'sparkline': 'false'
                    })
                    
                    if coin_price_data and 'market_data' in coin_price_data:
                        price = coin_price_data['market_data']['current_price']['usd']
                        value = price * amount
                        portfolio_value += value
                        
                        portfolio_data.append({
                            'id': coin_id,
                            'name': coin_price_data['name'],
                            'symbol': coin_price_data['symbol'].upper(),
                            'amount': amount,
                            'price': price,
                            'value': value
                        })
                except (ValueError, TypeError):
                    continue
    
    # Handle coin comparison
    compare_coins = request.form.getlist('compare_coins') if request.method == 'POST' else []
    comparison_data = []
    
    for coin_id in compare_coins:
        if coin_id:
            coin_compare_data = make_api_request(f"coins/{coin_id}", {
                'localization': 'false',
                'tickers': 'false',
                'market_data': 'true',
                'community_data': 'false',
                'developer_data': 'false',
                'sparkline': 'false'
            })
            
            if coin_compare_data:
                comparison_data.append(coin_compare_data)
    
    return render_template('index.html',
                         global_data=global_data,
                         trending_coins=trending_coins,
                         top_gainers=top_gainers,
                         top_losers=top_losers,
                         coin_data=coin_data,
                         historical_data=historical_data,
                         volume_data=volume_data,
                         portfolio_value=portfolio_value,
                         portfolio_data=portfolio_data,
                         comparison_data=comparison_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
