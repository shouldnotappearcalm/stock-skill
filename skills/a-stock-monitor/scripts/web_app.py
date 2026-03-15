#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股量化监控系统 - Web界面
Flask + ECharts
"""

from flask import Flask, render_template, jsonify, request
from datetime import datetime
from stock_cache_db import StockCache
from backtest_engine import BacktestEngine
from config import WATCHED_STOCKS as DEFAULT_WATCHED_STOCKS
import json
import os

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# 监控的核心股票（从 config.py 导入默认值）
WATCHED_STOCKS = list(DEFAULT_WATCHED_STOCKS)


# ============== 页面路由 ==============

@app.route('/')
def index():
    """首页 - 仪表盘"""
    return render_template('index.html')


@app.route('/stock/<code>')
def stock_detail(code):
    """股票详情页"""
    return render_template('stock_detail.html', code=code)


@app.route('/backtest')
def backtest_page():
    """回测工具页"""
    return render_template('backtest.html')


@app.route('/optimize')
def optimize_page():
    """参数优化页"""
    return render_template('optimize.html')


@app.route('/stocks-manage')
def stocks_manage_page():
    """股票池管理页"""
    return render_template('stocks_manage.html')


# ============== API接口 ==============

@app.route('/api/stocks')
def api_stocks():
    """获取所有监控股票（返回最近一次数据，不论是否过期）"""
    cache = StockCache()
    
    stocks = []
    for code in WATCHED_STOCKS:
        # 直接获取最近一次的数据（不过滤过期）
        stock = cache.get_stock(code)
        
        if stock:
            # 获取资金流
            fund = cache.get_fund_flow(code, max_age_hours=48)
            if fund:
                stock['fund_flow'] = fund
            
            # 获取技术指标
            tech = cache.get_tech_indicators(code, max_age_hours=48)
            if tech:
                stock['tech_indicators'] = tech
            
            stocks.append(stock)
    
    cache.close()
    
    return jsonify({
        'status': 'success',
        'data': stocks,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


@app.route('/api/stocks/realtime')
def api_stocks_realtime():
    """获取监控股票的实时价格（轻量级，仅价格和涨跌）"""
    cache = StockCache()
    
    stocks = []
    for code in WATCHED_STOCKS:
        stock = cache.get_stock(code)
        if stock:
            # 只返回关键字段，减少数据量
            stocks.append({
                'code': stock['code'],
                'name': stock['name'],
                'price': stock['price'],
                'change_pct': stock['change_pct'],
                'update_time': stock.get('update_time')
            })
    
    cache.close()
    
    return jsonify({
        'status': 'success',
        'data': stocks,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


@app.route('/api/stock/<code>')
def api_stock_detail(code):
    """获取单只股票详情"""
    cache = StockCache()
    
    stock = cache.get_stock(code)
    if not stock:
        cache.close()
        return jsonify({'status': 'error', 'message': '股票不存在'})
    
    # 获取资金流
    fund = cache.get_fund_flow(code, max_age_hours=24)
    if fund:
        stock['fund_flow'] = fund
    
    # 获取技术指标
    tech = cache.get_tech_indicators(code, max_age_hours=24)
    if tech:
        stock['tech_indicators'] = tech
    
    cache.close()
    
    return jsonify({
        'status': 'success',
        'data': stock
    })


@app.route('/api/history/<code>')
def api_history(code):
    """获取历史K线数据"""
    days = request.args.get('days', 60, type=int)
    
    from tech_indicators import TechIndicatorCalculator
    calc = TechIndicatorCalculator()
    
    history = calc.get_stock_history(code, days=days)
    
    if history is None:
        return jsonify({'status': 'error', 'message': '获取历史数据失败'})
    
    # 转换为ECharts需要的格式
    data = []
    for date, row in history.iterrows():
        data.append({
            'date': date.strftime('%Y-%m-%d'),
            'open': float(row['open']),
            'close': float(row['close']),
            'high': float(row['high']),
            'low': float(row['low']),
            'volume': float(row['volume'])
        })
    
    return jsonify({
        'status': 'success',
        'data': data
    })


@app.route('/api/backtest', methods=['POST'])
def api_backtest():
    """回测接口"""
    data = request.json
    
    symbol = data.get('symbol')
    strategy = data.get('strategy')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    initial_capital = data.get('initial_capital', 100000)
    
    if not all([symbol, strategy, start_date, end_date]):
        return jsonify({'status': 'error', 'message': '参数不完整'})
    
    # 执行回测
    engine = BacktestEngine()
    result = engine.backtest(
        symbol=symbol,
        strategy_name=strategy,
        start_date=start_date.replace('-', ''),
        end_date=end_date.replace('-', ''),
        initial_capital=initial_capital
    )
    
    if result is None:
        return jsonify({'status': 'error', 'message': '回测失败'})
    
    # 转换交易记录
    trades = []
    for trade in result['trades']:
        trades.append({
            'date': trade['date'].strftime('%Y-%m-%d'),
            'action': trade['action'],
            'price': trade['price'],
            'qty': trade['qty'],
            'amount': trade['amount'],
            'profit': trade.get('profit', 0)
        })
    
    result['trades'] = trades
    
    return jsonify({
        'status': 'success',
        'data': result
    })


@app.route('/api/cache/stats')
def api_cache_stats():
    """获取缓存统计"""
    cache = StockCache()
    stats = cache.get_cache_stats()
    cache.close()
    
    return jsonify({
        'status': 'success',
        'data': stats
    })


@app.route('/api/stock/<code>/refresh', methods=['POST'])
def api_refresh_stock(code):
    """刷新单只股票数据（异步）"""
    import threading
    
    def refresh_in_background(stock_code):
        """后台刷新数据"""
        try:
            from tech_indicators import TechIndicatorCalculator
            from stock_async_fetcher import StockAsyncFetcher
            
            # 1. 更新基础数据
            fetcher = StockAsyncFetcher()
            fetcher.fetch_and_cache([stock_code])
            
            # 2. 更新技术指标
            calc = TechIndicatorCalculator()
            result = calc.calculate_indicators(stock_code)
            if result:
                calc.cache.save_tech_indicators(stock_code, result)
            calc.close()
            
            # 3. 更新资金流（使用智能数据源）
            fund = fetcher.fetch_fund_flow(stock_code)
            
            # 关闭连接
            fetcher.close()
                
        except Exception as e:
            print(f"后台刷新{stock_code}失败: {e}")
    
    # 启动后台线程
    thread = threading.Thread(target=refresh_in_background, args=(code,))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'status': 'success',
        'message': f'正在后台刷新 {code} 的数据，请稍后刷新页面查看'
    })


# ============== 股票池管理API ==============

@app.route('/api/watchlist', methods=['GET'])
def api_get_watchlist():
    """获取当前监控股票列表（快速版）"""
    # 只返回代码和名称，不查询实时数据
    # 实时数据由前端异步加载
    
    stocks_info = []
    
    # 从缓存快速获取基本信息（不等待实时数据）
    cache = StockCache()
    
    for code in WATCHED_STOCKS:
        stock = cache.get_stock(code)
        
        if stock:
            stocks_info.append({
                'code': code,
                'name': stock['name'],
                'price': stock.get('price', 0),
                'change_pct': stock.get('change_pct', 0)
            })
        else:
            # 如果缓存没有，只返回代码（前端会显示"加载中"）
            stocks_info.append({
                'code': code,
                'name': '加载中...',
                'price': 0,
                'change_pct': 0
            })
    
    cache.close()
    
    return jsonify({
        'status': 'success',
        'data': stocks_info
    })


@app.route('/api/watchlist', methods=['POST'])
def api_add_to_watchlist():
    """添加股票到监控列表（快速版）"""
    data = request.json
    code = data.get('code', '').strip()
    
    if not code:
        return jsonify({'status': 'error', 'message': '股票代码不能为空'})
    
    # 验证代码格式（6位数字）
    if not code.isdigit() or len(code) != 6:
        return jsonify({'status': 'error', 'message': '股票代码格式错误（应为6位数字）'})
    
    # 检查是否已存在
    if code in WATCHED_STOCKS:
        return jsonify({'status': 'error', 'message': '该股票已在监控列表中'})
    
    # 简化验证：只检查代码格式，不实时查询
    # 如果股票不存在，首页加载时会显示"未知"
    
    # 添加到列表
    WATCHED_STOCKS.append(code)
    
    # 保存到配置文件
    save_watchlist()
    
    return jsonify({
        'status': 'success',
        'message': f'成功添加 {code}（请刷新首页查看详情）',
        'data': {'code': code, 'name': '待加载'}
    })


@app.route('/api/watchlist/<code>', methods=['DELETE'])
def api_remove_from_watchlist(code):
    """从监控列表移除股票"""
    if code not in WATCHED_STOCKS:
        return jsonify({'status': 'error', 'message': '该股票不在监控列表中'})
    
    WATCHED_STOCKS.remove(code)
    
    # 保存到配置文件
    save_watchlist()
    
    return jsonify({
        'status': 'success',
        'message': f'已移除 {code}'
    })


# 搜索缓存（内存缓存，避免重复请求）
_search_cache = {}
_search_cache_time = {}

@app.route('/api/stock/search')
def api_search_stock():
    """搜索股票（带缓存）"""
    keyword = request.args.get('q', '').strip()
    
    if not keyword:
        return jsonify({'status': 'error', 'message': '搜索关键词不能为空'})
    
    # 检查缓存（5分钟有效）
    import time
    now = time.time()
    if keyword in _search_cache:
        cache_time = _search_cache_time.get(keyword, 0)
        if now - cache_time < 300:  # 5分钟内使用缓存
            return jsonify({
                'status': 'success',
                'data': _search_cache[keyword],
                'cached': True
            })
    
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        
        # 模糊搜索（代码或名称）
        mask = df['代码'].str.contains(keyword, na=False) | df['名称'].str.contains(keyword, na=False)
        results = df[mask].head(10)
        
        stocks = []
        for _, row in results.iterrows():
            stocks.append({
                'code': row['代码'],
                'name': row['名称'],
                'price': float(row['最新价']),
                'change_pct': float(row['涨跌幅'])
            })
        
        # 缓存结果
        _search_cache[keyword] = stocks
        _search_cache_time[keyword] = now
        
        return jsonify({
            'status': 'success',
            'data': stocks
        })
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'搜索失败: {str(e)}'})


def save_watchlist():
    """保存监控列表到配置文件"""
    import os
    config_file = os.path.join(os.path.dirname(__file__), 'watchlist.json')
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(WATCHED_STOCKS, f, ensure_ascii=False, indent=2)


def load_watchlist():
    """从配置文件加载监控列表"""
    import os
    config_file = os.path.join(os.path.dirname(__file__), 'watchlist.json')
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                stocks = json.load(f)
                return stocks
        except:
            pass
    
    return None


def init_watchlist():
    """初始化监控列表"""
    config_file = os.path.join(os.path.dirname(__file__), 'watchlist.json')
    
    if os.path.exists(config_file):
        saved_list = load_watchlist()
        if saved_list:
            WATCHED_STOCKS.clear()
            WATCHED_STOCKS.extend(saved_list)
            return len(WATCHED_STOCKS), True  # 已加载
    
    # 文件不存在，创建默认列表
    save_watchlist()
    return len(WATCHED_STOCKS), False  # 新创建


# 模块加载时初始化
_count, _loaded = init_watchlist()
if _loaded:
    print(f"✅ 已加载 {_count} 只监控股票")
else:
    print(f"📝 已创建默认监控列表: {_count} 只股票")


# ============== 中长线选股API ==============

@app.route('/long-term-select')
def long_term_select_page():
    """中长线选股页面"""
    return render_template('long_term_select.html')


@app.route('/api/long-term-select', methods=['POST'])
def api_long_term_select():
    """中长线选股API"""
    from long_term_selector import LongTermSelector
    
    data = request.json
    top_n = data.get('top_n', 5)
    
    try:
        selector = LongTermSelector()
        stocks = selector.select_top_stocks(top_n=top_n)
        selector.close()
        
        return jsonify({
            'status': 'success',
            'data': stocks
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })


@app.route('/api/long-term-report', methods=['POST'])
def api_long_term_report():
    """生成中长线选股报告"""
    from long_term_selector import LongTermSelector
    
    data = request.json
    stocks = data.get('stocks', [])
    
    if not stocks:
        return jsonify({
            'status': 'error',
            'message': '无数据'
        })
    
    try:
        selector = LongTermSelector()
        report = selector.generate_report(stocks)
        selector.close()
        
        return jsonify({
            'status': 'success',
            'report': report
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })


# ============== 选股中心API ==============

@app.route('/stock-selector')
def stock_selector_page():
    """选股中心页面"""
    return render_template('stock_selector.html')


@app.route('/api/selector/run', methods=['POST'])
def api_run_selector():
    """运行选股器"""
    data = request.json
    selector_type = data.get('type', 'long')  # short/long
    top_n = data.get('top_n', 5)
    
    try:
        if selector_type == 'short':
            from short_term_selector import ShortTermSelector
            selector = ShortTermSelector()
            stocks = selector.select_top_stocks(top_n=top_n)
            selector.close()
        else:
            from long_term_selector import LongTermSelector
            selector = LongTermSelector()
            stocks = selector.select_top_stocks(top_n=top_n)
            selector.close()
        
        return jsonify({
            'status': 'success',
            'data': stocks
        })
        
    except Exception as e:
        import traceback
        print(f"❌ 选股失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        })


@app.route('/api/selector/report', methods=['POST'])
def api_get_selector_report():
    """获取选股报告"""
    data = request.json
    selector_type = data.get('type', 'long')
    stocks = data.get('stocks', [])
    
    if not stocks:
        return jsonify({
            'status': 'error',
            'message': '无数据'
        })
    
    try:
        if selector_type == 'short':
            from short_term_selector import ShortTermSelector
            selector = ShortTermSelector()
            report = selector.generate_report(stocks)
            selector.close()
        else:
            from long_term_selector import LongTermSelector
            selector = LongTermSelector()
            report = selector.generate_report(stocks)
            selector.close()
        
        return jsonify({
            'status': 'success',
            'report': report
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })


@app.route('/api/market/overview', methods=['GET'])
def api_market_overview():
    """市场总览API"""
    try:
        from market_analysis import MarketAnalysis
        cache = StockCache()
        stocks = []
        for code in WATCHED_STOCKS:
            stock = cache.get_stock(code)
            if stock:
                stocks.append(stock)
        analyzer = MarketAnalysis()
        overview = analyzer.get_market_overview(stocks)
        cache.close()
        return jsonify({'status': 'success', 'data': overview})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/api/market/sentiment')
def api_market_sentiment():
    """全市场情绪API - 基于所有A股数据"""
    try:
        from market_sentiment import calculate_market_sentiment
        # 先尝试获取真实数据
        sentiment = calculate_market_sentiment(use_demo_data=False)
        # 如果没有有效数据，使用演示数据
        if sentiment['stats']['total'] == 0:
            sentiment = calculate_market_sentiment(use_demo_data=True)
            sentiment['demo_mode'] = True  # 标记为演示模式
        return jsonify({'status': 'success', 'data': sentiment})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)})


# ============== 增强版选股API ==============

@app.route('/api/enhanced-selector/run', methods=['POST'])
def api_run_enhanced_selector():
    try:
        from enhanced_long_term_selector import EnhancedLongTermSelector
        selector = EnhancedLongTermSelector()
        stocks = selector.select_top_stocks(top_n=request.json.get('top_n', 5))
        selector.close()
        return jsonify({'status': 'success', 'data': stocks})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)})


if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║       📊 A股量化监控系统 Web界面                        ║
║                                                          ║
║       访问: http://localhost:5000                       ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    app.run(host='0.0.0.0', port=5000, debug=True)