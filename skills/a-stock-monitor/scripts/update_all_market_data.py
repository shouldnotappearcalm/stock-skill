#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新全市场A股数据到缓存数据库
用于市场情绪计算
支持多数据源兜底：东方财富 → akshare股票列表+腾讯行情
"""

import akshare as ak
import requests
import time
from stock_cache_db import StockCache
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


def get_all_stocks_eastmoney():
    """东方财富获取全市场数据（首选，数据全）"""
    try:
        df = ak.stock_zh_a_spot_em()
        if df is not None and not df.empty:
            return df
    except Exception as e:
        print(f"⚠️ 东方财富接口失败: {e}")
    return None


def get_stock_list_akshare():
    """从 akshare 获取股票代码列表"""
    try:
        df = ak.stock_info_a_code_name()
        if df is not None and not df.empty:
            return df['code'].tolist()
    except Exception as e:
        print(f"⚠️ akshare股票列表获取失败: {e}")
    return None


def get_realtime_tencent_batch(codes, batch_size=80):
    """腾讯财经批量获取实时行情"""
    results = []
    total = len(codes)
    
    for i in range(0, total, batch_size):
        batch = codes[i:i+batch_size]
        
        # 转换为腾讯格式
        symbols = []
        for code in batch:
            if code.startswith('6'):
                symbols.append(f'sh{code}')
            else:
                symbols.append(f'sz{code}')
        
        try:
            url = f"https://qt.gtimg.cn/q={','.join(symbols)}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'https://gu.qq.com/'
            }
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code != 200:
                print(f"⚠️ 腾讯请求失败: {resp.status_code}")
                continue
            
            lines = resp.text.strip().split('\n')
            
            for j, line in enumerate(lines):
                if not line or j >= len(batch):
                    continue
                
                try:
                    # 解析腾讯格式: v_sh600900="1~长江电力~600900~..."
                    if '=' not in line or '"' not in line:
                        continue
                    
                    data_str = line.split('"')[1]
                    fields = data_str.split('~')
                    
                    if len(fields) < 40:
                        continue
                    
                    code = batch[j]
                    name = fields[1]
                    price = float(fields[3]) if fields[3] else 0
                    prev_close = float(fields[4]) if fields[4] else price
                    open_price = float(fields[5]) if fields[5] else price
                    # fields[32] 是涨跌幅百分比
                    change_pct = float(fields[32]) if len(fields) > 32 and fields[32] else 0
                    high = float(fields[33]) if len(fields) > 33 and fields[33] else price
                    low = float(fields[34]) if len(fields) > 34 and fields[34] else price
                    # fields[6] 成交量单位是手，转换为股（1手=100股）
                    volume = float(fields[6]) * 100 if fields[6] else 0
                    # fields[37] 成交额单位为「万」元，转换为元
                    amount = float(fields[37]) * 10000 if len(fields) > 37 and fields[37] else 0
                    turnover = float(fields[38]) if len(fields) > 38 and fields[38] else 0
                    amplitude = float(fields[43]) if len(fields) > 43 and fields[43] else 0
                    
                    results.append({
                        'code': code,
                        'name': name,
                        'price': price,
                        'prev_close': prev_close,
                        'open': open_price,
                        'high': high,
                        'low': low,
                        'change_pct': change_pct,
                        'volume': volume,
                        'amount': amount,
                        'turnover': turnover,
                        'amplitude': amplitude,
                    })
                except Exception as e:
                    continue
            
            # 进度显示
            if (i + batch_size) % 500 == 0 or i + batch_size >= total:
                print(f"   处理进度: {min(i+batch_size, total)}/{total} ({len(results)} 成功)")
            
            time.sleep(0.15)  # 避免请求过快
            
        except Exception as e:
            print(f"⚠️ 腾讯批量请求失败: {e}")
            continue
    
    return results


def update_all_market_data():
    """更新全市场A股数据（多数据源兜底）"""
    print(f"\n{'='*60}")
    print(f"📊 开始更新全市场A股数据")
    print(f"{'='*60}\n")
    
    cache = StockCache()
    
    # 方案1: 东方财富（首选，数据全）
    print("🔄 尝试东方财富接口...")
    df = get_all_stocks_eastmoney()
    
    if df is not None and not df.empty:
        print(f"✅ 东方财富获取到 {len(df)} 只股票数据")
        
        stocks_data = []
        for idx, row in df.iterrows():
            try:
                code = str(row['代码'])
                amount = float(row['成交额']) if row['成交额'] else None
                if amount is not None and 0 < amount < 1e7:
                    amount = amount * 100000
                stock_data = {
                    'code': code,
                    'name': row['名称'],
                    'price': float(row['最新价']) if row['最新价'] else None,
                    'prev_close': float(row.get('昨收', 0)) if row.get('昨收') else None,
                    'open': float(row.get('今开', 0)) if row.get('今开') else None,
                    'high': float(row.get('最高', 0)) if row.get('最高') else None,
                    'low': float(row.get('最低', 0)) if row.get('最低') else None,
                    'change_pct': float(row['涨跌幅']) if row['涨跌幅'] else None,
                    'volume': float(row['成交量']) * 100 if row['成交量'] else None,
                    'amount': amount,
                    'turnover': float(row.get('换手率', 0)) if row.get('换手率') else None,
                    'amplitude': float(row.get('振幅', 0)) if row.get('振幅') else None,
                }
                stocks_data.append(stock_data)
                
                if (idx + 1) % 500 == 0:
                    print(f"   处理进度: {idx+1}/{len(df)}")
            except:
                continue
        
        # 批量保存
        cache.save_stocks(stocks_data)
        cache.close()
        print(f"\n✅ 数据更新完成! 成功: {len(stocks_data)} 只")
        return len(stocks_data)
    
    # 方案2: akshare股票列表 + 腾讯实时行情
    print("🔄 东方财富失败，尝试 akshare + 腾讯财经...")
    codes = get_stock_list_akshare()
    
    if codes:
        print(f"   获取到 {len(codes)} 只股票代码，开始获取行情...")
        
        results = get_realtime_tencent_batch(codes)
        
        if results:
            # 批量保存
            cache.save_stocks(results)
            cache.close()
            print(f"\n✅ 数据更新完成! 成功: {len(results)} 只")
            return len(results)
    
    cache.close()
    print(f"\n❌ 所有数据源均失败，请检查网络连接")
    return 0


if __name__ == '__main__':
    update_all_market_data()
