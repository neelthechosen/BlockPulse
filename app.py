import os
import time
import requests
from flask import Flask, jsonify, request, render_template
from functools import lru_cache
from datetime import datetime, timedelta

app = Flask(__name__)

# Configuration
COINGECKO_API_KEY = os.environ.get('COINGECKO_API_KEY', 'CG-oUpG62o22KvJGpmC99XE5tRz')
COINGECKO_BASE_URL = 'https://api.coingecko.com/api/v3'
HEADERS = {'x-cg-demo-api-key': COINGECKO_API_KEY}
REQUEST_TIMEOUT = 7

# In-memory caches
coin_list_cache = None
coin_list_last_fetch = 0
coin_list_ttl = 43200  # 12 hours in seconds

chart_cache = {}
chart_cache_ttl = 120  # 2 minutes

general_cache = {}
general_cache_ttl = 60  # 1 minute

def cg_get(path, params=None, retries=3):
    """Helper function to make requests to CoinGecko API with retries and backoff"""
    url = f"{COINGECKO_BASE_URL}{path}"
    
    for i in range(retries):
        try:
            response = requests.get(
                url, 
                params=params, 
                headers=HEADERS, 
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 429:
                # Rate limited - wait and retry
                backoff_time = 0.5 * (2 ** i)  # Exponential backoff: 0.5s, 1s, 2s
                time.sleep(backoff_time)
                continue
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            if i == retries - 1:  # Last retry
                raise e
            backoff_time = 0.5 * (2 ** i)
            time.sleep(backoff_time)
    
    return None

def get_coin_list():
    """Fetch and cache coin list for symbol/name resolution"""
    global coin_list_cache, coin_list_last_fetch
    
    current_time = time.time()
    if coin_list_cache is None or (current_time - coin_list_last_fetch) > coin_list_ttl:
        try:
            coin_list_cache = cg_get('/coins/list', {'include_platform': 'false'})
            coin_list_last_fetch = current_time
        except:
            # If we can't fetch new data, use the old cache if available
            if coin_list_cache is None:
                coin_list_cache = []
    
    return coin_list_cache

def resolve_query_to_id(query):
    """Resolve a search query to a coin ID using the cached coin list"""
    coin_list = get_coin_list()
    query_lower = query.lower().strip()
    
    # Create mappings for symbol and name
    symbol_to_ids = {}
    name_to_id = {}
    
    for coin in coin_list:
        symbol = coin['symbol'].lower()
        name = coin['name'].lower()
        coin_id = coin['id']
        
        if symbol not in symbol_to_ids:
            symbol_to_ids[symbol] = []
        symbol_to_ids[symbol].append(coin_id)
        
        name_to_id[name] = coin_id
    
    # First try exact symbol match
    if query_lower in symbol_to_ids:
        ids = symbol_to_ids[query_lower]
        if len(ids) == 1:
            return ids[0]
        # Multiple coins with same symbol - need to resolve by market cap
    
    # Then try exact name match
    if query_lower in name_to_id:
        return name_to_id[query_lower]
    
    # Then try partial matches
    for name, coin_id in name_to_id.items():
        if query_lower in name:
            return coin_id
            
    for symbol, ids in symbol_to_ids.items():
        if query_lower in symbol:
            if len(ids) == 1:
                return ids[0]
            # Multiple coins with same symbol - return the first one for now
    
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search')
def api_search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'ok': True, 'results': []})
    
    coin_list = get_coin_list()
    query_lower = query.lower()
    
    results = []
    for coin in coin_list:
        if (query_lower in coin['name'].lower() or 
            query_lower in coin['symbol'].lower()):
            results.append({
                'id': coin['id'],
                'name': coin['name'],
                'symbol': coin['symbol'].upper()
            })
            
            # Limit results to 10
            if len(results) >= 10:
                break
    
    return jsonify({'ok': True, 'results': results})

@app.route('/api/coin/<coin_id>')
def api_coin(coin_id):
    # Validate coin_id format
    if not all(c.islower() or c.isdigit() or c == '-' for c in coin_id):
        return jsonify({'ok': False, 'message': 'Invalid coin ID'})
    
    try:
        # Get coin data with additional details
        data = cg_get(f'/coins/{coin_id}', {
            'localization': 'false',
            'tickers': 'false',
            'market_data': 'true',
            'community_data': 'false',
            'developer_data': 'false',
            'sparkline': 'false'
        })
        
        if not data:
            return jsonify({'ok': False, 'message': 'Coin not found'})
        
        # Extract relevant information
        result = {
            'id': data.get('id'),
            'name': data.get('name'),
            'symbol': data.get('symbol', '').upper(),
            'rank': data.get('market_cap_rank', '—'),
            'price': data.get('market_data', {}).get('current_price', {}).get('usd', '—'),
            'market_cap': data.get('market_data', {}).get('market_cap', {}).get('usd', '—'),
            'volume_24h': data.get('market_data', {}).get('total_volume', {}).get('usd', '—'),
            'circulating_supply': data.get('market_data', {}).get('circulating_supply', '—'),
            'total_supply': data.get('market_data', {}).get('total_supply', '—'),
            'max_supply': data.get('market_data', {}).get('max_supply', '—'),
            'ath': data.get('market_data', {}).get('ath', {}).get('usd', '—'),
            'price_change_1h': data.get('market_data', {}).get('price_change_percentage_1h_in_currency', {}).get('usd', '—'),
            'price_change_24h': data.get('market_data', {}).get('price_change_percentage_24h_in_currency', {}).get('usd', '—'),
            'price_change_7d': data.get('market_data', {}).get('price_change_percentage_7d_in_currency', {}).get('usd', '—'),
            'image': data.get('image', {}).get('large', '')
        }
        
        return jsonify({'ok': True, 'data': result})
        
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})

@app.route('/api/chart/<coin_id>')
def api_chart(coin_id):
    # Validate coin_id format
    if not all(c.islower() or c.isdigit() or c == '-' for c in coin_id):
        return jsonify({'ok': False, 'message': 'Invalid coin ID'})
    
    days = request.args.get('days', '1')
    if days not in ['1', '7', '30', '90', '365']:
        return jsonify({'ok': False, 'message': 'Invalid days parameter'})
    
    # Check cache first
    cache_key = f"{coin_id}_{days}"
    if cache_key in chart_cache:
        cached_data, timestamp = chart_cache[cache_key]
        if time.time() - timestamp < chart_cache_ttl:
            return jsonify({'ok': True, 'prices': cached_data.get('prices', []), 'volumes': cached_data.get('total_volumes', [])})
    
    try:
        data = cg_get(f'/coins/{coin_id}/market_chart', {
            'vs_currency': 'usd',
            'days': days,
            'interval': 'hourly' if days == '1' else 'daily'
        })
        
        if data:
            # Cache the response
            chart_cache[cache_key] = (data, time.time())
            return jsonify({
                'ok': True, 
                'prices': data.get('prices', []), 
                'volumes': data.get('total_volumes', [])
            })
        else:
            return jsonify({'ok': False, 'message': 'Failed to fetch chart data'})
            
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})

@app.route('/api/top')
def api_top():
    # Check cache first
    if 'top' in general_cache:
        cached_data, timestamp = general_cache['top']
        if time.time() - timestamp < general_cache_ttl:
            return jsonify({'ok': True, 'coins': cached_data})
    
    try:
        data = cg_get('/coins/markets', {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 20,
            'page': 1,
            'sparkline': 'false',
            'price_change_percentage': '1h,24h,7d'
        })
        
        if data:
            # Format the data
            coins = []
            for coin in data:
                coins.append({
                    'id': coin.get('id'),
                    'name': coin.get('name'),
                    'symbol': coin.get('symbol', '').upper(),
                    'rank': coin.get('market_cap_rank', '—'),
                    'price': coin.get('current_price', '—'),
                    'price_change_24h': coin.get('price_change_percentage_24h', '—'),
                    'market_cap': coin.get('market_cap', '—'),
                    'volume_24h': coin.get('total_volume', '—'),
                    'image': coin.get('image', '')
                })
            
            # Cache the response
            general_cache['top'] = (coins, time.time())
            return jsonify({'ok': True, 'coins': coins})
        else:
            return jsonify({'ok': False, 'message': 'Failed to fetch top coins'})
            
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})

@app.route('/api/trending')
def api_trending():
    # Check cache first
    if 'trending' in general_cache:
        cached_data, timestamp = general_cache['trending']
        if time.time() - timestamp < general_cache_ttl:
            return jsonify({'ok': True, 'coins': cached_data})
    
    try:
        data = cg_get('/search/trending')
        
        if data:
            coins = []
            for item in data.get('coins', [])[:10]:
                coin_data = item.get('item', {})
                coins.append({
                    'id': coin_data.get('id'),
                    'name': coin_data.get('name'),
                    'symbol': coin_data.get('symbol', '').upper(),
                    'rank': coin_data.get('market_cap_rank', '—'),
                    'price': coin_data.get('price_btc', '—'),
                    'image': coin_data.get('thumb', '')
                })
            
            # Cache the response
            general_cache['trending'] = (coins, time.time())
            return jsonify({'ok': True, 'coins': coins})
        else:
            return jsonify({'ok': False, 'message': 'Failed to fetch trending coins'})
            
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})

@app.route('/api/gainers_losers')
def api_gainers_losers():
    # Check cache first
    if 'gainers_losers' in general_cache:
        cached_data, timestamp = general_cache['gainers_losers']
        if time.time() - timestamp < general_cache_ttl:
            return jsonify({'ok': True, 'gainers': cached_data['gainers'], 'losers': cached_data['losers']})
    
    try:
        data = cg_get('/coins/markets', {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 100,
            'page': 1,
            'sparkline': 'false',
            'price_change_percentage': '24h'
        })
        
        if data:
            # Sort by 24h change to get gainers and losers
            sorted_by_change = sorted(data, key=lambda x: x.get('price_change_percentage_24h', 0), reverse=True)
            
            gainers = []
            for coin in sorted_by_change[:10]:
                gainers.append({
                    'id': coin.get('id'),
                    'name': coin.get('name'),
                    'symbol': coin.get('symbol', '').upper(),
                    'price': coin.get('current_price', '—'),
                    'price_change_24h': coin.get('price_change_percentage_24h', '—'),
                    'image': coin.get('image', '')
                })
            
            losers = []
            for coin in sorted_by_change[-10:]:
                losers.append({
                    'id': coin.get('id'),
                    'name': coin.get('name'),
                    'symbol': coin.get('symbol', '').upper(),
                    'price': coin.get('current_price', '—'),
                    'price_change_24h': coin.get('price_change_percentage_24h', '—'),
                    'image': coin.get('image', '')
                })
            
            # Cache the response
            general_cache['gainers_losers'] = ({'gainers': gainers, 'losers': losers}, time.time())
            return jsonify({'ok': True, 'gainers': gainers, 'losers': losers})
        else:
            return jsonify({'ok': False, 'message': 'Failed to fetch gainers and losers'})
            
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})

@app.route('/api/global')
def api_global():
    # Check cache first
    if 'global' in general_cache:
        cached_data, timestamp = general_cache['global']
        if time.time() - timestamp < general_cache_ttl:
            return jsonify({'ok': True, 'data': cached_data})
    
    try:
        data = cg_get('/global')
        
        if data and 'data' in data:
            global_data = data['data']
            result = {
                'total_market_cap': global_data.get('total_market_cap', {}).get('usd', '—'),
                'market_cap_change_24h': global_data.get('market_cap_change_percentage_24h_usd', '—'),
                'btc_dominance': global_data.get('market_cap_percentage', {}).get('btc', '—'),
                'eth_dominance': global_data.get('market_cap_percentage', {}).get('eth', '—'),
                'active_cryptocurrencies': global_data.get('active_cryptocurrencies', '—'),
                'markets': global_data.get('markets', '—'),
                'exchanges': global_data.get('exchanges', '—')
            }
            
            # Cache the response
            general_cache['global'] = (result, time.time())
            return jsonify({'ok': True, 'data': result})
        else:
            return jsonify({'ok': False, 'message': 'Failed to fetch global data'})
            
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})

@app.route('/api/categories')
def api_categories():
    # Check cache first
    if 'categories' in general_cache:
        cached_data, timestamp = general_cache['categories']
        if time.time() - timestamp < general_cache_ttl:
            return jsonify({'ok': True, 'categories': cached_data})
    
    try:
        data = cg_get('/coins/categories')
        
        if data:
            # Sort by market cap and take top 10
            sorted_categories = sorted(data, key=lambda x: x.get('market_cap', 0), reverse=True)[:10]
            
            categories = []
            for category in sorted_categories:
                categories.append({
                    'name': category.get('name', '—'),
                    'market_cap': category.get('market_cap', '—'),
                    'volume_24h': category.get('volume_24h', '—'),
                    'market_cap_change_24h': category.get('market_cap_change_24h', '—')
                })
            
            # Cache the response
            general_cache['categories'] = (categories, time.time())
            return jsonify({'ok': True, 'categories': categories})
        else:
            return jsonify({'ok': False, 'message': 'Failed to fetch categories'})
            
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})

@app.route('/api/exchanges')
def api_exchanges():
    # Check cache first
    if 'exchanges' in general_cache:
        cached_data, timestamp = general_cache['exchanges']
        if time.time() - timestamp < general_cache_ttl:
            return jsonify({'ok': True, 'exchanges': cached_data})
    
    try:
        data = cg_get('/exchanges', {
            'per_page': 10,
            'page': 1
        })
        
        if data:
            exchanges = []
            for exchange in data:
                exchanges.append({
                    'name': exchange.get('name', '—'),
                    'trust_score': exchange.get('trust_score', '—'),
                    'trust_score_rank': exchange.get('trust_score_rank', '—'),
                    'trade_volume_24h_btc': exchange.get('trade_volume_24h_btc', '—'),
                    'year_established': exchange.get('year_established', '—'),
                    'image': exchange.get('image', '')
                })
            
            # Cache the response
            general_cache['exchanges'] = (exchanges, time.time())
            return jsonify({'ok': True, 'exchanges': exchanges})
        else:
            return jsonify({'ok': False, 'message': 'Failed to fetch exchanges'})
            
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})

@app.route('/api/stablecoins')
def api_stablecoins():
    # Check cache first
    if 'stablecoins' in general_cache:
        cached_data, timestamp = general_cache['stablecoins']
        if time.time() - timestamp < general_cache_ttl:
            return jsonify({'ok': True, 'coins': cached_data})
    
    try:
        data = cg_get('/coins/markets', {
            'vs_currency': 'usd',
            'category': 'stablecoins',
            'order': 'market_cap_desc',
            'per_page': 10,
            'page': 1,
            'sparkline': 'false'
        })
        
        if data:
            coins = []
            for coin in data:
                coins.append({
                    'id': coin.get('id'),
                    'name': coin.get('name'),
                    'symbol': coin.get('symbol', '').upper(),
                    'price': coin.get('current_price', '—'),
                    'market_cap': coin.get('market_cap', '—'),
                    'volume_24h': coin.get('total_volume', '—'),
                    'image': coin.get('image', '')
                })
            
            # Cache the response
            general_cache['stablecoins'] = (coins, time.time())
            return jsonify({'ok': True, 'coins': coins})
        else:
            return jsonify({'ok': False, 'message': 'Failed to fetch stablecoins'})
            
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})

@app.route('/api/fng')
def api_fng():
    # Check cache first
    if 'fng' in general_cache:
        cached_data, timestamp = general_cache['fng']
        if time.time() - timestamp < general_cache_ttl:
            return jsonify({'ok': True, 'now': cached_data['now'], 'history': cached_data['history']})
    
    try:
        response = requests.get('https://api.alternative.me/fng/?limit=7', timeout=REQUEST_TIMEOUT)
        data = response.json()
        
        if data and 'data' in data:
            # Extract current value and classification
            now_data = data['data'][0] if data['data'] else {}
            now = {
                'value': now_data.get('value', '—'),
                'classification': now_data.get('value_classification', '—')
            }
            
            # Extract history
            history = []
            for item in data['data']:
                history.append({
                    'value': item.get('value', '—'),
                    'classification': item.get('value_classification', '—'),
                    'timestamp': item.get('timestamp', '—')
                })
            
            # Cache the response
            general_cache['fng'] = ({'now': now, 'history': history}, time.time())
            return jsonify({'ok': True, 'now': now, 'history': history})
        else:
            return jsonify({'ok': False, 'message': 'Failed to fetch fear and greed index'})
            
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
