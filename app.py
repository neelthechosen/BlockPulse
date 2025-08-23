import os
import time
import requests
from flask import Flask, jsonify, render_template, request
from functools import lru_cache
from datetime import datetime, timedelta

app = Flask(__name__)

API_KEY = os.environ.get('COINGECKO_API_KEY', 'CG-oUpG62o22KvJGpmC99XE5tRz')
BASE_URL = 'https://api.coingecko.com/api/v3'
CACHE = {}
CACHE_TTL = {
    'coins_list': 43200,  # 12 hours
    'hot': 90,
    'chart': 120
}

def cg_get(path, params=None):
    cache_key = f"{path}:{str(params)}"
    if cache_key in CACHE:
        if time.time() - CACHE[cache_key]['time'] < CACHE_TTL.get('hot', 90):
            return CACHE[cache_key]['data']
    
    headers = {'x-cg-demo-api-key': API_KEY}
    backoffs = [0.5, 1, 2]
    for delay in backoffs:
        try:
            resp = requests.get(
                f"{BASE_URL}/{path}",
                params=params,
                headers=headers,
                timeout=7
            )
            resp.raise_for_status()
            data = resp.json()
            CACHE[cache_key] = {'data': data, 'time': time.time()}
            return data
        except requests.exceptions.HTTPError as e:
            if resp.status_code in [429, 500, 502, 503, 504]:
                time.sleep(delay)
                continue
            raise e
        except requests.exceptions.RequestException:
            time.sleep(delay)
            continue
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search')
def search():
    try:
        q = request.args.get('q', '').lower().strip()
        if not q:
            return jsonify({'ok': False, 'message': 'Empty query'})
        
        coins_list = cg_get('coins/list')
        if not coins_list:
            return jsonify({'ok': False, 'message': 'Could not fetch coins list'})
        
        results = []
        for coin in coins_list:
            if q in coin['symbol'].lower() or q in coin['name'].lower():
                results.append({
                    'id': coin['id'],
                    'name': coin['name'],
                    'symbol': coin['symbol'].upper()
                })
        return jsonify({'ok': True, 'results': results[:10]})
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})

@app.route('/api/coin/<id>')
def coin_data(id):
    try:
        data = cg_get(f'coins/{id}', {
            'localization': 'false',
            'tickers': 'false',
            'community_data': 'false',
            'developer_data': 'false'
        })
        if not data:
            return jsonify({'ok': False, 'message': 'Coin not found'})
        
        return jsonify({'ok': True, 'data': {
            'name': data['name'],
            'symbol': data['symbol'].upper(),
            'rank': data['market_cap_rank'],
            'price': data['market_data']['current_price']['usd'],
            'market_cap': data['market_data']['market_cap']['usd'],
            'volume_24h': data['market_data']['total_volume']['usd'],
            'circulating_supply': data['market_data']['circulating_supply'],
            'total_supply': data['market_data']['total_supply'],
            'max_supply': data['market_data']['max_supply'],
            'ath': data['market_data']['ath']['usd'],
            'price_change_1h': data['market_data']['price_change_percentage_1h_in_currency']['usd'],
            'price_change_24h': data['market_data']['price_change_percentage_24h_in_currency']['usd'],
            'price_change_7d': data['market_data']['price_change_percentage_7d_in_currency']['usd']
        }})
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})

@app.route('/api/chart/<id>')
def chart_data(id):
    try:
        days = request.args.get('days', '1')
        data = cg_get(f'coins/{id}/market_chart', {
            'vs_currency': 'usd',
            'days': days
        })
        if not data:
            return jsonify({'ok': False, 'message': 'No chart data'})
        
        return jsonify({
            'ok': True,
            'prices': data.get('prices', []),
            'volumes': data.get('total_volumes', [])
        })
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})

@app.route('/api/top')
def top_coins():
    try:
        data = cg_get('coins/markets', {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 20,
            'page': 1,
            'price_change_percentage': '1h,24h,7d'
        })
        if not data:
            return jsonify({'ok': False, 'message': 'Could not fetch top coins'})
        
        return jsonify({'ok': True, 'coins': data})
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})

@app.route('/api/trending')
def trending():
    try:
        data = cg_get('search/trending')
        if not data:
            return jsonify({'ok': False, 'message': 'Could not fetch trending'})
        
        coins = [{
            'name': coin['item']['name'],
            'symbol': coin['item']['symbol'],
            'rank': coin['item']['market_cap_rank'],
            'thumb': coin['item']['thumb']
        } for coin in data['coins'][:10]]
        
        return jsonify({'ok': True, 'coins': coins})
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})

@app.route('/api/gainers_losers')
def gainers_losers():
    try:
        data = cg_get('coins/markets', {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 250,
            'page': 1
        })
        if not data:
            return jsonify({'ok': False, 'message': 'Could not fetch markets'})
        
        sorted_coins = sorted(data, key=lambda x: x['price_change_percentage_24h'], reverse=True)
        gainers = sorted_coins[:10]
        losers = sorted_coins[-10:][::-1]
        
        return jsonify({'ok': True, 'gainers': gainers, 'losers': losers})
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})

@app.route('/api/global')
def global_data():
    try:
        data = cg_get('global')
        if not data:
            return jsonify({'ok': False, 'message': 'Could not fetch global data'})
        
        return jsonify({'ok': True, 'data': data['data']})
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})

@app.route('/api/categories')
def categories():
    try:
        data = cg_get('coins/categories')
        if not data:
            return jsonify({'ok': False, 'message': 'Could not fetch categories'})
        
        return jsonify({'ok': True, 'categories': data})
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})

@app.route('/api/exchanges')
def exchanges():
    try:
        data = cg_get('exchanges', {'per_page': 10})
        if not data:
            return jsonify({'ok': False, 'message': 'Could not fetch exchanges'})
        
        return jsonify({'ok': True, 'exchanges': data})
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})

@app.route('/api/stablecoins')
def stablecoins():
    try:
        data = cg_get('coins/markets', {
            'vs_currency': 'usd',
            'category': 'stablecoins',
            'order': 'market_cap_desc',
            'per_page': 20
        })
        if not data:
            return jsonify({'ok': False, 'message': 'Could not fetch stablecoins'})
        
        return jsonify({'ok': True, 'coins': data})
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})

@app.route('/api/fng')
def fear_and_greed():
    try:
        resp = requests.get('https://api.alternative.me/fng/?limit=7', timeout=7)
        resp.raise_for_status()
        data = resp.json()
        return jsonify({
            'ok': True,
            'now': data['data'][0],
            'history': data['data']
        })
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
