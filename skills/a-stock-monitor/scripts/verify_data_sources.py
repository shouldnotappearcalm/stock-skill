#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据源验证脚本：拉取并打印实时价、K线、成交额/成交量等，便于核对单位与数值。

用法:
  python3 verify_data_sources.py [代码]              # 默认 600519，拉取实时 + 最近 5 日 K 线
  python3 verify_data_sources.py 000858 --days 10     # 最近 10 日 K 线
  python3 verify_data_sources.py 600036 --realtime    # 仅实时
  python3 verify_data_sources.py 600036 --kline      # 仅 K 线
  python3 verify_data_sources.py 600036 --cache      # 同时打印缓存中的数据（若有）
"""

import argparse
from datetime import datetime, timedelta


def _fmt_vol(v):
    if v is None or (isinstance(v, float) and v != v):
        return "--"
    try:
        x = float(v)
        if x >= 1e8:
            return f"{x/1e8:.2f} 亿股"
        if x >= 1e4:
            return f"{x/1e4:.2f} 万股"
        return f"{x:.0f} 股"
    except (TypeError, ValueError):
        return str(v)


def _fmt_amt(v):
    if v is None or (isinstance(v, float) and v != v):
        return "--"
    try:
        x = float(v)
        if x >= 1e8:
            return f"{x/1e8:.2f} 亿元"
        if x >= 1e4:
            return f"{x/1e4:.2f} 万元"
        return f"{x:.0f} 元"
    except (TypeError, ValueError):
        return str(v)


def run_realtime(code: str, use_hybrid: bool = True):
    print("\n========== 实时行情 ==========")
    try:
        if use_hybrid:
            from hybrid_data_source import HybridDataSource
            ds = HybridDataSource()
            data = ds.get_realtime_price(code)
            label = "HybridDataSource(Tushare→统一数据源)"
        else:
            from unified_data_source import UnifiedDataSource
            ds = UnifiedDataSource()
            data = ds.get_realtime_price(code)
            label = "UnifiedDataSource(新浪→腾讯→东财)"
    except Exception as e:
        print(f"拉取失败: {e}")
        return
    if not data:
        print("无实时数据返回")
        return
    print(f"数据源: {label}")
    print(f"来源标识: {data.get('source', '--')}")
    print(f"  代码: {data.get('code')}  名称: {data.get('name')}")
    print(f"  最新价: {data.get('price')}  涨跌幅: {data.get('change_pct')}%")
    print(f"  今开: {data.get('open')}  最高: {data.get('high')}  最低: {data.get('low')}  昨收: {data.get('prev_close')}")
    print(f"  成交量(股): {data.get('volume')}  → 展示: {_fmt_vol(data.get('volume'))}")
    print(f"  成交额(元): {data.get('amount')}  → 展示: {_fmt_amt(data.get('amount'))}")
    print("  约定: 成交量单位=股, 成交额单位=元")


def run_kline(code: str, days: int):
    print(f"\n========== 历史 K 线（最近 {days} 日）==========")
    try:
        from unified_data_source import UnifiedDataSource
        ds = UnifiedDataSource()
        df = ds.get_history_data(code, days=days)
    except Exception as e:
        print(f"拉取失败: {e}")
        return
    if df is None or df.empty:
        print("无 K 线数据")
        return
    need = ["date", "open", "high", "low", "close", "volume", "amount"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        print(f"缺少列: {missing}")
        print(df.head())
        return
    df = df.tail(days).copy()
    df["volume_show"] = df["volume"].apply(lambda x: _fmt_vol(x))
    df["amount_show"] = df["amount"].apply(lambda x: _fmt_amt(x))
    print("列约定: date, open, high, low, close, volume(股), amount(元)")
    print(df[["date", "open", "high", "low", "close", "volume", "amount"]].to_string())
    print("\n展示用: volume → volume_show, amount → amount_show")
    print(df[["date", "close", "volume_show", "amount_show"]].to_string())


def run_cache(code: str):
    print("\n========== 本地缓存（stock_cache）==========")
    try:
        from stock_cache_db import StockCache
        cache = StockCache()
        row = cache.get_stock(code)
        cache.close()
    except Exception as e:
        print(f"读取缓存失败: {e}")
        return
    if not row:
        print("缓存中无该股票")
        return
    print(f"  代码: {row.get('code')}  名称: {row.get('name')}")
    print(f"  最新价: {row.get('price')}  涨跌幅: {row.get('change_pct')}%")
    print(f"  今开: {row.get('open')}  最高: {row.get('high')}  最低: {row.get('low')}")
    print(f"  成交量: {row.get('volume')}  → 展示: {_fmt_vol(row.get('volume'))}")
    print(f"  成交额: {row.get('amount')}  → 展示: {_fmt_amt(row.get('amount'))}")
    print(f"  更新时间: {row.get('update_time')}")


def main():
    parser = argparse.ArgumentParser(description="验证实时价、K线、成交额/成交量等数据源与单位")
    parser.add_argument("code", nargs="?", default="600519", help="股票代码，如 600519")
    parser.add_argument("--days", type=int, default=5, help="K 线取最近几日，默认 5")
    parser.add_argument("--realtime", action="store_true", help="仅拉取实时行情")
    parser.add_argument("--kline", action="store_true", help="仅拉取 K 线")
    parser.add_argument("--cache", action="store_true", help="同时打印缓存中的数据")
    parser.add_argument("--unified-only", action="store_true", help="实时仅用 UnifiedDataSource，不用 Hybrid")
    args = parser.parse_args()
    code = args.code.strip()
    if len(code) != 6 or not code.isdigit():
        print("请提供 6 位股票代码")
        return
    print(f"验证股票: {code}  (时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    if not args.kline:
        run_realtime(code, use_hybrid=not args.unified_only)
    if not args.realtime:
        run_kline(code, args.days)
    if args.cache:
        run_cache(code)
    print("\n---------- 单位说明 ----------")
    print("  成交量: 全链路统一为「股」；东方财富/akshare 接口为手，已 ×100 转股。")
    print("  成交额: 全链路统一为「元」；东方财富若为万，已 ×10000 转元；腾讯为万，已 ×10000 转元。")


if __name__ == "__main__":
    main()
