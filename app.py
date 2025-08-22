from flask import Flask, render_template, request, jsonify
import requests
import os

app = Flask(__name__)

# CoinGecko API configuration
API_KEY = "CG-oUpG62o22KvJGpmC99XE5tRz"
BASE_URL = "https://api.coingecko.com/api/v3"

@app.route('/')
def index():
    return render_template('index.html')

# Get global market data
@app.route('/global')
def get_global_data():
    try:
        url = f"{BASE_URL}/global"
        headers = {"x-cg-demo-api-key": API_KEY}
        response = requests.get(url, headers=headers)
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Search for coins
@app.route('/search/<query>')
def search_coins(query):
    try:
        url = f"{BASE_URL}/search?query={query}"
        headers = {"x-cg-demo-api-key": API_KEY}
        response = requests.get(url, headers=headers)
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Get coin data
@app.route('/coin/<coin_id>')
def get_coin_data(coin_id):
    try:
        url = f"{BASE_URL}/coins/{coin_id}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false"
        headers = {"x-cg-demo-api-key": API_KEY}
        response = requests.get(url, headers=headers)
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Get coin market chart
@app.route('/chart/<coin_id>/<days>')
def get_coin_chart(coin_id, days):
    try:
        url = f"{BASE_URL}/coins/{coin_id}/market_chart?vs_currency=usd&days={days}"
        headers = {"x-cg-demo-api-key": API_KEY}
        response = requests.get(url, headers=headers)
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Get trending coins
@app.route('/trending')
def get_trending_coins():
    try:
        url = f"{BASE_URL}/search/trending"
        headers = {"x-cg-demo-api-key": API_KEY}
        response = requests.get(url, headers=headers)
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Get top gainers and losers
@app.route('/top')
def get_top_coins():
    try:
        url = f"{BASE_URL}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=50&page=1&sparkline=false&price_change_percentage=24h"
        headers = {"x-cg-demo-api-key": API_KEY}
        response = requests.get(url, headers=headers)
        data = response.json()
        
        # Sort by price change to get gainers and losers
        sorted_by_change = sorted(data, key=lambda x: x['price_change_percentage_24h'], reverse=True)
        gainers = sorted_by_change[:10]
        losers = sorted_by_change[-10:]
        
        return jsonify({"gainers": gainers, "losers": losers})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Get fear and greed index (using Alternative API since CoinGecko doesn't have it)
@app.route('/fear-greed')
def get_fear_greed():
    try:
        # Using Alternative.me API for Fear & Greed Index
        url = "https://api.alternative.me/fng/"
        response = requests.get(url)
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
