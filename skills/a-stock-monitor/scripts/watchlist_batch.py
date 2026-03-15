#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量维护 watchlist.json
用于扩充选股候选池：短线/中长线选股仅在 watchlist 内执行，池子过小时可由此脚本从文件或指数成分股批量加入。
"""

import json
import os
import re
import argparse
from typing import List, Set

WATCHLIST_PATH = os.path.join(os.path.dirname(__file__), 'watchlist.json')

INDEX_MAP = {
    'hs300': ('000300', '沪深300'),
    'zz500': ('000905', '中证500'),
    'zz800': ('000906', '中证800'),
}


def _normalize_code(code: str) -> str:
    code = code.strip()
    if not code or code.startswith('#'):
        return ''
    m = re.match(r'^(\d{6})', code)
    return m.group(1) if m else ''


def _filter_codes(codes: List[str], exclude_gem: bool = True, exclude_star: bool = True) -> List[str]:
    out = []
    for c in codes:
        if not c or len(c) != 6:
            continue
        if exclude_gem and c.startswith('3'):
            continue
        if exclude_star and c.startswith('688'):
            continue
        out.append(c)
    return out


def load_watchlist() -> List[str]:
    if not os.path.exists(WATCHLIST_PATH):
        try:
            from config import WATCHED_STOCKS
            return list(WATCHED_STOCKS)
        except Exception:
            return []
    try:
        with open(WATCHLIST_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_watchlist(codes: List[str]) -> None:
    codes = _filter_codes(list(dict.fromkeys(codes)))
    with open(WATCHLIST_PATH, 'w', encoding='utf-8') as f:
        json.dump(codes, f, ensure_ascii=False, indent=2)
    print(f"✅ 已写入 {WATCHLIST_PATH}，共 {len(codes)} 只股票")


def codes_from_file(path: str) -> List[str]:
    codes = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('['):
                try:
                    arr = json.loads(line)
                    codes.extend([_normalize_code(str(x)) for x in arr])
                except json.JSONDecodeError:
                    pass
                continue
            codes.append(_normalize_code(line))
    return [c for c in codes if c]


def codes_from_index(index_key: str) -> List[str]:
    if index_key not in INDEX_MAP:
        raise ValueError(f"不支持的指数: {index_key}，可选: {list(INDEX_MAP.keys())}")
    symbol, name = INDEX_MAP[index_key]
    try:
        import akshare as ak
        df = ak.index_stock_cons(symbol=symbol)
    except Exception as e:
        raise RuntimeError(f"获取指数成分股失败: {e}") from e
    if df is None or df.empty:
        raise RuntimeError(f"指数 {name}({symbol}) 返回空数据")
    code_col = None
    for col in ['品种代码', 'code', '成分代码', 'stock_code']:
        if col in df.columns:
            code_col = col
            break
    if code_col is None:
        code_col = df.columns[0]
    raw = df[code_col].astype(str).str.strip().tolist()
    codes = []
    for c in raw:
        m = re.match(r'^(\d{6})', c)
        if m:
            codes.append(m.group(1))
    print(f"📊 {name}({symbol}) 成分股数量: {len(codes)}")
    return codes


def main():
    parser = argparse.ArgumentParser(description='批量维护 watchlist，扩充选股候选池')
    parser.add_argument('--file', type=str, help='从本地文件读取代码，每行一个 6 位代码或一行 JSON 数组')
    parser.add_argument('--index', type=str, choices=list(INDEX_MAP.keys()),
                        help='从指数成分股追加: hs300=沪深300, zz500=中证500, zz800=中证800')
    parser.add_argument('--replace', action='store_true', help='用新列表覆盖当前 watchlist，默认是合并去重')
    parser.add_argument('--no-filter', action='store_true', help='不排除创业板(3开头)和科创板(688开头)')
    args = parser.parse_args()

    if not args.file and not args.index:
        parser.print_help()
        print()
        print("示例:")
        print("  python3 watchlist_batch.py --index hs300")
        print("  python3 watchlist_batch.py --file codes.txt")
        print("  python3 watchlist_batch.py --index zz500 --replace")
        return

    current = load_watchlist()
    to_add: List[str] = []

    if args.file:
        if not os.path.exists(args.file):
            print(f"❌ 文件不存在: {args.file}")
            return
        to_add.extend(codes_from_file(args.file))
        print(f"📄 从文件读取到 {len(to_add)} 个代码")
    if args.index:
        to_add.extend(codes_from_index(args.index))

    to_add = list(dict.fromkeys(to_add))
    if not to_add:
        print("❌ 没有可添加的股票代码")
        return

    if not args.no_filter:
        to_add = _filter_codes(to_add, exclude_gem=True, exclude_star=True)
        print(f"   过滤创业板/科创板后: {len(to_add)} 只")

    if args.replace:
        new_list = to_add
    else:
        seen: Set[str] = set(current)
        for c in to_add:
            seen.add(c)
        new_list = list(seen)

    save_watchlist(new_list)
    print(f"   当前 watchlist 总数: {len(new_list)}")


if __name__ == '__main__':
    main()
