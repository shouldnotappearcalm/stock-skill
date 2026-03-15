#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一数据源 - 多级兜底
对外统一输出：实时行情、历史K线均经 东方财富→新浪→腾讯→akshare 等兜底，保证单源失败时自动切换。
"""

import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd

try:
    import akshare as ak
except Exception:
    ak = None

_STANDARD_COLS = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount']


def _symbol_suffix(code: str) -> str:
    return f'sh{code}' if code.startswith('6') else f'sz{code}'


def _amount_to_yuan(amount: float) -> float:
    """东方财富等接口成交额单位为「十万」元，此处统一转为元"""
    if amount is None:
        return 0
    try:
        a = float(amount)
        if a <= 0:
            return a
        if 0 < a < 1e7:
            return a * 100000
        return a
    except (TypeError, ValueError):
        return 0


def get_realtime_sina(code: str) -> Optional[Dict]:
    """新浪财经单只实时行情"""
    try:
        symbol = _symbol_suffix(code)
        url = f'http://hq.sinajs.cn/list={symbol}'
        r = requests.get(url, timeout=3)
        if r.status_code != 200 or 'var hq_str_' not in r.text:
            return None
        data_str = r.text.split('"')[1]
        fields = data_str.split(',')
        if len(fields) < 32:
            return None
        name = fields[0]
        price = float(fields[3])
        prev_close = float(fields[2])
        change_pct = ((price - prev_close) / prev_close) * 100 if prev_close else 0
        return {
            'code': code,
            'name': name,
            'price': price,
            'change_pct': change_pct,
            'volume': float(fields[8]) if fields[8] else 0,
            'amount': float(fields[9]) if fields[9] else 0,
            'open': float(fields[1]) if fields[1] else price,
            'high': float(fields[4]) if fields[4] else price,
            'low': float(fields[5]) if fields[5] else price,
            'prev_close': prev_close,
            'source': 'sina'
        }
    except Exception:
        return None


def get_realtime_tencent_single(code: str) -> Optional[Dict]:
    """腾讯财经单只实时行情"""
    try:
        symbol = _symbol_suffix(code)
        url = f'https://qt.gtimg.cn/q={symbol}'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://gu.qq.com/'
        }
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code != 200 or '=' not in r.text or '"' not in r.text:
            return None
        data_str = r.text.split('"')[1]
        fields = data_str.split('~')
        if len(fields) < 40:
            return None
        name = fields[1]
        price = float(fields[3]) if fields[3] else 0
        prev_close = float(fields[4]) if fields[4] else price
        change_pct = float(fields[32]) if len(fields) > 32 and fields[32] else 0
        volume = float(fields[6]) * 100 if fields[6] else 0
        # 腾讯 fields[37] 成交额单位为「万」元，转为元
        amount = float(fields[37]) * 10000 if len(fields) > 37 and fields[37] else 0
        return {
            'code': code,
            'name': name,
            'price': price,
            'change_pct': change_pct,
            'volume': volume,
            'amount': amount,
            'open': float(fields[5]) if fields[5] else price,
            'high': float(fields[33]) if len(fields) > 33 and fields[33] else price,
            'low': float(fields[34]) if len(fields) > 34 and fields[34] else price,
            'prev_close': prev_close,
            'source': 'tencent'
        }
    except Exception:
        return None


def get_realtime_tencent_batch(codes: List[str], batch_size: int = 80) -> List[Dict]:
    """腾讯财经批量实时行情"""
    results = []
    for i in range(0, len(codes), batch_size):
        batch = codes[i:i + batch_size]
        symbols = [_symbol_suffix(c) for c in batch]
        try:
            url = f"https://qt.gtimg.cn/q={','.join(symbols)}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'https://gu.qq.com/'
            }
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                continue
            for j, line in enumerate(r.text.strip().split('\n')):
                if not line or j >= len(batch) or '=' not in line or '"' not in line:
                    continue
                try:
                    data_str = line.split('"')[1]
                    fields = data_str.split('~')
                    if len(fields) < 40:
                        continue
                    code = batch[j]
                    name = fields[1]
                    price = float(fields[3]) if fields[3] else 0
                    prev_close = float(fields[4]) if fields[4] else price
                    change_pct = float(fields[32]) if len(fields) > 32 and fields[32] else 0
                    volume = float(fields[6]) * 100 if fields[6] else 0
                    amount = float(fields[37]) * 10000 if len(fields) > 37 and fields[37] else 0
                    results.append({
                        'code': code,
                        'name': name,
                        'price': price,
                        'change_pct': change_pct,
                        'volume': volume,
                        'amount': amount,
                        'open': float(fields[5]) if fields[5] else price,
                        'high': float(fields[33]) if len(fields) > 33 and fields[33] else price,
                        'low': float(fields[34]) if len(fields) > 34 and fields[34] else price,
                        'prev_close': prev_close,
                        'source': 'tencent'
                    })
                except Exception:
                    continue
            time.sleep(0.15)
        except Exception:
            continue
    return results


def get_realtime_akshare(code: str) -> Optional[Dict]:
    """akshare 全市场取单只（底层多为东方财富）"""
    if not ak:
        return None
    try:
        df = ak.stock_zh_a_spot_em()
        if df is None or df.empty:
            return None
        row = df[df['代码'] == code]
        if row.empty:
            return None
        r = row.iloc[0]
        def _col(row, key, default):
            return row[key] if key in row.index else default
        return {
            'code': code,
            'name': r['名称'],
            'price': float(r['最新价']),
            'change_pct': float(r['涨跌幅']),
            'volume': float(r['成交量']) * 100,
            'amount': _amount_to_yuan(float(r['成交额'])),
            'open': float(_col(r, '今开', r['最新价'])),
            'high': float(_col(r, '最高', r['最新价'])),
            'low': float(_col(r, '最低', r['最新价'])),
            'prev_close': float(_col(r, '昨收', r['最新价'])),
            'source': 'akshare'
        }
    except Exception:
        return None


def get_realtime_sina_batch(codes: List[str], max_codes: int = 50) -> Optional[List[Dict]]:
    """新浪批量实时"""
    try:
        symbols = [_symbol_suffix(c) for c in codes[:max_codes]]
        url = f'http://hq.sinajs.cn/list={",".join(symbols)}'
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        results = []
        for i, line in enumerate(r.text.strip().split('\n')):
            if 'var hq_str_' not in line or i >= len(codes):
                continue
            code = codes[i]
            data_str = line.split('"')[1]
            fields = data_str.split(',')
            if len(fields) < 32:
                continue
            price = float(fields[3])
            prev_close = float(fields[2])
            change_pct = ((price - prev_close) / prev_close) * 100 if prev_close else 0
            results.append({
                'code': code,
                'name': fields[0],
                'price': price,
                'change_pct': change_pct,
                'volume': float(fields[8]) if fields[8] else 0,
                'amount': float(fields[9]) if fields[9] else 0,
                'open': float(fields[1]) if fields[1] else price,
                'high': float(fields[4]) if fields[4] else price,
                'low': float(fields[5]) if fields[5] else price,
                'prev_close': prev_close,
                'source': 'sina'
            })
        return results if results else None
    except Exception:
        return None


def _normalize_history_columns(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """将历史K线 DataFrame 统一为 date, open, high, low, close, volume, amount"""
    cn_map = {'日期': 'date', '开盘': 'open', '最高': 'high', '最低': 'low', '收盘': 'close', '成交量': 'volume', '成交额': 'amount'}
    df = df.rename(columns={k: v for k, v in cn_map.items() if k in df.columns})
    df = df.copy()
    if 'amount' not in df.columns and 'close' in df.columns and 'volume' in df.columns:
        df['amount'] = (df['close'] * df['volume']).astype(float)
    if 'volume' not in df.columns and 'amount' in df.columns and 'close' in df.columns:
        df['volume'] = (df['amount'] / df['close'].replace(0, float('nan'))).fillna(0).astype(int)
    need = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount']
    if not all(c in df.columns for c in need):
        return None
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y%m%d')
    return df[need]


def get_history_eastmoney(code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """东方财富历史K线（akshare），成交量统一为股"""
    if not ak:
        return None
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust="")
        if df is None or df.empty:
            return None
        if '成交量' in df.columns:
            df = df.copy()
            df['成交量'] = df['成交量'] * 100
        return _normalize_history_columns(df)
    except Exception:
        return None


def get_history_sina(code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """新浪历史K线（akshare）"""
    if not ak:
        return None
    try:
        if not hasattr(ak, 'stock_zh_a_daily'):
            return None
        symbol = _symbol_suffix(code)
        df = ak.stock_zh_a_daily(symbol=symbol, start_date=start_date, end_date=end_date, adjust="")
        if df is None or df.empty:
            return None
        return _normalize_history_columns(df)
    except Exception:
        return None


def get_history_tencent(code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """腾讯历史K线（akshare）"""
    if not ak:
        return None
    try:
        if not hasattr(ak, 'stock_zh_a_hist_tx'):
            return None
        symbol = _symbol_suffix(code)
        df = ak.stock_zh_a_hist_tx(symbol=symbol, start_date=start_date, end_date=end_date, adjust="")
        if df is None or df.empty:
            return None
        return _normalize_history_columns(df)
    except Exception:
        return None


class UnifiedDataSource:
    """
    统一数据源：对外单一入口，内部多级兜底。
    实时：新浪 → 腾讯 → akshare(东财)
    历史：东财(ak) → 新浪(ak) → 腾讯(ak)
    """

    def get_realtime_price(self, code: str) -> Optional[Dict]:
        """单只实时行情，多源兜底"""
        out = get_realtime_sina(code)
        if out:
            return out
        out = get_realtime_tencent_single(code)
        if out:
            return out
        out = get_realtime_akshare(code)
        return out

    def get_realtime_batch(self, codes: List[str]) -> List[Dict]:
        """批量实时行情，多源兜底"""
        if not codes:
            return []
        out = get_realtime_sina_batch(codes)
        if out and len(out) >= min(len(codes), 50):
            return out
        out = get_realtime_tencent_batch(codes)
        if out:
            return out
        result = []
        for code in codes:
            item = self.get_realtime_price(code)
            if item:
                result.append(item)
        return result

    def get_history_data(self, code: str, days: int = 120) -> Optional[pd.DataFrame]:
        """历史K线，多源兜底。返回列: date, open, high, low, close, volume, amount"""
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime('%Y%m%d')
        df = get_history_eastmoney(code, start_date, end_date)
        if df is not None and not df.empty:
            return df.tail(days)
        df = get_history_sina(code, start_date, end_date)
        if df is not None and not df.empty:
            return df.tail(days)
        df = get_history_tencent(code, start_date, end_date)
        if df is not None and not df.empty:
            return df.tail(days)
        return None
