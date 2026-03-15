#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基本面数据（占位实现）
供 enhanced_long_term_selector 使用；无 Tushare 等数据源时返回空数据，选股仅依赖技术面
"""

from typing import Dict, Any


class FundamentalData:
    def get_stock_fundamental(self, code: str) -> Dict[str, Any]:
        return {
            'pe': 0,
            'roe': 0,
            'profit_growth': 0,
            'dividend_yield': 0
        }

    def close(self):
        pass
