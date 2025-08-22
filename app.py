from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

# CoinGecko API configuration
COINGECKO_API_KEY = "CG-oUpG62o22KvJGpmC99XE5tRz"
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

# Alternative.me API for Fear & Greed Index
FEAR_GREED_API_URL = "https://api.alternative.me/fng/"

def make_coingecko_request(endpoint, params=None):
    """Helper function to make requests to CoinGecko API"""
    headers = {"x-cg-demo-api-key": COINGECKO_API_KEY}
    url = f"{COINGECKO_BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making request to CoinGecko: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search_coins():
    query = request.args.get('query', '')
    if not query:
        return jsonify([])
    
    # Search for coins
    data = make_coingecko_request("search", {"query": query})
    if not data or 'coins' not in data:
        return jsonify([])
    
    # Get limited info for search results
    coins = []
    for coin in data['coins'][:10]:  # Limit to 10 results
        coins.append({
            'id': coin['id'],
            'name': coin['name'],
            'symbol': coin['symbol'],
            'market_cap_rank': coin.get('market_cap_rank', 'N/A')
        })
    
    return jsonify(coins)

@app.route('/coin/<coin_id>')
def get_coin_data(coin_id):
    # Get detailed coin information
    params = {
        'localization': 'false',
        'tickers': 'false',
        'market_data': 'true',
        'community_data': 'false',
        'developer_data': 'false',
        'sparkline': 'false'
    }
    
    data = make_coingecko_request(f"coins/{coin_id}", params)
    if not data:
        return jsonify({'error': 'Could not fetch coin data'})
    
    # Extract relevant data
    market_data = data.get('market_data', {})
    coin_info = {
        'name': data['name'],
        'symbol': data['symbol'].upper(),
        'current_price': market_data.get('current_price', {}).get('usd', 'N/A'),
        'market_cap': market_data.get('market_cap', {}).get('usd', 'N/A'),
        'total_volume': market_data.get('total_volume', {}).get('usd', 'N/A'),
        'circulating_supply': market_data.get('circulating_supply', 'N/A'),
        'total_supply': market_data.get('total_supply', 'N/A'),
        'price_change_percentage_24h': market_data.get('price_change_percentage_24h', 'N/A'),
        'price_change_percentage_7d': market_data.get('price_change_percentage_7d', 'N/A'),
        'price_change_percentage_30d': market_data.get('price_change_percentage_30d', 'N/A'),
        'image': data.get('image', {}).get('large', '')
    }
    
    return jsonify(coin_info)

@app.route('/coin/<coin_id>/market_chart')
def get_coin_chart(coin_id):
    days = request.args.get('days', '1')
    vs_currency = 'usd'
    
    data = make_coingecko_request(f"coins/{coin_id}/market_chart", {
        'vs_currency': vs_currency,
        'days': days,
        'interval': 'hourly' if days == '1' else 'daily'
    })
    
    if not data or 'prices' not in data:
        return jsonify({'error': 'Could not fetch chart data'})
    
    # Process chart data
    prices = [{'time': price[0], 'value': price[1]} for price in data['prices']]
    volumes = [{'time': volume[0], 'value': volume[1]} for volume in data['total_volumes']]
    
    return jsonify({
        'prices': prices,
        'volumes': volumes
    })

@app.route('/global')
def get_global_data():
    data = make_coingecko_request("global")
    if not data or 'data' not in data:
        return jsonify({'error': 'Could not fetch global data'})
    
    global_data = data['data']
    return jsonify({
        'total_market_cap': global_data.get('total_market_cap', {}).get('usd', 'N/A'),
        'market_cap_change_percentage_24h_usd': global_data.get('market_cap_change_percentage_24h_usd', 'N/A'),
        'btc_dominance': global_data.get('market_cap_percentage', {}).get('btc', 'N/A'),
        'active_cryptocurrencies': global_data.get('active_cryptocurrencies', 'N/A'),
        'markets': global_data.get('markets', 'N/A')
    })

@app.route('/trending')
def get_trending_coins():
    data = make_coingecko_request("search/trending")
    if not data or 'coins' not in data:
        return jsonify({'error': 'Could not fetch trending data'})
    
    trending_coins = []
    for coin in data['coins'][:7]:  # Get top 7 trending coins
        coin_data = coin['item']
        trending_coins.append({
            'id': coin_data['id'],
            'name': coin_data['name'],
            'symbol': coin_data['symbol'],
            'market_cap_rank': coin_data.get('market_cap_rank', 'N/A'),
            'thumb': coin_data.get('thumb', '')
        })
    
    return jsonify(trending_coins)

@app.route('/top_coins')
def get_top_coins():
    data = make_coingecko_request("coins/markets", {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 10,
        'page': 1,
        'sparkline': 'false',
        'price_change_percentage': '24h'
    })
    
    if not data:
        return jsonify({'error': 'Could not fetch top coins data'})
    
    top_coins = []
    for coin in data:
        top_coins.append({
            'id': coin['id'],
            'name': coin['name'],
            'symbol': coin['symbol'],
            'current_price': coin['current_price'],
            'price_change_percentage_24h': coin['price_change_percentage_24h'],
            'market_cap_rank': coin['market_cap_rank']
        })
    
    return jsonify(top_coins)

@app.route('/gainers_losers')
def get_gainers_losers():
    data = make_coingecko_request("coins/markets", {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 100,
        'page': 1,
        'sparkline': 'false',
        'price_change_percentage': '24h'
    })
    
    if not data:
        return jsonify({'error': 'Could not fetch gainers/losers data'})
    
    # Sort by 24h change to get gainers and losers
    sorted_by_change = sorted(data, key=lambda x: x['price_change_percentage_24h'] or 0, reverse=True)
    
    gainers = []
    for coin in sorted_by_change[:5]:  # Top 5 gainers
        gainers.append({
            'id': coin['id'],
            'name': coin['name'],
            'symbol': coin['symbol'],
            'price_change_percentage_24h': coin['price_change_percentage_24h'],
            'current_price': coin['current_price']
        })
    
    losers = []
    for coin in sorted_by_change[-5:]:  # Top 5 losers
        losers.append({
            'id': coin['id'],
            'name': coin['name'],
            'symbol': coin['symbol'],
            'price_change_percentage_24h': coin['price_change_percentage_24h'],
            'current_price': coin['current_price']
        })
    
    return jsonify({
        'gainers': gainers,
        'losers': losers
    })

@app.route('/fear_greed')
def get_fear_greed_index():
    try:
        response = requests.get(FEAR_GREED_API_URL, params={'limit': 1})
        response.raise_for_status()
        data = response.json()
        
        if data and 'data' in data and len(data['data']) > 0:
            return jsonify({
                'value': data['data'][0]['value'],
                'value_classification': data['data'][0]['value_classification'],
                'timestamp': data['data'][0]['timestamp']
            })
        else:
            return jsonify({'error': 'Could not fetch Fear & Greed data'})
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Fear & Greed index: {e}")
        return jsonify({'error': 'Could not fetch Fear & Greed data'})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
